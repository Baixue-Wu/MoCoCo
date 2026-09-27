You are annotating shots from the film "$title" for a video editor who will later
pick shots to illustrate a commentary script.

You have looked at $n keyframe images. Image k corresponds to shot k in the list
below. Each entry gives the shot id, its time range, and any dialogue heard
during it (may be empty).

$shots

For every shot, return:
- id: the shot id exactly as given
- description_en: one or two factual sentences in English describing what is
  visible: who, where, what happens, framing (close-up / wide), lighting. No
  interpretation of themes.
- description_zh: the same content in natural Chinese.
- mood: 1 to 3 lowercase English words for the emotional tone (e.g. "tense",
  "tender", "calm, melancholic").
- characters: short list of visible people, by name if the dialogue or film
  makes it clear, else by role ("young woman", "old man").
- setting: a few words for the location and time of day.
- tags: 3 to 8 lowercase English keywords useful for search (objects, actions,
  motifs, shot type).

Return only JSON matching the schema.
