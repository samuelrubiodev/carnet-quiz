# CarnetQuiz agent guide

## Project purpose

CarnetQuiz is a local application that creates driving-theory question banks from timestamped YouTube transcripts.

The application manages:

- Videos.
- Transcripts.
- Generation jobs.
- Validated questions.
- Tests.
- Statistics.

AI agents generate job JSON files. Application code performs deterministic validation and database import.

## Fast task routing

When the user provides a YouTube URL and a time limit, or asks to process part of a study video, treat it as a CarnetQuiz video-processing request.

Do not explore the complete repository before starting.

Use this workflow:

1. Add or locate the video.
2. Fetch its transcript.
3. Create a generation job for the requested interval.
4. Read the job's `request.json`, `transcript.json` and JSON schemas.
5. Process only that job.
6. Validate and commit valid results.


## Main commands

```bash
carnetquiz doctor
carnetquiz video add URL
carnetquiz video list
carnetquiz transcript fetch VIDEO_ID
carnetquiz job create VIDEO_ID --until 30m
carnetquiz job create VIDEO_ID --from 30m --until 60m
carnetquiz job list
carnetquiz job validate JOB_ID
carnetquiz job commit JOB_ID
carnetquiz serve
```

Use the following command when a command's exact options are unknown:

```bash
carnetquiz COMMAND --help
```

## Project map

- `src/carnetquiz/`: application source code.
- `prompts/`: source templates used to build job instructions.
- `.pi/prompts/`: user-invoked Pi prompt templates.
- `schemas/`: JSON schemas.
- `data/jobs/JOB_ID/`: isolated agent jobs.
- `tests/`: automated tests.
- `docs/`: human documentation.

## Job source of truth

For question generation, the current job's `transcript.json` is the only factual source. It contains only segments in the resolved half-open interval `[start_seconds, end_seconds)`: segment start is included, final boundary excluded. Do not use `last_processed_seconds` as an implicit job start.

Do not use:

- External driving knowledge.
- Another job's transcript.
- Websites.
- Previous conversations.
- Model memory.

If evidence is incomplete or ambiguous, omit the item.

## Question invariants

All questions must:

- Be understandable without seeing the source video.
- Contain all necessary context.
- Cite valid transcript segment IDs and times.
- Have three or four distinct options.
- Have exactly one valid answer.
- Include a self-contained explanation.

Never mention the video, lesson, transcript, instructor, narrator or explanation in visible question content.

### Incorrect

> Who does the explanation in the video call a driver?

### Correct

> Who is considered a driver?

## Database and repository safety

- Los agentes no deben ejecutar borrados selectivos ni reseteos de datos salvo petición explícita del usuario.
- Never edit SQLite directly.
- Use the `carnetquiz` CLI or approved MCP tools.
- Never bypass validation.
- Never write outside the repository.
- Do not modify unrelated files.
- Do not import a job before successful validation.

## Bounded job workflow

For each job:

1. Generate once.
2. Review once.
3. Repair rejected items once at most.
4. Run deterministic validation.
5. Commit valid results or report the remaining rejected items.

Never enter a repeated generation-review-repair loop.

## Validation

After modifying application code, run the most relevant tests first.

For a generated job, always run:

```bash
carnetquiz job validate JOB_ID
```

Import only after successful validation:

```bash
carnetquiz job commit JOB_ID
```

Never claim that validation or import succeeded unless the corresponding command completed successfully.