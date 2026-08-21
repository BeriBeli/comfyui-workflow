#!/usr/bin/env python3
"""Stream-copy H3 segment video and add exact-duration crossfaded audio.

Only compressed video packets and the small decoded audio waveforms are held in
memory.  Video frames are never decoded or collected into a minute-long batch.
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
        resampler = av.AudioResampler(format="fltp", layout="stereo", rate=sample_rate)
        for frame in container.decode(audio=0):
            chunks.extend(x.to_ndarray().astype(np.float32, copy=False) for x in resampler.resample(frame))
        chunks.extend(x.to_ndarray().astype(np.float32, copy=False) for x in resampler.resample(None))
    if not chunks:
        raise RuntimeError(f"No decoded audio in {path}")
    return np.concatenate(chunks, axis=1)


def fit_length(waveform: np.ndarray, target: int) -> np.ndarray:
    if waveform.shape[1] == target:
        return waveform
    old = np.linspace(0.0, 1.0, waveform.shape[1], endpoint=False)
    new = np.linspace(0.0, 1.0, target, endpoint=False)
    return np.stack([np.interp(new, old, channel) for channel in waveform]).astype(np.float32)


def equal_power_join(first: np.ndarray, second: np.ndarray, count: int) -> np.ndarray:
    if count <= 0:
        return np.concatenate((first, second), axis=1)
    if count > min(first.shape[1], second.shape[1]):
        raise ValueError("crossfade is longer than an adjacent audio segment")
    phase = np.linspace(0.0, math.pi / 2.0, count, dtype=np.float32)
    mixed = first[:, -count:] * np.cos(phase)[None, :] + second[:, :count] * np.sin(phase)[None, :]
    return np.concatenate((first[:, :-count], mixed, second[:, count:]), axis=1)


def count_frames(path: Path) -> tuple[int, tuple[int, int], str, Fraction]:
    with av.open(str(path)) as container:
        if not container.streams.video:
            raise RuntimeError(f"No video stream in {path}")
        stream = container.streams.video[0]
        count = sum(1 for _ in container.decode(stream))
        rate = stream.average_rate or stream.guessed_rate
        if rate is None:
            raise RuntimeError(f"Cannot determine frame rate for {path}")
        return count, (stream.width, stream.height), stream.codec_context.name, Fraction(rate)


def audio_packets(waveform: np.ndarray, sample_rate: int, stream: av.AudioStream) -> list[av.Packet]:
    packets: list[av.Packet] = []
    for start in range(0, waveform.shape[1], 1024):
        frame = av.AudioFrame.from_ndarray(waveform[:, start : start + 1024], format="fltp", layout="stereo")
        frame.sample_rate = sample_rate
        frame.pts = start
        frame.time_base = Fraction(1, sample_rate)
        packets.extend(stream.encode(frame))
    packets.extend(stream.encode(None))
    return packets


def seconds(packet: av.Packet) -> Fraction:
    if packet.dts is None or packet.time_base is None:
        return Fraction(10**12)
    return Fraction(packet.dts) * Fraction(packet.time_base)


def mux_streaming(
    paths: list[Path], frames: list[int], fps: int, waveform: np.ndarray,
    sample_rate: int, output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with av.open(str(paths[0])) as first, av.open(str(output_path), "w") as output:
        target_video = output.add_stream_from_template(first.streams.video[0])
        target_audio = output.add_stream("aac", rate=sample_rate)
        target_audio.layout = "stereo"
        target_audio.bit_rate = 192_000
        pending_audio = audio_packets(waveform, sample_rate, target_audio)
        audio_index = 0
        offset = Fraction(0)

        for path, frame_count in zip(paths, frames, strict=True):
            with av.open(str(path)) as source:
                source_video = source.streams.video[0]
                for packet in source.demux(source_video):
                    if packet.dts is None or packet.pts is None or packet.time_base is None:
                        continue
                    time_base = Fraction(packet.time_base)
                    shift = round(offset / time_base)
                    packet.dts += shift
                    packet.pts += shift
                    packet.stream = target_video
                    while audio_index < len(pending_audio) and seconds(pending_audio[audio_index]) <= seconds(packet):
                        output.mux(pending_audio[audio_index])
                        audio_index += 1
                    output.mux(packet)
            offset += Fraction(frame_count, fps)

        while audio_index < len(pending_audio):
            output.mux(pending_audio[audio_index])
            audio_index += 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--segment", type=Path, action="append", required=True)
    parser.add_argument(
        "--frames", type=int, action="append", required=True,
        help="Accepted frame count for the matching --segment; repeat in the same order.",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--crossfade-ms", type=float, default=100.0)
    parser.add_argument("--sample-rate", type=int, default=48_000)
    args = parser.parse_args()

    if len(args.segment) != len(args.frames):
        raise ValueError(
            f"--segment/--frames counts differ: {len(args.segment)} != {len(args.frames)}"
        )
    if any(count <= 0 for count in args.frames):
        raise ValueError("Every --frames value must be positive")
    expected_frames = args.frames
    metadata = [count_frames(path) for path in args.segment]
    actual_frames = [item[0] for item in metadata]
    if actual_frames != expected_frames:
        raise ValueError(f"Frame counts must be {expected_frames}, got {actual_frames}")
    dimensions = {item[1] for item in metadata}
    codecs = {item[2] for item in metadata}
    rates = {item[3] for item in metadata}
    if len(dimensions) != 1 or len(codecs) != 1 or rates != {Fraction(args.fps, 1)}:
        raise ValueError(f"Segments must share dimensions/codec/{args.fps}fps: {dimensions}, {codecs}, {rates}")

    requested_fade = round(args.crossfade_ms * args.sample_rate / 1000.0)
    if requested_fade < 0:
        raise ValueError("--crossfade-ms must not be negative")
    decoded = [decode_audio(path, args.sample_rate) for path in args.segment]
    base_samples = [round(count / args.fps * args.sample_rate) for count in expected_frames]
    boundary_fades = [
        min(requested_fade, base_samples[index], base_samples[index + 1])
        for index in range(len(base_samples) - 1)
    ]
    prepared = []
    for index, (waveform, frame_count) in enumerate(zip(decoded, expected_frames, strict=True)):
        extra = boundary_fades[index] if index < len(boundary_fades) else 0
        prepared.append(fit_length(waveform, round(frame_count / args.fps * args.sample_rate) + extra))
    result = prepared[0]
    for index, waveform in enumerate(prepared[1:]):
        result = equal_power_join(result, waveform, boundary_fades[index])
    target_samples = round(sum(expected_frames) / args.fps * args.sample_rate)
    result = fit_length(result, target_samples)
    peak = float(np.max(np.abs(result)))
    if peak > 0.98:
        result *= 0.98 / peak

    mux_streaming(args.segment, expected_frames, args.fps, result, args.sample_rate, args.output)
    final = count_frames(args.output)
    report = {
        "method": "stream-copy video + equal-power audio crossfade",
        "segments": [str(path) for path in args.segment],
        "segment_frames": expected_frames,
        "total_frames": sum(expected_frames),
        "fps": args.fps,
        "duration_seconds": sum(expected_frames) / args.fps,
        "crossfade_ms": args.crossfade_ms,
        "boundary_crossfade_samples": boundary_fades,
        "video_stream_copied": True,
        "dimensions": list(final[1]),
        "codec": final[2],
        "output": str(args.output),
    }
    if final[0] != sum(expected_frames):
        raise RuntimeError(
            f"Assembled output has {final[0]} frames, expected {sum(expected_frames)}"
        )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
