-- Query: https://dune.com/queries/8810230
-- Matview: None   cron: None
-- Última ejecución: 01M357NQRZC2SH03RQMCDWDWZM
-- Costo: 0.031 cr; filas: 170; engine medium
-- Chart source: new ecosystem addresses per month by entry protocol, complete months.
SELECT entry_month, entry_protocol, new_ecosystem_addresses, g_addresses, used_other_protocols_later
FROM dune.paltalabs.result_scf_first_protocol
WHERE is_complete
ORDER BY entry_month, entry_protocol
