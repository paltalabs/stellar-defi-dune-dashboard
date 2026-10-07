-- Query: https://dune.com/queries/8913380
-- Matview: ninguna (gráfico, schedule de Dune)
-- Última ejecución: 01M4C26XNYRMT19DC74KFN8W1R
-- Costo: 0.227 cr; filas: 9; engine medium
-- Chart source: the protocols this dashboard tracks, with what is measured and current coverage.
-- Soroswap appears as its two products and as a total (unique addresses across both).
WITH info (protocol, name, category, measured, ord) AS (VALUES
  ('blend', 'Blend', 'Lending', 'Supply, withdraw, borrow, repay, liquidations, backstop deposits and withdrawals', 1),
  ('aquarius', 'Aquarius', 'AMM', 'Swaps, liquidity deposits and withdrawals, reward claims', 2),
  ('soroswap_total', 'Soroswap (AMM + aggregator)', 'AMM and aggregator', 'Any of the two Soroswap products below; an address using both counts once', 3),
  ('soroswap_amm', '  Soroswap AMM', 'AMM', 'Swaps and liquidity on the Soroswap router and pairs', 4),
  ('soroswap_aggregator', '  Soroswap Aggregator', 'Aggregator', 'Swaps routed by the aggregator: contracts (all versions), SDEX path payments and multicall swaps built by its API', 5),
  ('phoenix', 'Phoenix', 'AMM', 'Swaps, liquidity provided and withdrawn', 6),
  ('sushiswap', 'SushiSwap', 'AMM (concentrated liquidity)', 'Swaps, liquidity minted and collected (since March 2026)', 7),
  ('fxdao', 'FxDAO', 'CDP stablecoins', 'Vault operations, redemptions, liquidations and locking pool', 8),
  ('etherfuse', 'Etherfuse', 'Tokenized bonds (classic assets)', 'Mints, redeems, payments and SDEX trades of its stablebonds', 9)
), contracts AS (
  SELECT protocol, COUNT(DISTINCT contract_id) AS registry_contracts FROM dune.paltalabs.result_scf_contracts GROUP BY 1
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
