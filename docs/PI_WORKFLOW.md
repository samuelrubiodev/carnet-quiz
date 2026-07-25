# Manual agent workflow

```bash
carnetquiz video add URL
carnetquiz transcript fetch VIDEO_ID
carnetquiz job create VIDEO_ID --until 30m
```

Then agent must:

1. Read `request.json`, `transcript.json` and the job-local JSON schemas.
2. Fill `concepts.json`.
3. Fill `questions.json`.
4. Fill `review.json`.
5. Run `carnetquiz job validate JOB_ID`.
6. Correct rejected elements once only.
7. Validate once again.
8. Run `carnetquiz job commit JOB_ID --yes`.

Agent must not edit SQLite or add knowledge absent from transcript.
