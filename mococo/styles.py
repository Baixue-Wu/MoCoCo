"""Everything the code knows about the two commentary styles lives here."""

STYLES = {
    "recap": {
        "label": {"en": "plot recap", "zh": "剧情速递"},
        "guidance": (
            "A fast, engaging plot rundown in the style of popular 'watch the whole movie "
            "in minutes' channels. Narrate what happens, keep the viewer oriented, add light "
            "humour or suspense, and keep every sentence moving the story forward."
        ),
        "pacing": "brisk: clips of 2-5 seconds, several per unit, cut on action",
        "chars_per_minute": {"zh": 270, "en": 900},
        "min_clip": 1.5,
        "max_clip": 6.0,
    },
    "analysis": {
        "label": {"en": "film analysis", "zh": "深度解析"},
        "guidance": (
            "A thoughtful analysis in the style of a video essayist: motifs, foreshadowing, "
            "framing and colour choices, what the director is doing and why. Plot is "
            "summarised only as far as needed to make each point. Reference production "
            "context when it illuminates a choice."
        ),
        "pacing": "measured: clips of 4-10 seconds, let shots breathe, one or two per unit",
        "chars_per_minute": {"zh": 230, "en": 780},
        "min_clip": 3.0,
        "max_clip": 12.0,
    },
}


def get(style: str) -> dict:
    if style not in STYLES:
        raise KeyError(f"unknown style {style!r}; choose one of {list(STYLES)}")
    return STYLES[style]
