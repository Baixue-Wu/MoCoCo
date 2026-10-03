import json
from pathlib import Path

from fastapi.testclient import TestClient

from mococo.media import ffmpeg
from mococo.server.app import create_app


def test_browser_upload_creates_project_with_its_own_movie(tmp_path):
    projects = tmp_path / "projects"
    client = TestClient(create_app(projects))
    movie = tmp_path / "sample.mp4"
    ffmpeg.run(["-f", "lavfi", "-i", "color=c=black:s=64x64:r=1", "-t", "1", "-c:v", "libx264", str(movie)])
    data = {"settings": json.dumps({"slug": "visitor-film", "title": "访客的电影"})}
    files = {"file": ("电影.mp4", movie.read_bytes(), "video/mp4")}

    response = client.post("/api/projects/upload", data=data, files=files)
    assert response.status_code == 200, response.text
    assert response.json()["slug"] == "visitor-film"
    stored = Path(response.json()["settings"]["film"])
    assert stored == projects / "visitor-film" / "source" / "电影.mp4"
    assert stored.read_bytes() == movie.read_bytes()
    assert client.get("/api/projects/visitor-film").status_code == 200

    duplicate = client.post("/api/projects/upload", data=data, files=files)
    assert duplicate.status_code == 400
    assert stored.read_bytes() == movie.read_bytes()

    wrong_type = client.post(
        "/api/projects/upload",
        data={"settings": json.dumps({"slug": "wrong-type"})},
        files={"file": ("notes.txt", b"notes", "text/plain")},
    )
    assert wrong_type.status_code == 400
    assert not (projects / "wrong-type").exists()

    unreadable = client.post(
        "/api/projects/upload",
        data={"settings": json.dumps({"slug": "unreadable"})},
        files={"file": ("bad.mp4", b"not a movie", "video/mp4")},
    )
    assert unreadable.status_code == 400
    assert not (projects / "unreadable").exists()
