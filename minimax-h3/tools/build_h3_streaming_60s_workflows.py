#!/usr/bin/env python3
"""Build the two-stage 60-second H3 streaming workflow set.

The generated workflows intentionally execute one clip per queue.  H3 AV
latents cross queue boundaries through the Motion Context package's paired
Save/Load nodes, so decoded frames do not accumulate for the whole minute.
"""

from __future__ import annotations

import copy
import json
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Minimax_H3_3x5s_Continuous_MotionContext22_RefineContext0.7MP_RTXVSR_1080p_12GB.json"
INIT_OUT = ROOT / "Minimax_H3_60s_Streaming_Init_RefineContext0.7MP_RTXVSR_1080p_12GB.json"
CONTINUE_OUT = ROOT / "Minimax_H3_60s_Streaming_Continue_RefineContext0.7MP_RTXVSR_1080p_12GB.json"
PROMPTS_OUT = ROOT / "Minimax_H3_60s_Streaming_Prompts.md"
PROMPTS_JSON_OUT = ROOT / "prompts" / "Minimax_H3_60s_prompts.json"


GLOBAL_VISUAL = (
    "2D hand-drawn Japanese fantasy animation in one uninterrupted eye-level "
    "medium-wide shot inside the same sunlit countryside kitchen. Preserve the "
    "exact young adult woman with short dark hair, cream blouse, moss-green "
    "overalls and red ribbon; the same tiny round leaf-eared forest spirit; the "
    "same red apple, wicker basket, old wooden table, open window, golden daylight, "
    "watercolor background, expressive pencil linework, gentle cel shading, camera "
    "height and spatial relationships. The camera continues the same slow, "
    "small-amplitude truck right without a reset. Preserve exact identities, "
    "clothing, proportions, props, lighting, watercolor texture, coherent hands "
    "and paws, and continuous camera velocity. No cut, scene change, camera jump, "
    "pose reset, new object, morphing, duplicate limb, text, logo or watermark."
)

SOUNDS = (
    "The same summer cicadas, soft birdsong, leaf-filled breeze and quiet kitchen "
    "room tone continue at matching levels without restarting. {detail}"
)

MUSIC = (
    "The same light waltz at a moderate tempo, played by celesta, pizzicato strings "
    "and wooden flute, continues at the same tempo and level without restarting. "
    "{detail}"
)


def prompt(action: str, sound: str, music: str) -> str:
    return (
        f"integrated_multimodal_description: [Shot 1] {GLOBAL_VISUAL} {action}\n\n"
        f"overall_soundscape: {SOUNDS.format(detail=sound)}\n\n"
        f"non_diegetic_music: {MUSIC.format(detail=music)}"
    )


PROMPTS = [
    prompt(
        "From 0.00 to 0.80 seconds, hold the established composition while she notices the basket rustling and the spirit's leaf-shaped ears appear. From 0.80 to 4.80 seconds, she smiles, places the red apple on the floor, and the shy spirit climbs out to sniff it. From 4.80 to 5.88 seconds, the spirit begins rolling the apple toward her as her right hand continues reaching forward, ending mid-motion for the next clip.",
        "Wicker creaks, fabric rustles, tiny paws touch the floor and the apple begins rolling softly across the floorboards.",
        "A short wooden-flute phrase remains unfinished at the boundary.",
    ),
    prompt(
        "From 0.00 to 0.92 seconds, preserve the preceding clip's exact pinned closing motion as the apple rolls and her hand continues forward. From 0.92 to 4.80 seconds, the spirit guides the same apple into her palm, climbs onto the table beside her hand, and watches her lift the apple. From 4.80 to 5.88 seconds, she begins placing it on the tabletop while the spirit shifts its weight toward it, ending mid-action.",
        "The apple rolls, taps her palm and touches the wood while tiny paws patter on the tabletop.",
        "The unfinished flute phrase resolves into two quiet celesta notes, then the waltz continues.",
    ),
    prompt(
        "From 0.00 to 0.92 seconds, continue her lowering hand and the spirit's weight shift exactly from the pinned head. From 0.92 to 4.80 seconds, she sets the apple on the table and slowly rotates it with two fingertips while the spirit follows the turning highlight with its head. From 4.80 to 5.88 seconds, the spirit raises one paw toward the still-turning apple, ending just before contact.",
        "The apple makes a soft wooden tap and a faint rolling scrape; her sleeve brushes the table and the spirit breathes quietly.",
        "Pizzicato strings keep the pulse while the wooden flute holds a light sustained note across the boundary.",
    ),
    prompt(
        "From 0.00 to 0.92 seconds, preserve the raised paw and the apple's remaining rotation. From 0.92 to 4.70 seconds, the spirit taps the apple twice, making it wobble toward the table edge, and the woman slides her open hand behind it without changing posture. From 4.70 to 5.88 seconds, the apple continues its gentle wobble as her palm approaches to stop it, ending before the catch.",
        "Two quiet paw taps, a short apple roll and a small wicker creak sit over the unchanged ambience.",
        "Celesta doubles the two taps while pizzicato strings continue evenly into the next clip.",
    ),
    prompt(
        "From 0.00 to 0.92 seconds, continue the wobbling apple and her approaching palm from the pinned context. From 0.92 to 4.70 seconds, she catches the apple softly, steadies it at the table center, and the spirit leans against it with both paws. From 4.70 to 5.88 seconds, a light breeze lifts the window curtain and flutters the spirit's leaf-shaped ears as both begin turning toward the window.",
        "The apple settles with one muted tap; the curtain and leaves rustle slightly louder while fabric moves at her elbow.",
        "The wooden flute begins a rising phrase that remains open at the boundary.",
    ),
    prompt(
        "From 0.00 to 0.92 seconds, preserve the ear flutter and shared turn toward the window. From 0.92 to 4.70 seconds, the woman and spirit watch two small bird shadows pass across the floor while she keeps one hand beside the apple. From 4.70 to 5.88 seconds, the spirit turns back first and begins nudging the apple toward the wicker basket.",
        "Bird wings pass outside, the curtain settles, and one paw makes a soft sliding sound against the apple.",
        "The flute phrase descends into the celesta pattern without changing tempo.",
    ),
    prompt(
        "From 0.00 to 0.92 seconds, continue the first nudge and the woman's returning gaze. From 0.92 to 4.70 seconds, the spirit pushes the apple in three small efforts toward the basket while she quietly moves the basket closer with her free hand. From 4.70 to 5.88 seconds, the basket stops beside the apple and the spirit places both paws on its rim, preparing to climb.",
        "Three soft apple rolls alternate with tiny paw steps, followed by wicker scraping gently over the tabletop.",
        "Pizzicato strings mark the three efforts while celesta and flute remain restrained.",
    ),
    prompt(
        "From 0.00 to 0.92 seconds, preserve both paws on the basket rim and the basket's final settling motion. From 0.92 to 4.70 seconds, the spirit climbs onto the rim, balances there, and looks between the woman and the apple while she steadies the basket with two fingertips. From 4.70 to 5.88 seconds, it reaches one paw back toward the apple as she begins rolling the apple closer.",
        "Wicker flexes under the spirit's weight, claws make tiny taps, and the apple starts rolling again.",
        "A quiet flute trill follows the balancing motion and carries into the next boundary.",
    ),
    prompt(
        "From 0.00 to 0.92 seconds, continue the apple's roll and the spirit's reaching paw exactly. From 0.92 to 4.70 seconds, she guides the apple to rest against the basket, and the spirit pats its top before lowering one foot inside the basket. From 4.70 to 5.88 seconds, the spirit begins climbing down while its ears and front paws remain visible above the rim.",
        "The apple touches wicker with a soft thump, followed by a low basket creak and gentle fabric movement.",
        "Celesta plays a descending three-note figure while the waltz pulse remains unchanged.",
    ),
    prompt(
        "From 0.00 to 0.92 seconds, preserve the spirit's careful descent and the woman's steady fingertips. From 0.92 to 4.70 seconds, the spirit settles inside the basket, turns once in place, and leaves its leaf-shaped ears visible while the woman rotates the apple so its red side faces the window light. From 4.70 to 5.88 seconds, she draws her hand back slowly as the spirit begins to yawn.",
        "Wicker rustles around the turning spirit, the apple makes a faint quarter-turn scrape, and a tiny breathy yawn begins.",
        "The wooden flute softens and the celesta spaces its notes farther apart without stopping.",
    ),
    prompt(
        "From 0.00 to 0.92 seconds, continue the yawn and her retreating hand without resetting either pose. From 0.92 to 4.70 seconds, the spirit finishes yawning, rests its chin on the basket rim, and blinks slowly while she places her hand beside the apple. From 4.70 to 5.88 seconds, both begin turning their gaze back toward the open window as the camera continues trucking right.",
        "The yawn fades into quiet breathing, wicker settles, and birdsong becomes briefly clearer through the open window.",
        "Pizzicato strings thin to a lighter pattern while a sustained flute tone crosses the boundary.",
    ),
    prompt(
        "From 0.00 to 0.92 seconds, preserve their shared turn and the sustained camera motion. From 0.92 to 4.80 seconds, the spirit nestles lower with only its ears visible, the woman rests one hand beside the apple, and both watch the moving leaves outside. From 4.80 to 5.88 seconds, their breathing and the curtain's final small movement settle into a peaceful stable tableau while the camera slows slightly but does not stop abruptly.",
        "Quiet breathing, one final wicker rustle, cicadas, birdsong and the soft breeze remain continuous to the end.",
        "The flute resolves, pizzicato strings stop gently, and one sustained celesta note fades at the end.",
    ),
]


def clone_node(source_nodes: list[dict], node_id: int, new_id: int, pos: list[float]) -> dict:
    node = copy.deepcopy(next(node for node in source_nodes if node["id"] == node_id))
    node["id"] = new_id
    node["pos"] = pos
    node["order"] = new_id
    for item in node.get("inputs", []):
        item["link"] = None
    for item in node.get("outputs", []):
        item["links"] = []
    return node


def custom_node(node_id: int, node_type: str, pos: list[float], widgets: list, title: str = "") -> dict:
    if node_type.endswith("LoadLatent"):
        inputs = []
        outputs = [{"name": "LATENT", "type": "LATENT", "links": []}]
        size = [330, 90]
    elif node_type.endswith("SaveLatent"):
        inputs = [{"name": "latent", "type": "LATENT", "link": None}]
        outputs = [{"name": "latent_path", "type": "STRING", "links": []}]
        size = [350, 90]
    else:
        raise ValueError(node_type)
    return {
        "id": node_id,
        "type": node_type,
        "pos": pos,
        "size": size,
        "flags": {},
        "order": node_id,
        "mode": 0,
        "inputs": inputs,
        "outputs": outputs,
        "title": title,
        "properties": {"Node name for S&R": node_type},
        "widgets_values": widgets,
        "color": "#1f1f48",
        "bgcolor": "rgba(24,24,27,.9)",
    }


def note_node(node_id: int, pos: list[float], text: str, title: str) -> dict:
    return {
        "id": node_id,
        "type": "MarkdownNote",
        "pos": pos,
        "size": [720, 360],
        "flags": {},
        "order": node_id,
        "mode": 0,
        "inputs": [],
        "outputs": [],
        "title": title,
        "properties": {"Node name for S&R": "MarkdownNote"},
        "widgets_values": [text],
    }


class Graph:
    def __init__(self, source: dict, name: str, definition: dict):
        self.source = source
        self.name = name
        self.definition = copy.deepcopy(definition)
        self.nodes: list[dict] = []
        self.links: list[list] = []
        self.next_node = 1
        self.next_link = 1

    def add_clone(self, source_id: int, pos: list[float]) -> dict:
        node = clone_node(self.source["nodes"], source_id, self.next_node, pos)
        self.next_node += 1
        self.nodes.append(node)
        return node

    def add(self, node: dict) -> dict:
        self.nodes.append(node)
        self.next_node = max(self.next_node, node["id"] + 1)
        return node

    @staticmethod
    def input_index(node: dict, name: str) -> int:
        return next(i for i, item in enumerate(node.get("inputs", [])) if item["name"] == name)

    @staticmethod
    def output_index(node: dict, name: str) -> int:
        return next(i for i, item in enumerate(node.get("outputs", [])) if item["name"] == name)

    def connect(self, origin: dict, output: str, target: dict, input_name: str, link_type: str) -> None:
        oslot = self.output_index(origin, output)
        tslot = self.input_index(target, input_name)
        link_id = self.next_link
        self.next_link += 1
        self.links.append([link_id, origin["id"], oslot, target["id"], tslot, link_type])
        origin["outputs"][oslot].setdefault("links", []).append(link_id)
        target["inputs"][tslot]["link"] = link_id

    def export(self) -> dict:
        return {
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"comfyui-workflow/{self.name}")),
            "revision": 0,
            "last_node_id": max(node["id"] for node in self.nodes),
            "last_link_id": self.next_link - 1,
            "nodes": self.nodes,
            "links": self.links,
            "groups": [],
            "definitions": {"subgraphs": [self.definition]},
            "config": {},
            "extra": copy.deepcopy(self.source.get("extra", {})),
            "version": self.source.get("version", 0.4),
            "name": self.name,
        }


def set_widgets(node: dict, **values) -> None:
    mapping = {
        "prompt": 0,
        "width": 1,
        "height": 2,
        "duration": 3,
        "seed": 4,
    }
    for name, value in values.items():
        node["widgets_values"][mapping[name]] = value


def add_per_clip_outputs(
    graph: Graph, clip: dict, x: int, crop_start: int, crop_length: int,
) -> None:
    components = graph.add_clone(122, [x, 180])
    graph.connect(clip, "VIDEO", components, "video", "VIDEO")

    image_trim = graph.add_clone(141, [x + 330, 80])
    image_trim["title"] = f"Deliverable Crop · Start {crop_start} · Keep Up To {crop_length}f"
    image_trim["widgets_values"] = [crop_start, crop_length]
    audio_trim = graph.add_clone(144, [x + 330, 280])
    audio_trim["title"] = "Deliverable Audio Crop · Script-overridable"
    audio_trim["widgets_values"] = [crop_start / 24, crop_length / 24]
    graph.connect(components, "images", image_trim, "image", "IMAGE")
    graph.connect(components, "audio", audio_trim, "audio", "AUDIO")

    create_07 = graph.add_clone(147, [x + 700, 80])
    create_07["title"] = "Create Candidate 0.7MP Segment"
    create_07["widgets_values"] = [24, 8]
    save_07 = graph.add_clone(148, [x + 1020, 80])
    save_07["title"] = "Save Candidate Segment · 0.7MP"
    save_07["widgets_values"] = ["video/H3_Stream60_Candidate_0.7MP", "auto", "auto"]

    graph.connect(image_trim, "IMAGE", create_07, "images", "IMAGE")
    graph.connect(audio_trim, "AUDIO", create_07, "audio", "AUDIO")
    graph.connect(components, "fps", create_07, "fps", "FLOAT")
    graph.connect(create_07, "VIDEO", save_07, "video", "VIDEO")

    rtx = graph.add_clone(123, [x + 700, 310])
    rtx["title"] = "Per-segment RTX VSR · Exact 1920×1080"
    create_rtx = graph.add_clone(124, [x + 1020, 310])
    create_rtx["title"] = "Create Candidate 1080p Segment"
    save_rtx = graph.add_clone(125, [x + 1340, 310])
    save_rtx["title"] = "Save Candidate Segment · 1080p"
    save_rtx["widgets_values"] = ["video/H3_Stream60_Candidate_1080p", "auto", "auto"]
    graph.connect(image_trim, "IMAGE", rtx, "images", "IMAGE")
    graph.connect(rtx, "upscaled_images", create_rtx, "images", "IMAGE")
    graph.connect(audio_trim, "AUDIO", create_rtx, "audio", "AUDIO")
    graph.connect(components, "fps", create_rtx, "fps", "FLOAT")
    graph.connect(create_rtx, "VIDEO", save_rtx, "video", "VIDEO")


def build_init(source: dict) -> dict:
    instance = next(node for node in source["nodes"] if node["id"] == 105)
    definition = next(d for d in source["definitions"]["subgraphs"] if d["id"] == instance["type"])
    graph = Graph(source, "MiniMax H3 60s Streaming · Clip 1 Initialize", definition)
    resolution = graph.add_clone(115, [-1500, 0])
    clip = graph.add_clone(105, [-1100, 0])
    clip["title"] = "Clip 1 · 141f raw · Drop first 10 · Deliver 131f"
    set_widgets(clip, prompt=PROMPTS[0], duration=5.875)
    graph.connect(resolution, "width", clip, "width", "INT")
    graph.connect(resolution, "height", clip, "height", "INT")

    save_base = graph.add(custom_node(graph.next_node, "MiniMaxH3MotionContextSaveLatent", [-650, 560], ["h3_stream60/base/clip", 1], "Save Clip 1 Base AV Latent"))
    save_refined = graph.add(custom_node(graph.next_node, "MiniMaxH3MotionContextSaveLatent", [-250, 560], ["h3_stream60/refined/clip", 1], "Save Clip 1 Refined AV Latent"))
    graph.connect(clip, "BASE_CONTEXT_LATENT", save_base, "latent", "LATENT")
    graph.connect(clip, "REFINED_CONTEXT_LATENT", save_refined, "latent", "LATENT")
    add_per_clip_outputs(graph, clip, -650, crop_start=10, crop_length=131)

    graph.add(note_node(graph.next_node, [-1500, 650], """## 60s Streaming · First Run\n\n1. Queue this workflow once.\n2. It renders 141 frames, drops the first 10 as pre-roll, and saves 131 accepted frames.\n3. It saves paired video/audio base and refined latents to `output/h3_stream60/`.\n4. Pick either the accepted 0.7MP or 1080p segment for final assembly.\n5. Continue with the companion `Streaming_Continue` workflow.\n\nDo not run Init again after accepting Clip 1 unless you intend to replace the whole chain.""", "Instructions · Clip 1"))
    return graph.export()


def build_continue(source: dict) -> dict:
    instance = next(node for node in source["nodes"] if node["id"] == 131)
    definition = next(d for d in source["definitions"]["subgraphs"] if d["id"] == instance["type"])
    graph = Graph(source, "MiniMax H3 60s Streaming · Clips 2-12 Continue", definition)
    resolution = graph.add_clone(115, [-1800, 0])
    load_base = graph.add(custom_node(graph.next_node, "MiniMaxH3MotionContextLoadLatent", [-1800, 300], ["h3_stream60/base", 1], "Load Previous Base AV Latent"))
    load_refined = graph.add(custom_node(graph.next_node, "MiniMaxH3MotionContextLoadLatent", [-1800, 440], ["h3_stream60/refined", 1], "Load Previous Refined AV Latent"))
    clip = graph.add_clone(131, [-1300, 0])
    clip["title"] = "Clip N · Load N-1 · Raw 141 · Deliver 119f"
    set_widgets(clip, prompt=PROMPTS[1], duration=5.875)
    graph.connect(resolution, "width", clip, "width", "INT")
    graph.connect(resolution, "height", clip, "height", "INT")
    graph.connect(load_base, "LATENT", clip, "context_latent", "LATENT")
    graph.connect(load_refined, "LATENT", clip, "refined_context_latent", "LATENT")

    save_base = graph.add(custom_node(graph.next_node, "MiniMaxH3MotionContextSaveLatent", [-850, 560], ["h3_stream60/base/clip", 2], "Save Current Base AV Latent"))
    save_refined = graph.add(custom_node(graph.next_node, "MiniMaxH3MotionContextSaveLatent", [-450, 560], ["h3_stream60/refined/clip", 2], "Save Current Refined AV Latent"))
    graph.connect(clip, "BASE_CONTEXT_LATENT", save_base, "latent", "LATENT")
    graph.connect(clip, "REFINED_CONTEXT_LATENT", save_refined, "latent", "LATENT")
    add_per_clip_outputs(graph, clip, -850, crop_start=0, crop_length=119)

    graph.add(note_node(graph.next_node, [-1800, 700], """## Streaming · Repeat for Clips 2-N\n\nFor Clip N:\n1. Set BOTH Load nodes to `N-1`.\n2. Set BOTH Save nodes to `N`.\n3. Inject prompt N.\n4. Queue once and inspect both boundaries/segment outputs.\n5. Reject: keep indexes unchanged and queue again; slot N is overwritten.\n6. Accept: record the accepted segment file, increment indexes, inject the next prompt.\n\nNever use index 0 for a retryable chain. Keep base and refined indexes identical. A regular continuation delivers 119 frames. For an arbitrary target duration, the runner changes only the final deliverable crop; the full paired AV latent checkpoint remains available for resume/extension.""", "Instructions · Clips 2-N"))
    return graph.export()


def main() -> None:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    INIT_OUT.write_text(json.dumps(build_init(source), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    CONTINUE_OUT.write_text(json.dumps(build_continue(source), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    prompt_sections = [
        "# MiniMax H3 60 秒流式生成 Prompts",
        "",
        "帧预算：Clip 1 交付 131 帧；Clip 2–12 各交付 119 帧；合计 1440 帧、24fps、60 秒。",
        "",
        "Clip 1 已写入 Init workflow，Clip 2 已写入 Continue workflow。每次接受当前段后，将下一段 prompt 完整复制到 Continue 子图的 `prompt` 字段。",
    ]
    for index, value in enumerate(PROMPTS, start=1):
        prompt_sections.extend(["", f"## Clip {index}", "", "```text", value, "```"])
    PROMPTS_OUT.write_text("\n".join(prompt_sections) + "\n", encoding="utf-8")
    PROMPTS_JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    PROMPTS_JSON_OUT.write_text(
        json.dumps(
            {"fps": 24, "prompts": [{"prompt": value} for value in PROMPTS]},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(INIT_OUT)
    print(CONTINUE_OUT)
    print(PROMPTS_OUT)
    print(PROMPTS_JSON_OUT)


if __name__ == "__main__":
    main()
