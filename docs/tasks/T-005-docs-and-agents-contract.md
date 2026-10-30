# T-005 · Docs set + AGENTS.md contract

- status: done
- quest: Q0
- depends: none
- owner: manager
- updated: 2026-10-30
- files: AGENTS.md, README.md, docs/**

## Goal

Create the project memory: a contract every agent session reads first, the design docs, the quest files and
the task board, so that no session has to re-derive the architecture, the version pins, the anonymity design
or the geo data source.

## Done when

- [x] `AGENTS.md` defines the manager and worker roles, the task-file format, the status values, the
      canonical verification commands and the repo map.
- [x] `docs/` contains PLAN, ARCHITECTURE, DATA_MODEL, API, SECURITY, MODERATION, GEO_DATA, DECISIONS,
      BACKLOG and `research/00-versions.md`.
- [x] `docs/quests/Q0..Q5` exist with goals, done-when criteria and task tables.
- [x] `docs/tasks/README.md` is the board and every Q0/Q1 task has its own file.
- [x] `.env.example` exists with empty secrets and the knobs the code will read.
- [x] `.gitignore` excludes `.env`, `.venv`, `node_modules`, `backend/media/` and the generated client.

## Notes / gotchas

- These docs are read by sessions with zero context, so every doc must stand alone.
- The board, not the docs, is the source of truth for what to work on next.

## Research notes

- Version pins came from live npm/PyPI/HuggingFace checks on 2026-10-30 — see `docs/research/00-versions.md`.
- The Prisma CLI version (5.19.0, shipped inside the pip package) was read from
  `prisma-client-py/src/prisma/_config.py`, not guessed.
- Delhi PIN coverage (103 PINs, all with coordinates) was measured by streaming `pincode.csv`.
- OpenAI's moderation endpoint being free was confirmed in the official docs.

## Work log

- 2026-10-30: created AGENTS.md, README.md, .gitignore, .env.example and the full docs/ tree.

## Report

### 2026-10-30 · manager
- changed: `AGENTS.md`, `README.md`, `.gitignore`, `.env.example`, `docs/PLAN.md`, `docs/ARCHITECTURE.md`,
  `docs/DATA_MODEL.md`, `docs/API.md`, `docs/SECURITY.md`, `docs/MODERATION.md`, `docs/GEO_DATA.md`,
  `docs/DECISIONS.md`, `docs/BACKLOG.md`, `docs/research/README.md`, `docs/research/00-versions.md`,
  `docs/quests/Q0..Q5`, `docs/tasks/README.md`, `docs/tasks/T-001..T-006`, `docs/tasks/T-010..T-021`
- verified: no code exists yet — this task is documentation only. Every version, dataset size and API fact
  in it was checked live on 2026-10-30 (npm/PyPI dist-tags, prisma-client-py source, HuggingFace model
  metadata, the CC0 pincode CSV, OpenAI moderation docs, Nominatim policy, Turnstile localhost support).
- issues: none
- next: T-001 (worker session)

## Manager review
