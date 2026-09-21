-- Query: https://dune.com/queries/8796528
-- Matview: dune.paltalabs.result_scf_users   cron: 0 8 * * *
-- Última ejecución: 01M32KQD3JEQYZN25T4YBV0HXB
-- Costo: 1.059 cr; filas: 137638; engine medium
-- History/live boundary follows the persisted live snapshot, not the clock.
SELECT protocol, activity_date, user_address, role, last_activity_at, row_kind, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_blend_users_live
UNION ALL
SELECT protocol, activity_date, user_address, role, last_activity_at, row_kind, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_blend_users_history
WHERE row_kind = 'metadata' OR activity_date < (SELECT MAX(covered_from) FROM dune.paltalabs.result_scf_blend_users_live WHERE row_kind = 'metadata')
UNION ALL
SELECT protocol, activity_date, user_address, role, last_activity_at, row_kind, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_aquarius_users_live
UNION ALL
SELECT protocol, activity_date, user_address, role, last_activity_at, row_kind, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_aquarius_users_history
WHERE row_kind = 'metadata' OR activity_date < (SELECT MAX(covered_from) FROM dune.paltalabs.result_scf_aquarius_users_live WHERE row_kind = 'metadata')
UNION ALL
SELECT protocol, activity_date, user_address, role, last_activity_at, row_kind, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_soroswap_users_live
UNION ALL
SELECT protocol, activity_date, user_address, role, last_activity_at, row_kind, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_soroswap_users_history
WHERE row_kind = 'metadata' OR activity_date < (SELECT MAX(covered_from) FROM dune.paltalabs.result_scf_soroswap_users_live WHERE row_kind = 'metadata')
UNION ALL
SELECT protocol, activity_date, user_address, role, last_activity_at, row_kind, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_phoenix_users_live
UNION ALL
SELECT protocol, activity_date, user_address, role, last_activity_at, row_kind, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_phoenix_users_history
WHERE row_kind = 'metadata' OR activity_date < (SELECT MAX(covered_from) FROM dune.paltalabs.result_scf_phoenix_users_live WHERE row_kind = 'metadata')
UNION ALL
SELECT protocol, activity_date, user_address, role, last_activity_at, row_kind, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_fxdao_users_live
UNION ALL
SELECT protocol, activity_date, user_address, role, last_activity_at, row_kind, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_fxdao_users_history
WHERE row_kind = 'metadata' OR activity_date < (SELECT MAX(covered_from) FROM dune.paltalabs.result_scf_fxdao_users_live WHERE row_kind = 'metadata')
UNION ALL
SELECT protocol, activity_date, user_address, role, last_activity_at, row_kind, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_etherfuse_users_live
UNION ALL
SELECT protocol, activity_date, user_address, role, last_activity_at, row_kind, covered_from, covered_until, refreshed_at, source_layer FROM dune.paltalabs.result_scf_etherfuse_users_history
WHERE row_kind = 'metadata' OR activity_date < (SELECT MAX(covered_from) FROM dune.paltalabs.result_scf_etherfuse_users_live WHERE row_kind = 'metadata')
