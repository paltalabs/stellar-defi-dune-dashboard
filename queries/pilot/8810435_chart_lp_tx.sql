-- Query: https://dune.com/queries/8810435
-- Matview: None   cron: None
-- Última ejecución: 01M358W9JH4JSCWTK2TQGGAA81
-- Costo: 0.087 cr; filas: 200; engine medium
-- Chart source: largest LP actions of the last 30 days, valued in USD.
SELECT closed_at, protocol, action, direction, user_address, pool, token_a, token_amount_a, usd_a,
       token_b, token_amount_b, usd_b, usd_total, valuation, tx_hash
FROM dune.paltalabs.result_scf_lp_tx
WHERE day >= CURRENT_DATE - INTERVAL '30' DAY AND day < CURRENT_DATE
ORDER BY usd_total DESC LIMIT 200
