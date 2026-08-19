# ComfyUI Workflows

这是我个人维护和使用的 ComfyUI workflow 仓库，主要用于整理、备份和分享经过实际调整的生成工作流。

这些 workflow 会根据我的设备、模型和使用习惯持续修改，不属于 ComfyUI 或相关模型项目的官方示例。导入后请根据自己的硬件环境、模型目录和自定义节点版本调整参数。

## Workflows

### MiniMax H3

面向约 12GB 显存显卡的视频生成工作流，包含 MiniMax H3 原生音频、latent 精修、分段连续生成、RIFE 补帧和 RTX VSR 1080p 输出。

- [MiniMax H3 workflow 说明](./minimax-h3/README.md)
- 15 秒单段生成
- 3 × 5 秒连续分段生成

## 使用说明

1. 进入对应 workflow 的子目录并阅读 README。
2. 下载所需模型，安装缺失的 ComfyUI 自定义节点。
3. 将 `.json` workflow 文件拖入 ComfyUI。
4. 检查模型路径、输出目录和生成参数后再运行。

不同 ComfyUI 版本、自定义节点版本和硬件环境可能产生不同结果。建议首次运行时保留默认参数，再逐步调整分辨率、采样设置和显存占用。

## 许可与内容

仓库仅保存 workflow 配置，不包含模型文件。模型、节点及其他第三方资源分别遵循其各自的许可条款。使用生成内容时，请遵守适用法律、模型许可及相关平台政策。
