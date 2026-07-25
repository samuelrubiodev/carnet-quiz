# Manual agent workflow

```bash
carnetquiz video add URL
carnetquiz transcript fetch VIDEO_ID
carnetquiz job create VIDEO_ID --until 30m
```

Then agent must:

1. Read `data/jobs/JOB_ID/context.md`.
2. Read `transcript.json`.
3. Fill `concepts.json`.
4. Fill `questions.json`.
5. Fill `review.json`.
6. Run `carnetquiz job validate JOB_ID`.
7. Correct rejected elements once only.
8. Validate once again.
9. Run `carnetquiz job commit JOB_ID --yes`.

Agent must not edit SQLite or add knowledge absent from transcript.
