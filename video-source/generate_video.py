from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
WORK = ROOT / "video-work"
SITE.mkdir(parents=True, exist_ok=True)
WORK.mkdir(parents=True, exist_ok=True)

W, H = 854, 480
FPS = 25

SCENES = [
    {"label": "01", "title": "髌股疼痛为何发生？", "lines": ["同时分析三条链", "负荷链 × 控制链 × 能力链"], "narration": "髌股疼痛综合征，需要同时分析负荷链、控制链和能力链。"},
    {"label": "02", "title": "负荷链", "lines": ["跑量、跳跃和屈膝负重是否骤增", "训练暴露是否超过组织耐受"], "narration": "负荷链关注近期跑量、跳跃、深蹲和上下楼等训练暴露，是否突然增加，并超过组织耐受。"},
    {"label": "03", "title": "控制链", "lines": ["观察骨盆、髋、膝、足和躯干", "膝内扣只能用于形成假设"], "narration": "控制链观察单腿任务中，骨盆、髋、膝、足和躯干的协同。膝内扣不能单独完成诊断。"},
    {"label": "04", "title": "能力链", "lines": ["股四头肌与臀肌力量和耐力", "是否满足当前运动任务"], "narration": "能力链评估股四头肌和臀肌的力量与耐力，能否满足当前运动任务。"},
    {"label": "05", "title": "评估闭环", "lines": ["问诊与红旗筛查 → 动作观察", "训练选择 → 疼痛与二十四小时复测"], "narration": "评估先完成问诊与红旗筛查，再观察动作、安排训练，并复测疼痛和二十四小时反应。"},
    {"label": "06", "title": "训练处方", "lines": ["写清动作、组次、频率和疼痛阈值", "达到标准后再进阶"], "narration": "训练处方要写清动作、组次、频率、疼痛阈值和进退阶条件。训练中疼痛控制在可接受范围，二十四小时内恢复到基线。"},
]


def find_font() -> str:
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    raise FileNotFoundError("No usable font found")


FONT = find_font()


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    if bold:
        for p in [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Bold.otf",
        ]:
            if Path(p).exists():
                return ImageFont.truetype(p, size)
    return ImageFont.truetype(FONT, size)


def rounded_gradient() -> Image.Image:
    img = Image.new("RGB", (W, H), "#082f45")
    px = img.load()
    for y in range(H):
        for x in range(W):
            t = (x / W) * 0.58 + (y / H) * 0.42
            r = int(8 + (25 - 8) * t)
            g = int(47 + (113 - 47) * t)
            b = int(69 + (139 - 69) * t)
            glow = max(0.0, 1.0 - math.hypot(x - 720, y - 75) / 320)
            px[x, y] = (min(255, int(r + 10 * glow)), min(255, int(g + 30 * glow)), min(255, int(b + 34 * glow)))
    return img


def draw_scene(i: int, scene: dict[str, object]) -> Path:
    img = rounded_gradient()
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle((42, 36, W - 42, H - 36), radius=28, fill=(3, 29, 43, 128), outline=(255, 255, 255, 34), width=2)
    d.rounded_rectangle((73, 68, 139, 134), radius=18, fill=(255, 255, 255, 30), outline=(255, 255, 255, 80), width=2)
    d.text((106, 101), str(scene["label"]), anchor="mm", font=font(29, True), fill="white")
    d.text((73, 160), str(scene["title"]), font=font(42, True), fill="white")
    y = 237
    for line in scene["lines"]:
        d.ellipse((78, y + 10, 90, y + 22), fill="#45d1df")
        d.text((106, y), str(line), font=font(26), fill="#e7f7fa")
        y += 58
    d.rounded_rectangle((73, 382, W - 73, 405), radius=12, fill=(255, 255, 255, 28))
    progress_w = int((W - 146) * (i + 1) / len(SCENES))
    d.rounded_rectangle((73, 382, 73 + progress_w, 405), radius=12, fill="#2fc5d3")
    d.text((73, 426), "运动康复学 · PFPS评估与功能训练", font=font(17), fill=(225, 244, 247, 215))
    out = WORK / f"scene_{i+1:02d}.png"
    img.save(out, optimize=True)
    return out


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required")
    voice = "cmn" if shutil.which("espeak-ng") else None
    segments: list[Path] = []
    for i, scene in enumerate(SCENES):
        png = draw_scene(i, scene)
        wav = WORK / f"scene_{i+1:02d}.wav"
        if voice:
            run(["espeak-ng", "-v", voice, "-s", "145", "-p", "48", "-w", str(wav), str(scene["narration"])])
        else:
            run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "7", str(wav)])
        seg = WORK / f"seg_{i+1:02d}.mp4"
        run([
            "ffmpeg", "-y", "-loop", "1", "-i", str(png), "-i", str(wav),
            "-vf", "fade=t=in:st=0:d=0.35,fade=t=out:st=6.6:d=0.35,format=yuv420p",
            "-c:v", "libx264", "-preset", "slow", "-crf", "27", "-maxrate", "240k", "-bufsize", "480k",
            "-r", str(FPS), "-c:a", "aac", "-b:a", "48k", "-ac", "1", "-ar", "44100",
            "-t", "7", "-shortest", "-movflags", "+faststart", str(seg)
        ])
        segments.append(seg)
    concat = WORK / "concat.txt"
    concat.write_text("\n".join(f"file '{p.as_posix()}'" for p in segments), encoding="utf-8")
    output = SITE / "p.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", "-movflags", "+faststart", str(output)])
    first = WORK / "scene_01.png"
    run(["ffmpeg", "-y", "-i", str(first), "-q:v", "3", str(SITE / "poster.jpg")])
    probe = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration,size,bit_rate",
        "-show_entries", "stream=codec_name,width,height,pix_fmt,sample_rate,channels", "-of", "json", str(output)
    ], text=True)
    (SITE / "video_metadata.json").write_text(probe, encoding="utf-8")
    print(json.dumps({"video": str(output), "size": output.stat().st_size}, ensure_ascii=False))


if __name__ == "__main__":
    main()
