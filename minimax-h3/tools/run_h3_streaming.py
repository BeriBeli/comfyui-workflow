#!/usr/bin/env python3
"""Plan or execute an arbitrary-duration MiniMax H3 streaming chain.

The script injects one prompt per segment into the Init/Continue UI workflow
templates, runs only one segment at a time through comfy-mcp, persists paired
base/refined AV latent checkpoints, frees ComfyUI memory between segments, and
optionally assembles the accepted compressed segments without decoding video.
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
import math
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator


FPS = 24
RAW_FRAMES = 141
INIT_START = 10
INIT_CAPACITY = 131
CONTINUE_CAPACITY = 119
ROOT = Path(__file__).resolve().parents[1]
INIT_TEMPLATE = ROOT / "Minimax_H3_60s_Streaming_Init_RefineContext0.7MP_RTXVSR_1080p_12GB.json"
CONTINUE_TEMPLATE = ROOT / "Minimax_H3_60s_Streaming_Continue_RefineContext0.7MP_RTXVSR_1080p_12GB.json"
ASSEMBLER = Path(__file__).with_name("assemble_h3_streaming_video.py")


@dataclass(frozen=True)
class SegmentPlan:
    index: int
    kind: str
    accepted_frames: int
    crop_start: int
    prompt: str
    seed: int | None


def frame_plan(total_frames: int) -> list[int]:
    """Return exact accepted frame counts without increasing peak VRAM."""
    if total_frames <= 0:
        raise ValueError("target frame count must be positive")
    if total_frames <= INIT_CAPACITY:
        return [total_frames]
    result = [INIT_CAPACITY]
    remaining = total_frames - INIT_CAPACITY
    while remaining:
        accepted = min(CONTINUE_CAPACITY, remaining)
        result.append(accepted)
        remaining -= accepted
    return result


def target_frames(duration_seconds: float | None, frames: int | None, fps: int) -> int:
    if (duration_seconds is None) == (frames is None):
        raise ValueError("pass exactly one of --duration-seconds or --target-frames")
    if frames is not None:
        if frames <= 0:
            raise ValueError("--target-frames must be positive")
        return frames
    assert duration_seconds is not None
    if not math.isfinite(duration_seconds) or duration_seconds <= 0:
        raise ValueError("--duration-seconds must be finite and positive")
    return math.floor(duration_seconds * fps + 0.5)


def load_prompts(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("prompts") if isinstance(payload, dict) else payload
    if not isinstance(entries, list):
        raise ValueError("prompt JSON must be a list or an object with a 'prompts' list")
    result: list[dict[str, Any]] = []
    for index, entry in enumerate(entries, start=1):
        if isinstance(entry, str):
            result.append({"prompt": entry, "seed": None})
            continue
        if not isinstance(entry, dict) or not isinstance(entry.get("prompt"), str):
            raise ValueError(f"prompt entry {index} must be a string or {{'prompt': string}}")
        seed = entry.get("seed")
        if seed is not None and (not isinstance(seed, int) or isinstance(seed, bool)):
            raise ValueError(f"prompt entry {index} seed must be an integer")
        result.append({"prompt": entry["prompt"], "seed": seed})
    return result


def make_plan(counts: list[int], prompts: list[dict[str, Any]]) -> list[SegmentPlan]:
    if len(prompts) < len(counts):
        raise ValueError(f"need {len(counts)} segmented prompts, got {len(prompts)}")
    return [
        SegmentPlan(
            index=index,
            kind="init" if index == 1 else "continue",
            accepted_frames=count,
            crop_start=INIT_START if index == 1 else 0,
            prompt=prompts[index - 1]["prompt"],
            seed=prompts[index - 1]["seed"],
        )
        for index, count in enumerate(counts, start=1)
    ]


def only_node(workflow: dict[str, Any], predicate: Any, label: str) -> dict[str, Any]:
    matches = [node for node in workflow.get("nodes", []) if predicate(node)]
    if len(matches) != 1:
        raise ValueError(f"expected one {label} node, found {len(matches)}")
    return matches[0]


def iter_graph_nodes(graph: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Yield every node in a UI graph, including nested subgraph definitions."""
    for node in graph.get("nodes", []) or []:
        if isinstance(node, dict):
            yield node
    definitions = graph.get("definitions", {}) or {}
    for subgraph in definitions.get("subgraphs", []) or []:
        if isinstance(subgraph, dict):
            yield from iter_graph_nodes(subgraph)


def apply_prompt_inside_subgraphs(
    workflow: dict[str, Any], prompt: str, seed: int | None,
) -> None:
    """Write prompt/duration/seed onto the inner H3 nodes Comfy actually samples.

    The Init/Continue templates wrap MiniMax H3 in a subgraph. Patching only the
    wrapper ``widgets_values`` leaves the nested ``MiniMaxH3ImageToVideo``
    defaults in place; comfy-mcp then generates the template's baked-in scene.
    """
    duration = RAW_FRAMES / FPS
    for node in iter_graph_nodes(workflow):
        node_type = str(node.get("type", ""))
        widgets = node.get("widgets_values")
        if not isinstance(widgets, list) or not widgets:
            continue
        if node_type == "MiniMaxH3ImageToVideo":
            widgets[0] = prompt
            if len(widgets) >= 4 and isinstance(widgets[3], int):
                widgets[3] = RAW_FRAMES
        elif node_type == "PrimitiveFloat" and str(node.get("title", "")).startswith("Float (duration)"):
            widgets[0] = duration
        elif node_type == "RandomNoise" and seed is not None:
            widgets[0] = seed


def assert_h3_prompts_injected(workflow: dict[str, Any], prompt: str) -> None:
    nodes = [
        node for node in iter_graph_nodes(workflow)
        if node.get("type") == "MiniMaxH3ImageToVideo"
    ]
    if not nodes:
        raise ValueError("workflow has no MiniMaxH3ImageToVideo node to receive the prompt")
    mismatches = [
        node.get("id") for node in nodes
        if not isinstance(node.get("widgets_values"), list)
        or not node["widgets_values"]
        or node["widgets_values"][0] != prompt
    ]
    if mismatches:
        raise ValueError(
            "H3 prompt was not written into MiniMaxH3ImageToVideo nodes "
            f"{mismatches}; refusing to submit the template default scene"
        )


def configure_workflow(
    template: dict[str, Any], segment: SegmentPlan, run_id: str,
) -> tuple[dict[str, Any], dict[str, str]]:
    workflow = copy.deepcopy(template)
    is_init = segment.kind == "init"
    clip = only_node(
        workflow,
        lambda node: str(node.get("title", "")).startswith("Clip ")
        and len(node.get("widgets_values", [])) >= 5,
        "H3 clip",
    )
    clip["widgets_values"][0] = segment.prompt
    clip["widgets_values"][3] = RAW_FRAMES / FPS
    if segment.seed is not None:
        clip["widgets_values"][4] = segment.seed
    clip["title"] = (
        f"Clip {segment.index} · {'Initialize' if is_init else f'Load {segment.index - 1}'}"
        f" · Deliver {segment.accepted_frames}f"
    )
    apply_prompt_inside_subgraphs(workflow, segment.prompt, segment.seed)
    assert_h3_prompts_injected(workflow, segment.prompt)

    image_crop = only_node(
        workflow,
        lambda node: node.get("type") == "ImageFromBatch"
        and str(node.get("title", "")).startswith("Deliverable Crop"),
        "deliverable image crop",
    )
    audio_crop = only_node(
        workflow,
        lambda node: node.get("type") == "TrimAudioDuration"
        and str(node.get("title", "")).startswith("Deliverable Audio Crop"),
        "deliverable audio crop",
    )
    image_crop["widgets_values"] = [segment.crop_start, segment.accepted_frames]
    audio_crop["widgets_values"] = [segment.crop_start / FPS, segment.accepted_frames / FPS]

    checkpoint_root = f"h3_stream/{run_id}"
    for node in workflow.get("nodes", []):
        node_type = str(node.get("type", ""))
        title = str(node.get("title", ""))
        widgets = node.get("widgets_values", [])
        if node_type == "MiniMaxH3MotionContextLoadLatent":
            widgets[0] = f"{checkpoint_root}/{'refined' if 'Refined' in title else 'base'}"
            widgets[1] = segment.index - 1
        elif node_type == "MiniMaxH3MotionContextSaveLatent":
            widgets[0] = f"{checkpoint_root}/{'refined' if 'Refined' in title else 'base'}/clip"
            widgets[1] = segment.index

    prefixes = {
        "0.7mp": f"video/H3_{run_id}_S{segment.index:04d}_0.7MP",
        "1080p": f"video/H3_{run_id}_S{segment.index:04d}_1080p",
    }
    for node in workflow.get("nodes", []):
        title = str(node.get("title", ""))
        if title == "Save Candidate Segment · 0.7MP":
            node["widgets_values"][0] = prefixes["0.7mp"]
        elif title == "Save Candidate Segment · 1080p":
            node["widgets_values"][0] = prefixes["1080p"]
    workflow["name"] = f"MiniMax H3 Streaming · {run_id} · Segment {segment.index}"
    return workflow, prefixes


def snapshot_outputs(output_root: Path, prefix: str) -> set[Path]:
    relative = Path(prefix)
    folder = output_root / relative.parent
    return set(folder.glob(f"{relative.name}*")) if folder.is_dir() else set()


def newest_output(output_root: Path, prefix: str, before: set[Path]) -> Path:
    candidates = snapshot_outputs(output_root, prefix) - before
    videos = [path for path in candidates if path.suffix.lower() in {".mp4", ".webm", ".mov", ".mkv"}]
    if not videos:
        raise RuntimeError(f"ComfyUI finished but no new video matched output/{prefix}*")
    return max(videos, key=lambda path: path.stat().st_mtime_ns)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def server_is_running(info: dict[str, Any]) -> bool:
    """Read comfy-mcp ``server_info`` whether ``running`` is top-level or nested."""
    if info.get("running") is True:
        return True
    server = info.get("server")
    return isinstance(server, dict) and server.get("running") is True


def workspace_path(info: dict[str, Any]) -> Path:
    workspace = info.get("workspace")
    if isinstance(workspace, dict):
        return Path(workspace["path"])
    if workspace:
        return Path(workspace)
    raise RuntimeError("comfy-mcp server_info did not include a workspace path")


def load_comfy_mcp() -> Any:
    if not os.environ.get("COMFY_BIN"):
        sibling = Path(sys.executable).with_name("comfy.exe")
        if sibling.exists():
            os.environ["COMFY_BIN"] = str(sibling)
    try:
        import comfy_mcp.server as comfy_server
    except ImportError as exc:
        raise RuntimeError(
            "comfy_mcp is not importable. Run this script with the Python beside "
            "your attached comfy-mcp.exe, or install comfy-mcp in this environment."
        ) from exc
    return comfy_server


async def execute_plan(
    args: argparse.Namespace, plan: list[SegmentPlan], run_dir: Path, run_id: str,
) -> list[Path]:
    comfy = load_comfy_mcp()
    info = comfy.server_info()
    if not server_is_running(info) and args.launch_comfyui:
        await comfy.launch_comfyui()
        info = comfy.server_info()
    if not server_is_running(info):
        raise RuntimeError("ComfyUI is not running; start it or pass --launch-comfyui")

    workspace = workspace_path(info)
    output_root = workspace / "output"
    templates = {
        "init": json.loads(args.init_template.read_text(encoding="utf-8")),
        "continue": json.loads(args.continue_template.read_text(encoding="utf-8")),
    }
    state_path = run_dir / "state.json"
    accepted: list[Path] = []
    if args.resume and state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("run_id") != run_id:
            raise ValueError(f"resume run_id mismatch: {state.get('run_id')} != {run_id}")
        completed = state.get("segments", [])
        indexes = [item.get("index") for item in completed]
        if indexes != list(range(1, len(indexes) + 1)):
            raise ValueError(f"resume state is not a contiguous accepted prefix: {indexes}")
        for item in completed:
            output_path = Path(item["output"])
            if not output_path.is_file():
                raise FileNotFoundError(f"accepted segment is missing: {output_path}")
            expected = plan[item["index"] - 1]
            if item.get("accepted_frames") != expected.accepted_frames or item.get("prompt") != expected.prompt:
                raise ValueError(f"resume plan changed at segment {item['index']}")
            accepted.append(output_path)
    else:
        state = {
            "run_id": run_id,
            "status": "running",
            "segments": [],
            "comfy_workspace": str(workspace),
        }

    for segment in plan[len(accepted) :]:
        workflow, prefixes = configure_workflow(templates[segment.kind], segment, run_id)
        workflow_path = run_dir / "workflows" / f"segment_{segment.index:04d}.json"
        write_json(workflow_path, workflow)
        verdict = comfy.validate_workflow(str(workflow_path))
        if verdict.get("valid") is not True:
            write_json(run_dir / f"validation_{segment.index:04d}.json", verdict)
            raise RuntimeError(f"comfy-mcp rejected segment {segment.index}: {verdict}")

        prefix = prefixes[args.tier]
        before = snapshot_outputs(output_root, prefix)
        try:
            result = await comfy.run_workflow(
                str(workflow_path), wait=True, timeout_seconds=args.timeout_seconds,
            )
            output_path = newest_output(output_root, prefix, before)
            accepted.append(output_path)
            state["segments"].append(
                {
                    **asdict(segment),
                    "workflow": str(workflow_path),
                    "output": str(output_path),
                    "run_result": result,
                }
            )
            write_json(state_path, state)
        finally:
            comfy.free_memory(unload_models=True, free_memory=True)

    state["status"] = "generated"
    write_json(state_path, state)
    return accepted


def assemble(args: argparse.Namespace, run_dir: Path, paths: list[Path], counts: list[int]) -> Path:
    output = args.output or (run_dir / f"{run_dir.name}_{sum(counts)}f_{args.tier}.mp4")
    report = output.with_suffix(".report.json")
    command = [
        str(args.assembler_python or sys.executable), str(ASSEMBLER),
        "--output", str(output), "--report", str(report),
        "--fps", str(args.fps), "--crossfade-ms", str(args.crossfade_ms),
    ]
    for path, count in zip(paths, counts, strict=True):
        command.extend(("--segment", str(path), "--frames", str(count)))
    subprocess.run(command, check=True)
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--duration-seconds", type=float)
    target.add_argument("--target-frames", type=int)
    parser.add_argument("--prompts", type=Path, required=True)
    parser.add_argument("--fps", type=int, default=FPS, choices=[FPS])
    parser.add_argument("--init-template", type=Path, default=INIT_TEMPLATE)
    parser.add_argument("--continue-template", type=Path, default=CONTINUE_TEMPLATE)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument(
        "--resume", action="store_true",
        help="Resume the contiguous accepted prefix recorded in --run-dir/state.json.",
    )
    parser.add_argument("--execute", action="store_true", help="Actually submit segments through comfy-mcp")
    parser.add_argument("--launch-comfyui", action="store_true")
    parser.add_argument("--timeout-seconds", type=float, default=3600.0)
    parser.add_argument("--tier", choices=["0.7mp", "1080p"], default="0.7mp")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--assembler-python", type=Path)
    parser.add_argument("--crossfade-ms", type=float, default=100.0)
    parser.add_argument("--no-assemble", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    total = target_frames(args.duration_seconds, args.target_frames, args.fps)
    counts = frame_plan(total)
    prompts = load_prompts(args.prompts)
    plan = make_plan(counts, prompts)
    existing_plan = None
    if args.resume:
        if args.run_dir is None:
            raise ValueError("--resume requires --run-dir")
        existing_plan_path = args.run_dir / "plan.json"
        if not existing_plan_path.is_file():
            raise FileNotFoundError(existing_plan_path)
        existing_plan = json.loads(existing_plan_path.read_text(encoding="utf-8"))
    run_id = args.run_id or (existing_plan or {}).get("run_id") or datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = args.run_dir or (ROOT / "runs" / run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "run_id": run_id,
        "requested_duration_seconds": args.duration_seconds,
        "target_frames": total,
        "fps": args.fps,
        "actual_duration_seconds": total / args.fps,
        "segment_frames": counts,
        "peak_vram_scaling": "one 141-frame H3 segment at a time; independent of total duration",
        "segments": [asdict(item) for item in plan],
    }
    if existing_plan is not None:
        stable_keys = ("run_id", "target_frames", "fps", "segment_frames")
        changed = [key for key in stable_keys if existing_plan.get(key) != manifest.get(key)]
        if changed:
            raise ValueError(f"resume command changes existing plan fields: {changed}")
    write_json(run_dir / "plan.json", manifest)
    print(json.dumps({key: value for key, value in manifest.items() if key != "segments"}, ensure_ascii=False, indent=2))
    if not args.execute:
        print(f"Plan only: {run_dir / 'plan.json'}")
        return

    paths = asyncio.run(execute_plan(args, plan, run_dir, run_id))
    if not args.no_assemble:
        output = assemble(args, run_dir, paths, counts)
        print(f"Assembled: {output}")


if __name__ == "__main__":
    main()
