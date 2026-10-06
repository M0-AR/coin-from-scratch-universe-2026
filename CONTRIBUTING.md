# Contributing

PRs welcome. This repo is a learning codebase, so small, well-tested changes beat big rewrites.

## Setup

```bash
python3 -m pip install -r requirements.txt
make test
```

## Rules

1. Every claim needs an executable: add/extend a test in `tests/` or a script in `experiments/`.
2. Never commit numbers by hand — generate them (`make experiments` writes `benchmarks/*.json`).
3. Keep `coin135.py` runnable with zero framework deps except `ecdsa`.
4. Update `README.md` + `docs/preview.html` quiz if you change consensus rules.
5. Run `make test && make experiments` before pushing.

## Good first issues

- Add fee support (`inputs = outputs + fee`) + fee-rate benchmark.
- Add Merkle root + SPV proof demo.
- Add `/docs` quiz questions (see `docs/preview.html` `QUIZ` array).
- Add Dockerfile healthcheck + persistence volume example.
