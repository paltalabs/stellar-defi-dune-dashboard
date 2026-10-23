-- Query: https://dune.com/queries/8996705
-- Matview: None   cron: None
-- Última ejecución: 01M5MDPKFYWRQ96AB5RXW0E0CJ
-- Costo: 0.055 cr; filas: 20; engine medium
-- Chart source: top 20 pools and vaults by liquidity moved (in + out), last 90 complete days, G and C.
WITH p AS (
  SELECT protocol, pool,
         SUM(usd_value) FILTER (WHERE direction = 'in') AS usd_in,
         SUM(usd_value) FILTER (WHERE direction = 'out') AS usd_out,
         COUNT(*) AS actions, COUNT(DISTINCT user_address) AS addresses,
         COUNT(DISTINCT CASE WHEN address_type = 'G' THEN user_address END) AS g_addresses
  FROM dune.paltalabs.result_scf_flow_tx
  WHERE flow_type = 'liquidity' AND day >= CURRENT_DATE - INTERVAL '90' DAY AND day < CURRENT_DATE
  GROUP BY 1, 2
)
SELECT protocol, pool, usd_in, usd_out, COALESCE(usd_in, 0) - COALESCE(usd_out, 0) AS usd_net,
       COALESCE(usd_in, 0) + COALESCE(usd_out, 0) AS usd_moved, actions, addresses, g_addresses
FROM p ORDER BY usd_moved DESC LIMIT 20
