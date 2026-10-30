# T-013 · Delhi area seed script

- status: ready
- quest: Q1
- depends: T-010
- owner: -
- updated: -
- files: backend/scripts/seed_areas.py, backend/tests/test_seed_areas.py, docs/GEO_DATA.md, backend/pyproject.toml

## Goal

Turn the CC0 India Post PIN dataset into the `Area` rows the app needs: one area per Delhi PIN code, with a
clean locality name, a normalised district, a centre coordinate and a radius. The script must be
re-runnable without duplicating rows, and it must not need the network once the CSV is cached.

## Done when

- [ ] `python scripts/seed_areas.py` inserts **103 Delhi PINs**, and **0** of them lack a latitude or
      longitude (assert both numbers in the script's output).
- [ ] Every `district` is upper-case and trimmed (`SOUTH WEST`, not `South East`).
- [ ] Every `name` has the office-type suffix stripped (`Karol Bagh`, not `Karol Bagh SO`).
- [ ] Every area's `radiusMeters` ≥ 1500 and is the max distance from the centre to that PIN's other
      offices.
- [ ] Running the script twice changes nothing (idempotent — upsert on `pincode`).
- [ ] The script works from a cached copy of the CSV (no network) and can download it if missing.
- [ ] `pytest -q` includes a test for the normalisation rules (suffix stripping, district casing, `NA`
      coordinates) using small inline fixtures — not the whole 21 MB file.
- [ ] `docs/GEO_DATA.md` is updated with the actual row counts and any new quirks found in the data.

## Notes / gotchas

- Source: `https://raw.githubusercontent.com/ghousekw/india-pincodes/master/pincode.csv` (**CC0 1.0**), columns
  `circlename, regionname, divisionname, officename, pincode, officetype, delivery, district, statename,
  latitude, longitude`. Full details and the verified numbers are in `docs/GEO_DATA.md`.
- The file is ~21 MB with 165,627 rows. Stream it (`csv.DictReader` over a urllib response) — do not load it
  into memory as a list of dicts.
- Filter with `statename.strip().upper() == "DELHI"`.
- Pick the **main office** per PIN: prefer `officetype == "SO"`, else the most common `officename`. The main
  office's coordinates become the area centre.
- The raw data has `NA` in the coordinate columns for some rows — treat that as missing.
- District casing is inconsistent in the source (`SOUTH WEST` vs `South East`). Normalise, do not assume.
- `officename` endings vary: ` SO`, ` BO`, ` PO`, ` S.O.`, ` B.O.`, ` Post Office`. Strip them all.
- Cache the CSV under `backend/.cache/` (gitignored) so re-running the seed is offline and fast.
- Write the counts to stdout — the manager verifies them from the real output.

## Research notes

Everything about the dataset is already measured and documented in `docs/GEO_DATA.md` §1 — do not
re-download and re-count it from scratch unless you are validating the seed script itself.

If you find a quirk that is not in `docs/GEO_DATA.md`, add it there (this file is the reference for later
sessions) and mention it in your report.

## Work log

## Report

## Manager review
