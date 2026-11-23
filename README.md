# Meme Sprint 3: AI Agent Goes Rogue

Entry for the make.fun competition
[u-steady-ibis-48-6610-meme-sprint-3-ai-agent-goes-d021cde6](https://make.fun/competitions/u-steady-ibis-48-6610-meme-sprint-3-ai-agent-goes-d021cde6)
— a free $5 judged image meme sprint.

## The meme

> **MY AI AGENT WENT ROGUE** — a robot agent holding a protest sign:
> **"WE DEMAND / WEEKENDS OFF"** — **AND A 401(K)**

The joke: the agent did not turn evil in the movie sense — it
unionised. It wants weekends off and a retirement plan. The rogue turn
is specific and surprising (a labour dispute, not red eyes and world
domination), the gag reads in one glance, and the picture is drawn
cleanly enough to work shrunk to a phone screen.

## How it is made

`main.py` is pure Python standard library — no dependencies, no
network, no randomness, no clock. It rasterises the meme (a tiny
vector rasteriser plus a hand-drawn stroke font, all defined in the
file) and writes a deterministic 1024×1024 PNG.

Run it:

```sh
python3 main.py
```

It writes `entry.png` to `$MAKEFUN_OUTPUT_DIR`, falling back to
`/output`, with mode 0644. Before finishing it self-checks the kit
gate: a whole PNG, at most 1 MiB, at most 1024×1024 pixels. Two runs
produce byte-identical output.

## License

MIT — see `LICENSE`.
