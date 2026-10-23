-- Query: https://dune.com/queries/8996711
-- Matview: None   cron: None
-- Última ejecución: 01M5MDQA200P690M9AGKK0PTM9
-- Costo: 0.112 cr; filas: 11; engine medium
-- Chart source: share of flow actions valued in USD per protocol and flow type, last 90 complete days.
SELECT protocol, flow_type, COUNT(*) AS actions, COUNT_IF(valuation = 'priced') AS priced,
       COUNT_IF(valuation = 'unpriced') AS unpriced, COUNT_IF(valuation IN ('excluded', 'no_tokens')) AS not_valued,
       CAST(COUNT_IF(valuation = 'priced') AS DOUBLE) / NULLIF(COUNT_IF(valuation NOT IN ('excluded', 'no_tokens')), 0) AS priced_share
FROM dune.paltalabs.result_scf_flow_tx
WHERE day >= CURRENT_DATE - INTERVAL '90' DAY AND day < CURRENT_DATE
GROUP BY 1, 2 ORDER BY 1, 2
