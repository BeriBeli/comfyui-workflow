#!/usr/bin/env python3
"""Run the official comfy-cli workflow validator from Python.

This wrapper deliberately invokes ``python -m comfy_cli`` instead of importing
private comfy-cli or comfy-mcp implementation modules. The CLI's structured
JSON envelope is the compatibility boundary.

A validation run needs either:

* ``--object-info``: a pinned ``/object_info`` JSON snapshot for reproducible,
  offline CI; or
* a running ComfyUI reachable through ``--host`` / ``--port``.

Repository-specific policy checks (frame arithmetic, RIFE policy, latent-MP
naming, prompt anchors, and audio stitching) remain in
``validate_workflows.py`` because ComfyUI's schema cannot express them.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


@dataclass(frozen=True)
class ValidationResult:
    path: Path
    valid: bool
    errors: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    converted_from_ui: bool
    object_info_source: str | None


def _workflow_files(paths: Iterable[Path]) -> list[Path]:
    files: set[Path] = set()
    for path in paths:
        path = path.expanduser()
        if path.is_file():
            if path.suffix.lower() == ".json":
                files.add(path.resolve())
            continue
        if path.is_dir():
            # Workflow exports live directly under minimax-h3. Avoid treating a
            # committed object_info snapshot or unrelated fixtures as workflows.
            for candidate in path.glob("*.json"):
                if candidate.is_file():
                    files.add(candidate.resolve())
            continue
        raise FileNotFoundError(path)
    return sorted(files)


def _last_json_object(text: str) -> dict[str, Any] | None:
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def _format_findings(items: Sequence[dict[str, Any]]) -> list[str]:
    rendered: list[str] = []
    for item in items:
        code = item.get("code") or "unknown"
        node = item.get("node_id") or item.get("node") or "?"
        field = item.get("field")
        message = item.get("message") or str(item)
        location = f"node {node}"
        if field:
            location += f" / {field}"
        rendered.append(f"{code}: {location}: {message}")
    return rendered


def _run_one(
    workflow: Path,
    *,
    object_info: Path | None,
    host: str,
    port: int,
    timeout: int,
) -> ValidationResult:
    command = [
        sys.executable,
        "-m",
        "comfy_cli",
        "--json",
        "--where",
        "local",
        "validate",
        "--workflow",
        str(workflow),
    ]
    if object_info is not None:
        command.extend(["--input", str(object_info)])
    else:
        command.extend(["--host", host, "--port", str(port)])

    env = os.environ.copy()
    env.setdefault("DO_NOT_TRACK", "1")
    env.setdefault("COMFY_NO_TELEMETRY", "1")
    env.setdefault("COMFY_WHERE", "local")

    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    envelope = _last_json_object(completed.stdout)
    if envelope is None:
        details = completed.stderr.strip() or completed.stdout.strip() or "no output"
        raise RuntimeError(f"comfy-cli returned no JSON envelope for {workflow}: {details}")

    data = envelope.get("data")
    error = envelope.get("error")
    if not isinstance(data, dict):
        message = error.get("message") if isinstance(error, dict) else None
        code = error.get("code") if isinstance(error, dict) else None
        details = completed.stderr.strip()
        raise RuntimeError(
            f"comfy-cli could not produce a validation verdict for {workflow}: "
            f"{code or 'unknown_error'}: {message or details or envelope}"
        )

    valid = data.get("valid")
    if not isinstance(valid, bool):
        raise RuntimeError(f"comfy-cli response for {workflow} has no boolean data.valid: {envelope}")

    errors = data.get("errors") if isinstance(data.get("errors"), list) else []
    warnings = data.get("warnings") if isinstance(data.get("warnings"), list) else []

    # comfy validate intentionally exits non-zero for valid:false. Conversely,
    # a zero exit without a truthful boolean verdict must never be treated as a
    # pass; the checks above fail closed.
    if completed.returncode == 0 and not valid:
        raise RuntimeError(f"comfy-cli returned exit 0 with valid:false for {workflow}")
    if completed.returncode != 0 and valid:
        details = completed.stderr.strip()
        raise RuntimeError(
            f"comfy-cli returned exit {completed.returncode} with valid:true for {workflow}: {details}"
        )

    return ValidationResult(
        path=workflow,
        valid=valid,
        errors=[item for item in errors if isinstance(item, dict)],
        warnings=[item for item in warnings if isinstance(item, dict)],
        converted_from_ui=data.get("converted_from_ui") is True,
        object_info_source=(
            str(data.get("object_info_source")) if data.get("object_info_source") is not None else None
        ),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Workflow JSON file(s), or directories whose top-level *.json files are workflows.",
    )
    parser.add_argument(
        "--object-info",
        type=Path,
        help="Pinned /object_info JSON snapshot. When omitted, validate against a live ComfyUI.",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("COMFY_VALIDATE_HOST") or "127.0.0.1",
        help="Live ComfyUI host (default: COMFY_VALIDATE_HOST or 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("COMFY_VALIDATE_PORT") or "8188"),
        help="Live ComfyUI port (default: COMFY_VALIDATE_PORT or 8188).",
    )
    parser.add_argument("--timeout", type=int, default=120, help="Per-workflow comfy-cli timeout in seconds.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if importlib.util.find_spec("comfy_cli") is None:
        print(
            "error: comfy-cli is not installed; install the CI-pinned version before running this wrapper",
            file=sys.stderr,
        )
        return 2

    object_info: Path | None = args.object_info
    if object_info is not None:
        object_info = object_info.expanduser().resolve()
        if not object_info.is_file():
            print(f"error: object_info snapshot not found: {object_info}", file=sys.stderr)
            return 2

    try:
        workflows = _workflow_files(args.paths)
    except FileNotFoundError as exc:
        print(f"error: path not found: {exc.args[0]}", file=sys.stderr)
        return 2

    if not workflows:
        print("error: no workflow JSON files found", file=sys.stderr)
        return 2

    failed = 0
    for workflow in workflows:
        try:
            result = _run_one(
                workflow,
                object_info=object_info,
                host=args.host,
                port=args.port,
                timeout=args.timeout,
            )
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            failed += 1
            print(f"[ERROR] {workflow}: {exc}", file=sys.stderr)
            continue

        source = result.object_info_source or (str(object_info) if object_info is not None else f"{args.host}:{args.port}")
        mode = "UI→API" if result.converted_from_ui else "API"
        status = "PASS" if result.valid else "FAIL"
        print(f"[{status}] {workflow} ({mode}, object_info={source})")
        for warning in _format_findings(result.warnings):
            print(f"  warning: {warning}")
        for error in _format_findings(result.errors):
            print(f"  error: {error}")
        if not result.valid:
            failed += 1

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
