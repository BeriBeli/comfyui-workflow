# ComfyUI Workflows

这是我个人维护和使用的 ComfyUI workflow 仓库，主要用于整理、备份和分享经过实际调整的生成工作流。

这些 workflow 会根据我的设备、模型和使用习惯持续修改，不属于 ComfyUI 或相关模型项目的官方示例。导入后请根据自己的硬件环境、模型目录和自定义节点版本调整参数。

## Workflows

### MiniMax H3

面向约 12GB 显存显卡的视频生成工作流，包含 MiniMax H3 原生音频、0.7MP latent 精修、双层 Motion Context 连续生成、任意时长流式执行和 RTX VSR 1080p 输出。推荐 workflow 使用 Direct 拼接；RIFE 仅作为语义连续时的小间隙备选策略。

- [MiniMax H3 workflow 说明](./minimax-h3/README.md)
- 15 秒单段生成
- 3 × 5 秒双层 Motion Context 连续分段生成
- 任意时长流式生成、分段 Prompt 注入和断点恢复
- 60 秒示例及 960×540 文档预览

## 使用说明

1. 进入对应 workflow 的子目录并阅读 README。
2. 下载所需模型，安装缺失的 ComfyUI 自定义节点。
3. 将 `.json` workflow 文件拖入 ComfyUI。
4. 检查模型路径、输出目录和生成参数后再运行。

MiniMax H3 的自定义节点兼容提交、模型 SHA-256、测试环境及不可自动更新项见
[兼容性与复现记录](./minimax-h3/COMPATIBILITY.md)。

不同 ComfyUI 版本、自定义节点版本和硬件环境可能产生不同结果。建议首次运行时保留默认参数，再逐步调整分辨率、采样设置和显存占用。

## 许可与内容

本仓库中的代码、workflow 配置、文档和仓库内预览文件采用
[MIT License](./LICENSE)，明确允许复制、修改、发布和分发，但需保留版权与许可声明。

仓库不包含模型文件。模型、自定义节点及其他第三方资源分别遵循其各自的许可条款。使用生成内容时，请遵守适用法律、模型许可及相关平台政策。
