-- Query: https://dune.com/queries/8796719
-- Matview: None   cron: None
-- Última ejecución: 01M5JYZQHGQ0N8GAXKV7N3CXMW
-- Costo: 0.039 cr; filas: 117; engine medium
-- Chart source: complete calendar weeks (months since 2024-02-01, the last 13 weeks), one row per protocol.
SELECT period_start, protocol, active_addresses, g_addresses, c_addresses,
       new_observed, returning_observed, growth_rate
FROM dune.paltalabs.result_scf_users_weekly
WHERE is_complete AND period_start >= date_add('week', -13, CAST(date_trunc('week', CURRENT_DATE) AS DATE))
ORDER BY period_start, protocol
