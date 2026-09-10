# CLAUDE.md

## Scope
Files:    the SCF #35 "Stellar DeFi Dune Dashboards" project: plan, protocol registry, SQL mirrors of every Dune query and matview, runbook.
Issues:   not used yet. Grant admin lives in `paltalabs/internal-ops` issue 216.
HubSpot:  not applicable.
Drive:    none.
NOT here: DeFindex and Soroswap dashboards and their credit optimisation → `paltalabs/dune-dashboards`.
Index:    `paltalabs/context` → `CLAUDE.md`, `REPOS.yml`

## What this is

Six DeFi protocols on Stellar (Blend, FxDAO, Soroswap, Aquarius, Phoenix, Etherfuse), one public
Dune dashboard, four deliverables funded by SCF #35 (`scf/submission-scf35.md`). The plan and the
credit budget are in `plan.md`. The protocol contract registry is `protocols.yml`.

## Design rules, decided 2026-09-10

1. **Nobody maintains this by hand.** Every recurring piece is a Dune materialized view with its
   own cron. No query schedules set in the Dune UI, because the API cannot see or restore them.
2. **Two layers per protocol, both automatic.** `result_scf_<protocol>_activity_archive` scans the
   full history and refreshes monthly (cron, first day of the month). `result_scf_<protocol>_activity`
   scans only what is newer than the archive and refreshes daily. Dashboard queries read the union
   of the two and never touch a raw `stellar.*` table.
3. **One normalized schema for every protocol** (`docs/modelo-de-datos.md`). All four deliverables
   are computed from it, so the raw tables are scanned once per period, not once per chart.
4. **Measure every execution.** `executionCostCredits` goes into the SQL file header and into
   `plan.md`. Engine `medium`, never `large`. If a change measures worse, revert it.
5. **Anyone can rebuild it from this repo.** `docs/runbook.md` lists the exact order: create query
   (not temporary), create matview with cron, wait for the first run, then the consumers.
6. Matview names are immutable and consumers reference them literally. Prefix: `result_scf_`.
7. Queries on Dune carry the prefix `SCF35 ·` in the name. Probes carry `[SCF35 probe]` and are
   temporary.
8. Dune duplicates rows in `stellar.history_contract_events` (every event appears twice, one per
   operation and one per transaction view). Always `SELECT DISTINCT` on the event grain.
9. No em-dashes in prose. Spanish in docs, English in dashboard titles and query names.

## Workflow

1. Read `plan.md`, find the next unchecked step.
2. Before touching a Dune query, `getDuneQuery` and diff against `queries/<protocol>/<id>_<slug>.sql`.
3. Apply in Dune, execute on medium, verify rows and cost, mirror the SQL here with the header.
4. Tick the step in `plan.md` with the date and the measured cost. Commit.
