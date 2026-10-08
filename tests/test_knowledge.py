import pytest
from fastapi.testclient import TestClient

from mococo import knowledge
from mococo.project import init_project
from mococo.server.app import create_app
from mococo.stages import script


@pytest.fixture
def project(tmp_path):
    film = tmp_path / 'film.mp4'
    film.write_bytes(b'test')
    return init_project(tmp_path / 'projects' / 'film', film, style='analysis')


def source(text='The dragon wound is a visual motif. 伤痕意象帮助观众重新识别小龙。'):
    return knowledge.Source(title='Review notes', author='Reviewer', url='https://example.org/review',
                            rights='Original test notes', text=text)


def test_retrieval_is_scoped_located_and_excludes_irrelevant_sources(project):
    record = knowledge.add_source(project, source())
    knowledge.add_source(project, source('Production used open source rendering software and a volunteer team.'))
    hits = knowledge.search(project, 'dragon wound')
    assert len(hits) == 1
    assert hits[0]['source_id'] == record['id']
    assert hits[0]['text'] == record['text'][hits[0]['start']:hits[0]['end']]
    assert knowledge.search(project, '伤痕')[0]['source_id'] == record['id']
    assert not knowledge.search(project, 'unrelated topic')
    assert len(knowledge.sources(project)) == 2
    knowledge.add_source(project, source())
    assert len(knowledge.sources(project)) == 2


def test_empty_retrieval_never_calls_model(project, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('No model call is allowed when evidence is missing')
    monkeypatch.setattr(knowledge.llm, 'ask', forbidden)
    answer = knowledge.suggest(project, 'What evidence supports this?')
    assert answer['gaps'] and not answer['claims']
    with pytest.raises(ValueError, match='Missing evidence'):
        knowledge.review(project, answer['id'], True)


def model_answer(project):
    chunk = knowledge.search(project, 'wound')[0]
    return {'claims': [{'text': 'The wound may support recognition.', 'kind': 'interpretation',
                        'citations': [chunk['id']], 'visual_query': 'dragon wing wound'}], 'gaps': []}


def test_citations_approval_and_source_changes(project, monkeypatch):
    record = knowledge.add_source(project, source())
    output = model_answer(project)
    seen = []
    monkeypatch.setattr(knowledge.llm, 'ask', lambda prompt, **kw: seen.append(prompt) or output)
    answer = knowledge.suggest(project, 'wound')
    assert record['url'] in seen[0] and record['text'] in seen[0]
    assert not answer['accepted']
    assert 'No approved' in knowledge.accepted_context(project)
    knowledge.review(project, answer['id'], True)
    assert output['claims'][0]['text'] in knowledge.accepted_context(project)
    knowledge.remove_source(project, record['id'])
    with pytest.raises(ValueError, match='Sources changed'):
        knowledge.accepted_context(project)
    knowledge.review(project, answer['id'], False)
    assert 'No approved' in knowledge.accepted_context(project)


def test_fabricated_citation_is_rejected_without_saving(project, monkeypatch):
    knowledge.add_source(project, source())
    output = model_answer(project)
    output['claims'][0]['citations'] = ['invented-source']
    monkeypatch.setattr(knowledge.llm, 'ask', lambda *a, **kw: output)
    with pytest.raises(ValueError, match='unretrieved citations'):
        knowledge.suggest(project, 'wound')
    assert knowledge.answers(project) == []


def test_accepted_context_reaches_draft_and_provenance_file(project, monkeypatch):
    knowledge.add_source(project, source())
    monkeypatch.setattr(knowledge.llm, 'ask', lambda *a, **kw: model_answer(project))
    answer = knowledge.suggest(project, 'wound')
    knowledge.review(project, answer['id'], True)
    monkeypatch.setattr(script, '_transcript_text', lambda p: 'dialogue')
    monkeypatch.setattr(script, '_shot_summaries', lambda p: 'dragon')
    seen = []
    monkeypatch.setattr(knowledge.llm, 'ask', lambda prompt, **kw: seen.append(prompt) or 'A creator draft.')
    script.draft(project)
    assert 'The wound may support recognition.' in seen[0]
    assert project.script_md('zh').read_text().strip() == 'A creator draft.'
    assert project.read_json(project.script_evidence_json)['source_revision'] == knowledge.fingerprint(project)


def test_api_validates_urls_and_project_scopes(project):
    client = TestClient(create_app(project.root.parent))
    path = '/api/projects/film/knowledge'
    payload = source().model_dump()
    assert client.post(path + '/sources', json={**payload, 'url': 'javascript:alert(1)'}).status_code == 422
    record = client.post(path + '/sources', json=payload).json()
    assert client.post(path + '/search', json={'query': 'wound'}).json()[0]['source_id'] == record['id']
    assert client.post(path + '/search', json={'query': '', 'limit': 100}).status_code == 400
    assert client.get('/api/projects/missing/knowledge').status_code == 404
    assert client.delete(path + '/sources/' + record['id']).status_code == 200
    assert client.get(path).json()['sources'] == []
