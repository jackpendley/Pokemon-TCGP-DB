# TCGP Optimizer — Web App

Next.js dashboard for the Pokémon TCG Pocket collection tracker. Reads the
Python pipeline's JSON artifacts (`../data/current`, `../data/reference`,
`../data/sync`) via the data layer in `lib/data/`; run
`python3 scripts/run_recommendations.py` in the repo root first to generate them.

```bash
npm run dev        # local dev server (includes the local-only Sync button)
npm run typecheck  # tsc --noEmit
npm test           # vitest
npm run build      # production build (no pipeline artifacts required)
```

Project conventions live in [AGENTS.md](AGENTS.md) (imported by CLAUDE.md).
