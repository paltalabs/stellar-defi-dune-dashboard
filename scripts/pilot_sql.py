"""SQL del piloto T1. No estima montos ni atribuye personas a direcciones."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
PROTOCOLS = ('blend', 'aquarius', 'soroswap', 'phoenix', 'fxdao', 'etherfuse')
PILOT_START = '2026-06-01'
HISTORY_START = '2024-02-01'


def users_source(protocol, start, end):
    path = next((ROOT / 'queries' / protocol).glob('*_activity.sql'))
    sql = '\n'.join(line for line in path.read_text().splitlines()
                    if not line.lstrip().startswith('--')).strip()
    sql = re.sub(r"((?:\w+\.)?closed_at_date) >= CURRENT_DATE - INTERVAL '45' DAY[^\n]*",
                 lambda m: f'{m[1]} >= {start} AND {m[1]} < {end}', sql)
    if protocol == 'soroswap':
        # Preserve each event payload; do not MAX(to) over a whole transaction.
        sql = sql.split(',\nkv AS (')[0]
        sql += """,
actors AS (
  SELECT kind, contract_id, closed_at, tx_hash, action,
         json_extract_scalar(elem, '$.val.address') AS user_address
  FROM ev CROSS JOIN UNNEST(CAST(json_extract(data_decoded, '$.map') AS ARRAY(JSON))) AS t(elem)
  WHERE json_extract_scalar(elem, '$.key.symbol') = 'to'
), routed AS (
  SELECT DISTINCT tx_hash FROM actors WHERE kind IN ('router', 'aggregator')
)
SELECT 'soroswap' AS protocol, closed_at, user_address,
       CASE WHEN kind = 'aggregator' THEN 'aggregator_user'
            WHEN action = 'swap' THEN 'swapper' ELSE 'lp' END AS role
FROM actors a
WHERE (kind = 'router' AND action IN ('swap', 'add', 'remove'))
   OR (kind = 'aggregator' AND action = 'swap')
   OR (kind = 'pair' AND action IN ('swap', 'deposit', 'withdraw')
       AND NOT EXISTS (SELECT 1 FROM routed r WHERE r.tx_hash = a.tx_hash))
"""
    elif protocol == 'phoenix':
        # Sender events are sufficient for address activity; never combine senders with MAX.
        sql = sql.split(',\n-- legacy')[0] if ',\n-- legacy' in sql else sql.split(',\nlegacy AS (')[0]
        sql += """,
actors AS (
  SELECT closed_at, action, json_extract_scalar(data_decoded, '$.address') AS user_address
  FROM ev WHERE replace(replace(field, ' ', '_'), '-', '_') = 'sender'
  UNION ALL
  SELECT closed_at, action, json_extract_scalar(elem, '$.val.address')
  FROM ev CROSS JOIN UNNEST(CAST(json_extract(data_decoded, '$.map') AS ARRAY(JSON))) AS t(elem)
  WHERE field IS NULL AND json_extract_scalar(elem, '$.key.symbol') = 'sender'
)
SELECT 'phoenix' AS protocol, closed_at, user_address,
       CASE WHEN action = 'swap' THEN 'swapper' ELSE 'lp' END AS role
FROM actors
"""
    return sql


def daily_users(protocol, layer):
    if layer == 'archive':
        start = f"DATE '{HISTORY_START}'"
        end = "CAST(date_trunc('week', CURRENT_DATE) AS DATE) - INTERVAL '7' DAY"
    elif protocol == 'etherfuse':
        start = "(SELECT MAX(covered_until) - INTERVAL '3' DAY FROM dune.paltalabs.result_scf_etherfuse_users_archive WHERE row_kind = 'metadata')"
        end = 'CURRENT_DATE'
    else:
        start, end = f"DATE '{PILOT_START}'", 'CURRENT_DATE'
    source = users_source(protocol, start, end)
    return f"""-- Generated from scripts/pilot_sql.py; T1 address activity only.
-- Daily UTC buckets. Metadata survives an empty protocol and is never a user.
WITH source AS (
{source}
), users AS (
  SELECT protocol, CAST(closed_at AT TIME ZONE 'UTC' AS DATE) AS activity_date,
         user_address, role, MAX(closed_at) AS last_activity_at
  FROM source
  WHERE regexp_like(user_address, '^[GC][A-Z2-7]{{55}}$') AND role IS NOT NULL
  GROUP BY 1, 2, 3, 4
)
SELECT protocol, activity_date, user_address, role, last_activity_at,
       'activity' AS row_kind, {start} AS covered_from, {end} AS covered_until,
       CURRENT_TIMESTAMP AS refreshed_at, '{layer}' AS source_layer
FROM users
UNION ALL
SELECT '{protocol}', CAST(NULL AS DATE), CAST(NULL AS VARCHAR), CAST(NULL AS VARCHAR),
       CAST(NULL AS TIMESTAMP WITH TIME ZONE), 'metadata', {start}, {end}, CURRENT_TIMESTAMP, '{layer}'
"""


def combined():
    branches = [f'SELECT * FROM dune.paltalabs.result_scf_{p}_users_live' for p in PROTOCOLS]
    branches += ["""SELECT a.* FROM dune.paltalabs.result_scf_etherfuse_users_archive a
WHERE a.row_kind = 'metadata' OR a.activity_date < (
  SELECT MAX(covered_from) FROM dune.paltalabs.result_scf_etherfuse_users_live WHERE row_kind = 'metadata'
)"""]
    return '-- Archive/live boundary follows the persisted live snapshot, not the clock.\n' + '\nUNION ALL\n'.join(branches)


def health():
    return """WITH metadata AS (
  SELECT protocol, MIN(covered_from) AS history_from, MAX(covered_until) AS covered_until,
         MAX(refreshed_at) FILTER (WHERE source_layer = 'live') AS live_refreshed_at,
         MIN(refreshed_at) AS oldest_layer_refresh
  FROM dune.paltalabs.result_scf_users WHERE row_kind = 'metadata' GROUP BY 1
), activity AS (
  SELECT protocol, MAX(last_activity_at) AS last_activity_at,
         COUNT(DISTINCT user_address) AS observed_addresses,
         COUNT(DISTINCT CASE WHEN user_address LIKE 'C%' THEN user_address END) AS c_addresses
  FROM dune.paltalabs.result_scf_users WHERE row_kind = 'activity' GROUP BY 1
)
SELECT m.*, a.last_activity_at, COALESCE(a.observed_addresses, 0) AS observed_addresses,
       COALESCE(a.c_addresses, 0) AS c_addresses,
       date_diff('hour', m.live_refreshed_at, CURRENT_TIMESTAMP) AS refresh_age_hours,
       CASE WHEN date_diff('hour', m.live_refreshed_at, CURRENT_TIMESTAMP) > 36
              OR covered_until < CURRENT_DATE - INTERVAL '1' DAY THEN 'STALE'
            ELSE 'OK' END AS pipeline_status,
       CASE WHEN m.protocol = 'etherfuse' THEN 'Historical since 2024-02-01 + daily live'
            ELSE 'Pilot since 2026-06-01; historical archive pending' END AS coverage_note
FROM metadata m LEFT JOIN activity a ON m.protocol = a.protocol ORDER BY m.protocol
"""


def periods(grain, roles=False):
    role_select = ", role" if roles else ''
    role_join = ' AND a.role = g.role' if roles else ''
    role_group = ', 4' if roles else ''
    return f"""-- Calendar {grain}s in UTC. New = first observed in covered history, not account creation.
WITH metadata AS (
  SELECT protocol, MIN(covered_from) AS history_from, MAX(covered_until) AS covered_until
  FROM dune.paltalabs.result_scf_users WHERE row_kind = 'metadata' GROUP BY 1
), activity AS (
  SELECT protocol, activity_date, user_address, role,
         MIN(activity_date) OVER (PARTITION BY protocol, user_address) AS first_seen
  FROM dune.paltalabs.result_scf_users WHERE row_kind = 'activity'
), grid AS (
  SELECT m.*, period_start{', r.role' if roles else ''}
  FROM metadata m
  CROSS JOIN UNNEST(sequence(CAST(date_trunc('{grain}', history_from) AS DATE),
    CAST(date_trunc('{grain}', covered_until - INTERVAL '1' DAY) AS DATE), {"INTERVAL '7' DAY" if grain == 'week' else "INTERVAL '1' MONTH"})) AS t(period_start)
  {"CROSS JOIN (SELECT DISTINCT role FROM activity) r" if roles else ''}
), counts AS (
  SELECT g.protocol, g.period_start,
    (g.period_start >= g.history_from AND date_add('{grain}', 1, g.period_start) <= g.covered_until) AS is_complete
    {', g.role' if roles else ''},
    COUNT(DISTINCT a.user_address) AS active_addresses,
    COUNT(DISTINCT CASE WHEN a.user_address LIKE 'G%' THEN a.user_address END) AS g_addresses,
    COUNT(DISTINCT CASE WHEN a.user_address LIKE 'C%' THEN a.user_address END) AS c_addresses,
    COUNT(DISTINCT CASE WHEN a.first_seen >= g.period_start THEN a.user_address END) AS new_observed,
    COUNT(DISTINCT CASE WHEN a.first_seen < g.period_start THEN a.user_address END) AS returning_observed,
    MIN(g.history_from) AS history_from, MAX(g.covered_until) AS covered_until
  FROM grid g LEFT JOIN activity a ON a.protocol = g.protocol
    AND a.activity_date >= g.period_start AND a.activity_date < date_add('{grain}', 1, g.period_start){role_join}
  GROUP BY 1, 2, 3{role_group}
), previous AS (
  SELECT *, LAG(active_addresses) OVER (PARTITION BY protocol{role_select} ORDER BY period_start) AS previous_active,
     LAG(is_complete) OVER (PARTITION BY protocol{role_select} ORDER BY period_start) AS previous_complete
  FROM counts
)
SELECT *, CASE WHEN is_complete AND previous_complete AND previous_active > 0
         THEN CAST(active_addresses - previous_active AS DOUBLE) / previous_active END AS growth_rate,
       CASE WHEN is_complete THEN 'Complete' ELSE 'Partial coverage / ongoing' END AS period_status
FROM previous ORDER BY period_start, protocol{role_select}
"""


def validation():
    return """WITH users AS (SELECT * FROM dune.paltalabs.result_scf_users WHERE row_kind = 'activity'),
duplicate_keys AS (
  SELECT protocol, activity_date, user_address, role, COUNT(*) AS n
  FROM users GROUP BY 1,2,3,4 HAVING COUNT(*) > 1
)
SELECT 'duplicate_daily_keys' AS check_name, COALESCE(SUM(n - 1), 0) AS failures FROM duplicate_keys
UNION ALL
SELECT 'invalid_addresses', COUNT(*) FROM users WHERE NOT regexp_like(user_address, '^[GC][A-Z2-7]{55}$')
UNION ALL
SELECT 'invalid_role_or_date', COUNT(*) FROM users WHERE role IS NULL OR activity_date IS NULL
UNION ALL
SELECT 'out_of_coverage', COUNT(*) FROM users WHERE activity_date < covered_from OR activity_date >= covered_until
UNION ALL
SELECT 'missing_protocol_metadata', 6 - COUNT(DISTINCT protocol)
FROM dune.paltalabs.result_scf_users WHERE row_kind = 'metadata'
UNION ALL
SELECT 'cohort_partition_weekly', COUNT(*) FROM dune.paltalabs.result_scf_users_weekly
WHERE new_observed + returning_observed <> active_addresses OR g_addresses + c_addresses <> active_addresses
UNION ALL
SELECT 'cohort_partition_monthly', COUNT(*) FROM dune.paltalabs.result_scf_users_monthly
WHERE new_observed + returning_observed <> active_addresses OR g_addresses + c_addresses <> active_addresses
"""


def chart_protocol(grain):
    # Matview executions only persist a row count, so charts need their own SELECT.
    return f"""-- Chart source: complete calendar {grain}s since the common pilot start, one row per protocol.
SELECT period_start, protocol, active_addresses, g_addresses, c_addresses,
       new_observed, returning_observed, growth_rate
FROM dune.paltalabs.result_scf_users_{grain}ly
WHERE is_complete AND period_start >= DATE '{PILOT_START}'
ORDER BY period_start, protocol
"""


def chart_roles(grain):
    return f"""-- Chart source: unique addresses per role across all protocols, complete calendar {grain}s.
SELECT CAST(date_trunc('{grain}', activity_date) AS DATE) AS period_start, role,
       COUNT(DISTINCT user_address) AS active_addresses,
       COUNT(DISTINCT CASE WHEN user_address LIKE 'C%' THEN user_address END) AS c_addresses
FROM dune.paltalabs.result_scf_users
WHERE row_kind = 'activity' AND activity_date >= DATE '{PILOT_START}'
  AND activity_date < CAST(date_trunc('{grain}', CURRENT_DATE) AS DATE)
GROUP BY 1, 2
ORDER BY 1, 2
"""


def chart_health():
    return """-- Chart source: coverage and freshness per protocol plus the validation total.
SELECT h.protocol, h.history_from, h.covered_until, h.last_activity_at, h.observed_addresses,
       h.c_addresses, h.live_refreshed_at, h.pipeline_status, h.coverage_note,
       (SELECT SUM(failures) FROM dune.paltalabs.result_scf_users_validation) AS validation_failures
FROM dune.paltalabs.result_scf_users_health h
ORDER BY h.protocol
"""


CHARTS = {'chart_weekly_protocol': lambda: chart_protocol('week'),
          'chart_monthly_protocol': lambda: chart_protocol('month'),
          'chart_roles_weekly': lambda: chart_roles('week'),
          'chart_roles_monthly': lambda: chart_roles('month'),
          'chart_health': chart_health}
