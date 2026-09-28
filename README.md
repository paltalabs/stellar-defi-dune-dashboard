# Stellar DeFi Dune Dashboards

Verifiable on-chain metrics for the DeFi protocols on Stellar: Blend, FxDAO, Soroswap, Aquarius,
Phoenix, Etherfuse and SushiSwap. Funded by SCF #35
([submission](scf/submission-scf35.md), [project page](https://communityfund.stellar.org/project/stellar-defi-dune-dashboards-xn9)).
Built by [PaltaLabs](https://github.com/paltalabs).

**Dashboard:** https://dune.com/paltalabs/stellar-defi

## Tranche 1: Weekly and Monthly Active Users

- Ecosystem WAU and MAU (unique addresses across all protocols)
- WAU and MAU per protocol
- WAU and MAU by role (swappers, LPs, aggregator users, lenders, borrowers, liquidators and more)
- New vs returning addresses, weekly and monthly
- Week-over-week and month-over-month growth
- Data coverage, pipeline health and validation

## How it works

1. **Source.** Soroban contract events and classic Stellar operations, read from Dune's
   `stellar.*` tables. No protocol-reported data.
2. **User.** A Stellar address that performs a protocol action (swap, add or remove liquidity,
   supply, borrow, repay, liquidation, claim, mint, redeem, trade). Classic accounts (`G...`) and
   contracts / smart wallets (`C...`) are counted and shown separately.
3. **Layers.** Per protocol, a full-history archive (since February 2024) and a live layer
   refreshed daily, both Dune materialized views. Every chart reads one normalized table of
   user actions; no chart scans raw chain tables.
4. **Validation.** A daily query checks duplicates, invalid addresses, gaps between layers,
   contracts missing from the SQL and cohort totals. Failures show in the health table.

## Repository

| Path | What |
|---|---|
| `queries/` | SQL of every Dune query, mirrored with its measured cost |
| `scripts/` | SQL generators (`activity_sql.py`, `pilot_sql.py`) and deploy script (`deploy_pilot.py`) |
| `protocols.yml` | Tracked contracts per protocol, with sources |
| `data/contracts.csv` | Contract registry discovered on-chain |
| `docs/modelo-de-datos.md` | Data model and user attribution per protocol (Spanish) |
| `docs/runbook.md` | How to rebuild and operate everything on Dune (Spanish) |
| `reports/` | Tranche reports (Spanish) |
