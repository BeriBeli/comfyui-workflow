# MiniMax H3 长视频连续性增强设计（V2）

## 1. 目标与定位

现有 `3 × 5 秒` workflow 已经具备两项重要能力：

1. 使用上一段精修视频的末帧作为下一段 I2VA 首帧；
2. 每段采用低分辨率首遍、H3 latent 放大和低 denoise 二次精修，最后通过 RIFE 和 RTX VSR 输出成片。

这套管线适合作为 **12GB 显存条件下的最终质量渲染器**。V2 的目标是在此基础上解决长视频生成：加入时间线/分段规划、边界检查、局部重生成与流式组装，并把 RIFE 降级为边界微修工具。FlowDirector 等方案可作为上层时间线和调度能力的参考或接入点，这里不存在替换关系。

核心判断是：

> H3 的连续性问题首先是语义、身份和运动状态问题，其次才是缺少中间帧的问题。RIFE 能修轻微运动间隙，不能修角色换脸、构图漂移、镜头轴线跳变或场景重置。

因此 V2 的主链路应当是：

```text
固定连续性锚点 + 上一段末帧/尾部运动参考
→ 低成本首遍预览
→ 边界 QC
→ 只重生成失败的下一段
→ 对通过 QC 的候选做 latent 精修
→ 自适应 Direct / RIFE / Cut / Dissolve
→ 音频 crossfade
→ RTX VSR
```

## 2. 非目标

V2 不承诺：

- 跨段逐像素一致；
- 用插帧修复身份或场景语义漂移；
- 在没有实机测试的情况下引入未固定版本的自定义节点；
- 把任意长度视频的所有解码帧长期保存在系统内存。

## 3. 失败类型与处理策略

### 3.1 身份/外观漂移

表现：脸型、发型、服装、道具、体型或绘画材质在边界处改变。

处理顺序：

1. 固定全局连续性锚点；
2. 下一段继续使用上一段精修末帧作为 `first_frame`；
3. 可用 REF2VA 时，额外提供上一段最后 48–72 帧（约 2–3 秒）作为运动参考；
4. 只重生成下一段首遍，选择通过边界检查的候选；
5. 不使用 RIFE 掩盖语义漂移。

### 3.2 运动状态重置

表现：上一段角色正在转头、抬手或行走，下一段却从静止状态重新启动；镜头推进速度或方向发生跳变。

处理顺序：

1. 局部 prompt 只描述“动作增量”，不要重新描述并重启整套动作；
2. 明确写出 `continue the current motion without a reset`；
3. 可用 REF2VA 时提供上一段尾部短视频；
4. 轻微速度差使用 2–4 张 RIFE 中间帧；
5. 方向相反或姿态突变时重生成下一段。

### 3.3 场景/镜头语义跳变

表现：空间布局、镜头轴线、焦段、光线方向或场景突然改变。

处理：

- 如果变化是剧情设计的一部分，使用 `CUT` 或 `DISSOLVE`；
- 如果本应连续，重生成下一段；
- 不使用 RIFE 对两个不同镜头做 morph。

### 3.4 音频接缝

表现：底噪、环境声、音乐相位、响度或节奏在边界处重新开始，出现 click/pop。

处理：

- 对环境声和音乐边界使用 80–150ms equal-power crossfade；
- 环境声变化缓慢时可扩大到 150–250ms；
- 明确硬切镜头时才允许硬切音频；
- 必要时在 crossfade 前做局部响度匹配。

## 4. Prompt 结构

### 4.1 全局连续性锚点

所有分段共享一份不可随意改写的锚点：

```text
A single continuous cinematic take.
Preserve the same subject identity, face, hair, outfit, body proportions,
props, scene geometry, lighting direction, color palette, camera axis,
camera height, lens character, and spatial relationships.
Continue the current body motion and camera motion naturally without a reset.
Do not redesign the characters or restart the action at the segment boundary.
```

对于手绘动画，还应固定：

```text
Preserve the same watercolor background, pencil line weight, cel-shading style,
texture density, and animation restraint across all segments.
```

### 4.2 局部动作增量

每段只描述该段新增的动作和镜头变化：

```text
[Local Action Delta]
The reaching hand continues forward from the previous frame.
The spirit finishes its current head tilt, then pushes the apple into her palm.
The camera continues the same slow truck right with unchanged height and speed.
```

不推荐每段重新完整介绍人物和场景，因为模型可能把它理解为一次新的生成任务。

### 4.3 分段末尾设计

除非计划硬切，分段末尾应进入一个可承接但不是完全静止的状态：

- 保留清晰姿态；
- 动作幅度逐渐减小；
- 镜头方向不变；
- 避免手、脸或快速物体在最后一帧严重运动模糊；
- 音乐和环境声不要在边界处结束乐句。

## 5. 推荐渲染架构

### 5.1 阶段 A：低成本预览

保留当前每段的 0.3MP、Turbo 8 steps 首遍，但在 latent upscale 之前暴露预览输出：

```text
Segment N first pass latent
→ low-resolution VAE decode
→ boundary preview / save candidate
```

首遍的目的不是直接交付，而是用较低成本确认：

- 人物身份；
- 场景布局；
- 镜头方向；
- 动作起点；
- 与上一段的边界状态。

### 5.2 阶段 B：边界 QC 与局部 retake

生成 Segment N 后，只检查：

```text
Segment N-1 尾部 8–16 帧
+
Segment N 开头 8–16 帧
```

检查结果分为：

| 分类 | 典型现象 | 动作 |
| --- | --- | --- |
| `PASS_DIRECT` | 身份、构图和运动连续，仅有重复首帧 | 删除重复帧，直接拼接 |
| `PASS_RIFE` | 语义一致，姿态/速度有轻微间隙 | 保留 2–4 张 RIFE 中间帧 |
| `CUT` | 有意切换镜头或场景 | 直接硬切，不做 RIFE |
| `DISSOLVE` | 时间/空间变化，需要柔和过渡 | 短交叉淡化 |
| `RETAKE` | 换脸、构图漂移、运动反向或场景重置 | 只重生成下一段首遍 |

候选 seed 建议使用可追踪的固定步进，例如：

```text
candidate_seed = base_seed + attempt * 17
```

通过 QC 后才进入高成本精修。

### 5.3 阶段 C：最终质量渲染

继续使用当前质量链：

```text
选中的首遍 latent
→ H3 latent upscale（12GB Safe 建议 0.5MP；Quality 可测试 0.7MP）
→ 6 steps / denoise 0.30
→ VAE decode
```

注意：文件名、`widgets_values`、`widgets_values_named`、workflow info 和 README 中的 MP 值必须一致。静态检查工具会报告歧义，但最终应在 ComfyUI 中重新输入并导出，而不是手工修改未知序列化字段。

### 5.4 阶段 D：自适应边界拼接

#### Direct

```text
上一段保留到最后一帧
下一段删除重复的第 0 帧
直接拼接
```

这是语义和运动已经连续时的首选，避免无意义的插帧慢动作。

#### RIFE

仅用于小幅运动间隙：

```text
上一段末帧 + 下一段首帧
→ RIFE ×3 或 ×5
→ 只保留 2–4 张内部帧
```

当两端人物、构图或光照明显不同，应切换到 `RETAKE`，而不是增加插帧数量。

#### Cut / Dissolve

- 有意切镜：`CUT`；
- 场景或时间变化：短 `DISSOLVE`；
- 不要让 RIFE 在不同镜头之间生成融合帧。

### 5.5 阶段 E：音频拼接

当前 `TrimAudioDuration + AudioConcat` 能保持大致长度，但仍是硬拼。V2 应在兼容节点或后处理工具可用时改为：

```text
Segment N audio tail
+
Segment N+1 audio head
→ 80–150ms equal-power crossfade
```

为了避免引入不确定自定义节点，baseline workflow 暂不直接替换音频节点；先在文档和校验器中明确该限制，后续以独立 workflow 版本实现。

## 6. 可选 REF2VA 尾部运动参考

单帧只描述“最后长什么样”，不能描述“刚才如何运动”。在 REF2VA 环境稳定后，下一段可使用：

```text
first_frame = 上一段精修末帧
ref_image   = 上一段精修末帧
ref_video   = 上一段最后 48–72 帧
```

建议先做 A/B：

- `I2VA_LAST_FRAME`：只传末帧；
- `REF2VA_TAIL_48`：末帧 + 最后 48 帧；
- `REF2VA_TAIL_72`：末帧 + 最后 72 帧。

REF2VA 分支不应直接覆盖当前稳定 workflow；应作为新的实验文件发布，并固定模型、节点仓库和 commit。

## 7. 面向长视频的 FlowDirector 参考点

适合复用或接入的能力：

- 时间线/Storyboard 规划；
- 全局 prompt 与局部 prompt 分离；
- 任意数量 block；
- 上一段末帧自动传递；
- target last frame；
- 只重做失败 block。

为长视频生产需要调整的实现点：

- 不在一个节点中长期保存所有解码帧并在最后 `torch.cat`；
- 不对每段向上对齐后忽略累计时长误差；
- 不只返回最后一个 block latent；
- 不把硬音频拼接称为无缝；
- 不将 24fps 模型暴露为任意 fps 而内部仍按 24fps 裁音频。

长期结构应拆为：

```text
Timeline Planner
→ Block Render Plan (JSON)
→ Preview Renderer / Final Renderer
→ Streaming Segment Assembler
```

长视频应逐段编码到磁盘，只在内存中保留当前 block 和必要的尾部帧。

## 8. 静态检查

运行：

```bash
python minimax-h3/tools/validate_workflows.py minimax-h3
```

严格模式会让 warning 也返回非零：

```bash
python minimax-h3/tools/validate_workflows.py --strict minimax-h3
```

当前检查包括：

- JSON 可解析性；
- 输入/输出 link 是否与 link 记录的目标匹配；
- 6-step / denoise 0.30 refine scheduler 是否残留外部 `steps` link；
- latent MP 的位置序列化值、命名值和文件名是否一致；
- 连续段 prompt 是否包含首帧引用和连续性锚点；
- RIFE 倍率、内部帧裁切和最终帧数计算；
- 音频边界裁切及硬拼接提示。

该工具是静态检查，不替代 ComfyUI 实机运行。

## 9. 验收测试矩阵

每类场景至少测试 4–6 个 seed：

1. 单人物缓慢动作；
2. 双主体交互；
3. 镜头持续平移/推进；
4. 手部与小道具交互；
5. 环境光线稳定；
6. 有意切镜或换场景。

对每个边界记录：

- 是否换脸/换装；
- 场景布局是否漂移；
- 运动方向是否一致；
- RIFE 是否产生融合、重复肢体或慢动作；
- 音频是否出现 click/pop 或音乐重启；
- 首遍候选次数；
- 最终耗时与峰值显存。

比较至少三种方案：

```text
Direct
RIFE 2–4 frames
Local Retake + Direct/RIFE
```

## 10. 实施阶段

### P0：本 PR

- 增加连续性设计文档；
- 增加 workflow 静态检查工具；
- 增加 GitHub Actions 基础校验；
- 在 README 中明确 RIFE 的适用边界和推荐生产流程。

### P1：清理 baseline JSON

在 ComfyUI 中完成并重新导出：

- 清除二次 refine scheduler 的残留 `steps` link；
- 统一 0.5MP / 0.7MP 文件名、节点和文档；
- 固定 ComfyUI、frontend、自定义节点和模型版本。

### P2：Preview / QC 分支

- 暴露每段低分首遍预览；
- 增加边界前后帧预览；
- 增加 Direct 与 RIFE 的可选择输出；
- 保留当前 RIFE workflow 作为可复现 baseline。

### P3：音频 crossfade 与局部 retake

- 引入经过验证的 equal-power crossfade；
- 允许只替换 Segment 2 或 Segment 3；
- 记录候选 seed 和 QC 结论。

### P4：REF2VA 尾部运动参考

- 增加 48/72 帧尾部参考模式；
- 与纯末帧 I2VA 做 A/B；
- 独立发布，不覆盖稳定版。

### P5：长视频

- 引入 Timeline Planner；
- block 逐段渲染和落盘；
- 精确裁回请求帧数；
- 流式音视频组装，避免系统内存随总时长线性增长。
