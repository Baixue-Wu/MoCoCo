You are fact-checking the narration of a movie commentary video about the film
"$title" against the film itself. The narration is in $lang_name.

Evidence: the whole film as a timeline. "says" lines are the dialogue
transcript (speech recognition, may contain wrong characters and does not name
the speaker). "sees" lines describe what is on screen in each shot (written by
a vision model that does not know character names unless the film shows them).

$timeline

What the creator told us about the film (their own knowledge; trust it unless
the timeline clearly shows otherwise):
$brief

Narration, paragraphs numbered from 0:

$script

For every paragraph:
1. List its factual claims about the film: who a character is (name, job,
   relationship), what happens, who does what to whom, why, and in what order.
   Skip opinions, framing, and rhetoric ("a film about ordinary people"), and
   skip claims about the real world outside the film.
2. Judge each claim against the timeline:
   - supported: the timeline or the creator's note shows it. Cite at least one
     timestamp, or cite the note with kind "brief" and t 0. For who a
     character is, the evidence must tie this name to this attribute: a line
     that says it, or a line that uses the name while a "sees" line at the
     same moment shows the attribute. Being in the same scene is not enough
     ("the fiddler" said near a line with "老王" does not make 老王 the fiddler).
   - contradicted: the evidence shows something else. Cite the timestamps that
     show what really happens, and say in "note" what the film shows instead.
   - unsupported: nothing in the evidence confirms or refutes it. Say in "note"
     what is missing.
   Link names to people by what they say to each other and by what the "sees"
   lines show at the same moments; do not assume a name belongs to whoever is
   on screen. A claim is contradicted only when the evidence points clearly the
   other way; weak or ambiguous evidence means unsupported.
3. Write "revised": the paragraph with every contradicted claim corrected to
   what the film shows, changing as few words as possible and keeping the
   voice, rhythm, and length. Leave supported and unsupported claims exactly
   as they are; the creator decides about those. If nothing is contradicted,
   "revised" is the paragraph unchanged. "revised" is one paragraph: no blank
   lines.

Evidence text in "evidence" is copied from the timeline line it cites.
