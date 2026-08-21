# MiniMax H3 60 秒流式生成 Prompts

帧预算：Clip 1 交付 131 帧；Clip 2–12 各交付 119 帧；合计 1440 帧、24fps、60 秒。

Clip 1 已写入 Init workflow，Clip 2 已写入 Continue workflow。每次接受当前段后，将下一段 prompt 完整复制到 Continue 子图的 `prompt` 字段。

## Clip 1

```text
integrated_multimodal_description: [Shot 1] 2D hand-drawn Japanese fantasy animation in one uninterrupted eye-level medium-wide shot inside the same sunlit countryside kitchen. Preserve the exact young adult woman with short dark hair, cream blouse, moss-green overalls and red ribbon; the same tiny round leaf-eared forest spirit; the same red apple, wicker basket, old wooden table, open window, golden daylight, watercolor background, expressive pencil linework, gentle cel shading, camera height and spatial relationships. The camera continues the same slow, small-amplitude truck right without a reset. Preserve exact identities, clothing, proportions, props, lighting, watercolor texture, coherent hands and paws, and continuous camera velocity. No cut, scene change, camera jump, pose reset, new object, morphing, duplicate limb, text, logo or watermark. From 0.00 to 0.80 seconds, hold the established composition while she notices the basket rustling and the spirit's leaf-shaped ears appear. From 0.80 to 4.80 seconds, she smiles, places the red apple on the floor, and the shy spirit climbs out to sniff it. From 4.80 to 5.88 seconds, the spirit begins rolling the apple toward her as her right hand continues reaching forward, ending mid-motion for the next clip.

overall_soundscape: The same summer cicadas, soft birdsong, leaf-filled breeze and quiet kitchen room tone continue at matching levels without restarting. Wicker creaks, fabric rustles, tiny paws touch the floor and the apple begins rolling softly across the floorboards.

non_diegetic_music: The same light waltz at a moderate tempo, played by celesta, pizzicato strings and wooden flute, continues at the same tempo and level without restarting. A short wooden-flute phrase remains unfinished at the boundary.
```

## Clip 2

```text
integrated_multimodal_description: [Shot 1] 2D hand-drawn Japanese fantasy animation in one uninterrupted eye-level medium-wide shot inside the same sunlit countryside kitchen. Preserve the exact young adult woman with short dark hair, cream blouse, moss-green overalls and red ribbon; the same tiny round leaf-eared forest spirit; the same red apple, wicker basket, old wooden table, open window, golden daylight, watercolor background, expressive pencil linework, gentle cel shading, camera height and spatial relationships. The camera continues the same slow, small-amplitude truck right without a reset. Preserve exact identities, clothing, proportions, props, lighting, watercolor texture, coherent hands and paws, and continuous camera velocity. No cut, scene change, camera jump, pose reset, new object, morphing, duplicate limb, text, logo or watermark. From 0.00 to 0.92 seconds, preserve the preceding clip's exact pinned closing motion as the apple rolls and her hand continues forward. From 0.92 to 4.80 seconds, the spirit guides the same apple into her palm, climbs onto the table beside her hand, and watches her lift the apple. From 4.80 to 5.88 seconds, she begins placing it on the tabletop while the spirit shifts its weight toward it, ending mid-action.

overall_soundscape: The same summer cicadas, soft birdsong, leaf-filled breeze and quiet kitchen room tone continue at matching levels without restarting. The apple rolls, taps her palm and touches the wood while tiny paws patter on the tabletop.

non_diegetic_music: The same light waltz at a moderate tempo, played by celesta, pizzicato strings and wooden flute, continues at the same tempo and level without restarting. The unfinished flute phrase resolves into two quiet celesta notes, then the waltz continues.
```

## Clip 3

```text
integrated_multimodal_description: [Shot 1] 2D hand-drawn Japanese fantasy animation in one uninterrupted eye-level medium-wide shot inside the same sunlit countryside kitchen. Preserve the exact young adult woman with short dark hair, cream blouse, moss-green overalls and red ribbon; the same tiny round leaf-eared forest spirit; the same red apple, wicker basket, old wooden table, open window, golden daylight, watercolor background, expressive pencil linework, gentle cel shading, camera height and spatial relationships. The camera continues the same slow, small-amplitude truck right without a reset. Preserve exact identities, clothing, proportions, props, lighting, watercolor texture, coherent hands and paws, and continuous camera velocity. No cut, scene change, camera jump, pose reset, new object, morphing, duplicate limb, text, logo or watermark. From 0.00 to 0.92 seconds, continue her lowering hand and the spirit's weight shift exactly from the pinned head. From 0.92 to 4.80 seconds, she sets the apple on the table and slowly rotates it with two fingertips while the spirit follows the turning highlight with its head. From 4.80 to 5.88 seconds, the spirit raises one paw toward the still-turning apple, ending just before contact.

overall_soundscape: The same summer cicadas, soft birdsong, leaf-filled breeze and quiet kitchen room tone continue at matching levels without restarting. The apple makes a soft wooden tap and a faint rolling scrape; her sleeve brushes the table and the spirit breathes quietly.

non_diegetic_music: The same light waltz at a moderate tempo, played by celesta, pizzicato strings and wooden flute, continues at the same tempo and level without restarting. Pizzicato strings keep the pulse while the wooden flute holds a light sustained note across the boundary.
```

## Clip 4

```text
integrated_multimodal_description: [Shot 1] 2D hand-drawn Japanese fantasy animation in one uninterrupted eye-level medium-wide shot inside the same sunlit countryside kitchen. Preserve the exact young adult woman with short dark hair, cream blouse, moss-green overalls and red ribbon; the same tiny round leaf-eared forest spirit; the same red apple, wicker basket, old wooden table, open window, golden daylight, watercolor background, expressive pencil linework, gentle cel shading, camera height and spatial relationships. The camera continues the same slow, small-amplitude truck right without a reset. Preserve exact identities, clothing, proportions, props, lighting, watercolor texture, coherent hands and paws, and continuous camera velocity. No cut, scene change, camera jump, pose reset, new object, morphing, duplicate limb, text, logo or watermark. From 0.00 to 0.92 seconds, preserve the raised paw and the apple's remaining rotation. From 0.92 to 4.70 seconds, the spirit taps the apple twice, making it wobble toward the table edge, and the woman slides her open hand behind it without changing posture. From 4.70 to 5.88 seconds, the apple continues its gentle wobble as her palm approaches to stop it, ending before the catch.

overall_soundscape: The same summer cicadas, soft birdsong, leaf-filled breeze and quiet kitchen room tone continue at matching levels without restarting. Two quiet paw taps, a short apple roll and a small wicker creak sit over the unchanged ambience.

non_diegetic_music: The same light waltz at a moderate tempo, played by celesta, pizzicato strings and wooden flute, continues at the same tempo and level without restarting. Celesta doubles the two taps while pizzicato strings continue evenly into the next clip.
```

## Clip 5

```text
integrated_multimodal_description: [Shot 1] 2D hand-drawn Japanese fantasy animation in one uninterrupted eye-level medium-wide shot inside the same sunlit countryside kitchen. Preserve the exact young adult woman with short dark hair, cream blouse, moss-green overalls and red ribbon; the same tiny round leaf-eared forest spirit; the same red apple, wicker basket, old wooden table, open window, golden daylight, watercolor background, expressive pencil linework, gentle cel shading, camera height and spatial relationships. The camera continues the same slow, small-amplitude truck right without a reset. Preserve exact identities, clothing, proportions, props, lighting, watercolor texture, coherent hands and paws, and continuous camera velocity. No cut, scene change, camera jump, pose reset, new object, morphing, duplicate limb, text, logo or watermark. From 0.00 to 0.92 seconds, continue the wobbling apple and her approaching palm from the pinned context. From 0.92 to 4.70 seconds, she catches the apple softly, steadies it at the table center, and the spirit leans against it with both paws. From 4.70 to 5.88 seconds, a light breeze lifts the window curtain and flutters the spirit's leaf-shaped ears as both begin turning toward the window.

overall_soundscape: The same summer cicadas, soft birdsong, leaf-filled breeze and quiet kitchen room tone continue at matching levels without restarting. The apple settles with one muted tap; the curtain and leaves rustle slightly louder while fabric moves at her elbow.

non_diegetic_music: The same light waltz at a moderate tempo, played by celesta, pizzicato strings and wooden flute, continues at the same tempo and level without restarting. The wooden flute begins a rising phrase that remains open at the boundary.
```

## Clip 6

```text
integrated_multimodal_description: [Shot 1] 2D hand-drawn Japanese fantasy animation in one uninterrupted eye-level medium-wide shot inside the same sunlit countryside kitchen. Preserve the exact young adult woman with short dark hair, cream blouse, moss-green overalls and red ribbon; the same tiny round leaf-eared forest spirit; the same red apple, wicker basket, old wooden table, open window, golden daylight, watercolor background, expressive pencil linework, gentle cel shading, camera height and spatial relationships. The camera continues the same slow, small-amplitude truck right without a reset. Preserve exact identities, clothing, proportions, props, lighting, watercolor texture, coherent hands and paws, and continuous camera velocity. No cut, scene change, camera jump, pose reset, new object, morphing, duplicate limb, text, logo or watermark. From 0.00 to 0.92 seconds, preserve the ear flutter and shared turn toward the window. From 0.92 to 4.70 seconds, the woman and spirit watch two small bird shadows pass across the floor while she keeps one hand beside the apple. From 4.70 to 5.88 seconds, the spirit turns back first and begins nudging the apple toward the wicker basket.

overall_soundscape: The same summer cicadas, soft birdsong, leaf-filled breeze and quiet kitchen room tone continue at matching levels without restarting. Bird wings pass outside, the curtain settles, and one paw makes a soft sliding sound against the apple.

non_diegetic_music: The same light waltz at a moderate tempo, played by celesta, pizzicato strings and wooden flute, continues at the same tempo and level without restarting. The flute phrase descends into the celesta pattern without changing tempo.
```

## Clip 7

```text
integrated_multimodal_description: [Shot 1] 2D hand-drawn Japanese fantasy animation in one uninterrupted eye-level medium-wide shot inside the same sunlit countryside kitchen. Preserve the exact young adult woman with short dark hair, cream blouse, moss-green overalls and red ribbon; the same tiny round leaf-eared forest spirit; the same red apple, wicker basket, old wooden table, open window, golden daylight, watercolor background, expressive pencil linework, gentle cel shading, camera height and spatial relationships. The camera continues the same slow, small-amplitude truck right without a reset. Preserve exact identities, clothing, proportions, props, lighting, watercolor texture, coherent hands and paws, and continuous camera velocity. No cut, scene change, camera jump, pose reset, new object, morphing, duplicate limb, text, logo or watermark. From 0.00 to 0.92 seconds, continue the first nudge and the woman's returning gaze. From 0.92 to 4.70 seconds, the spirit pushes the apple in three small efforts toward the basket while she quietly moves the basket closer with her free hand. From 4.70 to 5.88 seconds, the basket stops beside the apple and the spirit places both paws on its rim, preparing to climb.

overall_soundscape: The same summer cicadas, soft birdsong, leaf-filled breeze and quiet kitchen room tone continue at matching levels without restarting. Three soft apple rolls alternate with tiny paw steps, followed by wicker scraping gently over the tabletop.

non_diegetic_music: The same light waltz at a moderate tempo, played by celesta, pizzicato strings and wooden flute, continues at the same tempo and level without restarting. Pizzicato strings mark the three efforts while celesta and flute remain restrained.
```

## Clip 8

```text
integrated_multimodal_description: [Shot 1] 2D hand-drawn Japanese fantasy animation in one uninterrupted eye-level medium-wide shot inside the same sunlit countryside kitchen. Preserve the exact young adult woman with short dark hair, cream blouse, moss-green overalls and red ribbon; the same tiny round leaf-eared forest spirit; the same red apple, wicker basket, old wooden table, open window, golden daylight, watercolor background, expressive pencil linework, gentle cel shading, camera height and spatial relationships. The camera continues the same slow, small-amplitude truck right without a reset. Preserve exact identities, clothing, proportions, props, lighting, watercolor texture, coherent hands and paws, and continuous camera velocity. No cut, scene change, camera jump, pose reset, new object, morphing, duplicate limb, text, logo or watermark. From 0.00 to 0.92 seconds, preserve both paws on the basket rim and the basket's final settling motion. From 0.92 to 4.70 seconds, the spirit climbs onto the rim, balances there, and looks between the woman and the apple while she steadies the basket with two fingertips. From 4.70 to 5.88 seconds, it reaches one paw back toward the apple as she begins rolling the apple closer.

overall_soundscape: The same summer cicadas, soft birdsong, leaf-filled breeze and quiet kitchen room tone continue at matching levels without restarting. Wicker flexes under the spirit's weight, claws make tiny taps, and the apple starts rolling again.

non_diegetic_music: The same light waltz at a moderate tempo, played by celesta, pizzicato strings and wooden flute, continues at the same tempo and level without restarting. A quiet flute trill follows the balancing motion and carries into the next boundary.
```

## Clip 9

```text
integrated_multimodal_description: [Shot 1] 2D hand-drawn Japanese fantasy animation in one uninterrupted eye-level medium-wide shot inside the same sunlit countryside kitchen. Preserve the exact young adult woman with short dark hair, cream blouse, moss-green overalls and red ribbon; the same tiny round leaf-eared forest spirit; the same red apple, wicker basket, old wooden table, open window, golden daylight, watercolor background, expressive pencil linework, gentle cel shading, camera height and spatial relationships. The camera continues the same slow, small-amplitude truck right without a reset. Preserve exact identities, clothing, proportions, props, lighting, watercolor texture, coherent hands and paws, and continuous camera velocity. No cut, scene change, camera jump, pose reset, new object, morphing, duplicate limb, text, logo or watermark. From 0.00 to 0.92 seconds, continue the apple's roll and the spirit's reaching paw exactly. From 0.92 to 4.70 seconds, she guides the apple to rest against the basket, and the spirit pats its top before lowering one foot inside the basket. From 4.70 to 5.88 seconds, the spirit begins climbing down while its ears and front paws remain visible above the rim.

overall_soundscape: The same summer cicadas, soft birdsong, leaf-filled breeze and quiet kitchen room tone continue at matching levels without restarting. The apple touches wicker with a soft thump, followed by a low basket creak and gentle fabric movement.

non_diegetic_music: The same light waltz at a moderate tempo, played by celesta, pizzicato strings and wooden flute, continues at the same tempo and level without restarting. Celesta plays a descending three-note figure while the waltz pulse remains unchanged.
```

## Clip 10

```text
integrated_multimodal_description: [Shot 1] 2D hand-drawn Japanese fantasy animation in one uninterrupted eye-level medium-wide shot inside the same sunlit countryside kitchen. Preserve the exact young adult woman with short dark hair, cream blouse, moss-green overalls and red ribbon; the same tiny round leaf-eared forest spirit; the same red apple, wicker basket, old wooden table, open window, golden daylight, watercolor background, expressive pencil linework, gentle cel shading, camera height and spatial relationships. The camera continues the same slow, small-amplitude truck right without a reset. Preserve exact identities, clothing, proportions, props, lighting, watercolor texture, coherent hands and paws, and continuous camera velocity. No cut, scene change, camera jump, pose reset, new object, morphing, duplicate limb, text, logo or watermark. From 0.00 to 0.92 seconds, preserve the spirit's careful descent and the woman's steady fingertips. From 0.92 to 4.70 seconds, the spirit settles inside the basket, turns once in place, and leaves its leaf-shaped ears visible while the woman rotates the apple so its red side faces the window light. From 4.70 to 5.88 seconds, she draws her hand back slowly as the spirit begins to yawn.

overall_soundscape: The same summer cicadas, soft birdsong, leaf-filled breeze and quiet kitchen room tone continue at matching levels without restarting. Wicker rustles around the turning spirit, the apple makes a faint quarter-turn scrape, and a tiny breathy yawn begins.

non_diegetic_music: The same light waltz at a moderate tempo, played by celesta, pizzicato strings and wooden flute, continues at the same tempo and level without restarting. The wooden flute softens and the celesta spaces its notes farther apart without stopping.
```

## Clip 11

```text
integrated_multimodal_description: [Shot 1] 2D hand-drawn Japanese fantasy animation in one uninterrupted eye-level medium-wide shot inside the same sunlit countryside kitchen. Preserve the exact young adult woman with short dark hair, cream blouse, moss-green overalls and red ribbon; the same tiny round leaf-eared forest spirit; the same red apple, wicker basket, old wooden table, open window, golden daylight, watercolor background, expressive pencil linework, gentle cel shading, camera height and spatial relationships. The camera continues the same slow, small-amplitude truck right without a reset. Preserve exact identities, clothing, proportions, props, lighting, watercolor texture, coherent hands and paws, and continuous camera velocity. No cut, scene change, camera jump, pose reset, new object, morphing, duplicate limb, text, logo or watermark. From 0.00 to 0.92 seconds, continue the yawn and her retreating hand without resetting either pose. From 0.92 to 4.70 seconds, the spirit finishes yawning, rests its chin on the basket rim, and blinks slowly while she places her hand beside the apple. From 4.70 to 5.88 seconds, both begin turning their gaze back toward the open window as the camera continues trucking right.

overall_soundscape: The same summer cicadas, soft birdsong, leaf-filled breeze and quiet kitchen room tone continue at matching levels without restarting. The yawn fades into quiet breathing, wicker settles, and birdsong becomes briefly clearer through the open window.

non_diegetic_music: The same light waltz at a moderate tempo, played by celesta, pizzicato strings and wooden flute, continues at the same tempo and level without restarting. Pizzicato strings thin to a lighter pattern while a sustained flute tone crosses the boundary.
```

## Clip 12

```text
integrated_multimodal_description: [Shot 1] 2D hand-drawn Japanese fantasy animation in one uninterrupted eye-level medium-wide shot inside the same sunlit countryside kitchen. Preserve the exact young adult woman with short dark hair, cream blouse, moss-green overalls and red ribbon; the same tiny round leaf-eared forest spirit; the same red apple, wicker basket, old wooden table, open window, golden daylight, watercolor background, expressive pencil linework, gentle cel shading, camera height and spatial relationships. The camera continues the same slow, small-amplitude truck right without a reset. Preserve exact identities, clothing, proportions, props, lighting, watercolor texture, coherent hands and paws, and continuous camera velocity. No cut, scene change, camera jump, pose reset, new object, morphing, duplicate limb, text, logo or watermark. From 0.00 to 0.92 seconds, preserve their shared turn and the sustained camera motion. From 0.92 to 4.80 seconds, the spirit nestles lower with only its ears visible, the woman rests one hand beside the apple, and both watch the moving leaves outside. From 4.80 to 5.88 seconds, their breathing and the curtain's final small movement settle into a peaceful stable tableau while the camera slows slightly but does not stop abruptly.

overall_soundscape: The same summer cicadas, soft birdsong, leaf-filled breeze and quiet kitchen room tone continue at matching levels without restarting. Quiet breathing, one final wicker rustle, cicadas, birdsong and the soft breeze remain continuous to the end.

non_diegetic_music: The same light waltz at a moderate tempo, played by celesta, pizzicato strings and wooden flute, continues at the same tempo and level without restarting. The flute resolves, pizzicato strings stop gently, and one sustained celesta note fades at the end.
```
