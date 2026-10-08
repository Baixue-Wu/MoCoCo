"""Export a source-linked Sintel analysis study. Usage: uv run python scripts/export_analysis_example.py --film PATH --dest DIR"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from mococo import knowledge
from mococo.media import ffmpeg
from mococo.project import Project


def export(film: Path, dest: Path, source_dir: Path, evidence_project: Path | None = None, film_manifest: Path | None = None, video_url: str | None = None) -> None:
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
    lenses = [
        {'title': '从照料到伤害，为什么比单纯的战斗更悲伤？',
         'source_ids': ['review', 'observations'], 'frames': [196, 610],
         'draft': '先看辛特尔伸向小龙的手。身体的靠近，让保护成为一种可见的关系。影评人 Shashwat Pant 注意到，影片把早先的照料与后来的毁灭放在一起。我们可以沿着这条线索，把两个阶段并置：后面的对抗不只是一场动作戏，也使观众回头重看先前的亲密。',
         'gap': '这是借助影评展开的解读，不是导演意图的证明。单个面部近景不足以证明角色身份，必须结合前后情节。'},
        {'title': '人物与观众何时意识到时间已经过去？',
         'source_ids': ['observations'], 'frames': [196, 669],
         'draft': '这组画面比较的是辛特尔，而不只是在比较龙。早先的年轻面容和后来的灰发，让时间留下的变化变得可见。我们可以先呈现变化，再提出问题：她寻找的对象是否仍停留在记忆中的样子？这里把执念作为一种可能的理解，不替观众宣布唯一答案。',
         'gap': '这是依据片内画面提出的创作者解读。当前资料不能确定旅程持续了多少年，也没有导演访谈支持这一解释。'},
        {'title': 'RAG 如何帮助核实，而不是给观点贴上权威标签？',
         'source_ids': ['license', 'review'], 'frames': [610],
         'draft': '评价和事实需要分开：Pant 对表情表现力的赞赏，是评论者的判断；Blender Foundation 公布的开放许可，是可以回到官方页面核查的使用条件。我们保留解读的空间，同时把来源交给观众。',
         'gap': '影评的版权与电影的许可不同。截图保留电影署名；影评只提供链接和简短摘记。'},
    ]
    data = {'title': 'Sintel · 从照料到悲剧', 'kind': 'prepared_analysis_study',
            'sources': records, 'chunks': knowledge.chunks(records), 'frames': frames, 'lenses': lenses,
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
    args = parser.parse_args()
    export(args.film, args.dest, args.source_dir, args.evidence_project, args.film_manifest, args.video_url)


if __name__ == '__main__':
    main()
