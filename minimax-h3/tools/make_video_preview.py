#!/usr/bin/env python3
"""Create a deterministic H.264/AAC preview with PyAV."""

from __future__ import annotations

import argparse
import json
from fractions import Fraction
from pathlib import Path

import av


def stream_summary(path: Path) -> dict:
    with av.open(str(path)) as container:
        video = container.streams.video[0]
        audio = container.streams.audio[0] if container.streams.audio else None
        frame_count = sum(1 for _ in container.decode(video=0))
        return {
            "path": str(path.resolve()),
            "bytes": path.stat().st_size,
            "duration_seconds": float(container.duration / av.time_base),
            "video": {
                "codec": video.codec_context.name,
                "width": video.width,
                "height": video.height,
                "fps": str(video.average_rate),
                "frames": frame_count,
            },
            "audio": None if audio is None else {
                "codec": audio.codec_context.name,
                "sample_rate": audio.codec_context.sample_rate,
                "channels": audio.codec_context.channels,
            },
        }


def transcode(source: Path, output: Path, width: int, height: int, crf: int, audio_bitrate: int) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with av.open(str(source)) as input_container, av.open(
        str(output), "w", options={"movflags": "+faststart"}
    ) as output_container:
        input_video = input_container.streams.video[0]
        fps = input_video.average_rate or input_video.guessed_rate
        if fps is None:
            raise RuntimeError("source video frame rate is unavailable")
        output_video = output_container.add_stream("libx264", rate=fps)
        output_video.width = width
        output_video.height = height
        output_video.pix_fmt = "yuv420p"
        output_video.options = {"crf": str(crf), "preset": "medium"}

        input_audio = input_container.streams.audio[0] if input_container.streams.audio else None
        output_audio = None
        resampler = None
        if input_audio is not None:
            output_audio = output_container.add_stream("aac", rate=48_000)
            output_audio.layout = "stereo"
            output_audio.bit_rate = audio_bitrate
            resampler = av.AudioResampler(format="fltp", layout="stereo", rate=48_000)

        video_pts = 0
        audio_pts = 0
        selected = [input_video] + ([input_audio] if input_audio is not None else [])
        for packet in input_container.demux(selected):
            for frame in packet.decode():
                if isinstance(frame, av.VideoFrame):
                    resized = frame.reformat(width=width, height=height, format="yuv420p")
                    resized.pts = video_pts
                    resized.time_base = Fraction(fps.denominator, fps.numerator)
                    video_pts += 1
                    for encoded in output_video.encode(resized):
                        output_container.mux(encoded)
                elif output_audio is not None and resampler is not None:
                    for converted in resampler.resample(frame):
                        converted.pts = audio_pts
                        converted.time_base = Fraction(1, 48_000)
                        audio_pts += converted.samples
                        for encoded in output_audio.encode(converted):
                            output_container.mux(encoded)

        if output_audio is not None and resampler is not None:
            for converted in resampler.resample(None):
                converted.pts = audio_pts
                converted.time_base = Fraction(1, 48_000)
                audio_pts += converted.samples
                for encoded in output_audio.encode(converted):
                    output_container.mux(encoded)
        for encoded in output_video.encode(None):
            output_container.mux(encoded)
        if output_audio is not None:
            for encoded in output_audio.encode(None):
                output_container.mux(encoded)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=540)
    parser.add_argument("--crf", type=int, default=30)
    parser.add_argument("--audio-bitrate", type=int, default=96_000)
    args = parser.parse_args()

    before = stream_summary(args.input)
    transcode(args.input, args.output, args.width, args.height, args.crf, args.audio_bitrate)
    after = stream_summary(args.output)
    if before["video"]["frames"] != after["video"]["frames"]:
        raise RuntimeError(
            f"frame count changed: {before['video']['frames']} -> {after['video']['frames']}"
        )
    if before["video"]["fps"] != after["video"]["fps"]:
        raise RuntimeError(f"frame rate changed: {before['video']['fps']} -> {after['video']['fps']}")
    report = {
        "method": "PyAV libx264 CRF preview; audio transcoded to stereo AAC",
        "source": before,
        "preview": after,
        "settings": {
            "width": args.width,
            "height": args.height,
            "crf": args.crf,
            "audio_bitrate": args.audio_bitrate,
            "faststart": True,
        },
        "source_content_modified": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
