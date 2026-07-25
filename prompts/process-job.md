# Process a pending CarnetQuiz job

Find one `ready` job with `carnetquiz job list`. Read its `context.md` and `transcript.json`. Use only that transcript. Fill `concepts.json`, `questions.json`, and `review.json`; cite source segment IDs for every claim. Extract examinable rules, priorities, prohibitions, figures, obligations, exceptions, and practical cases. Exclude chatter.

Generate once. Review once. Repair rejected items once at most. Run `carnetquiz job validate JOB_ID`, then `carnetquiz job commit JOB_ID`. Never edit SQLite or use facts absent from transcript. Finish with imported/rejected summary.
