-- Query: https://dune.com/queries/8913380
-- Matview: None   cron: None
-- Última ejecución: 01M5JYK1DJW7CK4ESQ43ZJ68YW
-- Costo: 0.342 cr; filas: 8; engine medium
-- Chart source: the protocols this dashboard tracks, with what is measured and current coverage.
-- One row per protocol; Soroswap is its total (unique addresses across the AMM and the aggregator).
WITH info (protocol, name, category, measured, ord) AS (VALUES
  ('blend', 'Blend', 'Lending', 'Supply, withdraw, borrow, repay, liquidations, backstop deposits and withdrawals', 1),
  ('aquarius', 'Aquarius', 'AMM', 'Swaps, liquidity deposits and withdrawals (also concentrated-liquidity pools), reward claims', 2),
  ('soroswap_total', 'Soroswap', 'AMM and aggregator', 'AMM swaps and liquidity, and swaps routed by the aggregator (contracts, SDEX path payments, API multicall). Charts split it into soroswap_amm and soroswap_aggregator; here an address using both counts once', 3),
  ('phoenix', 'Phoenix', 'AMM', 'Swaps, liquidity provided and withdrawn', 4),
  ('sushiswap', 'SushiSwap', 'AMM (concentrated liquidity)', 'Swaps, liquidity minted and collected (since March 2026)', 5),
  ('fxdao', 'FxDAO', 'CDP stablecoins', 'Vault operations, redemptions, liquidations and locking pool', 6),
  ('etherfuse', 'Etherfuse', 'Tokenized bonds (classic assets)', 'Mints, redeems, payments and SDEX trades of its stablebonds', 7),
  ('defindex', 'DeFindex', 'Yield vaults', 'Deposits and withdrawals in DeFindex vaults (since May 2025)', 8)
), contracts AS (
  SELECT protocol, COUNT(DISTINCT contract_id) AS registry_contracts FROM dune.paltalabs.result_scf_contracts GROUP BY 1
  UNION ALL
  SELECT 'defindex', COUNT(DISTINCT contract_id) FROM dune.paltalabs.result_scf_defindex_activity_archive WHERE row_kind = 'activity'
), health AS (
  SELECT protocol, history_from, observed_addresses, last_activity_at, pipeline_status FROM dune.paltalabs.result_scf_users_health
  UNION ALL
  SELECT 'soroswap_total', MIN(h.history_from),
         (SELECT COUNT(DISTINCT user_address) FROM dune.paltalabs.result_scf_users
          WHERE row_kind = 'activity' AND protocol IN ('soroswap_amm', 'soroswap_aggregator')),
         MAX(h.last_activity_at), MIN(h.pipeline_status)
  FROM dune.paltalabs.result_scf_users_health h WHERE h.protocol IN ('soroswap_amm', 'soroswap_aggregator')
)
SELECT i.name AS protocol, i.category, i.measured,
       CASE WHEN i.protocol IN ('soroswap_amm', 'soroswap_total') THEN c_s.registry_contracts ELSE c.registry_contracts END AS pools_or_pairs_tracked,
       CAST(h.history_from AS DATE) AS tracked_since, h.observed_addresses AS addresses_observed,
       CAST(h.last_activity_at AS DATE) AS last_activity, h.pipeline_status AS status
FROM info i
LEFT JOIN health h ON h.protocol = i.protocol
LEFT JOIN contracts c ON c.protocol = i.protocol
LEFT JOIN contracts c_s ON c_s.protocol = 'soroswap'
ORDER BY i.ord
