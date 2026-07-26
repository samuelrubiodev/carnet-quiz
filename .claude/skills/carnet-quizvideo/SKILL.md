---

name: process-video
description: Process a YouTube study video through CarnetQuiz for a requested interval, generate and validate its question bank, and commit the completed job.
argument-hint: "<youtube-url> [end-time] | <youtube-url> <start-time> <end-time>"
arguments:
  - video_url
  - start_time
  - end_time
disable-model-invocation: true

---

# Process a CarnetQuiz study video

Process one interval of supplied YouTube study video through CarnetQuiz CLI.

Invocation forms:

```text
/process-video <youtube-url> [end-time]
/process-video <youtube-url> <start-time> <end-time>
```

Examples:

```text
/process-video https://youtube.com/watch?v=example 30m
/process-video https://youtube.com/watch?v=example 30m 60m
/process-video https://youtube.com/watch?v=example 1h 01:30:00
```

## Inputs and interval resolution

Resolve invocation arguments as follows:

* `VIDEO_URL`: `$video_url`.
* One time argument: it is `END_TIME`; set `START_TIME = 0m`.
* Two time arguments: `$start_time` is `START_TIME`; `$end_time` is `END_TIME`.
* No time argument: set `START_TIME = 0m` and `END_TIME = 30m`.

Thus, legacy invocation with one limit remains compatible:

```text
/process-video <youtube-url> 30m
```

means `0m–30m`.

`START_TIME` and `END_TIME` accept seconds (`1800`), minutes (`30m`), hours (`1h`) and clock notation (`01:30:00`). Do not invent times or use `last_processed_seconds` as an implicit start.

If `VIDEO_URL` is empty or was not provided, ask the user for the YouTube URL and do not execute CarnetQuiz commands.

Keep resolved `VIDEO_URL`, `START_TIME` and `END_TIME` unchanged throughout workflow. Do not substitute arbitrary values, infer identifiers, or invent command results.

Follow all applicable project instructions from `CLAUDE.md`.

Do not inspect complete repository before beginning. Use existing CarnetQuiz CLI and follow direct workflow below.

## 1. Check environment

Run:

```bash
carnetquiz doctor
```

If CarnetQuiz is not usable, stop immediately and report only concrete problem.

Do not continue after failed environment check.

## 2. Add or locate video

Run:

```bash
carnetquiz video add "$VIDEO_URL"
```

Read output and retain resulting video ID as `VIDEO_ID`.

If video already exists, reuse existing ID instead of creating duplicate.

Do not infer or invent `VIDEO_ID`.

## 3. Obtain transcript once

Run:

```bash
carnetquiz transcript fetch "$VIDEO_ID"
```

Do not download complete video or audio.

If valid transcript already exists, reuse it. Do not download transcript again for each interval.

Retain reported transcript source and language for final response.

If no usable transcript can be obtained, stop and report concrete problem.

## 4. Create exact resolved interval job

If only one final limit was supplied, run compatible command:

```bash
carnetquiz job create "$VIDEO_ID" --until "$END_TIME"
```

If both limits were supplied, run exactly:

```bash
carnetquiz job create "$VIDEO_ID" --from "$START_TIME" --until "$END_TIME"
```

The job must contain only transcript segments satisfying:

```text
segment.start_seconds >= START_TIME
segment.start_seconds < END_TIME
```

The initial boundary is inclusive; final boundary is exclusive.

Read output and retain resulting job ID as `JOB_ID`. Do not infer or invent `JOB_ID`.

Verify `request.json` contains resolved `start_seconds` and `end_seconds`. Do not silently replace either value.

## 5. Process only created job

Read only these files from created job:

```text
data/jobs/JOB_ID/request.json
data/jobs/JOB_ID/transcript.json
data/jobs/JOB_ID/concepts.schema.json
data/jobs/JOB_ID/questions.schema.json
data/jobs/JOB_ID/review.schema.json
```

Replace `JOB_ID` with actual job ID.

Do not inspect unrelated source files unless a required CarnetQuiz command fails because of apparent application defect.

Use:

* `request.json` as current job configuration.
* `transcript.json` as only factual source.
* Job-local JSON schemas as exact output contracts.

Generate and write:

```text
data/jobs/JOB_ID/concepts.json
data/jobs/JOB_ID/questions.json
data/jobs/JOB_ID/review.json
```

Use only current job's transcript as factual source. Do not read another job's transcript or regenerate previous intervals.

Do not supplement generated content with personal knowledge, web searches, other transcripts, repository documentation, unrelated job files, or unsupported assumptions.

All user-visible concepts, questions, answer options, feedback, and explanations must stand alone and remain independent of source video.

Never mention in generated educational content:

* The video.
* The lesson.
* The instructor.
* The explanation.
* The narrator.
* The transcript.
* The source material.
* What was said or shown.

Use unique concept and question IDs. Cite only segments and times inside `[start_seconds, end_seconds)`.

Write each JSON file so it conforms exactly to corresponding job-local schema. Do not create additional output files.

## 6. Validate

Run:

```bash
carnetquiz job validate "$JOB_ID"
```

Read complete validation result carefully.

If isolated items are rejected, perform at most one targeted repair affecting only rejected items.

Do not regenerate complete concept set or question bank. Do not modify valid items unnecessarily.

After single permitted repair, run validation exactly once more:

```bash
carnetquiz job validate "$JOB_ID"
```

Do not enter iterative repair loop or perform second repair attempt.

If errors remain after second validation, preserve result, report remaining errors, and do not commit.

## 7. Import

Commit only when final validation explicitly permits import:

```bash
carnetquiz job commit "$JOB_ID"
```

Do not commit if validation failed or does not explicitly permit import.

Read output and verify commit actually succeeded.

## 8. Final response

Report actual command/file values:

* Video ID.
* Job ID.
* Resolved interval `START_TIME–END_TIME`.
* Transcript source.
* Transcript language.
* Number of concepts generated.
* Number of questions generated.
* Number of valid questions.
* Number of rejected questions.
* Whether job was committed.
* Remaining errors.

Clearly distinguish succeeded, failed, not executed, and skipped commands.

Do not claim command success unless actually executed. Do not report invented, estimated, or inferred counts.
