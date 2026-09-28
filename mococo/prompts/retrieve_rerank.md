You are choosing footage for one paragraph of a movie commentary about "$title".

Paragraph (the narration the viewer will hear):
"$text"

Desired mood: $mood
Ideal footage: $visual_query

Candidate shots, each with id, time range, description, mood, and dialogue:

$candidates

Rank the candidates from best to worst fit for this paragraph. Judge on:
1. semantic match: the shot shows what the narration talks about
2. affective match: the shot's tone fits the desired mood
3. chronology: for plot narration, prefer shots from the part of the film the
   paragraph describes
4. variety: avoid near-duplicate shots in the top ranks

Return JSON with "ranked": a list of objects {id, score (0-100), why (one short
sentence in English), why_zh (the same sentence in Chinese)} covering every
candidate id once.
