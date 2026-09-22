"""SQL del piloto T1. No estima montos ni atribuye personas a direcciones."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
PROTOCOLS = ('blend', 'aquarius', 'soroswap', 'phoenix', 'fxdao', 'etherfuse')
PILOT_START = '2026-06-01'
LIVE_DAYS = 10          # static window so Dune prunes partitions; history holds everything older
BRIDGE_LIVE_FROM = '2026-09-17'   # Fase 0: history (frozen, until 2026-09-19) minus 2 days, literal for pruning
HISTORY_LAG_DAYS = 2    # history freezes up to live covered_until - 2 days (late rows stay live)
HISTORY_START = '2024-02-01'


def aquarius_source(start, end):
    """Router events plus pool events. Pools are where most Aquarius activity happens: in a 7-day
    sample (2026-09-21) 736 of 904 deposit_liquidity txs and 71.851 of 113.543 trade txs had no
    router event. deposit/withdraw_liquidity carry no user, so the tx signer is used."""
    import csv
    pools = [r['pool'] for r in csv.DictReader(open(ROOT / 'data' / 'aquarius-pools.csv'))]
    routers = ['CBQDHNBFBZYE4MKPWBSJOPIYLW4SFSXAXUTSXJN76GNKYVYPCKWC6QUK',
               'CA7RQDMMV6E53P5EDZA5GPWBZ33AMW2ZNO42XLI2RGRIAP4QXIARUOJQ',
               'CB4YHF4ESRJ4XZRXISLXSUZTYY6YPBPZ73MZWSTUWY46DKYW7IGLHGF7']
    # Literal IN lists: an IN (subquery UNION ...) here cost 181 cr on 2026-09-21 (no pruning on
    # contract_id); the same filter as a literal list cost 1,39 cr for 7 days.
    lit = lambda xs: ', '.join(f"'{x}'" for x in xs)
    return f"""WITH ev AS (
  SELECT DISTINCT he.contract_id, he.closed_at, lower(to_hex(he.transaction_hash)) AS tx_hash, he.topics_decoded
  FROM stellar.history_contract_events he
  WHERE he.closed_at_date >= {start} AND he.closed_at_date < {end}
    AND he.contract_id IN ({lit(routers + pools)})
    AND he.type_string = 'ContractEventTypeContract'
    AND he.successful = TRUE AND he.in_successful_contract_call = TRUE
    AND json_extract_scalar(he.topics_decoded, '$[0].symbol') IN ('swap', 'deposit', 'withdraw', 'claim',
        'trade', 'deposit_liquidity', 'withdraw_liquidity', 'claim_reward', 'position_update')
), tagged AS (
  SELECT e.*, json_extract_scalar(e.topics_decoded, '$[0].symbol') AS action,
         e.contract_id IN ({lit(routers)}) AS is_router
  FROM ev e
), routed AS (
  SELECT DISTINCT tx_hash FROM tagged WHERE is_router
), lp_direct AS (
  SELECT DISTINCT tx_hash, closed_at FROM tagged
  WHERE NOT is_router AND action IN ('deposit_liquidity', 'withdraw_liquidity')
    AND tx_hash NOT IN (SELECT tx_hash FROM routed)
), tx AS (
  SELECT t.id, lower(to_hex(t.transaction_hash)) AS tx_hash
  FROM stellar.history_transactions t
  WHERE t.closed_at_date >= {start} AND t.closed_at_date < {end} AND t.successful = TRUE
    AND lower(to_hex(t.transaction_hash)) IN (SELECT tx_hash FROM lp_direct)
), signer AS (
  SELECT tx.tx_hash, MIN(o.source_account) AS source_account
  FROM stellar.history_operations o JOIN tx ON tx.id = o.transaction_id
  WHERE o.closed_at_date >= {start} AND o.closed_at_date < {end} AND o.type_string = 'invoke_host_function'
  GROUP BY 1
)
SELECT 'aquarius' AS protocol, closed_at, user_address, role FROM (
  SELECT closed_at, json_extract_scalar(topics_decoded, '$[2].address') AS user_address,
         CASE action WHEN 'swap' THEN 'swapper' WHEN 'claim' THEN 'claimer' ELSE 'lp' END AS role
  FROM tagged WHERE is_router AND action IN ('swap', 'deposit', 'withdraw', 'claim')
  UNION ALL
  -- Direct pool trades: topics[3] is the caller (the router itself when routed, so excluded).
  SELECT closed_at, json_extract_scalar(topics_decoded, '$[3].address'), 'swapper'
  FROM tagged WHERE NOT is_router AND action = 'trade'
    AND json_extract_scalar(topics_decoded, '$[3].address') NOT IN ({lit(routers)})
  UNION ALL
  SELECT closed_at, json_extract_scalar(topics_decoded, '$[2].address'), 'claimer'
  FROM tagged WHERE NOT is_router AND action = 'claim_reward'
  UNION ALL
  SELECT closed_at, json_extract_scalar(topics_decoded, '$[1].address'), 'lp'
  FROM tagged WHERE NOT is_router AND action = 'position_update'
  UNION ALL
  SELECT d.closed_at, s.source_account, 'lp' FROM lp_direct d JOIN signer s ON s.tx_hash = d.tx_hash
)"""


def users_source(protocol, start, end):
    if protocol == 'aquarius':
        return aquarius_source(start, end)
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
    elif layer == 'history':
        # One-time raw build of the history layer (Aquarius, after the pool-event rewrite).
        start, end = f"DATE '{PILOT_START}'", f"DATE '{HISTORY_BOOTSTRAP_UNTIL}'"
    else:
        # Fase 0 bridge until the CLAUDE.md activity layers exist: grows one day per day, never gaps.
        start, end = f"DATE '{BRIDGE_LIVE_FROM}'", 'CURRENT_DATE'
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


HISTORY_BOOTSTRAP_UNTIL = '2026-09-19'
COLUMNS = ('protocol, activity_date, user_address, role, last_activity_at, row_kind, '
           'covered_from, covered_until, refreshed_at, source_layer')


def history_bootstrap(protocol):
    """First build of result_scf_<p>_users_history, copied from matviews that already hold the
    data (no raw scan). Aquarius is rebuilt from raw because its source logic changed."""
    if protocol == 'aquarius':
        return daily_users('aquarius', 'history')
    live = f'dune.paltalabs.result_scf_{protocol}_users_live'
    until = f"DATE '{HISTORY_BOOTSTRAP_UNTIL}'"
    start = f"DATE '{HISTORY_START if protocol == 'etherfuse' else PILOT_START}'"
    rows = f"""SELECT protocol, activity_date, user_address, role, last_activity_at FROM {live}
  WHERE row_kind = 'activity' AND activity_date < {until}"""
    if protocol == 'etherfuse':
        rows += f"""
  UNION ALL
  SELECT protocol, activity_date, user_address, role, last_activity_at
  FROM dune.paltalabs.result_scf_etherfuse_users_archive
  WHERE row_kind = 'activity' AND activity_date < (SELECT MAX(covered_from) FROM {live} WHERE row_kind = 'metadata')"""
    return f"""-- Bootstrap of the history layer from existing matviews. Replaced by the incremental SQL after the first run.
WITH r AS (
  {rows}
)
SELECT protocol, activity_date, user_address, role, last_activity_at, 'activity' AS row_kind,
       {start} AS covered_from, {until} AS covered_until, CURRENT_TIMESTAMP AS refreshed_at, 'history' AS source_layer
FROM r
UNION ALL
SELECT '{protocol}', CAST(NULL AS DATE), CAST(NULL AS VARCHAR), CAST(NULL AS VARCHAR),
       CAST(NULL AS TIMESTAMP WITH TIME ZONE), 'metadata', {start}, {until}, CURRENT_TIMESTAMP, 'history'
"""


def history_incremental(protocol):
    """Reads its own matview and appends the days the live layer has settled. Never rescans raw
    tables. If the live window no longer touches the history end, it does not advance (gap check
    in users_validation reports it)."""
    own = f'dune.paltalabs.result_scf_{protocol}_users_history'
    live = f'dune.paltalabs.result_scf_{protocol}_users_live'
    return f"""-- Incremental history: previous snapshot of this same matview + settled days from the live layer.
WITH prev AS (SELECT * FROM {own}),
pm AS (SELECT MIN(covered_from) AS covered_from, MAX(covered_until) AS old_until FROM prev WHERE row_kind = 'metadata'),
lm AS (SELECT MIN(covered_from) AS live_from, MAX(covered_until) AS live_until FROM {live} WHERE row_kind = 'metadata'),
b AS (
  SELECT pm.covered_from, pm.old_until,
         CASE WHEN lm.live_from <= pm.old_until
              THEN GREATEST(pm.old_until, CAST(lm.live_until - INTERVAL '{HISTORY_LAG_DAYS}' DAY AS DATE))
              ELSE pm.old_until END AS new_until
  FROM pm CROSS JOIN lm
)
SELECT p.protocol, p.activity_date, p.user_address, p.role, p.last_activity_at, 'activity' AS row_kind,
       b.covered_from, b.new_until AS covered_until, CURRENT_TIMESTAMP AS refreshed_at, 'history' AS source_layer
FROM prev p CROSS JOIN b WHERE p.row_kind = 'activity' AND p.activity_date < b.old_until
UNION ALL
SELECT l.protocol, l.activity_date, l.user_address, l.role, l.last_activity_at, 'activity',
       b.covered_from, b.new_until, CURRENT_TIMESTAMP, 'history'
FROM {live} l CROSS JOIN b
WHERE l.row_kind = 'activity' AND l.activity_date >= b.old_until AND l.activity_date < b.new_until
UNION ALL
SELECT '{protocol}', CAST(NULL AS DATE), CAST(NULL AS VARCHAR), CAST(NULL AS VARCHAR),
       CAST(NULL AS TIMESTAMP WITH TIME ZONE), 'metadata', b.covered_from, b.new_until, CURRENT_TIMESTAMP, 'history'
FROM b
"""


def combined():
    branches = []
    for p in PROTOCOLS:
        live = f'dune.paltalabs.result_scf_{p}_users_live'
        branches.append(f'SELECT {COLUMNS} FROM {live}')
        branches.append(f"""SELECT {COLUMNS} FROM dune.paltalabs.result_scf_{p}_users_history
WHERE row_kind = 'metadata' OR activity_date < (SELECT MAX(covered_from) FROM {live} WHERE row_kind = 'metadata')""")
    return '-- History/live boundary follows the persisted live snapshot, not the clock.\n' + '\nUNION ALL\n'.join(branches)


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
       'Full history since ' || CAST(m.history_from AS VARCHAR) || '; archive monthly, live daily' AS coverage_note
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
    import activity_sql
    registered = activity_sql.lit(activity_sql.registered_literals())
    return f"""WITH users AS (SELECT * FROM dune.paltalabs.result_scf_users WHERE row_kind = 'activity'),
duplicate_keys AS (
  SELECT protocol, activity_date, user_address, role, COUNT(*) AS n
  FROM users GROUP BY 1,2,3,4 HAVING COUNT(*) > 1
)
SELECT 'duplicate_daily_keys' AS check_name, COALESCE(SUM(n - 1), 0) AS failures FROM duplicate_keys
UNION ALL
SELECT 'invalid_addresses', COUNT(*) FROM users WHERE NOT regexp_like(user_address, '^[GC][A-Z2-7]{{55}}$')
UNION ALL
SELECT 'invalid_role_or_date', COUNT(*) FROM users WHERE role IS NULL OR activity_date IS NULL
UNION ALL
SELECT 'out_of_coverage', COUNT(*) FROM users WHERE activity_date < covered_from OR activity_date >= covered_until
UNION ALL
SELECT 'missing_protocol_metadata', {len(activity_sql.PROTOCOLS)} - COUNT(DISTINCT protocol)
FROM dune.paltalabs.result_scf_users WHERE row_kind = 'metadata'
UNION ALL
SELECT 'archive_live_gap', COUNT(*) FROM (
  SELECT protocol FROM dune.paltalabs.result_scf_users WHERE row_kind = 'metadata'
  GROUP BY 1
  HAVING MAX(covered_until) FILTER (WHERE source_layer = 'archive') IS NULL
      OR MAX(covered_until) FILTER (WHERE source_layer = 'archive') < MAX(covered_from) FILTER (WHERE source_layer = 'live')
)
UNION ALL
SELECT 'unregistered_contracts', COUNT(*) FROM dune.paltalabs.result_scf_contracts
WHERE contract_id NOT IN ({registered})
UNION ALL
SELECT 'cohort_partition_weekly', COUNT(*) FROM dune.paltalabs.result_scf_users_weekly
WHERE new_observed + returning_observed <> active_addresses OR g_addresses + c_addresses <> active_addresses
UNION ALL
SELECT 'cohort_partition_monthly', COUNT(*) FROM dune.paltalabs.result_scf_users_monthly
WHERE new_observed + returning_observed <> active_addresses OR g_addresses + c_addresses <> active_addresses
UNION ALL
SELECT 'overlap_diagonal_vs_health', COUNT(*) FROM dune.paltalabs.result_scf_overlap_matrix m
JOIN dune.paltalabs.result_scf_users_health h ON h.protocol = m.protocol_a
WHERE m.window_name = 'all_time' AND m.protocol_a = m.protocol_b AND m.shared_addresses <> h.observed_addresses
UNION ALL
SELECT 'overlap_totals', ABS((SELECT COUNT(DISTINCT user_address) FROM users)
  - (SELECT SUM(new_ecosystem_addresses) FROM dune.paltalabs.result_scf_first_protocol))
  + ABS((SELECT COUNT(DISTINCT user_address) FROM users)
  - (SELECT SUM(addresses) FROM dune.paltalabs.result_scf_protocol_count WHERE period_kind = 'all_time'))
  + ABS((SELECT COUNT(DISTINCT user_address) FROM users)
  - (SELECT SUM(addresses) FROM dune.paltalabs.result_scf_journeys))
"""


def chart_protocol(grain):
    # Matview executions only persist a row count, so charts need their own SELECT.
    return f"""-- Chart source: complete calendar {grain}s since 2024-02-01, one row per protocol.
SELECT period_start, protocol, active_addresses, g_addresses, c_addresses,
       new_observed, returning_observed, growth_rate
FROM dune.paltalabs.result_scf_users_{grain}ly
WHERE is_complete AND period_start >= DATE '{HISTORY_START}'
ORDER BY period_start, protocol
"""


def chart_roles(grain):
    return f"""-- Chart source: unique addresses per role across all protocols, complete calendar {grain}s.
SELECT CAST(date_trunc('{grain}', activity_date) AS DATE) AS period_start, role,
       COUNT(DISTINCT user_address) AS active_addresses,
       COUNT(DISTINCT CASE WHEN user_address LIKE 'C%' THEN user_address END) AS c_addresses
FROM dune.paltalabs.result_scf_users
WHERE row_kind = 'activity' AND activity_date >= DATE '{HISTORY_START}'
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


def chart_ecosystem(grain):
    return f"""-- Chart source: unique addresses across all protocols, complete calendar {grain}s.
SELECT CAST(date_trunc('{grain}', activity_date) AS DATE) AS period_start,
       COUNT(DISTINCT user_address) AS active_addresses,
       COUNT(DISTINCT CASE WHEN user_address LIKE 'G%' THEN user_address END) AS g_addresses,
       COUNT(DISTINCT CASE WHEN user_address LIKE 'C%' THEN user_address END) AS c_addresses
FROM dune.paltalabs.result_scf_users
WHERE row_kind = 'activity' AND activity_date >= DATE '{HISTORY_START}'
  AND activity_date < CAST(date_trunc('{grain}', CURRENT_DATE) AS DATE)
GROUP BY 1
ORDER BY 1
"""


USERS = "dune.paltalabs.result_scf_users WHERE row_kind = 'activity' AND activity_date < CURRENT_DATE"
FIRSTS = f"""SELECT user_address, protocol, MIN(activity_date) AS first_seen
  FROM {USERS} GROUP BY 1, 2"""


def overlap_matrix():
    """Deliverable 2. Diagonal = addresses of the protocol, so share_of_a is 'of A's addresses,
    how many also used B'. Intermediary contracts (aggregator, routers) inflate C overlap; the
    G columns are the main view."""
    return f"""-- Protocol x protocol shared addresses, all time and last 90/28 complete UTC days.
WITH windows AS (
  SELECT * FROM (VALUES ('all_time', DATE '{HISTORY_START}'),
    ('last_90d', CAST(CURRENT_DATE - INTERVAL '90' DAY AS DATE)),
    ('last_28d', CAST(CURRENT_DATE - INTERVAL '28' DAY AS DATE))) AS t(window_name, window_from)
), pa AS (
  SELECT DISTINCT w.window_name, w.window_from, u.protocol, u.user_address
  FROM dune.paltalabs.result_scf_users u CROSS JOIN windows w
  WHERE u.row_kind = 'activity' AND u.activity_date >= w.window_from AND u.activity_date < CURRENT_DATE
), totals AS (
  SELECT window_name, protocol, COUNT(*) AS protocol_addresses,
         COUNT_IF(user_address LIKE 'G%') AS protocol_g_addresses
  FROM pa GROUP BY 1, 2
), pairs AS (
  SELECT a.window_name, a.window_from, a.protocol AS protocol_a, b.protocol AS protocol_b,
         COUNT(*) AS shared_addresses, COUNT_IF(a.user_address LIKE 'G%') AS shared_g_addresses
  FROM pa a JOIN pa b ON a.window_name = b.window_name AND a.user_address = b.user_address
  GROUP BY 1, 2, 3, 4
)
SELECT p.window_name, p.window_from, CURRENT_DATE AS window_until, p.protocol_a, p.protocol_b,
       p.shared_addresses, p.shared_g_addresses, p.shared_addresses - p.shared_g_addresses AS shared_c_addresses,
       t.protocol_addresses AS protocol_a_addresses, t.protocol_g_addresses AS protocol_a_g_addresses,
       CAST(p.shared_addresses AS DOUBLE) / t.protocol_addresses AS share_of_a,
       CAST(p.shared_g_addresses AS DOUBLE) / NULLIF(t.protocol_g_addresses, 0) AS g_share_of_a
FROM pairs p JOIN totals t ON t.window_name = p.window_name AND t.protocol = p.protocol_a
ORDER BY 1, 4, 5
"""


def protocol_count():
    return f"""-- How many protocols each address used: all time, last 28 complete days, complete calendar months.
WITH u AS (SELECT protocol, activity_date, user_address FROM {USERS}),
per_period AS (
  SELECT 'all_time' AS period_kind, DATE '{HISTORY_START}' AS period_start, user_address,
         COUNT(DISTINCT protocol) AS protocols_used
  FROM u GROUP BY 3
  UNION ALL
  SELECT 'last_28d', CAST(CURRENT_DATE - INTERVAL '28' DAY AS DATE), user_address, COUNT(DISTINCT protocol)
  FROM u WHERE activity_date >= CURRENT_DATE - INTERVAL '28' DAY GROUP BY 3
  UNION ALL
  SELECT 'month', CAST(date_trunc('month', activity_date) AS DATE), user_address, COUNT(DISTINCT protocol)
  FROM u WHERE activity_date < CAST(date_trunc('month', CURRENT_DATE) AS DATE) GROUP BY 2, 3
), buckets AS (
  SELECT period_kind, period_start,
         CASE WHEN protocols_used >= 4 THEN '4+' ELSE CAST(protocols_used AS VARCHAR) END AS protocols_used,
         COUNT(*) AS addresses, COUNT_IF(user_address LIKE 'G%') AS g_addresses,
         COUNT_IF(user_address LIKE 'C%') AS c_addresses
  FROM per_period GROUP BY 1, 2, 3
)
SELECT *, CAST(addresses AS DOUBLE) / SUM(addresses) OVER (PARTITION BY period_kind, period_start) AS share_of_addresses,
       CAST(g_addresses AS DOUBLE) / NULLIF(SUM(g_addresses) OVER (PARTITION BY period_kind, period_start), 0) AS share_of_g_addresses
FROM buckets ORDER BY 1, 2, 3
"""


def first_protocol():
    return f"""-- Entry protocol of each address into the covered ecosystem (first day seen since {HISTORY_START}).
-- Seen in two protocols on its first day -> 'multiple'. Not account creation.
WITH firsts AS ({FIRSTS}),
eco AS (SELECT user_address, MIN(first_seen) AS eco_first_seen, COUNT(*) AS protocols_used FROM firsts GROUP BY 1),
entry AS (
  SELECT e.user_address, e.eco_first_seen, e.protocols_used,
         CASE WHEN COUNT(*) > 1 THEN 'multiple' ELSE MAX(f.protocol) END AS entry_protocol
  FROM eco e JOIN firsts f ON f.user_address = e.user_address AND f.first_seen = e.eco_first_seen
  GROUP BY 1, 2, 3
)
SELECT CAST(date_trunc('month', eco_first_seen) AS DATE) AS entry_month, entry_protocol,
       COUNT(*) AS new_ecosystem_addresses,
       COUNT_IF(user_address LIKE 'G%') AS g_addresses, COUNT_IF(user_address LIKE 'C%') AS c_addresses,
       COUNT_IF(protocols_used > 1) AS used_other_protocols_later,
       CAST(date_trunc('month', eco_first_seen) AS DATE) < CAST(date_trunc('month', CURRENT_DATE) AS DATE) AS is_complete
FROM entry GROUP BY 1, 2 ORDER BY 1, 2
"""


def journeys():
    return f"""-- First protocol -> second protocol per address (by first day seen). 'none' = never used a second one.
WITH firsts AS ({FIRSTS}),
ranked AS (SELECT *, DENSE_RANK() OVER (PARTITION BY user_address ORDER BY first_seen) AS step FROM firsts),
steps AS (
  SELECT user_address, step, MIN(first_seen) AS first_seen,
         CASE WHEN COUNT(*) > 1 THEN 'multiple' ELSE MAX(protocol) END AS protocol
  FROM ranked WHERE step <= 2 GROUP BY 1, 2
), pairs AS (
  SELECT s1.user_address, s1.protocol AS from_protocol, COALESCE(s2.protocol, 'none') AS to_protocol,
         date_diff('day', s1.first_seen, s2.first_seen) AS days_to_second
  FROM steps s1 LEFT JOIN steps s2 ON s2.user_address = s1.user_address AND s2.step = 2
  WHERE s1.step = 1
)
SELECT from_protocol, to_protocol, COUNT(*) AS addresses,
       COUNT_IF(user_address LIKE 'G%') AS g_addresses, COUNT_IF(user_address LIKE 'C%') AS c_addresses,
       CAST(COUNT(*) AS DOUBLE) / SUM(COUNT(*)) OVER (PARTITION BY from_protocol) AS share_of_from,
       approx_percentile(days_to_second, 0.5) AS median_days_to_second
FROM pairs GROUP BY 1, 2 ORDER BY 1, 3 DESC
"""


def chart_overlap():
    return """-- Chart source: protocol x protocol overlap, all time and last 90 days, off-diagonal pairs.
SELECT window_name, protocol_a, protocol_b, shared_addresses, shared_g_addresses, protocol_a_addresses,
       share_of_a, g_share_of_a
FROM dune.paltalabs.result_scf_overlap_matrix
WHERE window_name IN ('all_time', 'last_90d') AND protocol_a <> protocol_b AND shared_addresses > 0
ORDER BY window_name, share_of_a DESC
"""


def chart_protocol_count():
    return """-- Chart source: addresses by number of protocols used, complete calendar months.
SELECT period_start, protocols_used, addresses, g_addresses, share_of_addresses
FROM dune.paltalabs.result_scf_protocol_count
WHERE period_kind = 'month'
ORDER BY period_start, protocols_used
"""


def chart_first_protocol():
    return """-- Chart source: new ecosystem addresses per month by entry protocol, complete months.
SELECT entry_month, entry_protocol, new_ecosystem_addresses, g_addresses, used_other_protocols_later
FROM dune.paltalabs.result_scf_first_protocol
WHERE is_complete
ORDER BY entry_month, entry_protocol
"""


def chart_journeys():
    return """-- Chart source: first -> second protocol journeys, excluding addresses that stayed in one protocol.
SELECT from_protocol, to_protocol, addresses, g_addresses, share_of_from, median_days_to_second
FROM dune.paltalabs.result_scf_journeys
WHERE to_protocol <> 'none'
ORDER BY addresses DESC
"""


CHARTS = {'chart_integrity':lambda: __import__('activity_sql').chart_integrity(),
          'chart_ecosystem_weekly': lambda: chart_ecosystem('week'),
          'chart_ecosystem_monthly': lambda: chart_ecosystem('month'),
'chart_weekly_protocol': lambda: chart_protocol('week'),
          'chart_monthly_protocol': lambda: chart_protocol('month'),
          'chart_roles_weekly': lambda: chart_roles('week'),
          'chart_roles_monthly': lambda: chart_roles('month'),
          'chart_health': chart_health,
          'chart_overlap': chart_overlap,
          'chart_protocol_count': chart_protocol_count,
          'chart_first_protocol': chart_first_protocol,
          'chart_journeys': chart_journeys}
