# MiniMax H3 ComfyUI Workflows

面向约 12GB 显存显卡的 MiniMax H3 文生视频工作流，支持原生音频、跨段 Motion Context 和 RTX Video Super Resolution 输出。

仓库内置日式手绘奇幻动画提示词：水彩背景、铅笔线条、柔和赛璐璐上色、自然环境与森林精灵。

> 连续生成的生产建议与后续架构见 [`CONTINUITY_DESIGN.md`](./CONTINUITY_DESIGN.md)。核心原则是：先解决身份、构图和运动状态，再让 RIFE 修复轻微运动间隙；语义跳变应局部重生成，而不是强行插帧。

## 工作流

### 推荐：3 × 5 秒双层 Motion Context 0.7MP 连续生成

[`Minimax_H3_3x5s_Continuous_MotionContext22_RefineContext0.7MP_RTXVSR_1080p_12GB.json`](./Minimax_H3_3x5s_Continuous_MotionContext22_RefineContext0.7MP_RTXVSR_1080p_12GB.json)

- Segment 1 生成的 0.3MP AV latent 直接作为 Segment 2 的运动上下文，Segment 2 同样传给 Segment 3。
- 每段放大至约 0.7MP，并以 6 steps、denoise 0.30 精修；S2、S3 在精修阶段再次注入上一段 0.7MP 精修 latent 的 22 帧尾部。
- 两层上下文都携带 22 帧画面和 24 帧音频，解码后只同步裁掉一次固定上下文头。
- 三段以 Direct 模式拼接，不使用 RIFE 生成语义过渡帧。
- 实机 A/B 中，双层上下文把两处 0.7MP 边界 MAE 分别从 16.54 降到 4.12、从 16.76 降到 5.35。
- 最终为 370 帧、24fps、约 15.42 秒；同时输出约 1120×640 精修合成片和 RTX VSR 1920×1080 成片。
- 压缩预览已额外应用两次 100ms equal-power 音频 crossfade；workflow 原生输出可使用下述脚本做同样处理。

https://github.com/user-attachments/assets/d39b5e3f-c7dc-4aab-ac20-920809fca9a2

[▶ 播放或下载 960×540 压缩预览（0.91 MB）](./previews/Minimax_H3_MC22_RefineContext07_preview_540p.mp4)

### 任意时长防 OOM 流式生成

长视频版本不在一张图中累积全部解码帧，而是每次 Queue 一个分段，通过磁盘上的 base/refined H3 AV latent 继续下一段：

- [`Streaming Init · Clip 1`](./Minimax_H3_60s_Streaming_Init_RefineContext0.7MP_RTXVSR_1080p_12GB.json)
- [`Streaming Continue · Clips 2–N`](./Minimax_H3_60s_Streaming_Continue_RefineContext0.7MP_RTXVSR_1080p_12GB.json)
- [`任意时长脚本、分段 prompt 格式和断点恢复`](./STREAMING_ARBITRARY_DURATION.md)
- [`完整运行、重试和组装说明`](./STREAMING_60S.md)
- [`12 段连续 prompts`](./Minimax_H3_60s_Streaming_Prompts.md)

Clip 1 最多交付 131 帧，后续每段最多交付 119 帧，尾段按目标总帧数精确裁切。`tools/run_h3_streaming.py` 可通过 comfy-mcp 逐段注入 prompt、执行、保存双层 AV latent、释放显存和断点恢复。60 秒只是现成示例：`131 + 11 × 119 = 1440` 帧。

60 秒输出的实际长度为 1423 帧、24fps、约 59.29 秒。

https://github.com/user-attachments/assets/af11744a-7723-4584-9dab-577cb37c6148

[▶ 播放或下载 960×540 压缩预览（约 3.49 MB）](./previews/Minimax_H3_60s_preview_540p.mp4)

### 15 秒完整生成

[`Minimax_H3_Full15s_LightX2V_Latent0.5MP_RTXVSR_1080p_12GB.json`](./Minimax_H3_Full15s_LightX2V_Latent0.5MP_RTXVSR_1080p_12GB.json)

- 单段 T2VA，约 15 秒、24fps。
- 第一遍以 0.3MP、LightX2V Turbo 8 steps 生成。
- 视频 latent 放大后，以 6 steps、denoise 0.30 精修。
- 保留 H3 原生音频 latent。
- 同时输出 latent-refined 视频和 RTX VSR 1920×1080 视频。

当前 JSON 的文件名、位置序列化值和命名序列化值可能对 0.5MP / 0.7MP 表述不一致。导入后请确认实际节点值；正式发布前应在 ComfyUI 中重新输入目标值并导出，使文件名、workflow info、节点和文档一致。

### Equal-power 音频 crossfade 后处理

当前 ComfyUI 核心 `AudioConcat` 是硬拼。`tools/apply_equal_power_audio_crossfade.py` 会保留最终视频码流，只重新编码音频：对三段音频执行两次 100ms cosine/sine equal-power crossfade，并补偿重叠时长，使最终视频仍为精确 370 帧和约 15.42 秒。

```powershell
& <ComfyUI-python.exe> minimax-h3\tools\apply_equal_power_audio_crossfade.py `
  --segment <segment-1.mp4> --frames 124 `
  --segment <segment-2.mp4> --frames 119 `
  --segment <segment-3.mp4> --frames 127 `
  --video <combined-1080p.mp4> `
  --output <combined-crossfade-1080p.mp4> `
  --report <crossfade-report.json> `
  --crossfade-ms 100
```

该工具只依赖 ComfyUI 环境现有的 PyAV 和 NumPy。默认不会重新编码视频；音频编码为 48kHz AAC。运行后应检查报告中的边界采样跳变，并实际监听两个边界。

## 推荐连续性流程

对于 3 × 5 秒或更长的分段生成，推荐：

```text
固定全局连续性锚点
→ 上一段精修末帧作为下一段 first_frame
→ 先检查低分首遍边界
→ 只重生成失败的下一段
→ 通过后做 latent upscale + refine
→ refine 阶段再次注入上一段精修 latent 尾部
→ 按边界选择 Direct / RIFE / Cut / Dissolve
→ 音频 crossfade
→ RTX VSR
```

边界策略：

| 模式 | 使用场景 |
| --- | --- |
| Direct | 身份、构图和运动连续，只需删除重复首帧 |
| RIFE | 语义一致，仅有小幅姿态或速度间隙 |
| Cut | 有意切换镜头或场景 |
| Dissolve | 时间/空间变化，需要柔和过渡 |
| Retake | 换脸、构图漂移、运动反向或场景重置 |

当前推荐 workflow 固定使用 Direct。RIFE 只适合语义已经一致时的小幅姿态或速度间隙，不包含在精简后的推荐 workflow 中。

## 连续性 Prompt 模板

建议把 prompt 拆成“不变锚点”和“本段动作增量”。

全局锚点示例：

```text
A single continuous cinematic take.
Preserve the same subject identity, face, hair, outfit, body proportions,
props, scene geometry, lighting direction, color palette, camera axis,
camera height, lens character, and spatial relationships.
Continue the current body motion and camera motion naturally without a reset.
Do not redesign the characters or restart the action at the segment boundary.
```

局部段只描述新增动作，例如：

```text
The reaching hand continues forward from the previous frame.
The spirit finishes its current head tilt, then pushes the apple into her palm.
The camera continues the same slow truck right with unchanged height and speed.
```

使用 I2VA 末帧链的 baseline，Segment 2、3 应保留首帧引用：

```text
For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.
```

Motion Context 版不再使用 `<Picture 1>`，避免 I2VA 首帧锚点与 pinned latent head 竞争。详细建议见 [`CONTINUITY_DESIGN.md`](./CONTINUITY_DESIGN.md)。

## 静态校验

仓库提供不依赖 ComfyUI 的静态检查工具：

```bash
python minimax-h3/tools/validate_workflows.py minimax-h3
```

严格模式会让 warning 也返回非零：

```bash
python minimax-h3/tools/validate_workflows.py --strict minimax-h3
```

检查内容包括：

- JSON 可解析性和 link 目标一致性；
- 二次 refine scheduler 是否残留外部 `steps` link；
- latent MP 的文件名、位置值和命名值是否一致；
- 连续段 prompt 是否包含首帧引用和连续性锚点；
- 若目录中存在旧版 RIFE workflow，则检查其倍率、过渡帧裁切和最终帧数；
- 音频硬拼接提示。

静态检查不能替代 ComfyUI 实机运行和样片 A/B。

## 环境要求

- 支持 MiniMax H3 节点的较新版本 ComfyUI。
- NVIDIA GPU；工作流按约 12GB 显存设计。
- 足够的系统内存和磁盘空间用于模型、中间 latent 及视频输出。
- 推荐的 3×5 秒 workflow 需要 `ComfyUI-H3-Motion-Context`。
- 1080p 输出需要 NVIDIA RTX Video Super Resolution 节点和兼容硬件。

如果缺少节点，导入 workflow 后可通过 ComfyUI Manager 的缺失节点安装功能补齐。RTX VSR 不可用时，可以绕过相关节点，直接保存 latent-refined 输出。

## 所需模型

| 类型 | 文件名 | 放置目录 |
| --- | --- | --- |
| Diffusion model | `minimax_h3_fl2va_pruned_int8_convrot.safetensors` | `ComfyUI/models/diffusion_models/` |
| Text encoder | `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | `ComfyUI/models/text_encoders/` |
| Video VAE | `minimax_h3_video_vae_fp16.safetensors` | `ComfyUI/models/vae/` |
| Audio VAE | `minimax_h3_audio_vae_fp32.safetensors` | `ComfyUI/models/vae/` |
| LightX2V LoRA | `minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors` | `ComfyUI/models/loras/` |
| H3 latent upscaler（精修/旧版 workflow） | `minimax_h3_latent_upscaler_3d_bf16.safetensors` | 以对应自定义节点的模型目录为准 |

MiniMax 官方 ComfyUI 模型：

- [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3)
- [MiniMax H3 介绍](https://www.minimax.io/blog/minimax-h3)

经过实机验证的 ComfyUI/frontend、节点提交、模型 SHA-256 和更新限制统一记录在
[`COMPATIBILITY.md`](./COMPATIBILITY.md)。特别注意：Latent Upscaler 必须固定在兼容提交
`8b5058a`；其当前 `main` 已删除本 workflow 使用的旧节点类型，不能直接执行 Manager Update。

## 使用方法

1. 更新 ComfyUI，并安装导入后提示缺失的自定义节点。
2. 下载所需模型并放入对应目录，然后重启 ComfyUI。
3. 将所需 `.json` 文件拖入 ComfyUI 画布。
4. 检查模型选择节点和 latent 目标值，确保文件名与本地模型一致。
5. 修改 prompt、随机种子、分辨率或输出路径。
6. 对连续版先观察分段输出和边界，再决定是否保留当前 seed。
7. Queue Prompt，等待视频和音频生成、精修及保存完成。

workflow 的关键输入包括：

- `prompt`：在同一提示词中描述镜头、角色动作、环境音和非叙事配乐；连续版应使用固定锚点 + 局部动作增量。
- `width / height`：由 Resolution Selector 设置，尺寸会对齐到 32 的倍数。
- `duration`：自动换算为符合 H3 `17k+5` 帧网格的有效帧数。

## H3 提示词结构

默认 prompt 使用以下三个字段：

```text
integrated_multimodal_description: [Shot 1] ...

overall_soundscape: ...

non_diegetic_music: ...
```

修改连续版 prompt 时，请让上一段结尾状态与下一段开头动作自然衔接，并在三段中保持角色服装、道具、场景、光照、镜头方向及声音环境一致。

## 显存与性能

- 默认低分辨率首遍可减少生成时间，但第二遍精修仍会产生目标分辨率对应的峰值显存占用。
- 12GB 显存下不建议直接将 latent 目标提高到 1.2MP 或使用 2× latent 放大。
- 建议先用低分首遍筛选连续性，通过后再做高成本精修。
- 显存不足时，优先降低 latent 目标分辨率、关闭 RTX VSR，或使用较短 workflow 测试 prompt。
- 首次运行应先保持默认参数，确认所有模型和节点可正常加载后再逐步调整。

## 输出

默认输出位于 `ComfyUI/output/video/`。推荐 workflow 会保存三个分段、Direct 合并片和 RTX VSR 1080p 版本；实际文件名前缀可以在 Save Video 节点中修改。

## 说明

生成内容请遵守模型许可、当地法律以及所使用平台的内容政策。建议仅使用原创或已获授权的角色、素材和参考图像。
