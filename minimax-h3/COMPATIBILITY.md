# MiniMax H3 兼容性与复现记录

最后实机验证：2026-08-21，Windows，NVIDIA GeForce RTX 5070 12GB。

## 已验证运行环境

| 组件 | 已验证版本 / 提交 | 说明 |
| --- | --- | --- |
| ComfyUI Core | `v0.33.1` / `72865f4f27eaf5396f8f36370e0a2be3a9a090ee` | 在线 workflow schema validation 基准 |
| ComfyUI frontend | `1.48.7` | `comfyui_frontend_package` |
| comfy-cli | `1.16.0`，envelope schema `envelope/1` | 本机 comfy-mcp 后端；CI 固定 `1.13.0` |
| PyTorch / CUDA | `2.12.1+cu130` / CUDA `13.0` | 本机 ComfyUI Python 环境 |
| PyAV / NumPy | `18.0.0` / `2.5.1` | 流式封装与预览测试；CI 精确固定 |

## 自定义节点

| Manager / 仓库名 | 已验证版本 / 提交 | 更新策略 |
| --- | --- | --- |
| [`ComfyUI-H3-Motion-Context`](https://github.com/NikoDemon80/ComfyUI-H3-Motion-Context) | `f80e36bc1d7887a143b12e6645313fd6b9cd2aee` | 当前版本已验证 |
| [`Comfyui_Minimax_h3_latent_Upscaler`](https://github.com/LBH-123-AI/Comfyui_Minimax_h3_latent_Upscaler) | **`8b5058a35c81ca96eccf2f2207a598ddba1d8196`** | 必须固定；当前 `main` 删除 `H3LatentUpscalerNodeMegapixels` 和 `H3LatentUpscalerNode3DV3`，会令现有 workflow 失效 |
| `comfyui_nvidia_rtx_nodes` | registry `0.1.3` | 当前版本已验证 |

`h3_latent_io` 是本机 `custom_nodes` 下的单文件辅助节点，没有独立 Git 仓库。ComfyUI Manager
会把它误识别为上层 Core 仓库并显示错误的更新提示；本仓库的双层流式 workflow 使用
Motion Context 包自己的 AV latent Save/Load 节点，不依赖 `h3_latent_io`。

安装 Upscaler 后固定兼容提交：

```powershell
git -C <ComfyUI>/custom_nodes/Comfyui_Minimax_h3_latent_Upscaler `
  switch --detach 8b5058a35c81ca96eccf2f2207a598ddba1d8196
```

## 模型文件 SHA-256

以下哈希来自完成实机生成和在线验证的本地文件。模型目录可以通过 `extra_model_paths.yaml`
共享；文件名和 SHA-256 必须匹配，绝对路径不需要相同。

| 模型文件 | 字节数 | SHA-256 |
| --- | ---: | --- |
| `minimax_h3_fl2va_pruned_int8_convrot.safetensors` | 20,970,379,616 | `e889202c41dafb67b10d67b97f0d8541508036a6090af23425a5c2615d03c47a` |
| `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | 15,687,142,551 | `35a88d51044231fe332301d7a62aa81e3f2cba62febeb446e2c1e3e0ef76f2c6` |
| `minimax_h3_video_vae_fp16.safetensors` | 5,207,808,496 | `7c1f131492e7eddacaac9069a61b81bdd39de5cc96561e677c5eab1cdce5e522` |
| `minimax_h3_audio_vae_fp32.safetensors` | 605,254,808 | `8e505d95dd1561d47abd43d4238fd40d9bb1ae9e147ed0a4cba778d76ae4db48` |
| `minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors` | 1,956,193,000 | `2339acdf19bfe123f46b971ea35d367a84adb85de43627e1eceafa5a5b2b111e` |
| `minimax_h3_latent_upscaler_3d_bf16.safetensors` | 690,592,992 | `4f57821f5837f32f7142b67d815606dbd7550f194e5c769f7d6c3f83b146a5e6` |

## 已验证范围

- 15 秒双层 Motion Context 0.7MP workflow：comfy-mcp 在线校验 93 个转换节点；
- Streaming Init：34 个转换节点；
- Streaming Continue：39 个转换节点；
- 三者均为 0 error、0 warning、无付费 partner nodes；
- 仓库静态严格校验、帧规划、Prompt 注入、断点状态和 PyAV 组装测试由 GitHub Actions 执行。

在线 schema validation 仍不能估算 VRAM，也不能保证某个 seed 的视觉连续性。首次部署应先运行
Init 或短 workflow，再决定是否执行完整长片。
