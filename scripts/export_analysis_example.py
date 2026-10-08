"""Export a source-linked Sintel analysis study. Usage: uv run python scripts/export_analysis_example.py --film PATH --dest DIR"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from mococo import knowledge
from mococo.media import ffmpeg
from mococo.project import Project


def export_workflow(project: Project, dest: Path, narration_url: str) -> dict:
    """Export actual completed-project decisions without local paths or model scores."""
    from mococo.stages.render import fit_clips

    if not narration_url.startswith('https://'):
        raise ValueError('Provide an HTTPS --narration-url for the completed narration')
    settings = project.load()
    shots = project.read_json(project.shots_json)
    by_id = {shot['id']: shot for shot in shots}
    timing = project.read_json(project.narration_timing('zh'))
    by_time = {unit['id']: unit for unit in timing['units']}
    timeline = project.read_json(project.timeline_json)
    frames = dest / 'frames'
    frames.mkdir(exist_ok=True)
    for shot in shots:
        shutil.copyfile(project.frames_dir / f"{shot['id']}.jpg", frames / f"{shot['id']}.jpg")
    rendered, cursor = [], 0.0
    for index, unit in enumerate(timeline['units']):
        t = by_time[unit['id']]
        following = timeline['units'][index+1]['id'] if index+1 < len(timeline['units']) else None
        span = (by_time[following]['start'] if following else t['end']) - t['start']
        fitted = fit_clips(unit['clips'], span, by_id)
        clips = []
        for k, clip in enumerate(fitted):
            duration = ffmpeg.probe(project.render_dir / 'clips.zh' / f"{unit['id']}_{k:02}.mp4")['duration']
            item = {**clip, 'render_start': round(cursor, 3), 'render_end': round(cursor+duration, 3), 'render_seconds': duration}
            if clip.get('kind') == 'image':
                name = Path(clip['file']).name
                shutil.copyfile(project.retrieval_dir / clip['file'], dest / name)
                item['file'] = name
            clips.append(item)
            cursor += duration
        rendered.append({'id': unit['id'], 'clips': clips})
    subtitles = project.subtitles_srt('zh').read_text()
    (dest / 'subtitles.zh.srt').write_text(subtitles)
    return {'film': ffmpeg.probe(Path(settings.film)), 'segments': project.read_json(project.segments_json),
            'shots': shots, 'timeline': rendered, 'content_end': round(cursor, 3),
            'sources': knowledge.sources(project), 'evidence': project.read_json(project.script_evidence_json)['units'],
            'timing': {'voice': timing['voice'], 'source': timing['source'],
                       'units': [{k: u[k] for k in ('id', 'start', 'end')} for u in timing['units']]},
            'narration_url': narration_url, 'subtitles': subtitles}


def export(film: Path, dest: Path, source_dir: Path, evidence_project: Path | None = None, film_manifest: Path | None = None, video_url: str | None = None, finished_project: Path | None = None, narration_url: str | None = None) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    records = []
    for path in sorted(source_dir.glob('*.json')):
        record = knowledge.Source.model_validate_json(path.read_text()).model_dump()
        record['id'] = path.stem
        records.append(record)
    frames = []
    for seconds, caption in [(196, '伸手接近小龙：亲近关系'), (610, '成年龙的近景：体量与关系的变化'), (669, '辛特尔的灰发：时间流逝的可见线索')]:
        name = f'frame-{seconds}.jpg'
        ffmpeg.extract_frame(film, seconds, dest / name)
        frames.append({'time': seconds, 'file': name, 'caption': caption})
    data = {'title': 'Sintel · 从照料到悲剧', 'kind': 'prepared_analysis_study',
            'sources': records, 'chunks': knowledge.chunks(records), 'frames': frames,
            'source_url': 'https://download.blender.org/durian/movies/Sintel.2010.720p.mkv.zip',
            'license_url': 'https://creativecommons.org/licenses/by/3.0/',
            'attribution': '© copyright Blender Foundation | www.sintel.org',
            'changes': '从原片提取并缩小截图，另写中文解读草稿；不是新的已渲染解说成片。'}
    if evidence_project:
        saved = knowledge.answers(Project(evidence_project))
        if not saved:
            raise ValueError('Run mococo knowledge suggest before exporting a live run')
        data['saved_run'] = saved[-1]
        project = Project(evidence_project)
        if project.timeline_json.exists():
            from mococo.stages.images import validate_timeline
            data['external_images'] = []
            for record in validate_timeline(project, project.read_json(project.timeline_json)):
                name = Path(record['file']).name
                shutil.copyfile(project.retrieval_dir / record['file'], dest / name)
                data['external_images'].append({**record, 'file': name})
    if film_manifest:
        if not video_url or not video_url.startswith('https://'):
            raise ValueError('Provide an HTTPS --video-url for the completed film')
        movie = json.loads(film_manifest.read_text())
        data['movie'] = {k: movie[k] for k in ('title', 'author', 'duration', 'chapters', 'script', 'sha256', 'production')}
        data['movie']['url'] = video_url
        data['kind'] = 'finished_analysis_film'
        data['changes'] = '电影片段经重剪，添加中文解说、字幕、章节与署名；概念图作为制作资料插入。'
    if finished_project:
        if not film_manifest or not narration_url:
            raise ValueError('Finished workflow requires --film-manifest and --narration-url')
        project = Project(finished_project)
        if project.script_md('zh').read_text() != data['movie']['script']:
            raise ValueError('Project script differs from the published film manifest')
        data['workflow'] = export_workflow(project, dest, narration_url)
    (dest / 'study.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    for path in source_dir.glob('*.json'):
        (dest / path.name).write_bytes(path.read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--film', required=True, type=Path)
    parser.add_argument('--dest', required=True, type=Path)
    parser.add_argument('--source-dir', type=Path, default=Path('mococo/examples/sintel'))
    parser.add_argument('--evidence-project', type=Path, help='Optional project containing a real, saved RAG run')
    parser.add_argument('--film-manifest', type=Path, help='Manifest of a completed commentary video')
    parser.add_argument('--video-url', help='Published HTTPS video URL')
    parser.add_argument('--finished-project', type=Path, help='Completed project used to render this video')
    parser.add_argument('--narration-url', help='Published narration audio URL')
    args = parser.parse_args()
    export(args.film, args.dest, args.source_dir, args.evidence_project, args.film_manifest, args.video_url, args.finished_project, args.narration_url)


if __name__ == '__main__':
    main()
