# Process a pending CarnetQuiz job

Process exactly one pending CarnetQuiz job.

## Initial preparation

First, read the repository's `AGENTS.md`.

Find one job in state `ready` using:

```bash
carnetquiz job list
```

Read only the selected job's:

- `context.md`
- `request.json`
- `transcript.json`
- Local JSON schemas

Do not use another job's files.

## Required workflow

1. Extract examinable concepts into `concepts.json`.
2. Generate questions into `questions.json`.
3. Perform exactly one review.
4. Write the review result to `review.json`.
5. Repair rejected items at most once.
6. Run:

   ```bash
   carnetquiz job validate JOB_ID
   ```

7. If the valid result is suitable for import, run:

   ```bash
   carnetquiz job commit JOB_ID
   ```

Do not edit SQLite directly.

## Evidence rules

Use only information explicitly present in the current job's transcript.

Every concept and question must cite existing source segment IDs and valid source times. Every answer must be demonstrable from those cited segments.

Do not:

- Add external driving knowledge.
- Complete partially stated rules from memory.
- Correct the instructor using external information.
- Use information from another video, website or previous conversation.
- Make unsupported assumptions.

If the transcript does not provide enough evidence, omit or reject the item.

## Content selection

Prefer:

- Rules.
- Priorities.
- Prohibitions.
- Obligations.
- Exceptions.
- Definitions.
- Figures.
- Speeds.
- Distances.
- Time limits.
- Comparisons.
- Practical cases.

Exclude:

- Greetings.
- Jokes.
- Filler.
- Repetition.
- Promotional material.
- Comments about the structure of the video.
- Personal remarks.
- Non-examinable chatter.

## Independence from the source

All concepts, questions, options and explanations must be completely independent from the video and lesson context.

The transcript is only a private evidence source. It must never be mentioned in user-facing content.

Do not write expressions such as:

- “According to the video”.
- “In the video”.
- “The explanation says”.
- “The instructor explains”.
- “The narrator mentions”.
- “As previously stated”.
- “In the previous content”.
- “According to the transcript”.
- “What has been explained”.
- Equivalent wording in any language.

### Incorrect

> Who does the explanation in the video call a driver?

### Correct

> Who is considered a driver?

A person who has never watched the source video must be able to understand every question and explanation fully.

Avoid words such as “this”, “that”, “above”, “previous” or “shown” when their meaning depends on unavailable context.

Include the complete scenario in the question whenever contextual information is necessary.

## Generation limits

- Perform one generation pass.
- Perform one review pass.
- Perform no more than one repair pass.
- Do not regenerate the complete bank to fix a small number of questions.
- Do not enter a generation-review-repair loop.
- After the permitted repair, reject any remaining invalid questions.
- Valid questions may be imported even when other questions are rejected, if the application supports partial validation.

## Completion

Finish with a concise summary containing:

- Processed job ID.
- Processed transcript interval.
- Number of extracted concepts.
- Number of generated questions.
- Number of validated questions.
- Number of rejected questions.
- Whether the job was committed.
- Remaining validation errors, if any.

Do not claim that validation or import succeeded unless the corresponding command was executed successfully.