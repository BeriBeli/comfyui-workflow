#!/usr/bin/env python3
"""Unit tests for arbitrary-duration H3 streaming planning/injection."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("run_h3_streaming.py")
SPEC = importlib.util.spec_from_file_location("run_h3_streaming", MODULE_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load runner from {MODULE_PATH}")
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


class StreamingRunnerTests(unittest.TestCase):
    def test_exact_sixty_seconds(self) -> None:
        self.assertEqual(runner.frame_plan(1440), [131] + [119] * 11)

    def test_partial_final_segment(self) -> None:
        self.assertEqual(runner.frame_plan(888), [131] + [119] * 6 + [43])

    def test_shorter_than_first_capacity(self) -> None:
        self.assertEqual(runner.frame_plan(120), [120])

    def test_workflow_injection_sets_indices_prompt_and_crop(self) -> None:
        runner_template = json.loads(runner.CONTINUE_TEMPLATE.read_text(encoding="utf-8"))
        segment = runner.SegmentPlan(4, "continue", 43, 0, "segmented prompt", 12345)
        workflow, prefixes = runner.configure_workflow(runner_template, segment, "unit")
        clip = runner.only_node(
            workflow,
            lambda node: str(node.get("title", "")).startswith("Clip 4"),
            "clip",
        )
        self.assertEqual(clip["widgets_values"][0], "segmented prompt")
        self.assertEqual(clip["widgets_values"][4], 12345)
        crop = runner.only_node(
            workflow,
            lambda node: node.get("type") == "ImageFromBatch"
            and str(node.get("title", "")).startswith("Deliverable Crop"),
            "crop",
        )
        self.assertEqual(crop["widgets_values"], [0, 43])
        loads = [node for node in workflow["nodes"] if str(node.get("type", "")).endswith("LoadLatent")]
        saves = [node for node in workflow["nodes"] if str(node.get("type", "")).endswith("SaveLatent")]
        self.assertEqual({node["widgets_values"][1] for node in loads}, {3})
        self.assertEqual({node["widgets_values"][1] for node in saves}, {4})
        self.assertIn("S0004", prefixes["0.7mp"])

    def test_workflow_injection_overwrites_nested_h3_prompt(self) -> None:
        prompt = "neutral segmented prompt for subgraph injection"
        for template_path in (runner.INIT_TEMPLATE, runner.CONTINUE_TEMPLATE):
            template = json.loads(template_path.read_text(encoding="utf-8"))
            kind = "init" if template_path == runner.INIT_TEMPLATE else "continue"
            segment = runner.SegmentPlan(1 if kind == "init" else 2, kind, 119, 0, prompt, 12345)
            workflow, _ = runner.configure_workflow(template, segment, "unit")
            h3_nodes = [
                node for node in runner.iter_graph_nodes(workflow)
                if node.get("type") == "MiniMaxH3ImageToVideo"
            ]
            self.assertGreaterEqual(len(h3_nodes), 1, template_path.name)
            for node in h3_nodes:
                widgets = node["widgets_values"]
                self.assertEqual(widgets[0], prompt, template_path.name)
                self.assertEqual(widgets[3], runner.RAW_FRAMES, template_path.name)
                self.assertNotIn("Miyazaki", widgets[0])
                self.assertNotIn("forest spirit", widgets[0])
            durations = [
                node["widgets_values"][0]
                for node in runner.iter_graph_nodes(workflow)
                if node.get("type") == "PrimitiveFloat"
                and str(node.get("title", "")).startswith("Float (duration)")
            ]
            self.assertTrue(durations, template_path.name)
            self.assertTrue(all(value == 5.875 for value in durations), durations)
            seeds = [
                node["widgets_values"][0]
                for node in runner.iter_graph_nodes(workflow)
                if node.get("type") == "RandomNoise"
            ]
            self.assertTrue(seeds, template_path.name)
            self.assertTrue(all(value == 12345 for value in seeds), seeds)

    def test_server_info_nested_running_flag(self) -> None:
        nested = {
            "server": {"running": True, "url": "http://127.0.0.1:8188"},
            "workspace": {"path": "C:/ComfyUI", "type": "default"},
        }
        self.assertTrue(runner.server_is_running(nested))
        self.assertEqual(runner.workspace_path(nested), Path("C:/ComfyUI"))
        self.assertFalse(runner.server_is_running({"server": {"running": False}}))
        self.assertTrue(runner.server_is_running({"running": True}))


if __name__ == "__main__":
    unittest.main()
