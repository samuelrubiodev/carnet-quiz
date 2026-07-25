---

name: process-video
description: Process a YouTube study video through CarnetQuiz, generate and validate its question bank up to a requested time limit, and commit the completed job.
argument-hint: "<youtube-url> [time-limit, default: 30m]"
arguments:
  - video_url
  - time_limit
disable-model-invocation: true

---

# Process a CarnetQuiz study video

Process the supplied YouTube study video through the existing CarnetQuiz CLI.

This skill is invoked as:

```text
/process-video <youtube-url> [time-limit]
```

## Inputs

Resolve the invocation arguments as follows:

* `VIDEO_URL`: `$video_url`
* `TIME_LIMIT`: `$time_limit`

If `TIME_LIMIT` is empty or was not provided, use:

```text
30m
```

If `VIDEO_URL` is empty or was not provided, ask the user for the YouTube URL and do not execute any CarnetQuiz commands.

Keep the resolved values available throughout the workflow.

Do not substitute arbitrary values, infer identifiers, or invent command results.

Follow all applicable project instructions from `CLAUDE.md`.

Do not inspect the complete repository before beginning. Use the existing CarnetQuiz CLI and follow the direct workflow below.

## 1. Check the environment

Run:

```bash
carnetquiz doctor
```

If CarnetQuiz is not usable, stop immediately and report only the concrete problem.

Do not continue with later commands after a failed environment check.

## 2. Add or locate the video

Run:

```bash
carnetquiz video add "$VIDEO_URL"
```

Read the command output and retain the resulting video ID as `VIDEO_ID`.

If the video already exists, reuse its existing ID instead of creating a duplicate.

Do not infer or invent `VIDEO_ID`.

## 3. Obtain the transcript

Run:

```bash
carnetquiz transcript fetch "$VIDEO_ID"
```

Do not download the complete video or its audio.

If a valid transcript already exists, reuse it.

Retain the reported transcript source and language for the final response.

If no usable transcript can be obtained, stop and report the concrete problem.

## 4. Create the job

Run:

```bash
carnetquiz job create "$VIDEO_ID" --until "$TIME_LIMIT"
```

Read the command output and retain the resulting job ID as `JOB_ID`.

Do not infer or invent `JOB_ID`.

## 5. Process only the created job

Read only the following job files:

```text
data/jobs/JOB_ID/request.json
data/jobs/JOB_ID/transcript.json
```

Replace `JOB_ID` with the actual job ID.

Also locate and read only the JSON Schema files belonging to the current job.

Do not inspect unrelated source files unless a required CarnetQuiz command fails because of an apparent application defect.

This skill is the complete source of workflow and generation instructions.

Use:

* `request.json` as the current job configuration.
* `transcript.json` as the only factual source.
* The job-local JSON schemas as the exact output contracts.

Generate and write:

```text
data/jobs/JOB_ID/concepts.json
data/jobs/JOB_ID/questions.json
data/jobs/JOB_ID/review.json
```

Use only the current job's transcript as the factual source.

Do not supplement the generated content with:

* Personal or general knowledge.
* Web searches.
* Other transcripts.
* Repository documentation.
* Unrelated job files.
* Assumptions not supported by the transcript.

All user-visible concepts, questions, answer options, feedback, and explanations must stand on their own and remain independent of the source video.

Never mention any of the following in generated educational content:

* The video.
* The lesson.
* The instructor.
* The explanation.
* The narrator.
* The transcript.
* The source material.
* What was said or shown.

Write each JSON file so that it conforms exactly to its corresponding job-local schema.

Do not create additional output files.

## 6. Validate

Run:

```bash
carnetquiz job validate "$JOB_ID"
```

Read the complete validation result carefully.

If isolated items are rejected, perform at most one targeted repair affecting only the rejected items.

Do not regenerate the complete concept set or question bank to repair isolated failures.

Do not modify valid items unnecessarily.

After the single permitted targeted repair, run validation exactly once more:

```bash
carnetquiz job validate "$JOB_ID"
```

Do not enter an iterative repair loop.

Do not perform a second repair attempt.

If errors remain after the second validation, preserve the validation result, report the remaining errors, and do not continue to commit.

## 7. Import

Commit the job only when the final validation result explicitly permits import.

Run:

```bash
carnetquiz job commit "$JOB_ID"
```

Do not run the commit command if validation failed or does not explicitly permit import.

Read the command output and verify that the commit actually succeeded.

## 8. Final response

Report:

* Video ID.
* Job ID.
* Processed interval.
* Transcript source.
* Transcript language.
* Number of concepts generated.
* Number of questions generated.
* Number of valid questions.
* Number of rejected questions.
* Whether the job was committed.
* Any remaining errors.

Base every reported value on actual command output or generated job files.

Clearly distinguish between:

* Commands that succeeded.
* Commands that failed.
* Commands that were not executed.
* Steps that were skipped because a prerequisite failed.

Do not claim that a command succeeded unless it was actually executed successfully.

Do not report invented, estimated, or inferred counts.
