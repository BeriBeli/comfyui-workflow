#!/usr/bin/env python3
"""Static checks for the MiniMax H3 ComfyUI workflow JSON files.

The checker intentionally uses only the Python standard library so it can run
locally and in GitHub Actions without installing ComfyUI or custom nodes.
It does not prove that a workflow will render successfully; it catches common
serialization and continuity-pipeline mistakes before a workflow is published.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

SEVERITY_ORDER = {"INFO": 0, "WARN": 1, "ERROR": 2}
LATENT_MP_RE = re.compile(r"Latent(?P<mp>\d+(?:\.\d+)?)MP", re.IGNORECASE)
SEGMENT_RE = re.compile(r"Segment\s*(?P<index>[123])", re.IGNORECASE)
FRAME_COUNT_RE = re.compile(r"(?P<frames>\d+)\s*Frames?", re.IGNORECASE)

# Auxiliary JSON must be explicitly identified. Never infer that a JSON file is
# auxiliary merely because its ``nodes`` array is missing: that would also hide
# an accidentally emptied or damaged workflow export from CI.
AUXILIARY_JSON_SUFFIXES = frozenset({("ci", "object_info.json")})


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    path: Path
    scope: str
    message: str

    def render(self, root: Path | None = None) -> str:
        path = self.path
        if root is not None:
            try:
                path = path.relative_to(root)
            except ValueError:
                pass
        return f"[{self.severity}] {path} :: {self.scope} :: {self.code} :: {self.message}"


@dataclass(frozen=True)
class NodeRef:
    scope: str
    node: dict[str, Any]
    links: Sequence[Any]


class WorkflowValidator:
    def __init__(self, path: Path, document: dict[str, Any]) -> None:
        self.path = path
        self.document = document
        self.findings: list[Finding] = []

    def add(self, severity: str, code: str, scope: str, message: str) -> None:
        self.findings.append(Finding(severity, code, self.path, scope, message))

    def validate(self) -> list[Finding]:
        if not isinstance(self.document.get("nodes"), list):
            self.add("ERROR", "NOT_WORKFLOW", "root", "JSON object has no top-level nodes array")
            return self.findings

        self._check_link_integrity()
        self._check_refine_schedulers()
        self._check_latent_megapixels()

        if self._looks_like_continuity_workflow():
            self._check_continuity_prompts()
            self._check_boundary_pipeline()
            self._check_audio_pipeline()

        if not any(f.severity == "ERROR" for f in self.findings):
            self.add("INFO", "PARSE_OK", "root", "workflow JSON parsed and static checks completed")
        return self.findings

    def _walk_scopes(self) -> Iterator[tuple[str, list[dict[str, Any]], Sequence[Any]]]:
        yield "root", self.document.get("nodes", []), self.document.get("links", [])
        definitions = self.document.get("definitions", {})
        for index, subgraph in enumerate(definitions.get("subgraphs", []) or []):
            name = subgraph.get("name") or subgraph.get("id") or str(index)
            scope = f"subgraph:{name}"
            yield scope, subgraph.get("nodes", []) or [], subgraph.get("links", []) or []

    def _iter_nodes(self) -> Iterator[NodeRef]:
        for scope, nodes, links in self._walk_scopes():
            for node in nodes:
                if isinstance(node, dict):
                    yield NodeRef(scope, node, links)

    @staticmethod
    def _normalise_link(raw: Any) -> tuple[Any, Any, Any, Any, Any] | None:
        if isinstance(raw, list) and len(raw) >= 5:
            return raw[0], raw[1], raw[2], raw[3], raw[4]
        if isinstance(raw, dict):
            return (
                raw.get("id"),
                raw.get("origin_id"),
                raw.get("origin_slot"),
                raw.get("target_id"),
                raw.get("target_slot"),
            )
        return None

    def _check_link_integrity(self) -> None:
        for scope, nodes, raw_links in self._walk_scopes():
            links: dict[Any, tuple[Any, Any, Any, Any, Any]] = {}
            for raw in raw_links:
                link = self._normalise_link(raw)
                if link is None:
                    self.add("WARN", "UNKNOWN_LINK_FORMAT", scope, f"cannot interpret link record: {raw!r}")
                    continue
                link_id = link[0]
                if link_id in links:
                    self.add("WARN", "DUPLICATE_LINK_ID", scope, f"link id {link_id!r} occurs more than once")
                links[link_id] = link

            for node in nodes:
                node_id = node.get("id")
                title = node.get("title") or node.get("type") or f"node {node_id}"
                for input_index, input_spec in enumerate(node.get("inputs", []) or []):
                    link_id = input_spec.get("link") if isinstance(input_spec, dict) else None
                    if link_id is None:
                        continue
                    link = links.get(link_id)
                    if link is None:
                        self.add(
                            "WARN",
                            "DANGLING_INPUT_LINK",
                            scope,
                            f"{title}: input {input_index} references missing link id {link_id}",
                        )
                        continue
                    _, _, _, target_id, target_slot = link
                    if target_id != node_id or target_slot != input_index:
                        self.add(
                            "WARN",
                            "LINK_TARGET_MISMATCH",
                            scope,
                            (
                                f"{title}: input {input_index} records link {link_id}, but that link targets "
                                f"node {target_id} input {target_slot}; this is often stale widget-link metadata"
                            ),
                        )

                for output_index, output_spec in enumerate(node.get("outputs", []) or []):
                    output_links = output_spec.get("links") if isinstance(output_spec, dict) else None
                    if not output_links:
                        continue
                    for link_id in output_links:
                        link = links.get(link_id)
                        if link is None:
                            self.add(
                                "WARN",
                                "DANGLING_OUTPUT_LINK",
                                scope,
                                f"{title}: output {output_index} references missing link id {link_id}",
                            )
                            continue
                        _, origin_id, origin_slot, _, _ = link
                        if origin_id != node_id or origin_slot != output_index:
                            self.add(
                                "WARN",
                                "LINK_ORIGIN_MISMATCH",
                                scope,
                                (
                                    f"{title}: output {output_index} records link {link_id}, but that link originates "
                                    f"from node {origin_id} output {origin_slot}"
                                ),
                            )

    @staticmethod
    def _widget_triplet(node: dict[str, Any]) -> tuple[str | None, float | None, float | None]:
        values = node.get("widgets_values")
        if isinstance(values, list) and len(values) >= 3:
            scheduler = values[0] if isinstance(values[0], str) else None
            steps = float(values[1]) if isinstance(values[1], (int, float)) else None
            denoise = float(values[2]) if isinstance(values[2], (int, float)) else None
            return scheduler, steps, denoise
        if isinstance(values, dict):
            scheduler = values.get("scheduler")
            steps = values.get("steps")
            denoise = values.get("denoise")
            return (
                scheduler if isinstance(scheduler, str) else None,
                float(steps) if isinstance(steps, (int, float)) else None,
                float(denoise) if isinstance(denoise, (int, float)) else None,
            )
        return None, None, None

    @staticmethod
    def _input_link(node: dict[str, Any], name: str) -> Any:
        for input_spec in node.get("inputs", []) or []:
            if isinstance(input_spec, dict) and input_spec.get("name") == name:
                return input_spec.get("link")
        return None

    def _check_refine_schedulers(self) -> None:
        for ref in self._iter_nodes():
            node = ref.node
            if node.get("type") != "BasicScheduler":
                continue
            _, steps, denoise = self._widget_triplet(node)
            if steps is None or denoise is None:
                continue
            if math.isclose(steps, 6.0) and math.isclose(denoise, 0.30, abs_tol=1e-6):
                link_id = self._input_link(node, "steps")
                title = node.get("title") or f"BasicScheduler {node.get('id')}"
                if link_id is not None:
                    self.add(
                        "WARN",
                        "REFINE_STEPS_LINKED",
                        ref.scope,
                        (
                            f"{title}: the 6-step refine scheduler still has steps link {link_id}; "
                            "disconnect and re-save it so the visible value cannot be overridden"
                        ),
                    )

    @staticmethod
    def _latent_mp_values(node: dict[str, Any]) -> tuple[float | None, float | None]:
        positional: float | None = None
        named: float | None = None
        values = node.get("widgets_values")
        if isinstance(values, list) and len(values) >= 2 and isinstance(values[1], (int, float)):
            positional = float(values[1])
        named_values = node.get("widgets_values_named")
        if isinstance(named_values, dict) and isinstance(named_values.get("target_megapixels"), (int, float)):
            named = float(named_values["target_megapixels"])
        return positional, named

    def _check_latent_megapixels(self) -> None:
        filename_match = LATENT_MP_RE.search(self.path.name)
        filename_mp = float(filename_match.group("mp")) if filename_match else None
        observed: list[float] = []

        for ref in self._iter_nodes():
            node = ref.node
            if node.get("type") != "H3LatentUpscalerNodeMegapixels":
                continue
            positional, named = self._latent_mp_values(node)
            title = node.get("title") or f"H3LatentUpscaler {node.get('id')}"
            if positional is not None:
                observed.append(positional)
            if named is not None:
                observed.append(named)
            if positional is not None and named is not None and not math.isclose(positional, named, abs_tol=1e-9):
                self.add(
                    "WARN",
                    "MP_SERIALIZATION_MISMATCH",
                    ref.scope,
                    (
                        f"{title}: widgets_values says {positional:g}MP but widgets_values_named says {named:g}MP; "
                        "re-enter the value in ComfyUI and export again"
                    ),
                )

        if filename_mp is not None and observed:
            unique = sorted({round(value, 6) for value in observed})
            if not all(math.isclose(filename_mp, value, abs_tol=1e-9) for value in unique):
                self.add(
                    "WARN",
                    "MP_FILENAME_MISMATCH",
                    "root",
                    (
                        f"file name advertises {filename_mp:g}MP, while serialized latent targets are {unique}; "
                        "align file name, workflow info, node value and README"
                    ),
                )

    def _looks_like_continuity_workflow(self) -> bool:
        text = self.path.name.lower()
        info = self.document.get("extra", {}).get("info", {})
        if isinstance(info, dict):
            text += " " + str(info.get("name", "")).lower()
        return "continuous" in text or "3x5" in text or "3×5" in text

    @staticmethod
    def _first_prompt(node: dict[str, Any]) -> str:
        values = node.get("widgets_values")
        if isinstance(values, list) and values and isinstance(values[0], str):
            return values[0]
        if isinstance(values, dict):
            prompt = values.get("prompt")
            return prompt if isinstance(prompt, str) else ""
        return ""

    def _check_continuity_prompts(self) -> None:
        segments: dict[int, tuple[str, str]] = {}
        for ref in self._iter_nodes():
            node = ref.node
            title = str(node.get("title", ""))
            match = SEGMENT_RE.search(title)
            if not match:
                continue
            index = int(match.group("index"))
            prompt = self._first_prompt(node)
            if prompt:
                segments.setdefault(index, (ref.scope, prompt))

        for index in (2, 3):
            item = segments.get(index)
            if item is None:
                self.add("WARN", "MISSING_SEGMENT_PROMPT", "root", f"could not locate Segment {index} prompt")
                continue
            scope, prompt = item
            lowered = prompt.lower()
            if "<picture 1>" not in lowered:
                self.add(
                    "WARN",
                    "MISSING_FIRST_FRAME_REFERENCE",
                    scope,
                    f"Segment {index} prompt does not explicitly reference <Picture 1>",
                )
            continuity_terms = ("without a reset", "direct continuation", "continues", "continue naturally")
            if not any(term in lowered for term in continuity_terms):
                self.add(
                    "WARN",
                    "MISSING_CONTINUATION_LANGUAGE",
                    scope,
                    f"Segment {index} prompt does not explicitly say that motion continues without a reset",
                )
            anchors = ("identity", "clothing", "lighting", "camera", "spatial")
            present = sum(term in lowered for term in anchors)
            if present < 3:
                self.add(
                    "WARN",
                    "WEAK_CONTINUITY_ANCHOR",
                    scope,
                    (
                        f"Segment {index} prompt only contains {present}/5 common continuity anchors; "
                        "keep identity, clothing, lighting, camera axis and spatial relationships stable"
                    ),
                )

    @staticmethod
    def _numeric_widgets(node: dict[str, Any]) -> list[float]:
        values = node.get("widgets_values")
        if not isinstance(values, list):
            return []
        return [float(value) for value in values if isinstance(value, (int, float))]

    def _check_boundary_pipeline(self) -> None:
        rife_nodes: list[NodeRef] = []
        kept_transition_frames: list[int] = []
        kept_segment_frames: list[int] = []
        advertised_total: int | None = None

        for ref in self._iter_nodes():
            node = ref.node
            node_type = str(node.get("type", ""))
            title = str(node.get("title", ""))
            if node_type == "FrameInterpolate":
                rife_nodes.append(ref)
                numeric = self._numeric_widgets(node)
                if not numeric or int(numeric[0]) != 5:
                    self.add(
                        "WARN",
                        "UNEXPECTED_RIFE_MULTIPLIER",
                        ref.scope,
                        f"{title or node_type}: expected multiplier 5 for four interior frames, got {numeric[:1]}",
                    )
            if node_type == "ImageFromBatch":
                values = self._numeric_widgets(node)
                if len(values) >= 2:
                    length = int(values[1])
                    if "Intermediate Frames" in title:
                        kept_transition_frames.append(length)
                        if int(values[0]) != 1 or length != 4:
                            self.add(
                                "WARN",
                                "UNEXPECTED_TRANSITION_SLICE",
                                ref.scope,
                                f"{title}: expected batch_index=1 and length=4, got {values[:2]}",
                            )
                    elif "Keep Frames" in title:
                        kept_segment_frames.append(length)
            total_match = FRAME_COUNT_RE.search(title)
            if total_match and "Add Segment 3" in title:
                advertised_total = int(total_match.group("frames"))

        if not rife_nodes:
            self.add("WARN", "NO_RIFE_BRANCH", "root", "continuity workflow has no RIFE interpolation branch")
        elif len(rife_nodes) != 2:
            self.add("WARN", "RIFE_BOUNDARY_COUNT", "root", f"expected 2 RIFE boundaries, found {len(rife_nodes)}")

        if kept_segment_frames and kept_transition_frames:
            computed_total = sum(kept_segment_frames) + sum(kept_transition_frames)
            if advertised_total is not None and computed_total != advertised_total:
                self.add(
                    "ERROR",
                    "FRAME_TOTAL_MISMATCH",
                    "root",
                    (
                        f"segment/transition slices total {computed_total} frames, but the final node advertises "
                        f"{advertised_total} frames"
                    ),
                )
            else:
                self.add(
                    "INFO",
                    "FRAME_TOTAL",
                    "root",
                    f"computed stitched length is {computed_total} frames",
                )

        self.add(
            "INFO",
            "RIFE_SCOPE",
            "root",
            "RIFE can smooth small motion gaps; identity, composition or scene jumps should trigger a local retake instead",
        )

    def _check_audio_pipeline(self) -> None:
        trim_nodes: list[NodeRef] = []
        has_concat = False
        has_crossfade = False

        for ref in self._iter_nodes():
            node_type = str(ref.node.get("type", ""))
            if node_type == "TrimAudioDuration":
                trim_nodes.append(ref)
                values = self._numeric_widgets(ref.node)
                if len(values) >= 2:
                    expected = 1.0 / 24.0
                    if not math.isclose(values[0], expected, abs_tol=0.01):
                        self.add(
                            "WARN",
                            "AUDIO_BOUNDARY_TRIM",
                            ref.scope,
                            (
                                f"{ref.node.get('title') or node_type}: start trim {values[0]:.4f}s differs from "
                                f"one 24fps frame ({expected:.4f}s)"
                            ),
                        )
            if node_type == "AudioConcat":
                has_concat = True
            if "crossfade" in node_type.lower() or "crossfade" in str(ref.node.get("title", "")).lower():
                has_crossfade = True

        if has_concat and not has_crossfade:
            self.add(
                "WARN",
                "HARD_AUDIO_CONCAT",
                "root",
                (
                    "audio segments are trimmed and concatenated without a crossfade; use an 80-150ms "
                    "equal-power crossfade for ambience/music boundaries when a compatible node is available"
                ),
            )
        if len(trim_nodes) not in (0, 2):
            self.add("WARN", "AUDIO_TRIM_COUNT", "root", f"expected 2 boundary audio trims, found {len(trim_nodes)}")


def discover_files(inputs: Sequence[Path]) -> list[Path]:
    files: list[Path] = []
    for input_path in inputs:
        if input_path.is_file():
            files.append(input_path)
        elif input_path.is_dir():
            files.extend(sorted(input_path.glob("*.json")))
        else:
            raise FileNotFoundError(input_path)
    return sorted(dict.fromkeys(path.resolve() for path in files))


def load_workflow(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        document = json.load(handle)
    if not isinstance(document, dict):
        raise ValueError("top-level JSON value must be an object")
    return document


def is_known_auxiliary_json(path: Path) -> bool:
    """Return whether ``path`` is an explicitly supported non-workflow JSON."""

    parts = path.parts
    return len(parts) >= 2 and tuple(parts[-2:]) in AUXILIARY_JSON_SUFFIXES


def validate_paths(paths: Iterable[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        try:
            document = load_workflow(path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            findings.append(Finding("ERROR", "JSON_LOAD_FAILED", path, "root", str(exc)))
            continue
        if is_known_auxiliary_json(path):
            findings.append(
                Finding("INFO", "SKIPPED_AUXILIARY_JSON", path, "root", "explicitly allowed object_info snapshot")
            )
            continue
        findings.extend(WorkflowValidator(path, document).validate())
    return findings


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path(__file__).resolve().parents[1]],
        help="workflow JSON file or directory (default: minimax-h3 directory)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="return a non-zero status for warnings as well as errors",
    )
    parser.add_argument(
        "--quiet-info",
        action="store_true",
        help="hide informational findings",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    try:
        files = discover_files(args.paths)
    except FileNotFoundError as exc:
        print(f"[ERROR] path not found: {exc}", file=sys.stderr)
        return 2

    if not files:
        print("[ERROR] no JSON files found", file=sys.stderr)
        return 2

    common_root = Path(os.path.commonpath([str(path.parent) for path in files]))
    findings = validate_paths(files)
    visible = [f for f in findings if not args.quiet_info or f.severity != "INFO"]
    for finding in sorted(visible, key=lambda item: (str(item.path), SEVERITY_ORDER[item.severity], item.code)):
        print(finding.render(common_root))

    errors = sum(f.severity == "ERROR" for f in findings)
    warnings = sum(f.severity == "WARN" for f in findings)
    infos = sum(f.severity == "INFO" for f in findings)
    print(f"Checked {len(files)} JSON file(s): {errors} error(s), {warnings} warning(s), {infos} info message(s).")

    if errors:
        return 1
    if args.strict and warnings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
