# MiniMax H3 任意时长流式运行器

可以脚本化任意目标时长，并为每一段传入独立 prompt。这里的“任意”是指目标总帧数不受 workflow 图规模限制；仍受磁盘空间、运行时间和可用 prompt 数量限制。

## 运行原理

脚本 [`tools/run_h3_streaming.py`](./tools/run_h3_streaming.py) 不会动态复制一张越来越大的 ComfyUI 图。它按顺序执行两个固定模板：

```text
Init：生成 141 帧 → 丢弃 10 帧预滚 → 最多交付 131 帧
Continue：读取上一段 base/refined AV latent → 生成 141 帧
          → Motion Context 内部消耗 22 帧上下文头 → 最多交付 119 帧
          → 保存新的两层 AV latent → 释放模型和显存缓存
重复 Continue，最后一段按剩余帧数裁切
```

目标帧数是 `round(目标秒数 × 24)`。帧规划为：

- 不超过 131 帧：只运行一次 Init，并裁到目标帧数；
- 超过 131 帧：第一段 131 帧，之后每段最多 119 帧；
- 最后一段只交付余数，因此成片帧数精确，不依赖 MP4 非关键帧截断。

例如 37 秒是 888 帧：

```text
[131, 119, 119, 119, 119, 119, 119, 43]
```

无论总长 60 秒还是 10 分钟，ComfyUI 同时只持有一个 141 帧工作段。GPU 峰值大致保持单段规模；系统内存也不会保留整片解码帧。总时长增加时，运行时间、分段 MP4、checkpoint 和最终文件的磁盘占用仍会近似线性增长。

## 分段 prompt 文件

JSON 可以是字符串数组，也可以使用带 seed 的对象。段数必须不少于脚本规划出的段数；多余 prompt 会被忽略。

```json
{
  "fps": 24,
  "prompts": [
    {
      "prompt": "integrated_multimodal_description: [Shot 1] ...\n\noverall_soundscape: ...\n\nnon_diegetic_music: ...",
      "seed": 12345
    },
    {
      "prompt": "integrated_multimodal_description: [Shot 1] Continue the exact preceding motion ...\n\noverall_soundscape: ...\n\nnon_diegetic_music: ...",
      "seed": 23456
    }
  ]
}
```

可直接参考 60 秒的 12 段示例：[`prompts/Minimax_H3_60s_prompts.json`](./prompts/Minimax_H3_60s_prompts.json)。每段 prompt 应重复身份、服装、场景、镜头和声音锚点，同时只改变当前段动作；下一段开头应继续上一段结尾尚未完成的运动。

## 先生成计划，不花生成时间

下面只计算帧数、检查 prompt 数量并写入 `plan.json`，不会连接或运行 ComfyUI：

```powershell
& <comfy-mcp旁的python.exe> minimax-h3\tools\run_h3_streaming.py `
  --duration-seconds 37 `
  --prompts minimax-h3\prompts\my_37s_prompts.json `
  --run-dir minimax-h3\runs\my_37s
```

也可以用 `--target-frames 888` 避免秒数到帧数的舍入。

## 通过 comfy-mcp 执行

使用与已附加 `comfy-mcp.exe` 同目录的 Python；如 ComfyUI 尚未启动，可加 `--launch-comfyui`：

```powershell
$env:COMFY_BIN = '<comfy-mcp旁的comfy.exe>'
& <comfy-mcp旁的python.exe> minimax-h3\tools\run_h3_streaming.py `
  --duration-seconds 60 `
  --prompts minimax-h3\prompts\Minimax_H3_60s_prompts.json `
  --run-dir minimax-h3\runs\stream60 `
  --run-id stream60 `
  --execute `
  --launch-comfyui `
  --tier 0.7mp `
  --assembler-python <ComfyUI-python.exe>
```

每段执行前都会调用 comfy-mcp 的在线 workflow validation；执行后记录输出文件并调用显存/模型释放。全部完成后，脚本调用流式 assembler：视频包直接复用，只解码音频并在边界执行 100ms equal-power crossfade。

工作目录保存：

- `plan.json`：精确帧计划和全部 prompt；
- `workflows/segment_NNNN.json`：实际提交给 ComfyUI 的每段 workflow；
- `state.json`：已完成段、输出路径和 comfy-mcp 结果；
- ComfyUI `output/h3_stream/<run-id>/`：base/refined AV latent checkpoints；
- ComfyUI `output/video/`：每段 0.7MP 和 1080p 候选。

## 中断恢复

重新运行同样的时长和 prompt 文件，并添加：

```powershell
--run-dir minimax-h3\runs\stream60 --resume --execute
```

运行器会校验 `state.json` 必须是连续的已完成前缀、分段文件仍存在、帧数和 prompt 没有变化，然后从下一段继续。它不会把被中断的当前段标记为完成。不要在恢复前删除两层 latent 或已记录的分段 MP4。

## 质量控制边界

脚本能保证帧数、索引、上下文链和内存边界，不能保证模型每次都生成视觉连续的内容。对于重要作品，建议先按段执行并检查边界；若身份、构图或运动方向发生跳变，保持当前 index 不变，修改 prompt/seed 后局部重跑。RIFE 只适合语义已经一致的微小速度或姿态间隙。
