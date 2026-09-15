# advisory-brief round-5 benchmark run (first pass)

This directory holds a complete run of the declared acceptance benchmark made immediately after the
advisory-brief batch: 17 development cases (18 declared tasks) with 18 completed, and 4 holdout cases
with 4 completed. Zero task-shape mismatches, zero prohibited-claim hits, zero disallowed statuses,
zero critical failures, no abstention.

A second invocation of the same command was pointed at this same output directory and was refused by
the script before the holdout set was re-run (`FileExistsError` on `holdout/`), so the holdout files here
are from the first pass. The rerun into a fresh directory is `../acceptance-benchmark-20260915n/`, and that
is the run cited in docs/49. Both directories are kept: the refusal is the guard working, not a result to hide.
