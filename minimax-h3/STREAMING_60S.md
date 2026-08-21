# MiniMax H3 60 秒双层 Motion Context 流式运行说明

这套方案把一分钟生成拆成 12 次独立 Queue。每次只处理一个分段，上一段的 H3 视频/音频 latent 通过磁盘传给下一次运行，避免在一张 ComfyUI 图里保留 1440 个解码帧。

## 文件

- 第一次运行：[`Minimax_H3_60s_Streaming_Init_RefineContext0.7MP_RTXVSR_1080p_12GB.json`](./Minimax_H3_60s_Streaming_Init_RefineContext0.7MP_RTXVSR_1080p_12GB.json)
- 后续重复运行：[`Minimax_H3_60s_Streaming_Continue_RefineContext0.7MP_RTXVSR_1080p_12GB.json`](./Minimax_H3_60s_Streaming_Continue_RefineContext0.7MP_RTXVSR_1080p_12GB.json)
- 12 段连续 prompt：[`Minimax_H3_60s_Streaming_Prompts.md`](./Minimax_H3_60s_Streaming_Prompts.md)
- 可直接传入脚本的 prompt JSON：[`prompts/Minimax_H3_60s_prompts.json`](./prompts/Minimax_H3_60s_prompts.json)
- 任意时长自动运行器：[`tools/run_h3_streaming.py`](./tools/run_h3_streaming.py)
- 最终流式组装：[`tools/assemble_h3_streaming_video.py`](./tools/assemble_h3_streaming_video.py)

两个 workflow 都保留 0.3MP 首遍、0.7MP latent refine、双层 Motion Context 和逐段 RTX VSR。区别是每次 Queue 结束后立即保存当前分段和两套 AV latent，不在 ComfyUI 内拼接整分钟。

## 精确帧数

| 分段 | H3 原始帧 | 内部裁切 | 交付帧数 |
| --- | ---: | --- | ---: |
| Clip 1 | 141 | 丢弃开头 10 帧预滚 | 131 |
| Clip 2–12 | 每段 141 | Motion Context Trim 删除开头 22 帧 | 每段 119 |

```text
131 + 11 × 119 = 1440 frames
1440 / 24fps = 60.0 seconds
```

Clip 1 丢弃的是开头而不是结尾，因此保存的完整 latent 与交付视频拥有同一个真实末帧；Clip 2 可以从该末帧之前的 22 帧运动状态继续，不会因为时长补偿而跨过隐藏尾帧。

## 第一步：生成 Clip 1

1. 导入 `Streaming_Init` workflow；
2. 保持 0.3MP 首遍、0.7MP refine、5.875 秒请求时长和默认 Clip 1 prompt；
3. Queue 一次；
4. 检查 131 帧候选分段；
5. 若接受，保留所选的 0.7MP 或 1080p MP4；
6. workflow 会同时写入：

```text
ComfyUI/output/h3_stream60/base/clip_00001.safetensors
ComfyUI/output/h3_stream60/refined/clip_00001.safetensors
```

这两个文件都包含 H3 的视频与音频 latent。普通 ComfyUI `SaveLatent` 不能替代它们。

如果 Clip 1 不合格，可以重跑 Init。接受 Clip 1 后不要再覆盖 slot 1，除非准备让整条链从头重做。

## 第二步：生成 Clip 2–12

导入 `Streaming_Continue` workflow。默认已经配置为生成 Clip 2：

```text
Base Load index      = 1
Refined Load index   = 1
Base Save index      = 2
Refined Save index   = 2
Prompt               = Clip 2
```

生成 Clip N 时必须同时设置：

```text
两个 Load index = N - 1
两个 Save index = N
prompt          = Prompt 手册中的 Clip N
```

操作循环：

1. Queue 当前 Clip N；
2. 查看 0.7MP 与 1080p 候选，重点检查上一段末尾到本段开头；
3. 不接受：保持四个 index 不变，更换 seed 或 prompt 后重跑；当前 slot N latent 会被覆盖；
4. 接受：记录这次生成的候选 MP4 路径；
5. 将 Load/Save index 各加 1，粘贴下一段 prompt；
6. Clip 12 接受后停止。

不要使用 index 0。它会加载目录中最新 latent，重试时可能错误地把刚拒绝的当前段当作上一段。

Base 与 Refined 两组 index 必须始终一致。混用不同 clip 的两层上下文，可能导致首遍动作来自一段、精修纹理却来自另一段。

## 为什么这个版本降低 OOM 风险

一次 Continue Queue 只加载：

- 上一段 base AV latent；
- 上一段 refined AV latent；
- 当前段 H3 模型、upscaler、VAE 与最多约 141 帧工作数据；
- 当前段 RTX VSR 输入输出。

它不包含跨 12 段的 `ImageBatch`、`AudioConcat` 或最终 1440 帧 RTX VSR 批次。Queue 结束后，后续连续性状态已经写到 safetensors；下一次运行不依赖上一段的解码帧缓存。

这使峰值大致接近单个 5–6 秒分段，而不是随一分钟总帧数线性增长。ComfyUI 自身仍可能缓存最近一次运行；如果系统内存没有在两次 Queue 之间回落，可以执行 ComfyUI 的清理缓存/释放模型操作或重启后再继续，磁盘 latent 不会丢失。

## 第三步：流式组装 60 秒成片

选择同一输出层级的 12 个已接受 MP4：全部使用 0.7MP，或全部使用 1080p。它们必须具有相同分辨率、编码器和 24fps。

使用 ComfyUI Python 环境运行：

```powershell
& <ComfyUI-python.exe> minimax-h3\tools\assemble_h3_streaming_video.py `
  --segment <clip-01-accepted.mp4> --frames 131 `
  --segment <clip-02-accepted.mp4> --frames 119 `
  --segment <clip-03-accepted.mp4> --frames 119 `
  --segment <clip-04-accepted.mp4> --frames 119 `
  --segment <clip-05-accepted.mp4> --frames 119 `
  --segment <clip-06-accepted.mp4> --frames 119 `
  --segment <clip-07-accepted.mp4> --frames 119 `
  --segment <clip-08-accepted.mp4> --frames 119 `
  --segment <clip-09-accepted.mp4> --frames 119 `
  --segment <clip-10-accepted.mp4> --frames 119 `
  --segment <clip-11-accepted.mp4> --frames 119 `
  --segment <clip-12-accepted.mp4> --frames 119 `
  --output <H3_Stream60_Final.mp4> `
  --report <H3_Stream60_Final.report.json> `
  --crossfade-ms 100
```

脚本会：

- 验证每个 MP4 的实际帧数等于对应 `--frames`；
- 验证所有分段分辨率、codec 和帧率一致；
- 不解码视频图像，直接按时间戳流式复用压缩视频包；
- 只解码体积很小的音频 waveform；
- 在 11 个音频边界执行 100ms equal-power crossfade；
- 输出并复检精确 1440 帧、24fps、60 秒成片。

视频码流不重新编码；音频编码为 48kHz stereo AAC。

## 中断、重试与恢复

- 生成中断：重新打开 Continue workflow，Load 使用最后一个已接受 clip 的 index；
- 当前段失败：不要递增 index，重跑会覆盖当前 latent slot；
- ComfyUI 重启：磁盘 latent 仍可继续使用；
- 不确定最后接受到哪一段：检查 `output/h3_stream60/base` 与 `refined`，两边最大且共同存在的 index 才是可继续点；
- 不要只保留 refined latent；下一段首遍仍需要 base latent；
- 最终成片完成并确认备份前，不要清理 `h3_stream60` latent 或已接受分段。

## 已知限制

- 这是“一个分段一次 Queue”的流式 workflow set，不是一键运行 12 段的单次 Prompt；这是防止 ComfyUI 输出缓存累积的必要取舍；
- 每段仍需要人工边界 QC，失败段应局部重生成；
- Save Video 会为每次尝试生成候选文件，latent slot 则会覆盖；最终组装时必须选择 12 个真正接受的文件；
- 0.7MP 与 1080p 不能混合组装；
- 不应在最终组装前删除中间分段，因为最终视频是从它们的压缩码流直接构建的。
