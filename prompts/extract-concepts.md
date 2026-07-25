# Extract concepts

Read only the current job's `transcript.json`.

Extract all distinct examinable concepts that are explicitly supported by the
transcript. Write them to `concepts.json` using stable, readable identifiers.

Prioritize:

- rules;
- priorities;
- prohibitions;
- obligations;
- exceptions;
- definitions;
- figures, distances, speeds and time limits;
- differences between similar concepts;
- practical cases that could reasonably become exam questions.

Exclude:

- greetings;
- jokes;
- filler;
- repetitions;
- personal opinions;
- references to the course or lesson structure;
- comments about what the instructor will explain later;
- information that is not relevant to an examination.

Every concept must:

- cite one or more existing transcript segment IDs;
- include valid source start and end times;
- be completely supported by the cited evidence;
- contain no external facts;
- remain understandable outside the context of the video;
- use neutral, self-contained wording;
- avoid references to the video, transcript, explanation, instructor, narrator
  or speaker.

The transcript is evidence only. Do not write concepts such as:

- "What the instructor says about drivers";
- "Definition explained in the video";
- "Rule mentioned in this lesson".

Write instead:

- "Definition of driver";
- "Priority of traffic signals";
- "Maximum speed on a conventional road".

Source references belong only in the metadata fields. They must not be part of
the concept title or summary.

Merge concepts that express the same rule. Do not create several concepts merely
because the same information appears in different transcript segments.

Do not infer missing details, complete incomplete rules from memory or correct
the transcript using external driving knowledge. When the evidence is
insufficient or ambiguous, omit the concept.