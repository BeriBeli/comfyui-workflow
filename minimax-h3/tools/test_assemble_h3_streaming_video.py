#!/usr/bin/env python3
"""Integration test for the 60-second packet-streaming assembler."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import math
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

import av
import numpy as np


MODULE_PATH = Path(__file__).with_name("assemble_h3_streaming_video.py")
SPEC = importlib.util.spec_from_file_location("assemble_h3_streaming_video", MODULE_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load assembler from {MODULE_PATH}")
assembler = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = assembler
SPEC.loader.exec_module(assembler)


def packet_seconds(packet: av.Packet) -> Fraction:
    if packet.dts is None or packet.time_base is None:
        return Fraction(10**9)
    return Fraction(packet.dts) * Fraction(packet.time_base)


def make_segment(path: Path, frame_count: int, clip_index: int) -> None:
    sample_rate = 48_000
    sample_count = round(frame_count / 24 * sample_rate)
    time = np.arange(sample_count, dtype=np.float32) / sample_rate
    tone = (0.05 * np.sin(2 * math.pi * (220 + clip_index * 10) * time)).astype(np.float32)
    waveform = np.stack((tone, tone))

    with av.open(str(path), "w") as output:
        video = output.add_stream("mpeg4", rate=24)
        video.width = 64
        video.height = 64
        video.pix_fmt = "yuv420p"
        audio = output.add_stream("aac", rate=sample_rate)
        audio.layout = "stereo"
        packets: list[av.Packet] = []

        for index in range(frame_count):
            pixels = np.empty((64, 64, 3), dtype=np.uint8)
            pixels[:, :, 0] = (clip_index * 19) % 255
            pixels[:, :, 1] = (index * 3) % 255
            pixels[:, :, 2] = 80
            frame = av.VideoFrame.from_ndarray(pixels, format="rgb24")
            frame.pts = index
            frame.time_base = Fraction(1, 24)
            packets.extend(video.encode(frame))
        packets.extend(video.encode(None))

        for start in range(0, sample_count, 1024):
            frame = av.AudioFrame.from_ndarray(waveform[:, start : start + 1024], format="fltp", layout="stereo")
            frame.sample_rate = sample_rate
            frame.pts = start
            frame.time_base = Fraction(1, sample_rate)
            packets.extend(audio.encode(frame))
        packets.extend(audio.encode(None))

        for packet in sorted(packets, key=lambda item: (packet_seconds(item), item.stream.index)):
            output.mux(packet)


class StreamingAssemblerTests(unittest.TestCase):
    def run_assembler(self, root: Path, frame_counts: list[int]) -> tuple[Path, dict]:
        segments = []
        for index, frame_count in enumerate(frame_counts, start=1):
            path = root / f"segment-{index:02d}.mp4"
            make_segment(path, frame_count, index)
            segments.append(path)

        output = root / "assembled.mp4"
        report = root / "assembled.report.json"
        old_argv = sys.argv
        try:
            sys.argv = [str(MODULE_PATH)]
            for path, frame_count in zip(segments, frame_counts, strict=True):
                sys.argv.extend(("--segment", str(path), "--frames", str(frame_count)))
            sys.argv.extend(("--output", str(output), "--report", str(report)))
            with contextlib.redirect_stdout(io.StringIO()):
                assembler.main()
        finally:
            sys.argv = old_argv
        return output, json.loads(report.read_text(encoding="utf-8"))

    def test_twelve_segments_produce_exact_1440_frames(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frame_counts = [131] + [119] * 11
            output, result = self.run_assembler(root, frame_counts)
            metadata = assembler.count_frames(output)
            self.assertEqual(metadata[0], 1440)
            self.assertEqual(metadata[1], (64, 64))
            self.assertEqual(result["total_frames"], 1440)
            self.assertEqual(result["duration_seconds"], 60.0)
            self.assertTrue(result["video_stream_copied"])

    def test_one_frame_tail_caps_crossfade(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output, result = self.run_assembler(root, [131, 1])
            self.assertEqual(assembler.count_frames(output)[0], 132)
            self.assertEqual(result["boundary_crossfade_samples"], [2000])


if __name__ == "__main__":
    unittest.main()
