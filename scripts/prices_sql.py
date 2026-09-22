"""SQL de la Tranche 2, Entregable 3: precios diarios propios y actividad de LPs (solo AMMs).

Tokens: data/tokens.csv (export-tokens en deploy_pilot.py). Cada token de las capas es un contrato
(SAC o wasm) o un asset clásico ('native', 'CODE:ISSUER', vía SDEX del aggregator de Soroswap). Un
SAC se une a su asset clásico con scripts/sac.py (id derivado offline, validado 253 de 253). Los
wasm traen sus decimales en METADATA; las capas guardan raw * 1e-7, así que el monto real es
amount * 10^(7 - decimals).

Precio: por día y asset, VWAP del SDEX contra USDC de Circle; si no alcanza el volumen mínimo,
VWAP contra XLM por XLM/USDC del día. Los tokens sin mercado en el SDEX ese día toman el precio
implícito de sus swaps Soroban (capas de actividad) contra un token con precio SDEX.
"""
import csv
from pathlib import Path

import activity_sql

ROOT = Path(__file__).resolve().parent.parent
TOKENS_CSV = ROOT / 'data' / 'tokens.csv'
USDC = 'USDC:GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN'
START = activity_sql.HISTORY_START
MIN_USD_VOLUME = 50          # a day's VWAP needs at least this much quote volume to count
RECOMPUTE_DAYS = 7           # incremental: days recomputed from raw on every run
FFILL_DAYS = 7               # valuation uses the last price seen up to this many days before
PRICES = 'dune.paltalabs.result_scf_token_prices'
LP_TX = 'dune.paltalabs.result_scf_lp_tx'
LP_ADD = ('deposit', 'pool_deposit', 'provide_liquidity', 'add_liquidity', 'locking_deposit')
# Aquarius pool deposits before this date were parsed as [a, b, shares] instead of [shares, a, b]:
# amount_a holds LP shares and amount_b holds token a's amount; token b's amount was not kept.
AQUARIUS_DEPOSIT_FIXED_FROM = '2026-09-01'
MAX_LEG_RATIO = 10           # AMM legs further apart than this: a leg price is wrong, value 2 x the smaller
LP_REMOVE = ('withdraw', 'pool_withdraw', 'withdraw_liquidity', 'remove_liquidity', 'locking_withdraw', 'collect')
SWAP_ROLES = ('swapper', 'aggregator_user')
lit = activity_sql.lit


def asset_key(prefix):
    return (f"CASE WHEN {prefix}_asset_type = 'native' THEN 'native' "
            f"ELSE {prefix}_asset_code || ':' || {prefix}_asset_issuer END")


# ---- token discovery (probes run by export-tokens) -------------------------------------------

def layer_tokens():
    return f"""-- Every token in swap and LP rows of the fourteen activity layers.
WITH act AS (
{activity_sql.all_activity('role, token_a, token_b', "row_kind = 'activity' AND role IN ('lp', 'swapper', 'aggregator_user')")}
)
SELECT token, COUNT(*) AS rows_ FROM (SELECT token_a AS token FROM act UNION ALL SELECT token_b FROM act)
WHERE token IS NOT NULL GROUP BY 1"""


def sac_assets(contracts):
    return f"""-- SAC contract -> classic asset, from SAC balance and instance entries since 2024.
SELECT contract_id, arbitrary(asset_type) AS asset_type, arbitrary(asset_code) AS asset_code,
       arbitrary(asset_issuer) AS asset_issuer
FROM stellar.contract_data
WHERE closed_at_date >= DATE '2024-01-01' AND contract_id IN ({lit(contracts)}) AND asset_code <> ''
GROUP BY 1"""


def instances(contracts):
    return f"""-- Latest instance storage (METADATA: decimals, symbol) of the remaining token contracts.
SELECT contract_id, max_by(val_decoded, closed_at) AS instance
FROM stellar.contract_data
WHERE closed_at_date >= DATE '2024-01-01' AND contract_id IN ({lit(contracts)})
  AND contract_key_type = 'ScValTypeScvLedgerKeyContractInstance'
GROUP BY 1"""


def sdex_assets(days=30):
    return f"""-- Classic assets traded on the SDEX recently: candidates for offline SAC derivation.
SELECT DISTINCT asset FROM (
  SELECT {asset_key('selling')} AS asset FROM stellar.history_trades
  WHERE closed_at_date >= CURRENT_DATE - INTERVAL '{days}' DAY
  UNION ALL
  SELECT {asset_key('buying')} FROM stellar.history_trades
  WHERE closed_at_date >= CURRENT_DATE - INTERVAL '{days}' DAY
)"""


def tokens():
    return list(csv.DictReader(open(TOKENS_CSV)))


def token_values():
    rows = []
    for t in tokens():
        asset = f"'{t['asset']}'" if t['asset'] else 'NULL'
        symbol = (t['symbol'] or '').replace("'", "''")
        decimals = t['decimals'] or '7'
        rows.append(f"('{t['token']}', '{t['kind']}', {asset}, '{symbol}', {decimals})")
    return 'SELECT * FROM (VALUES\n  ' + ',\n  '.join(rows) + '\n) AS t(token, kind, asset, symbol, decimals)'


def classic_assets():
    return sorted({t['asset'] for t in tokens() if t['asset']} | {'native', USDC})


# ---- daily prices ------------------------------------------------------------------------------

def prices(incremental=True):
    """Observed daily prices only (no forward fill), one row per (day, token). Incremental: the
    previous snapshot up to RECOMPUTE_DAYS ago plus those days recomputed from the raw tables."""
    since = (f"CURRENT_DATE - INTERVAL '{RECOMPUTE_DAYS}' DAY" if incremental else f"DATE '{START}'")
    swaps_where = (f"row_kind = 'activity' AND role IN ({lit(SWAP_ROLES)}) AND amount_a <> 0 AND amount_b <> 0 "
                   f"AND token_a IS NOT NULL AND token_b IS NOT NULL "
                   f"AND CAST(closed_at AT TIME ZONE 'UTC' AS DATE) >= {since} "
                   f"AND CAST(closed_at AT TIME ZONE 'UTC' AS DATE) < CURRENT_DATE")
    prev = (f"SELECT day, token, asset, symbol, decimals, price_usd, price_source, volume_usd, refreshed_at\n"
            f"FROM {PRICES} WHERE day < {since}\nUNION ALL\n") if incremental else ''
    return f"""-- Generated by scripts/prices_sql.py. Daily USD price per token, observed days only.
-- SDEX VWAP vs Circle USDC, else vs XLM x XLM/USDC; else implied by Soroban swaps against an SDEX-priced token.
WITH tokens AS (
{token_values()}
), trades AS (
  SELECT closed_at_date AS day, {asset_key('selling')} AS sell, {asset_key('buying')} AS buy,
         CAST(selling_amount AS DOUBLE) AS sell_amount, CAST(buying_amount AS DOUBLE) AS buy_amount
  FROM stellar.history_trades
  WHERE closed_at_date >= {since} AND closed_at_date < CURRENT_DATE
    AND selling_amount > 0 AND buying_amount > 0
), legs AS (
  SELECT day, sell AS asset, buy AS quote, sell_amount AS asset_amount, buy_amount AS quote_amount FROM trades
  UNION ALL
  SELECT day, buy, sell, buy_amount, sell_amount FROM trades
), quoted AS (
  SELECT day, asset,
         SUM(quote_amount) FILTER (WHERE quote = '{USDC}') AS usdc_volume,
         SUM(quote_amount) FILTER (WHERE quote = '{USDC}') / SUM(asset_amount) FILTER (WHERE quote = '{USDC}') AS usdc_vwap,
         SUM(quote_amount) FILTER (WHERE quote = 'native') AS xlm_volume,
         SUM(quote_amount) FILTER (WHERE quote = 'native') / SUM(asset_amount) FILTER (WHERE quote = 'native') AS xlm_vwap
  FROM legs
  WHERE quote IN ('native', '{USDC}') AND asset IN ({lit(classic_assets())})
  GROUP BY 1, 2
), xlm AS (
  SELECT day, usdc_vwap AS xlm_usd FROM quoted WHERE asset = 'native' AND usdc_volume >= {MIN_USD_VOLUME}
), sdex AS (
  SELECT q.day, q.asset,
         CASE WHEN q.asset = '{USDC}' THEN 1.0
              WHEN q.asset = 'native' THEN x.xlm_usd
              WHEN q.usdc_volume >= {MIN_USD_VOLUME} THEN q.usdc_vwap
              WHEN q.xlm_volume * x.xlm_usd >= {MIN_USD_VOLUME} THEN q.xlm_vwap * x.xlm_usd END AS price_usd,
         CASE WHEN q.asset IN ('{USDC}', 'native') THEN 'sdex_anchor'
              WHEN q.usdc_volume >= {MIN_USD_VOLUME} THEN 'sdex_usdc'
              WHEN q.xlm_volume * x.xlm_usd >= {MIN_USD_VOLUME} THEN 'sdex_xlm' END AS price_source,
         COALESCE(q.usdc_volume, 0) + COALESCE(q.xlm_volume * x.xlm_usd, 0) AS volume_usd
  FROM quoted q LEFT JOIN xlm x ON x.day = q.day
), sdex_token AS (
  SELECT s.day, t.token, s.price_usd, s.price_source, s.volume_usd
  FROM sdex s JOIN tokens t ON t.asset = s.asset
  WHERE s.price_usd IS NOT NULL
), swaps AS (
  SELECT CAST(closed_at AT TIME ZONE 'UTC' AS DATE) AS day, token_a, ABS(amount_a) AS amount_a, token_b, ABS(amount_b) AS amount_b
  FROM (
{activity_sql.all_activity('closed_at, role, token_a, amount_a, token_b, amount_b', swaps_where)}
  )
), sides AS (
  SELECT day, token_a AS token, amount_a AS amount, token_b AS other, amount_b AS other_amount FROM swaps
  UNION ALL
  SELECT day, token_b, amount_b, token_a, amount_a FROM swaps
), implied AS (
  SELECT s.day, s.token,
         SUM(CAST(s.other_amount AS DOUBLE) * power(10, 7 - ot.decimals) * p.price_usd) AS volume_usd,
         SUM(CAST(s.other_amount AS DOUBLE) * power(10, 7 - ot.decimals) * p.price_usd)
           / SUM(CAST(s.amount AS DOUBLE) * power(10, 7 - tt.decimals)) AS price_usd
  FROM sides s
  JOIN sdex_token p ON p.token = s.other AND p.day = s.day
  JOIN tokens ot ON ot.token = s.other
  JOIN tokens tt ON tt.token = s.token
  WHERE NOT EXISTS (SELECT 1 FROM sdex_token x WHERE x.token = s.token AND x.day = s.day)
  GROUP BY 1, 2
  HAVING SUM(CAST(s.other_amount AS DOUBLE) * power(10, 7 - ot.decimals) * p.price_usd) >= {MIN_USD_VOLUME}
), observed AS (
  SELECT day, token, price_usd, price_source, volume_usd FROM sdex_token
  UNION ALL
  SELECT day, token, price_usd, 'soroban_swaps', volume_usd FROM implied
)
{prev}SELECT o.day, o.token, t.asset, t.symbol, t.decimals, o.price_usd, o.price_source, o.volume_usd, CURRENT_TIMESTAMP AS refreshed_at
FROM observed o JOIN tokens t ON t.token = o.token
"""


# ---- LP metrics --------------------------------------------------------------------------------

def lp_tx():
    """One row per LP action of the AMMs (role lp; Blend has no lp role), valued in USD with the
    last price seen up to FFILL_DAYS before the action. Amounts corrected by token decimals.
    Constant-product and stable pools take both legs at similar value, so: legacy Aquarius deposits
    count 2 x leg a; legs more than MAX_LEG_RATIO apart (an illiquid token with a bad price) count
    2 x the smaller; one unpriced leg counts 2 x the priced one. SushiSwap (CLMM, single-sided
    positions are legitimate) always adds the priced legs."""
    direction = (f"CASE WHEN action IN ({lit(LP_ADD)}) THEN 'add' WHEN action IN ({lit(LP_REMOVE)}) THEN 'remove' "
                 "ELSE 'other' END")
    return f"""-- Generated by scripts/prices_sql.py. LP actions valued in USD (Deliverable 3, value per transaction).
WITH tokens AS (
{token_values()}
), raw AS (
  SELECT *, protocol = 'aquarius' AND action = 'pool_deposit'
            AND closed_at < TIMESTAMP '{AQUARIUS_DEPOSIT_FIXED_FROM} 00:00:00 UTC' AS legacy_layout
  FROM (
{activity_sql.all_activity('protocol, contract_id, closed_at, tx_hash, user_address, action, pool, token_a, amount_a, token_b, amount_b', "row_kind = 'activity' AND role = 'lp'")}
  )
), lp AS (
  SELECT protocol, contract_id, closed_at, tx_hash, user_address, action, pool, token_a, token_b, legacy_layout,
         CASE WHEN legacy_layout THEN amount_b ELSE amount_a END AS amount_a,
         CASE WHEN legacy_layout THEN NULL ELSE amount_b END AS amount_b,
         ROW_NUMBER() OVER (ORDER BY closed_at, tx_hash, user_address, action, pool, token_a, amount_a) AS lp_row
  FROM raw
), legs AS (
  SELECT lp_row, 'a' AS leg, token_a AS token, amount_a AS amount, CAST(closed_at AT TIME ZONE 'UTC' AS DATE) AS day FROM lp
  UNION ALL
  SELECT lp_row, 'b', token_b, amount_b, CAST(closed_at AT TIME ZONE 'UTC' AS DATE) FROM lp
), valued AS (
  SELECT l.lp_row, l.leg,
         ABS(CAST(l.amount AS DOUBLE)) * power(10, 7 - COALESCE(t.decimals, 7)) AS token_amount,
         max_by(p.price_usd, p.day) AS price_usd, max_by(p.price_source, p.day) AS price_source
  FROM legs l
  LEFT JOIN tokens t ON t.token = l.token
  LEFT JOIN {PRICES} p ON p.token = l.token AND p.day <= l.day AND p.day >= l.day - INTERVAL '{FFILL_DAYS}' DAY
  WHERE l.token IS NOT NULL AND l.amount IS NOT NULL
  GROUP BY l.lp_row, l.leg, l.amount, t.decimals
), pivot AS (
  SELECT lp_row,
         MAX(token_amount) FILTER (WHERE leg = 'a') AS token_amount_a, MAX(price_usd) FILTER (WHERE leg = 'a') AS price_a,
         MAX(token_amount) FILTER (WHERE leg = 'b') AS token_amount_b, MAX(price_usd) FILTER (WHERE leg = 'b') AS price_b,
         array_join(array_distinct(array_agg(price_source) FILTER (WHERE price_source IS NOT NULL)), ',') AS price_sources
  FROM valued GROUP BY 1
)
SELECT lp.protocol, lp.contract_id, lp.pool, lp.closed_at, CAST(lp.closed_at AT TIME ZONE 'UTC' AS DATE) AS day,
       lp.tx_hash, lp.user_address, lp.action, {direction} AS direction,
       lp.token_a, v.token_amount_a, v.price_a, v.token_amount_a * v.price_a AS usd_a,
       lp.token_b, v.token_amount_b, v.price_b, v.token_amount_b * v.price_b AS usd_b,
       CASE WHEN lp.legacy_layout THEN 2 * v.token_amount_a * v.price_a
            WHEN lp.protocol = 'sushiswap' THEN COALESCE(v.token_amount_a * v.price_a, 0) + COALESCE(v.token_amount_b * v.price_b, 0)
            WHEN v.token_amount_a * v.price_a > 0 AND v.token_amount_b * v.price_b > 0
             AND GREATEST(v.token_amount_a * v.price_a, v.token_amount_b * v.price_b)
               > {MAX_LEG_RATIO} * LEAST(v.token_amount_a * v.price_a, v.token_amount_b * v.price_b)
              THEN 2 * LEAST(v.token_amount_a * v.price_a, v.token_amount_b * v.price_b)
            WHEN v.token_amount_a > 0 AND v.token_amount_b > 0 AND (v.price_a IS NULL) <> (v.price_b IS NULL)
              THEN 2 * COALESCE(v.token_amount_a * v.price_a, v.token_amount_b * v.price_b)
            ELSE COALESCE(v.token_amount_a * v.price_a, 0) + COALESCE(v.token_amount_b * v.price_b, 0) END AS usd_total,
       CASE WHEN lp.legacy_layout THEN 'legacy_2x_a'
            WHEN lp.protocol = 'sushiswap' THEN 'sum'
            WHEN v.token_amount_a * v.price_a > 0 AND v.token_amount_b * v.price_b > 0
             AND GREATEST(v.token_amount_a * v.price_a, v.token_amount_b * v.price_b)
               > {MAX_LEG_RATIO} * LEAST(v.token_amount_a * v.price_a, v.token_amount_b * v.price_b) THEN 'capped_2x_min'
            WHEN v.token_amount_a > 0 AND v.token_amount_b > 0 AND (v.price_a IS NULL) <> (v.price_b IS NULL) THEN 'one_leg_2x'
            ELSE 'sum' END AS usd_method,
       CASE WHEN lp.token_a IS NULL AND lp.token_b IS NULL THEN 'no_tokens'
            WHEN (lp.token_a IS NULL OR v.price_a IS NOT NULL OR COALESCE(v.token_amount_a, 0) = 0)
             AND (lp.token_b IS NULL OR v.price_b IS NOT NULL OR COALESCE(v.token_amount_b, 0) = 0) THEN 'priced'
            WHEN v.price_a IS NOT NULL OR v.price_b IS NOT NULL THEN 'partial'
            ELSE 'unpriced' END AS valuation,
       v.price_sources, CURRENT_TIMESTAMP AS refreshed_at
FROM lp LEFT JOIN pivot v ON v.lp_row = lp.lp_row
"""


def lp_periods():
    return f"""-- Active LPs and USD added/removed per calendar week and month (UTC), per protocol and all AMMs.
WITH tx AS (SELECT * FROM {LP_TX} WHERE day < CURRENT_DATE),
grains AS (
  SELECT 'week' AS grain, CAST(date_trunc('week', day) AS DATE) AS period_start, * FROM tx
  UNION ALL
  SELECT 'month', CAST(date_trunc('month', day) AS DATE), * FROM tx
), both_ AS (
  SELECT grain, period_start, protocol, user_address, direction, usd_total, valuation FROM grains
  UNION ALL
  SELECT grain, period_start, 'all AMMs', user_address, direction, usd_total, valuation FROM grains
)
SELECT grain, period_start, protocol,
       COUNT(DISTINCT user_address) AS active_lps,
       COUNT(DISTINCT CASE WHEN user_address LIKE 'G%' THEN user_address END) AS g_lps,
       COUNT(DISTINCT CASE WHEN user_address LIKE 'C%' THEN user_address END) AS c_lps,
       COUNT(*) AS lp_actions,
       SUM(usd_total) FILTER (WHERE direction = 'add') AS usd_added,
       SUM(usd_total) FILTER (WHERE direction = 'remove') AS usd_removed,
       COALESCE(SUM(usd_total) FILTER (WHERE direction = 'add'), 0) - COALESCE(SUM(usd_total) FILTER (WHERE direction = 'remove'), 0) AS usd_net,
       CAST(COUNT_IF(valuation = 'priced') AS DOUBLE) / COUNT(*) AS priced_action_share,
       date_add(grain, 1, period_start) <= CURRENT_DATE AS is_complete
FROM both_ GROUP BY 1, 2, 3
ORDER BY 1, 2, 3
"""


def lp_top():
    return f"""-- Top 100 LP addresses by USD added, all AMMs, all time and last 90 / 30 complete days.
WITH windows AS (
  SELECT * FROM (VALUES ('all_time', DATE '{START}'),
    ('last_90d', CAST(CURRENT_DATE - INTERVAL '90' DAY AS DATE)),
    ('last_30d', CAST(CURRENT_DATE - INTERVAL '30' DAY AS DATE))) AS t(window_name, window_from)
), per_lp AS (
  SELECT w.window_name, w.window_from, x.user_address,
         SUM(x.usd_total) FILTER (WHERE x.direction = 'add') AS usd_added,
         SUM(x.usd_total) FILTER (WHERE x.direction = 'remove') AS usd_removed,
         COUNT(*) AS lp_actions,
         array_join(array_sort(array_distinct(array_agg(x.protocol))), ', ') AS protocols,
         COUNT(DISTINCT x.pool) AS pools,
         MIN(x.day) AS first_day, MAX(x.day) AS last_day
  FROM {LP_TX} x CROSS JOIN windows w
  WHERE x.day >= w.window_from AND x.day < CURRENT_DATE
  GROUP BY 1, 2, 3
), ranked AS (
  SELECT *, COALESCE(usd_added, 0) - COALESCE(usd_removed, 0) AS usd_net,
         ROW_NUMBER() OVER (PARTITION BY window_name ORDER BY usd_added DESC NULLS LAST, user_address) AS rank_
  FROM per_lp
)
SELECT * FROM ranked WHERE rank_ <= 100 ORDER BY window_name, rank_
"""


def price_coverage():
    return f"""-- Share of LP USD and actions that could be valued, per protocol, last 90 complete days and all time.
SELECT CASE WHEN day >= CURRENT_DATE - INTERVAL '90' DAY THEN 'last_90d' ELSE 'older' END AS window_name, protocol,
       COUNT(*) AS lp_actions, COUNT_IF(valuation = 'priced') AS priced, COUNT_IF(valuation = 'partial') AS partial,
       COUNT_IF(valuation = 'unpriced') AS unpriced, COUNT_IF(valuation = 'no_tokens') AS no_tokens,
       CAST(COUNT_IF(valuation = 'priced') AS DOUBLE) / NULLIF(COUNT_IF(valuation <> 'no_tokens'), 0) AS priced_share
FROM {LP_TX} WHERE day < CURRENT_DATE
GROUP BY 1, 2 ORDER BY 1, 2
"""


def chart_lp_periods(grain):
    return f"""-- Chart source: active LPs and USD added/removed per complete calendar {grain}.
SELECT period_start, protocol, active_lps, g_lps, lp_actions, usd_added, usd_removed, usd_net, priced_action_share
FROM dune.paltalabs.result_scf_lp_periods
WHERE grain = '{grain}' AND is_complete
ORDER BY period_start, protocol
"""


def chart_lp_top():
    return """-- Chart source: top 100 LPs by USD added, last 90 days.
SELECT rank_, user_address, usd_added, usd_removed, usd_net, lp_actions, protocols, pools, first_day, last_day
FROM dune.paltalabs.result_scf_lp_top WHERE window_name = 'last_90d' ORDER BY rank_
"""


def chart_lp_tx():
    return """-- Chart source: largest LP actions of the last 30 days, valued in USD.
SELECT closed_at, protocol, action, direction, user_address, pool, token_a, token_amount_a, usd_a,
       token_b, token_amount_b, usd_b, usd_total, valuation, tx_hash
FROM dune.paltalabs.result_scf_lp_tx
WHERE day >= CURRENT_DATE - INTERVAL '30' DAY AND day < CURRENT_DATE
ORDER BY usd_total DESC LIMIT 200
"""


def chart_price_coverage():
    return """-- Chart source: LP valuation coverage per protocol.
SELECT * FROM dune.paltalabs.result_scf_lp_price_coverage ORDER BY window_name, protocol
"""


METRICS = {'token_prices': prices, 'lp_tx': lp_tx, 'lp_periods': lp_periods, 'lp_top': lp_top,
           'lp_price_coverage': price_coverage}
CHARTS = {'chart_lp_weekly': lambda: chart_lp_periods('week'),
          'chart_lp_monthly': lambda: chart_lp_periods('month'),
          'chart_lp_top': chart_lp_top,
          'chart_lp_tx': chart_lp_tx,
          'chart_price_coverage': chart_price_coverage}
