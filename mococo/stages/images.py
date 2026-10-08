"""Search contextual images, approve inserts, and preserve export attribution."""
from __future__ import annotations

import hashlib
import io
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from mococo.project import Project
from mococo.provider import images as provider


def _unit(project: Project, unit_id: str):
    units = project.read_json(project.segments_json)['units']
    if not any(u['id'] == unit_id for u in units):
        raise ValueError('Unknown commentary unit; segment the script and refresh first')


def search(project: Project, unit_id: str, query: str, limit: int = 8) -> dict:
    _unit(project, unit_id)
    found = provider.query(search=query, limit=limit)
    data = project.read_json(project.image_search_json) if project.image_search_json.exists() else {}
    data[unit_id] = {'query': query, 'results': found, 'status': 'found' if found else 'no_eligible_images'}
    project.write_json(project.image_search_json, data)
    if project.candidates_json.exists():
        candidates = project.read_json(project.candidates_json)
        for unit in candidates['units']:
            if unit['unit_id'] == unit_id:
                unit.pop('image_search_error', None)
        project.write_json(project.candidates_json, candidates)
    project.log_event('image_search', unit=unit_id, query=query, results=len(found))
    return data[unit_id]


def preview(project: Project, unit_id: str, image_id: str) -> Path:
    """Cache a search thumbnail without approving or inserting it."""
    _unit(project, unit_id)
    saved = project.read_json(project.image_search_json).get(unit_id, {}) if project.image_search_json.exists() else {}
    record = next((r for r in saved.get('results', []) if r['id'] == image_id), None)
    if not record:
        raise ValueError('Image is not among this unit’s search results; search again')
    name = hashlib.sha256(record['image_url'].encode()).hexdigest()[:24] + '.jpg'
    path = project.image_preview_dir / name
    if not path.exists():
        contents = provider.download(record['image_url'])
        with Image.open(io.BytesIO(contents)) as image:
            if image.width * image.height > 20_000_000:
                raise ValueError('Image resolution is too large; select a smaller image')
            image = image.convert('RGB')
            image.thumbnail((480, 480))
            path.parent.mkdir(parents=True, exist_ok=True)
            image.save(path, quality=85)
    return path


def approve(project: Project, unit_id: str, image_id: str) -> dict:
    _unit(project, unit_id)
    saved = project.read_json(project.image_search_json).get(unit_id, {}) if project.image_search_json.exists() else {}
    candidate = next((r for r in saved.get('results', []) if r['id'] == image_id), None)
    if not candidate:
        raise ValueError('Image is not among this unit’s search results; search again')
    refreshed = provider.query(page_id=image_id)
    if not refreshed:
        raise ValueError('Image license or metadata is no longer eligible; choose another image')
    record = refreshed[0]
    if any(record[k] != candidate[k] for k in ('artist', 'license', 'license_url', 'title')):
        raise ValueError('Image attribution changed; search again and review its updated terms')
    candidates = project.read_json(project.candidates_json)
    target = next((c for c in candidates['units'] if c['unit_id'] == unit_id), None)
    if not target:
        raise ValueError('Run shot retrieval for this unit before approving an image')
    timeline = project.read_json(project.timeline_json) if project.timeline_json.exists() else None
    timeline_unit = next((u for u in timeline['units'] if u['id'] == unit_id), None) if timeline else None
    if timeline and timeline_unit is None:
        raise ValueError('Timeline no longer contains this unit; rerun cut before inserting')
    contents = provider.download(record['image_url'])
    with Image.open(io.BytesIO(contents)) as image:
        if image.width * image.height > 20_000_000:
            raise ValueError('Image resolution is too large; select a smaller image')
        image.load()
        image = image.convert('RGB')
        image.thumbnail((1280, 1280))
        filename = f'commons-{image_id}-{hashlib.sha256(contents).hexdigest()[:12]}.jpg'
        project.external_dir.mkdir(parents=True, exist_ok=True)
        image.save(project.external_dir / filename, quality=92)
    record.update(file=f'external/{filename}', approved=True,
                  changes='Resized and converted to JPEG; inserted as contextual illustration, not original film footage.')
    target['external'] = [r for r in target.get('external', []) if r.get('id') != image_id] + [record]
    project.write_json(project.candidates_json, candidates)
    if timeline_unit is not None:
        timeline_unit['clips'] = [c for c in timeline_unit['clips'] if c.get('image_id') != image_id]
        timeline_unit['clips'].insert(0, clip(record))
        project.write_json(project.timeline_json, timeline)
    project.log_event('image_approved', unit=unit_id, image_id=image_id)
    return record


def clip(record: dict) -> dict:
    return {'kind': 'image', 'file': record['file'], 'caption': record['caption'],
            'seconds': 3.5, 'image_id': record['id'], 'attribution': record,
            'why': 'Creator-approved contextual image'}


def revoke(project: Project, unit_id: str, image_id: str) -> None:
    candidates = project.read_json(project.candidates_json)
    for unit in candidates['units']:
        if unit['unit_id'] == unit_id:
            unit['external'] = [r for r in unit.get('external', []) if r.get('id') != image_id]
    project.write_json(project.candidates_json, candidates)
    if project.timeline_json.exists():
        timeline = project.read_json(project.timeline_json)
        for unit in timeline['units']:
            if unit['id'] == unit_id:
                unit['clips'] = [c for c in unit['clips'] if c.get('image_id') != image_id]
        project.write_json(project.timeline_json, timeline)
    project.log_event('image_revoked', unit=unit_id, image_id=image_id)


def validate_timeline(project: Project, timeline: dict) -> list[dict]:
    registered = project.read_json(project.candidates_json) if project.candidates_json.exists() else {'units': []}
    approved = {(u['unit_id'], r['file']): r for u in registered['units']
                for r in u.get('external', []) if r.get('approved')}
    used = {}
    for unit in timeline['units']:
        for item in unit['clips']:
            if item.get('kind') != 'image':
                continue
            record = approved.get((unit['id'], item['file']))
            if not record or not provider.allowed_license(record['license'], record['license_url']):
                raise ValueError('An image has no approved license record; remove it or approve it through image search')
            path = (project.retrieval_dir / item['file']).resolve()
            if not path.is_relative_to(project.external_dir.resolve()) or not path.is_file():
                raise ValueError('Approved image file is missing or outside the image folder; approve it again')
            used[record['id']] = record
    return list(used.values())


def credit_artifacts(project: Project, records: list[dict]) -> list[Path]:
    """Create a sidecar and visible credit cards for the exported movie."""
    project.render_dir.mkdir(parents=True, exist_ok=True)
    lines = ['# External image credits', 'Images are contextual illustrations, not original film footage.']
    cards = []
    for record in records:
        detail = [record['title'], record['artist'], record['license'], record['source_url'],
                  record['license_url'], record['changes']]
        lines.append('\n\n'.join(detail))
        canvas = Image.new('RGB', (1280, 720), '#101719')
        draw = ImageDraw.Draw(canvas)
        font = ImageFont.load_default(size=26)
        text = '\n'.join(textwrap.fill(line, 78) for line in ['EXTERNAL IMAGE CREDITS', *detail])
        draw.multiline_text((48, 40), text, font=font, fill='white', spacing=10)
        card = project.render_dir / f"credit-{record['id']}.png"
        canvas.save(card)
        cards.append(card)
    project.image_credits_md.write_text('\n\n'.join(lines)+'\n', encoding='utf-8')
    project.write_json(project.render_dir / 'image-credits.json', records)
    return cards
