---

name: process-video
description: Add a YouTube study video to CarnetQuiz, obtain its transcript, generate and validate a question bank up to a requested time limit, and commit the completed job. Use when the user asks to process, import, analyse, or generate CarnetQuiz questions from a YouTube study video.

---

# Process a CarnetQuiz study video

Process a YouTube study video through the existing CarnetQuiz CLI.

## Inputs

Obtain the following values from the user's request:

* `VIDEO_URL`: the YouTube video URL.
* `TIME_LIMIT`: the point through which content must be processed.

If the user does not specify a time limit, use:

```text
30m
```

If no YouTube URL was provided, request it before running any commands.

Keep the resolved values available throughout the workflow. Do not substitute arbitrary values or invent identifiers.

Follow the repository's applicable `AGENTS.md` instructions.

Do not inspect the complete repository before beginning. Use the existing CarnetQuiz CLI and follow the direct workflow below.

## 1. Check the environment

Run:

```bash
carnetquiz doctor
```

Stop and report the concrete problem only if CarnetQuiz is not usable.

Do not continue with later commands after a failed environment check.

## 2. Add or locate the video

Run, replacing `VIDEO_URL` with the URL supplied by the user:

```bash
carnetquiz video add "$VIDEO_URL"
```

Read the command output and retain the resulting video ID as `VIDEO_ID`.

If the video already exists, reuse its existing ID instead of creating a duplicate.

Do not infer or invent the video ID.

## 3. Obtain the transcript

Run:

```bash
carnetquiz transcript fetch "$VIDEO_ID"
```

Do not download the complete video or its audio.

If a valid transcript already exists, reuse it.

Retain any reported transcript source and language for the final response.

## 4. Create the job

Run, replacing `TIME_LIMIT` with the resolved processing limit:

```bash
carnetquiz job create "$VIDEO_ID" --until "$TIME_LIMIT"
```

Read the command output and retain the resulting job ID as `JOB_ID`.

Do not infer or invent the job ID.

## 5. Process only the created job

Read only the following job files:

```text
data/jobs/JOB_ID/request.json
data/jobs/JOB_ID/transcript.json
```

Replace `JOB_ID` with the actual job ID.

Also read the JSON Schema files belonging to the current job.

Do not inspect unrelated source files unless a required CarnetQuiz command fails because of an apparent application defect.

This skill is the complete source of agent workflow and generation instructions.

Use `request.json` for the current job configuration, `transcript.json` as the
only factual source, and the job-local JSON schemas as the output contracts.

Generate and write:

```text
data/jobs/JOB_ID/concepts.json
data/jobs/JOB_ID/questions.json
data/jobs/JOB_ID/review.json
```

Use only the current job's transcript as the factual source.

Do not supplement the content with personal knowledge, web searches, other transcripts, repository documentation, or unrelated files.

All user-visible concepts, questions, answer options, feedback, and explanations must stand on their own and be independent of the source video.

Never mention any of the following in generated educational content:

* The video.
* The lesson.
* The instructor.
* The explanation.
* The narrator.
* The transcript.
* The source material.
* What was said or shown.

Write the JSON files so that they conform exactly to the current job's schemas.

## 6. Validate

Run:

```bash
carnetquiz job validate "$JOB_ID"
```

Read the validation result carefully.

If isolated items are rejected, perform at most one targeted repair affecting only those rejected items.

Do not regenerate the complete concept set or question bank to repair isolated validation failures.

After the permitted targeted repair, run validation exactly once more:

```bash
carnetquiz job validate "$JOB_ID"
```

Do not enter an iterative repair loop.

If errors remain after the second validation, report them and do not perform additional repairs.

## 7. Import

Commit the job only when validation explicitly permits import.

Run:

```bash
carnetquiz job commit "$JOB_ID"
```

Do not run the commit command when validation does not permit it.

## 8. Final response

Report:

* Video ID.
* Job ID.
* Processed interval.
* Transcript source and language.
* Number of concepts generated.
* Number of questions generated.
* Number of valid questions.
* Number of rejected questions.
* Whether the job was committed.
* Any remaining errors.

Base every reported value on actual command output or generated job files.

Do not claim that a command succeeded unless it was actually executed successfully.
