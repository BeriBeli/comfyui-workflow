#!/usr/bin/env python3
"""Regression tests for the MiniMax H3 workflow policy validator."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("validate_workflows.py")
SPEC = importlib.util.spec_from_file_location("validate_workflows", MODULE_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import bootstrap guard
    raise RuntimeError(f"cannot load validator from {MODULE_PATH}")
validator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validator
SPEC.loader.exec_module(validator)


class ValidateWorkflowPathsTests(unittest.TestCase):
    def _validate_document(self, document: object, relative_path: str = "workflow.json"):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(document), encoding="utf-8")
            return validator.validate_paths([path])

    def test_missing_nodes_is_an_error(self) -> None:
        findings = self._validate_document({"links": []})

        self.assertTrue(
            any(f.severity == "ERROR" and f.code == "NOT_WORKFLOW" for f in findings),
            findings,
        )

    def test_null_nodes_is_an_error(self) -> None:
        findings = self._validate_document({"nodes": None, "links": []})

        self.assertTrue(
            any(f.severity == "ERROR" and f.code == "NOT_WORKFLOW" for f in findings),
            findings,
        )

    def test_valid_workflow_is_not_skipped(self) -> None:
        findings = self._validate_document({"nodes": [], "links": []})

        self.assertTrue(any(f.code == "PARSE_OK" for f in findings), findings)
        self.assertFalse(any(f.code.startswith("SKIPPED_") for f in findings), findings)

    def test_known_object_info_snapshot_is_explicitly_skipped(self) -> None:
        findings = self._validate_document({}, "ci/object_info.json")

        self.assertEqual([f.code for f in findings], ["SKIPPED_AUXILIARY_JSON"])
        self.assertEqual(findings[0].severity, "INFO")

    def test_streaming_workflows_satisfy_memory_contract(self) -> None:
        workflow_root = MODULE_PATH.parent.parent
        paths = [
            workflow_root / "Minimax_H3_60s_Streaming_Init_RefineContext0.7MP_RTXVSR_1080p_12GB.json",
            workflow_root / "Minimax_H3_60s_Streaming_Continue_RefineContext0.7MP_RTXVSR_1080p_12GB.json",
        ]
        findings = validator.validate_paths(paths)

        self.assertFalse(
            any(f.severity in ("WARN", "ERROR") for f in findings),
            [f.render() for f in findings],
        )
        self.assertEqual(
            sum(f.code == "STREAMING_MEMORY_SCOPE" for f in findings),
            2,
            [f.render() for f in findings],
        )

    def test_all_published_workflows_are_strict_clean(self) -> None:
        workflow_root = MODULE_PATH.parent.parent
        findings = validator.validate_paths(sorted(workflow_root.glob("*.json")))

        self.assertFalse(
            any(f.severity in ("WARN", "ERROR") for f in findings),
            [f.render() for f in findings],
        )


if __name__ == "__main__":
    unittest.main()
