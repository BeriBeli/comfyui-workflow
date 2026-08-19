#!/usr/bin/env python3
"""Regression tests for the MiniMax H3 workflow policy validator."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("validate_workflows.py")
SPEC = importlib.util.spec_from_file_location("validate_workflows", MODULE_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import bootstrap guard
    raise RuntimeError(f"cannot load validator from {MODULE_PATH}")
validator = importlib.util.module_from_spec(SPEC)
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


if __name__ == "__main__":
    unittest.main()
