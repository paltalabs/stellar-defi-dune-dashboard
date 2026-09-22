-- Query: https://dune.com/queries/8810360
-- Matview: dune.paltalabs.result_scf_lp_price_coverage   cron: 0 9 * * *
-- Última ejecución: 01M358SWRK1W81AC4MKN08KJKH
-- Costo: 1.08 cr; filas: 10; engine medium
-- Share of LP USD and actions that could be valued, per protocol, last 90 complete days and all time.
SELECT CASE WHEN day >= CURRENT_DATE - INTERVAL '90' DAY THEN 'last_90d' ELSE 'older' END AS window_name, protocol,
       COUNT(*) AS lp_actions, COUNT_IF(valuation = 'priced') AS priced, COUNT_IF(valuation = 'partial') AS partial,
       COUNT_IF(valuation = 'unpriced') AS unpriced, COUNT_IF(valuation = 'no_tokens') AS no_tokens,
       CAST(COUNT_IF(valuation = 'priced') AS DOUBLE) / NULLIF(COUNT_IF(valuation <> 'no_tokens'), 0) AS priced_share
FROM dune.paltalabs.result_scf_lp_tx WHERE day < CURRENT_DATE
GROUP BY 1, 2 ORDER BY 1, 2
