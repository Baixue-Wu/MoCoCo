"""Command line entry. Only this file may exit; everything else raises."""

from __future__ import annotations

from pathlib import Path

import typer
from rich import print as rprint

from mococo.project import Project, init_project

app = typer.Typer(help="MoCoCo: Movie Commentary Co-creation.", no_args_is_help=True)
script_app = typer.Typer(help="Draft and segment the commentary script.", no_args_is_help=True)
app.add_typer(script_app, name="script")
knowledge_app = typer.Typer(help="Import, retrieve and review external evidence.", no_args_is_help=True)
app.add_typer(knowledge_app, name="knowledge")
images_app = typer.Typer(help="Retrieve and approve reusable contextual images.", no_args_is_help=True)
app.add_typer(images_app, name="images")


@images_app.command("search")
def images_search(project: Path, unit_id: str, query: str, limit: int = 8):
    """Search Commons for attributed reusable images, without inserting them."""
    from mococo.stages import images
    rprint(images.search(Project(project), unit_id, query, limit))


@images_app.command("approve")
def images_approve(project: Path, unit_id: str, image_id: str):
    """Recheck the license, download and insert an image into this unit."""
    from mococo.stages import images
    rprint(images.approve(Project(project), unit_id, image_id))


@images_app.command("revoke")
def images_revoke(project: Path, unit_id: str, image_id: str):
    """Remove an image from this unit's candidates and timeline."""
    from mococo.stages import images
    images.revoke(Project(project), unit_id, image_id)



@knowledge_app.command("add")
def knowledge_add(project: Path, source: Path):
    """Import a source JSON with title, url, author, kind, rights and text."""
    from mococo import knowledge
    rprint(knowledge.add_source(Project(project), knowledge.Source.model_validate_json(source.read_text(encoding="utf-8"))))


@knowledge_app.command("search")
def knowledge_search(project: Path, query: str, limit: int = 5):
    """Retrieve source passages without calling a model."""
    from mococo import knowledge
    rprint(knowledge.search(Project(project), query, limit))


@knowledge_app.command("suggest")
def knowledge_suggest(project: Path, query: str, limit: int = 5):
    """Generate a cited suggestion from retrieved passages; does not accept it."""
    from mococo import knowledge
    rprint(knowledge.suggest(Project(project), query, limit))


@knowledge_app.command("review")
def knowledge_review(project: Path, answer_id: str, accept: bool = False):
    """Accept with --accept, or revoke a previous acceptance."""
    from mococo import knowledge
    rprint(knowledge.review(Project(project), answer_id, accept))



def _langs(value: str) -> list[str]:
    langs = [v.strip() for v in value.split(",") if v.strip()]
    bad = [l for l in langs if l not in ("zh", "en")]
    if bad:
        raise typer.BadParameter(f"unknown language(s) {bad}; use zh, en, or zh,en")
    return langs


@app.command()
def init(
    project: Path = typer.Argument(..., help="Project folder to create"),
    film: Path = typer.Option(..., help="Path to the film file"),
    title: str = typer.Option(None, help="Film title (defaults to file name)"),
    style: str = typer.Option("recap", help="recap | analysis"),
    langs: str = typer.Option("zh", help="Script languages, e.g. zh, en, or zh,en"),
    subtitles: str = typer.Option(None, help="Subtitle languages (default: same as --langs)"),
    voices: str = typer.Option(None, help="Voiceover languages (default: same as --langs)"),
    minutes: float = typer.Option(5.0, help="Target narration length in minutes"),
    brief: str = typer.Option("", help="One paragraph on what the video should say"),
):
    """Create a project folder with project.json."""
    script_langs = _langs(langs)
    p = init_project(
        project,
        film,
        title=title,
        style=style,
        script_langs=script_langs,
        subtitle_langs=_langs(subtitles) if subtitles else script_langs,
        voice_langs=_langs(voices) if voices else script_langs,
        target_minutes=minutes,
        brief=brief,
    )
    rprint(f"[green]created[/] {p.settings_path}")


@app.command()
def ingest(
    project: Path,
    force: bool = typer.Option(False, help="Redo every step even if outputs exist"),
    whisper: str = typer.Option("small", help="faster-whisper model size: tiny|base|small|medium|large-v3"),
    workers: int = typer.Option(4, help="Parallel caption requests"),
    max_captions: int = typer.Option(320, help="Representative shots to caption across the film"),
):
    """Detect shots, extract keyframes, transcribe, caption, and index the film."""
    from mococo.stages import ingest as stage

    summary = stage.run(
        Project(project), force=force, whisper_size=whisper,
        workers=workers, max_captions=max_captions,
    )
    rprint(summary)


@script_app.command("draft")
def script_draft(project: Path, lang: str = typer.Option(None, help="zh | en; default: every script language"), force: bool = False):
    """Let the model draft the commentary script from the brief, transcript, and shots."""
    from mococo.stages import script as stage

    for path in stage.draft(Project(project), lang=lang, force=force):
        rprint(f"[green]wrote[/] {path}")


@script_app.command("segment")
def script_segment(project: Path, force: bool = False):
    """Split script.<lang>.md into units with intent, mood, and search queries."""
    from mococo.stages import script as stage

    path = stage.segment(Project(project), force=force)
    rprint(f"[green]wrote[/] {path}")


@app.command()
def retrieve(project: Path, top: int = typer.Option(6, help="Candidates kept per unit"), force: bool = False):
    """Find candidate shots (and external references) for every script unit."""
    from mococo.stages import retrieve as stage

    path = stage.run(Project(project), top=top, force=force)
    rprint(f"[green]wrote[/] {path}")


@app.command()
def cut(project: Path, force: bool = False):
    """Assemble candidates into a timed timeline."""
    from mococo.stages import cut as stage

    path = stage.run(Project(project), force=force)
    rprint(f"[green]wrote[/] {path}")


@app.command()
def voice(project: Path, lang: str = typer.Option(None), force: bool = False):
    """Synthesize narration (or align an uploaded one) per language."""
    from mococo.stages import voice as stage

    for path in stage.run(Project(project), lang=lang, force=force):
        rprint(f"[green]wrote[/] {path}")


@app.command()
def render(project: Path, lang: str = typer.Option(None), force: bool = False):
    """Cut clips, mux narration and subtitles, write the final mp4."""
    from mococo.stages import render as stage

    for path in stage.run(Project(project), lang=lang, force=force):
        rprint(f"[green]wrote[/] {path}")


@app.command()
def run(project: Path, force: bool = False):
    """Run every stage in order."""
    from mococo.stages import cut, ingest, render, retrieve, script, voice

    p = Project(project)
    rprint(ingest.run(p, force=force))
    script.draft(p, force=force)
    script.segment(p, force=force)
    retrieve.run(p, force=force)
    cut.run(p, force=force)
    voice.run(p, force=force)
    for path in render.run(p, force=force):
        rprint(f"[green]wrote[/] {path}")


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8765, projects: Path = typer.Option(Path("projects"), help="Folder holding project folders")):
    """Start the local web app."""
    import uvicorn

    from mococo.server.app import create_app

    uvicorn.run(create_app(projects.resolve()), host=host, port=port)


def main():
    try:
        app()
    except Exception as e:  # library code raises; we exit here with the message intact
        rprint(f"[red]error:[/] {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
