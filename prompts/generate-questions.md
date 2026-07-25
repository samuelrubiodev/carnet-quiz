# Generate questions

Use only the valid concepts in `concepts.json` and the supporting evidence in the
current job's `transcript.json`.

Generate a varied bank of self-contained examination-style questions and write
them to `questions.json`.

Every question must:

- be understandable without watching the video;
- be answerable without reading the transcript;
- contain all context necessary to identify the correct answer;
- be supported exclusively by the cited transcript segments;
- include valid source segment IDs and source start and end times;
- contain three or four plausible and distinct options;
- have exactly one `correct_option`;
- include a concise, self-contained explanation;
- use a supported question type and difficulty value;
- use a stable, readable identifier;
- reference an existing concept.

The video and transcript are evidence sources only. Never refer to them in the
visible question content.

The question, options and explanation must not mention or imply:

- the video;
- this video;
- the lesson;
- this lesson;
- the course;
- the explanation;
- the previous explanation;
- the instructor;
- the professor;
- the teacher;
- the narrator;
- the speaker;
- the transcript;
- what was said;
- what was mentioned;
- what was explained;
- the previous content;
- the text above;
- any equivalent source-dependent wording.

Incorrect:

- "According to the video, who is considered a driver?"
- "Who does the explanation call a driver?"
- "What does the instructor say about this signal?"
- "As previously explained, what is the maximum speed?"

Correct:

- "Who is considered a driver?"
- "Which signal has priority in this situation?"
- "What is the maximum permitted speed?"
- "What must the driver do in this situation?"

Do not use deictic expressions such as "this case", "this vehicle", "the previous
situation" or "the signal shown" unless the complete case, vehicle or signal is
explicitly described within the question itself.

Generate varied question types when the evidence permits, including:

- direct questions;
- definitions;
- comparisons;
- practical cases;
- priorities;
- obligations;
- prohibitions;
- exceptions;
- carefully written negative questions.

Avoid:

- ambiguity;
- double negatives;
- incomplete scenarios;
- trivia about the video;
- obvious or absurd distractors;
- options that overlap;
- several options that could reasonably be correct;
- grammatical clues;
- always placing the correct answer in the same position;
- making the correct option consistently longer or more detailed;
- near-duplicate questions;
- superficial rewrites of the same question;
- knowledge not present in the transcript.

Negative questions must clearly emphasize words such as `NOT`, `INCORRECT` or
`EXCEPT`.

The explanation must state why the selected option is correct. It must not say
merely that the video, instructor or transcript says so.

Before accepting each question, verify:

1. Would it make complete sense to someone who has never seen the video?
2. Can its answer be demonstrated using the cited segments?
3. Is exactly one option correct?
4. Are all distractors plausible but incorrect according to the same evidence?
5. Does it avoid every reference to the source or lesson?
6. Is it meaningfully different from the other questions?

If any answer is no, rewrite or omit the question.