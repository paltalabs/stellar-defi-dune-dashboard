-- Query: https://dune.com/queries/8796720
-- Matview: None   cron: None
-- Última ejecución: 01M5JYZW31QG2TJ65D451M45NV
-- Costo: 0.041 cr; filas: 248; engine medium
-- Chart source: complete calendar months (months since 2024-02-01, the last 13 weeks), one row per protocol.
SELECT period_start, protocol, active_addresses, g_addresses, c_addresses,
       new_observed, returning_observed, growth_rate
FROM dune.paltalabs.result_scf_users_monthly
WHERE is_complete AND period_start >= DATE '2024-02-01'
ORDER BY period_start, protocol
