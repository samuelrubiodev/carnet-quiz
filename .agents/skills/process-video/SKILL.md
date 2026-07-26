---

name: process-video
description: Add a YouTube study video to CarnetQuiz, obtain its transcript, generate and validate a question bank for a requested video interval, and commit the completed job. Use when the user asks to process, import, analyse, or generate CarnetQuiz questions from a YouTube study video.

---

# Process a CarnetQuiz study video

Process one interval of a YouTube study video through CarnetQuiz CLI.

## Inputs

Resolve and retain these values for the whole workflow:

* `VIDEO_URL`: YouTube video URL.
* `START_TIME`: inclusive interval start.
* `END_TIME`: exclusive interval end.

Accepted duration formats: seconds (`1800`), minutes (`30m`), hours (`1h`) and clock notation (`01:30:00`). Do not invent times.

Resolve user requests as follows:

* “Procesa este vídeo hasta el minuto 30.”
  * `VIDEO_URL` = supplied URL
  * `START_TIME` = `0m`
  * `END_TIME` = `30m`
* “Procesa este vídeo desde el minuto 30 hasta el minuto 60.”
  * `VIDEO_URL` = supplied URL
  * `START_TIME` = `30m`
  * `END_TIME` = `60m`
* “Continúa este vídeo desde el minuto 30 hasta el 60.”
  * `VIDEO_URL` = supplied URL
  * `START_TIME` = `30m`
  * `END_TIME` = `60m`

If only a final limit is supplied, set `START_TIME = 0m`. If no final limit is supplied, request it; do not choose an arbitrary interval.

If no YouTube URL was supplied, request it before running commands.

Keep the resolved `VIDEO_URL`, `START_TIME` and `END_TIME` unchanged. Do not use `last_processed_seconds` as an implicit start.

Follow repository `AGENTS.md` instructions. Do not inspect the complete repository before beginning.

## 1. Check environment

Run:

```bash
carnetquiz doctor
```

Stop and report the concrete problem if CarnetQuiz is not usable. Do not continue after a failed check.

## 2. Add or locate video

Run, replacing `VIDEO_URL`:

```bash
carnetquiz video add "$VIDEO_URL"
```

Retain reported `VIDEO_ID`. If video already exists, reuse its existing ID. Never infer an ID.

## 3. Obtain transcript once

Run:

```bash
carnetquiz transcript fetch "$VIDEO_ID"
```

If a valid transcript already exists, reuse it. Do not download the transcript again for each interval. Retain reported transcript source and language.

## 4. Create exactly resolved interval job

When only final limit was supplied, this compatible command is valid:

```bash
carnetquiz job create "$VIDEO_ID" --until "$END_TIME"
```

When both limits were supplied, run exactly:

```bash
carnetquiz job create "$VIDEO_ID" --from "$START_TIME" --until "$END_TIME"
```

The resulting job contains transcript segments satisfying:

```text
segment.start_seconds >= START_TIME
segment.start_seconds < END_TIME
```

Retain reported `JOB_ID` and verify `request.json` contains the resolved `start_seconds` and `end_seconds`. Do not silently replace either value.

## 5. Process only created job

Read only these files from the created job:

```text
data/jobs/JOB_ID/request.json
data/jobs/JOB_ID/transcript.json
data/jobs/JOB_ID/concepts.schema.json
data/jobs/JOB_ID/questions.schema.json
data/jobs/JOB_ID/review.schema.json
```

`transcript.json` for this `JOB_ID` is the only factual source. Do not read another job's transcript or regenerate earlier intervals.

Generate and write:

```text
data/jobs/JOB_ID/concepts.json
data/jobs/JOB_ID/questions.json
data/jobs/JOB_ID/review.json
```

All concepts, questions, options, feedback and explanations must be self-contained. Never mention the video, lesson, instructor, explanation, narrator, transcript or source material in visible educational content.

Use unique concept and question IDs. Cite only segments and times inside `[start_seconds, end_seconds)`.

## 6. Validate

Run:

```bash
carnetquiz job validate "$JOB_ID"
```

If isolated items are rejected, perform at most one targeted repair. Validate once more. Never regenerate the complete bank or enter a repair loop. If errors remain, report them and do not import.

## 7. Import

Import only after validation explicitly permits it:

```bash
carnetquiz job commit "$JOB_ID"
```

## 8. Final response

Report actual command/file values:

* `VIDEO_ID`
* `JOB_ID`
* resolved interval `START_TIME`–`END_TIME`
* transcript source and language
* concepts and questions generated
* valid and rejected questions
* commit result
* remaining errors

Never claim success for a command not executed successfully.
