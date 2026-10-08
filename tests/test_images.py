import io
from pathlib import Path

import pytest
from PIL import Image

from mococo.project import init_project
from mococo.provider import images as provider
from mococo.stages import cut, images, render
from mococo.media import ffmpeg


@pytest.fixture
def project(tmp_path):
    film = tmp_path / 'film.mp4'
    film.write_bytes(b'fixture')
    p = init_project(tmp_path / 'project', film)
    p.write_json(p.segments_json, {'primary_lang': 'zh', 'units': [{'id': 'u001', 'text': {'zh': '资料图测试'}}]})
    p.write_json(p.candidates_json, {'units': [{'unit_id': 'u001', 'shots': [], 'external': []}]})
    p.write_json(p.timeline_json, {'units': [{'id': 'u001', 'clips': []}]})
    return p


def record():
    return dict(id='123', title='File:Test.png', image_url='https://upload.wikimedia.org/test.png',
                source_url='https://commons.wikimedia.org/wiki/File:Test.png', artist='Test Artist',
                license='CC BY 3.0', license_url='https://creativecommons.org/licenses/by/3.0/',
                caption='Test concept art', credit='Own work', restrictions='')


def install_provider(monkeypatch):
    data = io.BytesIO()
    Image.new('RGB', (80, 60), 'green').save(data, 'PNG')
    monkeypatch.setattr(provider, 'query', lambda **kwargs: [record()])
    monkeypatch.setattr(provider, 'download', lambda url: data.getvalue())


def test_search_does_not_insert_and_approval_is_revocable(project, monkeypatch):
    install_provider(monkeypatch)
    images.search(project, 'u001', 'concept art')
    assert images.preview(project, 'u001', '123').is_file()
    assert not project.read_json(project.timeline_json)['units'][0]['clips']
    approved = images.approve(project, 'u001', '123')
    timeline = project.read_json(project.timeline_json)
    assert timeline['units'][0]['clips'][0]['image_id'] == '123'
    assert (project.retrieval_dir / approved['file']).exists()
    assert images.validate_timeline(project, timeline)[0]['artist'] == 'Test Artist'
    images.revoke(project, 'u001', '123')
    assert not project.read_json(project.timeline_json)['units'][0]['clips']
    with pytest.raises(ValueError, match='no approved'):
        images.validate_timeline(project, timeline)


def test_unknown_image_and_changed_license_are_rejected(project, monkeypatch):
    install_provider(monkeypatch)
    images.search(project, 'u001', 'concept art')
    with pytest.raises(ValueError, match='not among'):
        images.approve(project, 'u001', '999')
    monkeypatch.setattr(provider, 'query', lambda **kwargs: [])
    with pytest.raises(ValueError, match='no longer eligible'):
        images.approve(project, 'u001', '123')
    assert not provider.allowed_license('CC BY-SA 4.0', 'https://creativecommons.org/licenses/by-sa/4.0/')
    assert not provider.allowed_license('CC BY 3.0', 'https://fake.example/licenses/by/3.0/')
    assert not provider.allowed_license('CC BY-NC 3.0', 'https://creativecommons.org/licenses/by-nc/3.0/')
    assert provider.allowed_license('CC0', 'https://creativecommons.org/publicdomain/zero/1.0/')


def test_real_ffmpeg_renders_insert_and_attribution_cards(project, monkeypatch):
    install_provider(monkeypatch)
    images.search(project, 'u001', 'concept art')
    images.approve(project, 'u001', '123')
    # Real tiny media, silence in place of TTS. No provider is called.
    ffmpeg.run(['-f', 'lavfi', '-i', 'color=c=black:s=128x72:r=25', '-f', 'lavfi',
                '-i', 'anullsrc=r=48000:cl=stereo', '-t', '1', '-c:v', 'libx264', '-c:a', 'aac', project.load().film])
    project.narration_audio('zh').parent.mkdir(parents=True, exist_ok=True)
    ffmpeg.run(['-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-t', '1', str(project.narration_audio('zh'))])
    project.write_json(project.shots_json, [])
    project.write_json(project.narration_timing('zh'), {'units': [{'id': 'u001', 'start': 0, 'end': 1}]})
    cut.run(project, force=True)
    assert project.read_json(project.timeline_json)['units'][0]['clips'][0]['image_id'] == '123'
    settings = project.load(); settings.subtitle_langs = []; project.save(settings)
    output = render.render_lang(project, 'zh', force=True, workers=1)
    assert ffmpeg.probe(output)['duration'] >= 8.9
    assert 'Test Artist' in project.image_credits_md.read_text()
    assert 'https://creativecommons.org/licenses/by/3.0/' in project.image_credits_md.read_text()
    assert (project.render_dir / 'credit-123.png').exists()
