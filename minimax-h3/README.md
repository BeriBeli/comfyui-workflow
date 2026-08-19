# MiniMax H3 ComfyUI Workflows

面向约 12GB 显存显卡的 MiniMax H3 文生视频工作流，支持原生音频、latent 精修、RIFE 补帧和 RTX Video Super Resolution 输出。

仓库内置日式手绘奇幻动画提示词：水彩背景、铅笔线条、柔和赛璐璐上色、自然环境与森林精灵。

## 工作流

### 15 秒完整生成

[`Minimax_H3_Full15s_LightX2V_Latent0.5MP_RTXVSR_1080p_12GB.json`](./Minimax_H3_Full15s_LightX2V_Latent0.5MP_RTXVSR_1080p_12GB.json)

- 单段 T2VA，约 15 秒、24fps。
- 第一遍以 0.3MP、LightX2V Turbo 8 steps 生成。
- 视频 latent 放大至约 0.7MP，再以 6 steps、denoise 0.30 精修。
- 保留 H3 原生音频 latent。
- 同时输出 latent-refined 视频和 RTX VSR 1920×1080 视频。

### 3 × 5 秒连续生成

[`Minimax_H3_3x5s_Continuous_RIFE4F_Latent0.7MP_RTXVSR_1080p_12GB.json`](./Minimax_H3_3x5s_Continuous_RIFE4F_Latent0.7MP_RTXVSR_1080p_12GB.json)

- Segment 1 使用 T2VA。
- Segment 2、3 自动使用上一段精修视频的末帧作为 I2VA 首帧。
- 每段先以 0.3MP、Turbo 8 steps 生成，再放大至约 0.7MP，以 6 steps、denoise 0.30 精修。
- 两个分段边界分别用 RIFE v4.26 生成 4 张中间帧，并裁掉等量边界原帧。
- 合并后为 370 帧、24fps，时长约 15.42 秒。
- 分段音频会同步裁切并拼接。
- 同时输出约 1120×640 合并视频和 RTX VSR 1920×1080 视频。

连续性依赖上一段末帧、匹配的 I2VA 提示词，以及固定的角色、场景、光照和镜头描述。生成模型无法保证逐像素一致。

## 环境要求

- 支持 MiniMax H3 节点的较新版本 ComfyUI。
- NVIDIA GPU；工作流按约 12GB 显存设计。
- 足够的系统内存和磁盘空间用于模型、中间 latent 及视频输出。
- 3×5 秒工作流需要 RIFE 帧插值节点。
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
| H3 latent upscaler | `minimax_h3_latent_upscaler_3d_bf16.safetensors` | 以对应自定义节点的模型目录为准 |
| RIFE（仅连续版） | `rife_v4.26.safetensors` | 以帧插值节点的模型目录为准 |

MiniMax 官方 ComfyUI 模型：

- [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3)
- [MiniMax H3 介绍](https://www.minimax.io/blog/minimax-h3)

## 使用方法

1. 更新 ComfyUI，并安装导入后提示缺失的自定义节点。
2. 下载所需模型并放入对应目录，然后重启 ComfyUI。
3. 将所需 `.json` 文件拖入 ComfyUI 画布。
4. 检查模型选择节点，确保文件名与本地模型一致。
5. 修改 prompt、随机种子、分辨率或输出路径。
6. Queue Prompt，等待视频和音频生成、精修及保存完成。

工作流的关键输入包括：

- `prompt`：在同一提示词中描述镜头、角色动作、环境音和非叙事配乐。
- `width / height`：由 Resolution Selector 设置，尺寸会对齐到 32 的倍数。
- `duration`：自动换算为符合 H3 `17k+5` 帧网格的有效帧数。

## H3 提示词结构

默认 prompt 使用以下三个字段：

```text
integrated_multimodal_description: [Shot 1] ...

overall_soundscape: ...

non_diegetic_music: ...
```

连续版的 Segment 2、3 还会在开头保留 I2VA 首帧引用：

```text
For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.
```

修改连续版 prompt 时，请让上一段结尾状态与下一段开头动作自然衔接，并在三段中保持角色服装、道具、场景、光照、镜头方向及声音环境一致。

## 显存与性能

- 默认低分辨率首遍可减少生成时间，但第二遍精修仍会产生目标分辨率对应的峰值显存占用。
- 12GB 显存下不建议直接将 latent 目标提高到 1.2MP 或使用 2× latent 放大。
- 显存不足时，优先降低 latent 目标分辨率、关闭 RTX VSR，或使用较短工作流测试 prompt。
- 首次运行应先保持默认参数，确认所有模型和节点可正常加载后再逐步调整。

## 输出

默认输出位于 `ComfyUI/output/video/`。工作流会分别保存精修原片和 RTX VSR 1080p 版本，实际文件名前缀可以在 Save Video 节点中修改。

## 说明

生成内容请遵守模型许可、当地法律以及所使用平台的内容政策。建议仅使用原创或已获授权的角色、素材和参考图像。
