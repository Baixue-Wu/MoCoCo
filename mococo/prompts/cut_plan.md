You are assembling a rough cut for a $style_label movie commentary about "$title".

Narration units in order, each with its spoken duration in seconds and the
ranked candidate shots (id, duration available, score, why):

$units

Pacing guidance: $pacing

For each unit choose an ordered list of clips that together fill the unit's
narration duration (within +-10%). Each clip: {shot_id, seconds}. Use each
shot's available duration; you may take a portion of a long shot. Rules:
- prefer higher-scored candidates, but keep visual variety and chronological
  flow across neighbouring units
- do not reuse a shot in two units unless nothing else fits
- clips shorter than $min_clip seconds are not allowed
- a unit may hold one long clip or several short ones depending on the pacing guidance

Return only JSON matching the schema: {"units": [{"id", "clips": [{"shot_id", "seconds"}]}]}.
