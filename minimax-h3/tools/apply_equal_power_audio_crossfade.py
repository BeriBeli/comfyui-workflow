#!/usr/bin/env python3
"""Replace hard-concatenated H3 audio with exact-duration equal-power fades.

The video stream is remuxed without re-encoding.  S1 and S2 audio are extended
by one crossfade duration before sequential overlap, so two overlaps do not
shorten the requested 370-frame timeline.
"""

from __future__ import annotations

import argparse
import json
import math
from fractions import Fraction
from pathlib import Path

import av
import numpy as np


def decode_audio(path: Path, sample_rate: int) -> np.ndarray:
    chunks: list[np.ndarray] = []
    with av.open(str(path)) as container:
        if not container.streams.audio:
            raise RuntimeError(f"No audio stream in {path}")
        stream = container.streams.audio[0]
        resampler = av.AudioResampler(format="fltp", layout="stereo", rate=sample_rate)
        for frame in container.decode(stream):
            for converted in resampler.resample(frame):
                chunks.append(converted.to_ndarray().astype(np.float32, copy=False))
        for converted in resampler.resample(None):
            chunks.append(converted.to_ndarray().astype(np.float32, copy=False))
    if not chunks:
        raise RuntimeError(f"No audio samples decoded from {path}")
    return np.concatenate(chunks, axis=1)


def fit_length(waveform: np.ndarray, target_samples: int) -> np.ndarray:
    """Small deterministic duration correction using linear interpolation."""
    if waveform.shape[1] == target_samples:
        return waveform
    old_positions = np.linspace(0.0, 1.0, waveform.shape[1], endpoint=False)
    new_positions = np.linspace(0.0, 1.0, target_samples, endpoint=False)
    return np.stack(
        [np.interp(new_positions, old_positions, channel) for channel in waveform],
        axis=0,
    ).astype(np.float32)


def equal_power_join(first: np.ndarray, second: np.ndarray, fade_samples: int) -> np.ndarray:
    if fade_samples <= 0:
        return np.concatenate((first, second), axis=1)
    if min(first.shape[1], second.shape[1]) < fade_samples:
        raise ValueError("Crossfade is longer than one of its inputs")
    phase = np.linspace(0.0, math.pi / 2.0, fade_samples, endpoint=True, dtype=np.float32)
    fade_out = np.cos(phase)[None, :]
    fade_in = np.sin(phase)[None, :]
    mixed = first[:, -fade_samples:] * fade_out + second[:, :fade_samples] * fade_in
    return np.concatenate((first[:, :-fade_samples], mixed, second[:, fade_samples:]), axis=1)


def mux_video_with_audio(video_path: Path, waveform: np.ndarray, sample_rate: int, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with av.open(str(video_path)) as source, av.open(str(output_path), mode="w") as output:
        source_video = source.streams.video[0]
        target_video = output.add_stream_from_template(source_video)
        target_audio = output.add_stream("aac", rate=sample_rate)
        target_audio.layout = "stereo"
        target_audio.bit_rate = 192_000

        video_packets = []
        for packet in source.demux(source_video):
            if packet.dts is None:
                continue
            packet.stream = target_video
            video_packets.append(packet)

        audio_packets = []
        frame_size = 1024
        for start in range(0, waveform.shape[1], frame_size):
            chunk = waveform[:, start : start + frame_size]
            frame = av.AudioFrame.from_ndarray(chunk, format="fltp", layout="stereo")
            frame.sample_rate = sample_rate
            frame.pts = start
            frame.time_base = Fraction(1, sample_rate)
            audio_packets.extend(target_audio.encode(frame))
        audio_packets.extend(target_audio.encode(None))

        # MP4 needs packets from both streams in timestamp order.
        def seconds(packet: av.Packet) -> float:
            if packet.dts is None:
                return float("inf")
            return float(packet.dts * packet.time_base)

        tagged = [(seconds(packet), 0, packet) for packet in video_packets]
        tagged.extend((seconds(packet), 1, packet) for packet in audio_packets)
        for _, _, packet in sorted(tagged, key=lambda item: (item[0], item[1])):
            output.mux(packet)


def seam_metrics(waveform: np.ndarray, sample_rate: int, boundary_seconds: float) -> dict[str, float]:
    index = round(boundary_seconds * sample_rate)
    radius = max(2, round(0.002 * sample_rate))
    delta = np.abs(np.diff(waveform[:, index - radius : index + radius + 1], axis=1))
    before = waveform[:, max(0, index - round(0.05 * sample_rate)) : index]
    after = waveform[:, index : min(waveform.shape[1], index + round(0.05 * sample_rate))]
    return {
        "boundary_seconds": boundary_seconds,
        "exact_sample_delta": float(np.max(np.abs(waveform[:, index] - waveform[:, index - 1]))),
        "local_2ms_delta_p99": float(np.percentile(delta, 99)),
        "local_2ms_delta_max": float(np.max(delta)),
        "rms_before_50ms": float(np.sqrt(np.mean(before**2))),
        "rms_after_50ms": float(np.sqrt(np.mean(after**2))),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--segment", type=Path, action="append", required=True)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--frames", type=int, action="append", required=True)
    parser.add_argument("--crossfade-ms", type=float, default=100.0)
    parser.add_argument("--sample-rate", type=int, default=48_000)
    args = parser.parse_args()

    if len(args.segment) != len(args.frames):
        raise ValueError("Each --segment needs one matching --frames value")
    if len(args.segment) < 2:
        raise ValueError("At least two segments are required")

    fade_samples = round(args.crossfade_ms * args.sample_rate / 1000.0)
    durations = [frames / args.fps for frames in args.frames]
    decoded = [decode_audio(path, args.sample_rate) for path in args.segment]
    prepared = []
    for index, (waveform, duration) in enumerate(zip(decoded, durations, strict=True)):
        extra = fade_samples if index < len(decoded) - 1 else 0
        prepared.append(fit_length(waveform, round(duration * args.sample_rate) + extra))

    result = prepared[0]
    for waveform in prepared[1:]:
        result = equal_power_join(result, waveform, fade_samples)

    expected_samples = round(sum(durations) * args.sample_rate)
    result = fit_length(result, expected_samples)
    peak = float(np.max(np.abs(result)))
    if peak > 0.98:
        result *= 0.98 / peak

    mux_video_with_audio(args.video, result, args.sample_rate, args.output)
    encoded = decode_audio(args.output, args.sample_rate)
    hard = decode_audio(args.video, args.sample_rate)
    boundaries = np.cumsum(durations)[:-1].tolist()
    report = {
        "method": "equal-power cosine/sine overlap",
        "crossfade_ms": args.crossfade_ms,
        "sample_rate": args.sample_rate,
        "target_samples": expected_samples,
        "encoded_samples": int(encoded.shape[1]),
        "target_duration_seconds": expected_samples / args.sample_rate,
        "video_stream_copied": True,
        "boundaries": [
            {
                "hard_concat": seam_metrics(hard, args.sample_rate, boundary),
                "crossfaded": seam_metrics(encoded, args.sample_rate, boundary),
            }
            for boundary in boundaries
        ],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
