-- Query: https://dune.com/queries/8796720
-- Matview: None   cron: None
-- Última ejecución: 01M32WXY0PHQEFY9Z5RP77HT4J
-- Costo: 0.035 cr; filas: 186; engine medium
-- Chart source: complete calendar months since 2024-02-01, one row per protocol.
SELECT period_start, protocol, active_addresses, g_addresses, c_addresses,
       new_observed, returning_observed, growth_rate
FROM dune.paltalabs.result_scf_users_monthly
WHERE is_complete AND period_start >= DATE '2024-02-01'
ORDER BY period_start, protocol
