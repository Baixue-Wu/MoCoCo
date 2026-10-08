"""Build a reviewed commentary plan into a narrated film, with source credits."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from mococo import knowledge
from mococo.media import ffmpeg
from mococo.project import Project, init_project
from mococo.stages import images, render, voice


def card(path: Path, heading: str, lines: list[str], font: Path):
    canvas = Image.new('RGB', (1280, 544), '#10282c')
    draw = ImageDraw.Draw(canvas)
    draw.text((56, 38), heading, font=ImageFont.truetype(str(font), 34), fill='#dfc390')
    y = 105
    for line in lines:
        for row in textwrap.wrap(line, 92) or ['']:
            draw.text((56, y), row, font=ImageFont.truetype(str(font), 23), fill='white')
            y += 33
    if y > 515:
        raise ValueError('Credit card exceeds the frame; split its text into more cards')
    canvas.save(path)


def build(film: Path, plan_path: Path, root: Path, source_dir: Path, image_project: Path, font: Path, force: bool = False):
    plan = json.loads(plan_path.read_text())
    if not font.is_file():
        raise FileNotFoundError(f'Provide a Chinese font with --font: {font}')
    digest = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    p = Project(root)
    stamp = p.root / 'build-input.json'
    if p.settings_path.exists():
        if not force and (not stamp.exists() or p.read_json(stamp)['plan_sha256'] != digest or p.load().film != str(film.resolve())):
            raise ValueError('This project has different inputs; choose a new --project folder')
    else:
        p = init_project(root, film, title=plan['title'], style=plan['style'])
        p.write_json(stamp, {'plan_sha256': digest})
    p.write_json(stamp, {'plan_sha256': digest})
    settings = p.load()
    settings.film = str(film.resolve())
    settings.voice.zh = plan['voice']; settings.voice.rate = plan['voice_rate']
    p.save(settings)
    source_records = {}
    for source in sorted(source_dir.glob('*.json')):
        source_records[source.stem] = knowledge.add_source(p, knowledge.Source.model_validate_json(source.read_text()))
    ref_project = Project(image_project)
    refs = images.validate_timeline(ref_project, ref_project.read_json(ref_project.timeline_json))
    ref = next((r for r in refs if r['id'] == plan['image_id']), None)
    if not ref:
        raise ValueError('Approve the plan image in --image-project before building')
    p.external_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ref_project.retrieval_dir / ref['file'], p.retrieval_dir / ref['file'])
    units, candidates, shots, timeline, evidence = [], [], [], [], []
    film_info = ffmpeg.probe(film)
    for u in plan['units']:
        units.append({'id': u['id'], 'text': {'zh': u['text']}, 'intent': u['heading'],
                      'mood': 'reflective', 'keywords': [], 'visual_query_en': u['heading'],
                      'needs_context': bool(u.get('image')), 'context_query': 'Sintel concept art'})
        clips, ranked = [], []
        for i, (start, end) in enumerate(u['ranges']):
            if not 0 <= start < end <= film_info['duration']:
                raise ValueError(f'Invalid film range for {u["id"]}: {start}-{end}')
            sid = f'{u["id"]}-{i:02}'
            shots.append({'id': sid, 'start': start, 'end': end, 'duration': end-start, 'frame': f'frames/{sid}.jpg'})
            ffmpeg.extract_frame(film, (start+end)/2, p.frames_dir / f'{sid}.jpg')
            clips.append({'shot_id': sid, 'in': start, 'out': end, 'seconds': end-start, 'why': u['heading']})
            ranked.append({'shot_id': sid, 'score': 100, 'why': 'Editorially selected footage', 'why_zh': '按解析论点选取的原片片段'})
        if u.get('image'):
            clips.insert(0, {**images.clip(ref), 'seconds': 10.0})
        matches = knowledge.search(p, u['text'])
        candidates.append({'unit_id': u['id'], 'shots': ranked, 'chosen': [r['shot_id'] for r in ranked],
                           'external': [ref] if u.get('image') else [], 'knowledge': matches,
                           'knowledge_status': 'retrieved' if matches else 'missing'})
        evidence.append({'unit': u['id'], 'source_ids': [source_records[k]['id'] for k in u['source_keys']],
                         'retrieved': matches, 'film_ranges': u['ranges'],
                         'review': 'AI-assisted editorial draft checked against selected film frames; not a claim of human approval or director intent.'})
        timeline.append({'id': u['id'], 'estimated_seconds': sum(c['seconds'] for c in clips), 'clips': clips})
    p.write_json(p.segments_json, {'primary_lang': 'zh', 'units': units})
    p.script_md('zh').write_text('\n\n'.join(u['text'] for u in plan['units'])+'\n')
    p.write_json(p.script_evidence_json, {'source_revision': knowledge.fingerprint(p), 'units': evidence})
    p.write_json(p.shots_json, shots)
    p.write_json(p.candidates_json, {'units': candidates})
    p.write_json(p.timeline_json, {'style': plan['style'], 'units': timeline})
    print('Prepared script and footage:', len(units), 'units', flush=True)
    voice.run(p, force=force)
    timing = p.read_json(p.narration_timing('zh'))['units']
    print('Narration:', timing[-1]['end'], 'seconds', flush=True)
    render.render_lang(p, 'zh', force=force, workers=4)
    decorated = p.render_dir / 'commentary.mp4'
    font_dir = p.render_dir / 'fonts'
    font_dir.mkdir(exist_ok=True)
    shutil.copyfile(font, font_dir / font.name)
    font_name = ImageFont.truetype(str(font), 28).getname()[0]
    ass = ['[Script Info]', 'ScriptType: v4.00+', 'PlayResX: 1280', 'PlayResY: 544',
           '[V4+ Styles]', 'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
           f'Style: Heading,{font_name},28,&H00FFFFFF,&H00FFFFFF,&H002C2810,&H002C2810,0,0,0,0,100,100,0,0,3,10,0,7,32,32,26,1',
           '[Events]', 'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']
    def ass_time(seconds):
        centis = round(seconds * 100)
        h, rem = divmod(centis, 360000)
        m, rem = divmod(rem, 6000)
        sec, cs = divmod(rem, 100)
        return f'{h}:{m:02}:{sec:02}.{cs:02}'
    chapters = []
    for u, t in zip(plan['units'], timing):
        end = min(t['start'] + 6, t['end'])
        ass.append(f"Dialogue: 0,{ass_time(t['start'])},{ass_time(end)},Heading,,0,0,0,,{u['heading']}")
        chapters.append({'title': u['heading'], 'start': t['start'], 'end': t['end']})
    headings = p.render_dir / 'headings.ass'
    headings.write_text('\n'.join(ass)+'\n')
    def filter_path(path):
        return path.resolve().as_posix().replace(':', '\\:').replace("'", "\\'")
    vf = f"ass='{filter_path(headings)}':fontsdir='{filter_path(font_dir)}'"
    ffmpeg.run(['-i', str(p.output_mp4('zh')), '-vf', vf, '-c:v', 'libx264', '-preset', 'medium',
                '-crf', '22', '-c:a', 'aac', '-ar', '48000', '-ac', '2', str(decorated)])
    cards = [
        ('作品与电影素材', [f'Baixue Wu | MoCoCo', '中文解析 / 重新剪辑 / AI 辅助制作 / 合成配音',
         'Source film: Sintel (2010), directed by Colin Levy', '© copyright Blender Foundation | www.sintel.org',
         'Film excerpts and original audio: CC BY 3.0', 'https://creativecommons.org/licenses/by/3.0/',
         'Changes: excerpted, reordered, narrated and subtitled.', 'https://durian.blender.org/sharing']),
        ('影评与解读依据', ['Shashwat Pant (2010-12-01), Open Source For You',
         'Sintel, the Movie: Open Source Goes to Hollywood',
         'https://www.opensourceforu.com/2010/12/sintel-the-movie-open-source-goes-to-hollywood/',
         '使用简短改写摘记，未转载影评全文。', '影片中的动作、色彩与时间结构：结合原片画面解读。',
         '观点不等于导演意图；片中概念图的作者与许可见前一张署名卡。'])]
    parts = [decorated]
    for i, (heading, lines) in enumerate(cards):
        png = p.render_dir / f'film-credit-{i}.png'; video = png.with_suffix('.mp4')
        card(png, heading, lines, font)
        ffmpeg.image_clip(png, 10, video, width=1280, height=544)
        parts.append(video)
    joined = p.render_dir / 'joined.mp4'; ffmpeg.concat(parts, joined)
    output = p.render_dir / 'sintel-analysis.zh.mp4'
    ffmpeg.run(['-i', str(joined), '-c', 'copy', '-movflags', '+faststart', str(output)])
    manifest = {'title': plan['title'], 'author': plan['author'], 'duration': ffmpeg.probe(output)['duration'],
                'sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'chapters': chapters,
                'script': p.script_md('zh').read_text(), 'plan_sha256': digest,
                'production': 'AI-assisted editorial script and selected footage; MoCoCo narration, subtitles, image insertion and rendering.',
                'image_credits': refs, 'sources': list(source_records.values())}
    p.write_json(p.render_dir / 'film-manifest.json', manifest)
    print(output, manifest['duration'], 'seconds', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--film', required=True, type=Path)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--source-dir', required=True, type=Path)
    parser.add_argument('--image-project', required=True, type=Path)
    parser.add_argument('--font', required=True, type=Path)
    parser.add_argument('--force', action='store_true', help='Rebuild generated media after editing the plan')
    args = parser.parse_args()
    build(args.film, args.plan, args.project, args.source_dir, args.image_project, args.font, args.force)


if __name__ == '__main__':
    main()
