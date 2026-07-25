# CarnetQuiz agent rules

These rules apply to every agent working in this repository.

## Source of truth

- Use only the current job's `transcript.json` as the factual source for generated concepts and questions.
- Never add external driving knowledge.
- Never complete an incomplete rule from memory.
- Never use information from another job, video, website or conversation.
- If the transcript evidence is insufficient or ambiguous, omit or reject the item.

## Evidence

- Every concept and question must cite existing transcript segment IDs.
- Every concept and question must include valid source start and end times.
- Cited segments must belong to the current job and remain inside its requested interval.
- Every correct answer and explanation must be directly demonstrated by the cited evidence.
- Source segment IDs and times are metadata only.

## Independent user-facing content

All concepts, questions, options and explanations must be understandable without watching the source video.

The source video, transcript and instructor must never be mentioned in visible question content.

Forbidden wording includes references to:

- The video.
- This video.
- The lesson.
- The course.
- The explanation.
- The instructor.
- The professor.
- The teacher.
- The narrator.
- The speaker.
- The transcript.
- What was said.
- What was explained.
- What was mentioned.
- Previous content.
- Text shown above.
- Equivalent source-dependent wording.

### Incorrect

> Who does the explanation in the video call a driver?

### Correct

> Who is considered a driver?

Do not use unresolved expressions such as:

- “This situation”.
- “The previous case”.
- “The vehicle mentioned”.
- “The signal shown”.
- “As explained above”.

These expressions may only be used when their complete context is included directly in the question.

A person who has never seen the source must be able to understand and answer each question from its own wording.

## Question quality

Every question must:

- Have three or four distinct and plausible options.
- Have exactly one correct answer.
- Reference an existing valid concept.
- Include a concise explanation.
- Avoid ambiguity and double negatives.
- Avoid obvious distractors.
- Avoid grammatical clues.
- Avoid duplicate and near-duplicate questions.
- Include every detail required to understand a practical case.

Negative questions must clearly emphasize terms such as `NOT`, `INCORRECT` or `EXCEPT`.

## Repository and database safety

- Never edit SQLite directly.
- Use the `carnetquiz` CLI or the approved MCP tools.
- Never execute arbitrary SQL.
- Respect the job-local JSON schemas.
- Validate every job before import.
- Import only with:

  ```bash
  carnetquiz job commit JOB_ID
  ```

- Do not write outside the repository or the current job directory.
- Do not modify unrelated files.
- Do not bypass validation.
- Do not mark a job as committed manually.

## Bounded workflow

For each job:

1. Generate once.
2. Review once.
3. Repair rejected items once at most.
4. Run deterministic validation.
5. Commit valid results or leave invalid items rejected.

Do not enter repeated generation, review or repair loops.

Do not regenerate an entire question bank to repair a small number of defective items.

After the permitted repair, reject any remaining invalid items and report them.

## Required completion report

At the end of a job, report:

- Job ID.
- Processed interval.
- Concepts generated.
- Questions generated.
- Questions validated.
- Questions rejected.
- Whether the job was committed.
- Any remaining errors.

Never claim that a command, validation or import succeeded unless it was actually executed successfully.