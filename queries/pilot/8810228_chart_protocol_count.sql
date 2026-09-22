-- Query: https://dune.com/queries/8810228
-- Matview: None   cron: None
-- Última ejecución: 01M357NKVS3W88CAQ21GFPDMRT
-- Costo: 0.035 cr; filas: 111; engine medium
-- Chart source: addresses by number of protocols used, complete calendar months.
SELECT period_start, protocols_used, addresses, g_addresses, share_of_addresses
FROM dune.paltalabs.result_scf_protocol_count
WHERE period_kind = 'month'
ORDER BY period_start, protocols_used
