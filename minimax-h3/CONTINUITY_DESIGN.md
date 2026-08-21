# MiniMax H3 双层 Motion Context 0.7MP 连续生成设计

本文说明最终推荐 workflow 的运行原理、帧数设计、连续性策略与已知限制。可执行实现为：

[`Minimax_H3_3x5s_Continuous_MotionContext22_RefineContext0.7MP_RTXVSR_1080p_12GB.json`](./Minimax_H3_3x5s_Continuous_MotionContext22_RefineContext0.7MP_RTXVSR_1080p_12GB.json)

目标是在约 12GB 显存条件下，将三个 H3 分段生成成一条约 15.42 秒的连续镜头，并同时保留 H3 原生音频、0.7MP latent 精修和 RTX VSR 1080p 输出。

## 1. 核心思路

这个 workflow 不再依赖“上一段末帧 + RIFE”制造连续感，而是在两次采样阶段都把上一段的 latent 尾部注入下一段：

1. **0.3MP 首遍 Motion Context**：传递人物、构图、动作速度、镜头运动和原生音频的短期状态；
2. **0.7MP 精修 Motion Context**：在细节重建阶段再次传递上一段精修 latent，防止首遍连续、精修后边界又漂移；
3. **Direct 拼接**：删除下一段被固定在开头的上下文帧后直接连接，不生成语义未知的中间帧；
4. **音频后处理**：workflow 内保持精确时长的硬拼，发布样片再做 100ms equal-power crossfade。

Motion Context 解决的是生成阶段的状态延续；RIFE 只能平滑两个已经语义一致的端点。身份、场景或动作方向发生变化时，插帧不能修复问题。

## 2. 总体数据流

```text
Resolution Selector：16:9 / 0.3MP / 32 对齐
                    │
                    ▼
Segment 1：普通 T2VA 首遍（8 steps）
  ├─ BASE_CONTEXT_LATENT ───────────────┐
  └─ 0.7MP upscale + refine（6 / 0.30）│
       └─ REFINED_CONTEXT_LATENT ─────┐ │
                                      │ │
                    ┌─────────────────┘ │
                    ▼                   ▼
Segment 2：0.3MP Motion Context + 0.7MP Refine Motion Context
  ├─ 裁掉固定在头部的 22 帧上下文
  ├─ BASE_CONTEXT_LATENT ───────────────┐
  └─ REFINED_CONTEXT_LATENT ──────────┐ │
                                      │ │
                    ┌─────────────────┘ │
                    ▼                   ▼
Segment 3：0.3MP Motion Context + 0.7MP Refine Motion Context
  └─ 裁掉上下文头，再裁到最终帧预算
                    │
                    ▼
ImageBatch Direct 拼接 + AudioConcat
  ├─ 1120×640 左右的 0.7MP 精修合成片
  └─ RTX VSR → 1920×1080 最终片
```

`BASE_CONTEXT_LATENT` 和 `REFINED_CONTEXT_LATENT` 是两条独立的链。它们不能合并成一条，也不应只保留高分链：首遍采样需要低分上下文稳定动作，精修采样需要高分上下文稳定边界细节。

## 3. 单段内部原理

### 3.1 Segment 1：建立连续性状态

Segment 1 没有上一段上下文，按普通 T2VA 运行：

```text
MiniMaxH3ImageToVideo
→ 0.3MP latent
→ Turbo 8 steps / denoise 1.0 / Euler
→ BASE_CONTEXT_LATENT
→ H3 latent upscaler（目标 0.7MP）
→ 6 steps / denoise 0.30 refine
→ REFINED_CONTEXT_LATENT
→ 视频与音频 VAE decode
```

当前 16:9 首遍尺寸是 `736×416`。0.7MP 精修实机输出约为 `1120×640`。

Segment 1 同时输出两份可供后段使用的 latent：首遍采样结果与精修采样结果。它自身没有 pinned context，因此不裁头。

### 3.2 Segment 2、3：第一层 0.3MP Motion Context

下一段仍使用自己的文本 prompt 创建 H3 conditioning，但 `MiniMaxH3MotionContext` 会把上一段的 `BASE_CONTEXT_LATENT` 尾部固定到当前采样的头部：

```text
本段 conditioning
+ 本段待采样 latent
+ 上一段 BASE_CONTEXT_LATENT 尾部 22 帧
+ 24 帧音频上下文
→ 带上下文的首遍采样
```

22 个画面上下文帧约等于 `0.92s @ 24fps`，24 个音频上下文帧对应约 1 秒。画面和声音的上下文长度并不相同，节点会把需要裁除的画面帧数传给 `MiniMaxH3MotionContextTrim`，由它在解码后同步处理视频与音频。

这里没有再传 `<Picture 1>` 首帧引用。原因是单帧 I2VA 锚点可能与 pinned latent head 竞争，而 latent 尾部已经携带了更完整的姿态、速度和相机运动信息。

### 3.3 第二层 0.7MP Refine Motion Context

首遍 latent 放大到 0.7MP 后，本段不会直接独立精修。第二个 `MiniMaxH3MotionContext` 使用上一段的 `REFINED_CONTEXT_LATENT`，再次注入 22 帧上下文：

```text
本段放大后的 0.7MP latent
+ text-only refine conditioning
+ 上一段 REFINED_CONTEXT_LATENT 尾部 22 帧
→ 6 steps / denoise 0.30 refine
```

精修阶段采用 text-only conditioning，避免重新引入首帧图像约束；高分 Motion Context 负责对齐边界附近的纹理、线条、光照和局部形状。

第二层很重要：如果只有 0.3MP 上下文，首遍边界可能连续，但两段各自做 0.7MP refine 时仍可能重新产生纹理、轮廓或姿态差异。

### 3.4 只裁一次上下文头

两个 Motion Context 都约束同一段时间范围，但输出不能裁两次。workflow 在最终 0.7MP 解码后，通过 `MiniMaxH3MotionContextTrim` 统一删除开头固定的 22 帧，并匹配音频尾部。

因此应保持：

- 首遍与精修层的 context frame 配置一致；
- S2、S3 各只经过一次最终 trim；
- 不在外层再次删除 S2 的 22 帧；
- 修改 context 长度后重新计算每段原始帧数与最终总帧数。

## 4. 帧数与时长设计

H3 使用受约束的帧网格，Motion Context 又会占用下一段头部，所以三个节点的请求时长并不都是字面上的 5 秒。

| 分段 | 节点请求时长 | 原始/含上下文帧 | Motion Context 裁头 | 最终参与拼接 | 作用 |
| --- | ---: | ---: | ---: | ---: | --- |
| Segment 1 | 5.000s | 124 | 0 | 124 | 建立初始状态 |
| Segment 2 | 5.875s | 141 | 22 | 119 | 提供约 5 秒新内容 |
| Segment 3 | 6.5833s | 158 | 22 | 136，再取前 127 | 补足网格后裁到目标总长 |

最终帧数：

```text
124 + 119 + 127 = 370 frames
370 / 24 = 15.4167 seconds
```

Segment 3 解码后使用 `ImageFromBatch` 保留 127 帧，音频用 `TrimAudioDuration` 保留 `127/24 = 5.2917s`。这样视频和音频都精确对齐到 370 帧。

这些数字与 22 帧上下文绑定。不要只把 Segment 2、3 的 duration 改回 5 秒，否则裁头后总时长会不足。

## 5. 内存与 OOM 控制设计

这个 workflow 的“12GB”主要指 **GPU 显存目标**，不是保证任何 12GB 显卡在任意 ComfyUI 启动参数和后台负载下都不会 OOM。它依靠降低单个阶段的峰值和强制分段串行，而不是依靠一个显式的 `Unload Model` 节点。

### 5.1 为什么三个分段不会同时采样

两条 Motion Context 链构成了严格依赖：

```text
S1 base → S1 refine
              │
              ├─ S2 base 必须等待 S1 base context
              └─ S2 refine 必须等待 S1 refined context
                                      │
                                      ├─ S3 base
                                      └─ S3 refine
```

S2 必须读取 S1 的两种 latent，S3 又必须读取 S2 的两种 latent，因此 ComfyUI 不能并行运行三个 H3 sampler。任一时刻只有当前分段的首遍或精修 sampler 在工作，避免把三段扩散模型激活值同时放进显存。

双层 Motion Context 表示“同一段先后运行两层上下文”，不是“两套 sampler 并行运行”。

### 5.2 降低峰值显存的具体措施

1. **首遍只用 0.3MP**：在 `736×416` 上完成最昂贵的从噪声生成，避免直接以 0.7MP 做完整 denoise；
2. **0.7MP 使用 latent upscale + 低 denoise refine**：高分阶段只有 6 steps、denoise 0.30，而不是再次从纯噪声完整生成；
3. **目标停在 0.7MP**：约 `1120×640` 是本机 12GB 配置验证过的质量档，不在 H3 refine 阶段直接做 1080p；
4. **RTX VSR 放在生成完成之后**：1920×1080 只用于最终图像超分，不把 1080p latent 送回 H3 sampler；
5. **上下文窗口固定为短尾部**：Motion Context 从上一段 latent 中固定 22 个画面帧，而不是把多个完整历史分段作为采样上下文；
6. **分段顺序由 latent 依赖锁定**：不要复制三条独立分支并行 Queue，否则会失去串行带来的显存保护。

ComfyUI 的模型加载、CPU offload 和缓存回收仍由其 model management 决定。JSON 内没有强制卸载节点，因此实际余量还受 ComfyUI 版本、启动参数、PyTorch/CUDA 版本、预览方式以及其他占用 GPU 的程序影响。

### 5.3 各阶段的内存峰值

```text
阶段 A：0.3MP H3 首遍采样
→ 阶段 B：0.7MP latent upscaler
→ 阶段 C：0.7MP 低 denoise refine（通常是主要显存压力点）
→ 阶段 D：VAE 视频/音频解码
→ 三段完成后：370 帧合并
→ 阶段 E：RTX VSR 1920×1080
```

不同阶段使用不同模型或算子，不会把 0.3MP sampler、0.7MP refine 和 RTX VSR 同时执行。实机运行时应观察阶段 C 和阶段 E，而不能只看首遍成功就判断整条 workflow 一定不会 OOM。

### 5.4 GPU 显存与系统内存是两个问题

当前 workflow 为了在 ComfyUI 内直接合成成片，会让外层 `GetVideoComponents`、`ImageBatch` 和音频节点保留三段解码结果，直到 370 帧合并完成。它降低了 **GPU 同时采样** 的峰值，但最终图像批次与音频仍会占用 **系统内存**。

因此它适合当前约 15 秒长度，不是任意长视频的恒定内存流式实现：

- 视频长度继续增加时，解码帧和最终 `ImageBatch` 的系统内存会近似随帧数增长；
- 外层实际传递的是上一段 latent 输出，Motion Context 节点在采样时取其尾部；上一段完整输出可能在依赖完成前短暂存活；
- 保存分段视频不等于立即释放所有内存，只要最终合并节点仍依赖这些帧，ComfyUI 就需要保留相应结果。

若扩展到更多分段，应改为：

```text
生成一个分段
→ 保存到磁盘
→ 只保留下一段所需的 base/refined latent 尾部
→ 释放完整解码帧
→ 全部分段完成后用 FFmpeg/PyAV 流式拼接
```

这需要新的 streaming assembler 或分阶段 workflow；不能简单复制当前 S3 子图到 S4、S5 后仍期待内存占用不变。

该结构已经在流式 workflow set 中实现。60 秒的手动运行方法见 [`STREAMING_60S.md`](./STREAMING_60S.md)；任意时长、分段 prompt 注入和断点恢复见 [`STREAMING_ARBITRARY_DURATION.md`](./STREAMING_ARBITRARY_DURATION.md)。它使用 Motion Context 包专用的 AV latent Save/Load 节点，让 base/refined 两条上下文链跨 Queue 持久化，并由 PyAV 最后流式组装任意段数的成片。

脚本只把最后一个交付分段裁到剩余帧数，双层 checkpoint 在交付裁切之前保存。因而目标为 37 秒时可以交付 `[131, 119 × 6, 43]`，同时保留最后一次完整 latent，之后仍可继续延长。这把峰值显存限定在单个 141 帧工作段；总时长只线性增加运行时间和磁盘占用，不会线性增加 ComfyUI 图内的解码帧缓存。

### 5.5 发生 OOM 时的降级顺序

按对画质和连续性影响由小到大处理：

1. 确保同一时间只 Queue 一个完整 workflow，并关闭其他占用 GPU 的程序；
2. 关闭或降低 ComfyUI 实时预览，使用适合显存的 ComfyUI low-VRAM/model-offload 启动配置；
3. 暂时绕过 RTX VSR，先确认 0.7MP 合成片能够完整生成；
4. 将 latent refine 目标从 0.7MP 降到 0.5MP；
5. 缩短单段生成长度并重新计算 H3 帧网格、context trim 和最终帧数；
6. 最后才考虑缩短 22 帧 Motion Context，因为这会直接减少可用于运动连续性的历史窗口。

不要通过减少 S2/S3 的原始 duration 来“省显存”而不重算裁头；这会导致最终时长不足。也不要直接把 0.3MP 首遍提升到 0.7MP，那会明显提高完整 denoise 阶段的峰值。

## 6. 拼接与输出

### 6.1 视频

三段最终图像通过两个 `ImageBatch` 节点直接拼接：

```text
S1 124f + S2 119f + S3 127f = 370f
```

推荐版本不使用 RIFE。Motion Context 已让下一段头部继承上一段尾部运动，Direct 拼接可避免额外的融合影、肢体 morph、重复帧和局部慢动作。

### 6.2 音频

H3 原生音频随各段一起生成。S1、S2 和裁到 127 帧的 S3 音频通过两个 `AudioConcat` 硬拼，保证 workflow 内部时长可预测。

硬拼仍可能出现轻微 click、底噪或音乐相位跳变。仓库脚本：

[`tools/apply_equal_power_audio_crossfade.py`](./tools/apply_equal_power_audio_crossfade.py)

会保留最终视频码流，只对三个分段音频执行两次 100ms equal-power crossfade，并补偿重叠时长。README 中的压缩预览已经应用该处理；workflow 的原生输出没有自动应用。

### 6.3 两级成片

workflow 同时保存：

- 三个独立的 0.7MP 精修分段，便于检查和音频后处理；
- 约 `1120×640`、370 帧的 Direct 合成片；
- RTX VSR `ULTRA` 放大得到的 `1920×1080`、370 帧最终片。

RTX VSR 只提高输出分辨率，不负责修复生成语义或分段连续性。

## 7. Prompt 如何配合 Motion Context

Motion Context 传递短期状态，prompt 负责防止模型主动重新设计长期语义。三个分段应共享不变锚点：

- 同一角色身份、脸、发型、服装和身体比例；
- 同一道具、场景几何、光线方向和空间关系；
- 同一画风、线条粗细、纹理密度和色彩；
- 同一镜头轴线、高度、运动方向与速度；
- 同一环境声、音乐速度和响度。

后续段只描述动作增量，例如：

```text
Continue the preceding clip's exact closing framing.
Continue the current hand motion and the same slow truck right without a reset.
Preserve exact identities, clothing, props, lighting and spatial relationships.
No cut, scene change, camera jump, pose reset, morphing or new object.
```

建议让每段结尾进入“可承接、但仍有微小运动”的稳定状态。边界附近的大幅遮挡、快速旋转、严重运动模糊和突然变焦都会增加下一段漂移概率。

## 8. 为什么不再保留 RIFE baseline

旧 workflow 使用上一段末帧作为 I2VA 首帧，再由 RIFE 补边界帧。它适合验证“单帧锚定 + 插帧”的局限，但不是当前推荐生产路径：

- 单帧只能说明最后的外观，不能表达此前的运动速度和方向；
- 两段独立 refine 后仍可能在高分细节处漂移；
- RIFE 面对身份、构图或动作语义差异时会生成融合帧，而不是修复连续性。

因此旧 RIFE JSON 可以从精简仓库中删除。设计文档应保留，因为 JSON 记录“怎么运行”，本文记录“为什么这样连接、哪些数字不能随意改、失败时该检查哪里”。

## 9. 实机验证结果

最终版本已在本地 ComfyUI 完整执行：

- 实际执行 93 个节点，无运行错误或警告；
- S1 / S2 / S3 输出分别为 124 / 119 / 136 帧，约 `1120×640`；
- S3 裁至 127 帧后合计 370 帧；
- RTX VSR 成片为 `1920×1080`、24fps、约 15.42 秒；
- 边界帧 MAE：S1→S2 为 `4.12`，S2→S3 为 `5.35`；
- 对照的独立 0.7MP refine 边界 MAE 分别为 `16.54` 和 `16.76`。

MAE 只能说明像素边界差异下降，不能单独证明动作语义正确。最终仍应实际观看两个边界，并监听音频衔接。

压缩预览：

[`previews/Minimax_H3_MC22_RefineContext07_preview_540p.mp4`](./previews/Minimax_H3_MC22_RefineContext07_preview_540p.mp4)

## 10. 调参边界与排错

优先保持以下已验证组合：

| 项目 | 当前值 |
| --- | --- |
| 首遍分辨率 | 16:9，0.3MP，32 对齐（736×416） |
| 首遍采样 | Turbo 8 steps，denoise 1.0，Euler |
| latent 精修目标 | 0.7MP（约 1120×640） |
| 精修采样 | 6 steps，denoise 0.30 |
| 视频上下文 | 22 帧 |
| 音频上下文 | 24 帧 |
| 合成方式 | Direct |
| 最终帧率 | 24fps |
| RTX 输出 | 1920×1080，ULTRA |

如果画面仍不连续，按以下顺序定位：

1. 先看 0.3MP 首遍边界；若已换脸、换场景或运动反向，重生成失败的下一段；
2. 首遍连续而 0.7MP 不连续，检查 `REFINED_CONTEXT_LATENT` 是否正确跨段连接；
3. 边界出现重复或停顿，检查是否在 Motion Context Trim 之外又裁切或插帧；
4. 总帧数不是 370，检查 S2/S3 duration、22 帧 context、S3 的 127 帧裁切；
5. 音频 click 但画面正常，运行 equal-power crossfade 后处理；
6. 不要用 RIFE 掩盖换脸、物体变化、镜头跳变或动作重置。

## 11. 依赖与维护原则

推荐 workflow 需要：

- 支持 MiniMax H3 的较新 ComfyUI；
- `ComfyUI-H3-Motion-Context` 提供 Motion Context 与 Trim 节点；
- H3 latent upscaler 节点及对应模型；
- NVIDIA RTX Video Super Resolution 节点与兼容显卡；
- README 所列的 H3 diffusion、text encoder、video/audio VAE 和 Turbo LoRA。

维护时应同时检查：

- JSON 文件名、节点目标 MP、输出前缀和文档是否一致；
- 两条 context latent 链是否都跨段连接；
- context 长度、原始 duration、trim 和最终帧数是否联动；
- prompt 是否继续使用固定锚点 + 局部动作增量；
- README、本文、预览视频是否指向同一个最终版本。

静态检查：

```powershell
python minimax-h3/tools/validate_workflows.py minimax-h3
```

静态检查不能替代 ComfyUI 实机运行和样片观看。
