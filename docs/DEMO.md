# Demo video (60 seconds, no screen recorder needed)

You have two paths. Both are verified to work with this repo.

## Option A — Animated terminal (already in `docs/preview.html`)

Open `docs/preview.html` (or the GitHub Pages link below) and press **Play demo**.
It types the exact commands from `make demo` with real measured output —
no recording, no editing, reproducible by definition.

## Option B — Record a real GIF (terminal → GIF)

```bash
# 1. Install a terminal recorder (pick one):
#    screencli (single command), asciinema, or vhs (Charm)
pip install screencli  # or: brew install vhs / pip install asciinema

# 2. Record this exact session (keep it under 60s):
PYTHONPATH=src python3 coin135.py
make test
python3 experiments/07_genesis_verify.py

# 3. Export to docs/assets/demo.gif (max width 800px, 15 fps — GitHub renders it inline)
# 4. Reference it at the top of README:
#    ![demo](docs/assets/demo.gif)
```

Tips from 2026 README research: keep the GIF under ~5 MB, show the *result*
(passing tests, mined hash, genesis match) in the first 10 seconds, and always
keep a text transcript below the GIF for accessibility and AI parsing.
