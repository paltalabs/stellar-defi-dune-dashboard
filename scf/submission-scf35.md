# SCF #35: Stellar DeFi Dune Dashboards

Texto de la submission tal como quedó aprobada. Copiado el 2026-09-10 desde
https://communityfund.stellar.org/project/stellar-defi-dune-dashboards-xn9. Es la referencia
contra la que se mide cada entregable; no se edita, se comenta en `plan.md`.

- Ronda: SCF #35, categoría Build, estado Awarded.
- Presupuesto: USD 25.000 en tres tranches de USD 8.333.
- Video: ver la página del proyecto.

## Problem we are solving

Currently, most DeFi stats on Stellar come from project-provided reports, which are not always
transparent or easy to verify. Platforms like DeFi Llama and DappRadar often rely on these
reports instead of pulling data directly from the blockchain.

On the other hand, there are many ecosystem stats very useful that can only be calculated using
an external tool like Dune Dashboards, like Percentage of Swaps being aggregated, average
slippage of swaps and more.

## How DeFi Dune Dashboards solves this

The Stellar DeFi Dune Dashboards will change this by providing fully verifiable, on-chain data
from smart contract activity from all DeFi protocols on the ecosystem. These dashboards will
track important stats like Weekly and Monthly Active Users, Average Slippage on Trades, Volume
Analysis, Percentage of Aggregated Trades, and Liquidity Provider Activity.

For AMMs and aggregators, we will show key insights, including trade volume, slippage, price
impact, and how often trades go through aggregators instead of single AMMs. We will also track
arbitrage profits and how many trades are related to arbitrage.

This project will make Stellar DeFi data more transparent and accessible for everyone, helping
users, developers, and investors understand how healthy and active the ecosystem really is. We
will also maintain and update the dashboards for one year to ensure they stay reliable.

Extra comments: Dune dashboards need regular maintenance. Over time, some queries can become too
large because they are analyzing more and more data. When this happens, we need to export the
results into Materialized Views to keep the dashboards fast and reliable. This submission
includes the ongoing maintenance of all queries and dashboards.

## Success criteria

- At least 10 new stars every month on our dashboards.
- Support of the community: our dashboards will be shared more than 1,000 times on Twitter
  after 6 months.

## Go-to-market

Engage with projects in the community to share our dashboards on social media, specifically
the projects that we are tracking. Provide information to SDF and SCF teams for better decision
making.

## Traction evidence

PaltaLabs has been supporting the "Soroban AMMs on Stellar" dashboard (Soroswap AMM and
Aggregator, Blend Backstop, Phoenix Pools, Aquarius AMM), updated 4 times a day:
https://dune.com/paltalabs/soroban-amms-on-stellar. Also the Soroswap dashboard:
https://dune.com/paltalabs/soroswap. All queries: https://dune.com/paltalabs. 26 stars in total.

## Deliverables

How to measure completion, for every deliverable: the query is available and verifiable on our
dashboard and runs every 6 hours.

Protocols, for every deliverable: Blend, FxDAO, Soroswap, Aquarius, Phoenix, Etherfuse.

### Tranche 1 (USD 8.333, 1 month): Weekly and Monthly Active Users

Deliverable 1: Weekly and Monthly Active Users. Tracks how many unique users interact with each
selected DeFi protocol on Soroban:

- Unique wallets per time period
- Per-protocol breakdown
- Action-based segmentation (swappers, LPs, aggregator users, lenders, borrowers, liquidators)
- New vs returning users
- Weekly and monthly growth rate

### Tranche 2 (USD 8.333, 1 month): User overlap and LP activity

Deliverable 2 (USD 3.333): Protocol overlap in users. Unique users and their overlaps between
protocols, how many users interact with more than one protocol. Objective: identify which
protocols bring new addresses into the ecosystem, revealing user journeys and synergies.

Deliverable 3 (USD 5.000): Liquidity provider activity. How LPs move capital between protocols:

- Query to calculate the value per transaction, considering token prices on SDEX and Soroban DEXes
- Active LP wallets (unique addresses interacting as LPs)
- Top LPs (addresses providing the most liquidity)

### Tranche 3 (USD 8.333, 1 month): Liquidity flows and migrations

Deliverable 4: Liquidity inflows and outflows per protocol or pool, and liquidity migration
(how liquidity is added or removed).

## Team

PaltaLabs, a hacker hub focused on Stellar: Soroswap.Finance AMM and Aggregator, DeFindex
vaults, @soroban-react, Create Soroban Dapp. Five full-time developers.
