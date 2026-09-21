-- Query: https://dune.com/queries/8796528
-- Matview: dune.paltalabs.result_scf_users   cron: 0 8 * * *
-- Última ejecución: 01M32D28K5R7HT4KKZ9P1DYASW
-- Costo: 1.206 cr; filas: 119814; engine medium
-- Archive/live boundary follows the persisted live snapshot, not the clock.
SELECT * FROM dune.paltalabs.result_scf_blend_users_live
UNION ALL
SELECT * FROM dune.paltalabs.result_scf_aquarius_users_live
UNION ALL
SELECT * FROM dune.paltalabs.result_scf_soroswap_users_live
UNION ALL
SELECT * FROM dune.paltalabs.result_scf_phoenix_users_live
UNION ALL
SELECT * FROM dune.paltalabs.result_scf_fxdao_users_live
UNION ALL
SELECT * FROM dune.paltalabs.result_scf_etherfuse_users_live
UNION ALL
SELECT a.* FROM dune.paltalabs.result_scf_etherfuse_users_archive a
WHERE a.row_kind = 'metadata' OR a.activity_date < (
  SELECT MAX(covered_from) FROM dune.paltalabs.result_scf_etherfuse_users_live WHERE row_kind = 'metadata'
)
