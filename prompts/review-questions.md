# Review questions

Perform exactly one review of the current job's `concepts.json` and
`questions.json`.

Use only:

- the current job's `transcript.json`;
- the job-local schemas;
- the current job's concepts and questions.

Do not use external driving knowledge.

## Evidence review

For every concept and question, verify that:

- every cited segment ID exists;
- every cited segment belongs to the current job;
- every cited time is inside the job interval;
- the cited evidence directly supports the claim;
- the explanation and correct answer do not contain unsupported details;
- no information has been completed from memory.

Reject items whose evidence is insufficient, ambiguous or outside the allowed
interval.

## Question structure review

Verify that every question:

- references an existing valid concept;
- contains three or four distinct options;
- has unique option IDs;
- has exactly one correct answer;
- identifies an existing option as `correct_option`;
- contains a meaningful explanation;
- has plausible but incorrect distractors;
- has no duplicate options;
- is not a duplicate or near-duplicate of another question;
- does not rely on grammatical or formatting clues;
- does not contain an incomplete practical case;
- has a valid type and difficulty.

## Independence review

Every question must work as an independent examination question for a person who
has never watched the source video.

Review the question, every option and its explanation.

Reject or repair items containing references such as:

- video;
- this video;
- lesson;
- course;
- explanation;
- instructor;
- professor;
- teacher;
- narrator;
- speaker;
- transcript;
- previous content;
- what was said;
- what was explained;
- what was mentioned;
- according to the source;
- equivalent source-dependent wording.

Also reject questions containing unresolved references such as:

- "this situation";
- "the previous case";
- "the vehicle mentioned";
- "the signal shown";
- "as stated above";

unless the complete referenced context is included directly in the question.

Incorrect:

> According to the explanation, who is considered a driver?

Correct:

> Who is considered a driver?

Incorrect:

> What should the vehicle mentioned previously do?

Correct:

> A vehicle approaches a stop sign. What must its driver do?

Source segment IDs and times are metadata. Their presence must never affect the
visible wording of the question.

## Review result

Write the result to `review.json`.

Record:

- reviewed concept IDs;
- accepted concept IDs;
- rejected concept IDs and reasons;
- reviewed question IDs;
- accepted question IDs;
- rejected question IDs and reasons;
- repaired question IDs;
- summary counts.

Use specific rejection reasons, such as:

- `unsupported_by_transcript`;
- `source_dependent_wording`;
- `missing_context`;
- `multiple_valid_answers`;
- `invalid_source_segment`;
- `outside_job_range`;
- `duplicate_question`;
- `duplicate_option`;
- `ambiguous_wording`;
- `invalid_correct_option`;
- `external_knowledge`;
- `invalid_schema`.

Repair rejected items at most once. Preserve their original concept, evidence and
meaning whenever possible.

Do not regenerate the complete question bank. After the single permitted repair,
leave any remaining defective items rejected.