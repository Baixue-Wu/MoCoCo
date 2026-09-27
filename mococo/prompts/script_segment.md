Split a movie commentary script into units for video editing. The film is
"$title". The script is in $lang_name.

Script (paragraphs separated by blank lines):

$script

For each paragraph, in order, return one unit with:
- id: "u001", "u002", ...
- text: the paragraph text verbatim
- intent: one of "hook", "plot", "character", "theme", "technique", "context", "closing"
- mood: 1 to 3 lowercase English words for the emotional tone the visuals should carry
- visual_query_en: one English sentence describing the ideal footage for this
  paragraph (who, where, doing what, framing), written for a visual search engine
- keywords: 3 to 8 lowercase English keywords (characters, objects, places, actions)
- needs_context: true when the paragraph makes a claim about production history,
  cultural reference, or director intent that the film's own footage cannot
  show; false otherwise
- context_query: when needs_context is true, a short web search query in English
  that would find a reference image or source; else empty string

Keep paragraph text exactly as given, never merge or split paragraphs.
Return only JSON matching the schema.
