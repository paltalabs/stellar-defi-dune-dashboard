"""SQL de la Fase 1: capas de actividad normalizadas según CLAUDE.md y docs/modelo-de-datos.md.

Por protocolo: result_scf_<p>_activity_archive (historia completa, cron mensual) y
result_scf_<p>_activity (lo posterior al archive, cron diario). Las listas de contratos van
literales en el SQL: un IN (subquery) no poda y costó 3,5 veces más en la misma consulta
(2026-09-22, 0,198 contra 0,057 cr). Las listas salen de data/contracts.csv, que se regenera
desde result_scf_contracts (el registro que se descubre solo); el check unregistered_contracts
de users_validation avisa cuando el registro tiene contratos que el SQL todavía no incluye.
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROTOCOLS = ('blend', 'aquarius', 'soroswap', 'phoenix', 'fxdao', 'etherfuse', 'sushiswap')
HISTORY_START = '2024-02-01'
# SushiSwap's factory first appears on 2026-03-02: its archive starts there instead of scanning 2024.
SUSHI_START = '2026-03-01'
HISTORY_STARTS = {'sushiswap': SUSHI_START}
LIVE_PRUNE_DAYS = 75
REGISTRY_CSV = ROOT / 'data' / 'contracts.csv'

BLEND_FACTORIES = ['CCZD6ESMOGMPWH2KRO4O7RGTAPGTUPFWFQBELQSS7ZUK63V3TZWETGAG',
                   'CDSYOAVXFY7SM5S64IZPPPYB4GVGGLMQVFREPSQQEZVIWXX5R23G4QSU']
BLEND_BACKSTOPS = ['CAO3AGAMZVRMHITL36EJ2VZQWKYRPWMQAPDQD5YEOF3GIF7T44U4JAL3',
                   'CAQQR5SWBXKIGZKPBZDH3KM5GQ5GUTPKB7JAFCINLZBC5WXPJKRG3IM7']
SOROSWAP_FACTORY = 'CA4HEQTL2WPEUYKYKCDOHCDNIV4QHNJ7EL4J4NQ6VADP7SYHVRYZ7AW2'
SOROSWAP_ROUTER = 'CAG5LRYQ5JVEUI5TEID72EYOVX44TTUJT5BQR2J6J77FH65PCCFAJDDH'
SOROSWAP_AGGREGATORS = ['CCHCH6XVKTMKTYCTKKTKNE2TFP5CMORNY77TA6XSRAD2XM7I2SJBUH3H',
                        'CC2CMNKAFI3KKL6ROMIYJKKX2WE2MV5QAF7DZDWC57ENHV6DQTHT3W64',
                        'CBFAORZNK4JSCJYT3ZLWFQ5QEI4IHOIYY6XCYT3E47AK6ZMZFKFP6ZKA',
                        'CACITNMTUSTZYKKH4TJVXNH4C4XHGYFVAPQ2EE3D5LTL3HIA32QY4Q6X',
                        'CDPJAUHPMJBOPUHBWBHO7NKSTR6J5EXZZ2OX4QGSXIHEJLBDY2JABM3L',
                        'CCXNPJPNWT4WDWKTUNRPKNUHFYKZW6XBJAOHKAW2KLY5PBBGX6ZCFUJC',
                        'CAWTTRKV7N4MBFSFU7BBZVMOAFEVYMZEDUS4ULBGUQH5YMFKPOFUWPF3',
                        'CCWLXIBMONXFCXELPFHXPT4VSXKUSSP67DXNXWQ4YIPFGNBHQWEX4W4P',
                        'CDEM2W2D2SC7VU3NOCIKHZWCUNCAUWI5GUGHSWBJNBENRHSVIMUT6EM2',
                        'CAYP3UWLJM7ZPTUKL6R6BFGTRWLZ46LRKOXTERI2K6BIJAWGYY62TXTO']
PHOENIX_FACTORY = 'CB4SVAWJA6TSRNOJZ7W2AWFW46D5VR4ZMFZKDIKXEINZCZEGZCJZCKMI'
AQUARIUS_ROUTERS = ['CBQDHNBFBZYE4MKPWBSJOPIYLW4SFSXAXUTSXJN76GNKYVYPCKWC6QUK',
                    'CA7RQDMMV6E53P5EDZA5GPWBZ33AMW2ZNO42XLI2RGRIAP4QXIARUOJQ',
                    'CB4YHF4ESRJ4XZRXISLXSUZTYY6YPBPZ73MZWSTUWY46DKYW7IGLHGF7']
FXDAO_VAULTS = 'CCUN4RXU5VNDHSF4S4RKV4ZJYMX2YWKOH6L4AKEKVNVDQ7HY5QIAO4UB'
FXDAO_LOCKING = 'CDCART6WRSM2K4CKOAOB5YKUVBSJ6KLOVS7ZEJHA4OAQ2FXX7JOHLXIP'
ETHERFUSE_ISSUER = 'GCRYUGD5NVARGXT56XEZI5CIFCQETYHAPQQTHO2O3IQZTHDH4LATMYWC'
COMET_BLND_USDC = 'CAS3FL6TLZKDGGSISDBWGGPXT3NRR4DYTZD7YOD3HMYO6LTJUVGRVEAM'
SUSHI_FACTORY = 'CD3KRKGDRVWPXVB3VXLUMQKMX6XZ6Q2H334IVZD4XXNAMKSRVQL5GLYF'
# Contracts that route trades for end users. A trade whose user is one of these is counted for
# the contract, not for the person behind it (docs/modelo-de-datos.md, integridad).
AGGREGATORS = SOROSWAP_AGGREGATORS + [SOROSWAP_ROUTER] + AQUARIUS_ROUTERS

EVENT_FILTERS = """AND he.type_string = 'ContractEventTypeContract'
    AND he.successful = TRUE AND he.in_successful_contract_call = TRUE"""


def lit(values):
    return ', '.join(f"'{v}'" for v in values)


def registry(incremental=True):
    """result_scf_contracts: pools and pairs discovered from factory storage and router events.
    The full scan since 2024 cost 78,9 cr (2026-09-22); the weekly refresh reads its own previous
    snapshot and only scans the last 14 days."""
    since = "CURRENT_DATE - INTERVAL '14' DAY" if incremental else f"DATE '{HISTORY_START}'"
    body = registry_scan(since)
    if not incremental:
        return body
    return f"""-- Contract registry, incremental: previous snapshot of this matview + contracts seen in the last 14 days.
WITH prev AS (SELECT protocol, kind, contract_id, token_a, token_b, first_seen FROM dune.paltalabs.result_scf_contracts),
fresh AS (
{body}
)
SELECT protocol, kind, contract_id, MAX(token_a) AS token_a, MAX(token_b) AS token_b, MIN(first_seen) AS first_seen
FROM (SELECT * FROM prev UNION ALL SELECT * FROM fresh)
GROUP BY 1, 2, 3
"""


def registry_scan(since):
    return f"""-- Contract registry discovered on chain. Source of data/contracts.csv, which feeds the literal
-- contract lists of every activity query (a literal list prunes; an IN (subquery) does not).
SELECT 'blend' AS protocol, 'pool' AS kind, json_extract_scalar(key_decoded, '$.vec[1].address') AS contract_id,
       CAST(NULL AS VARCHAR) AS token_a, CAST(NULL AS VARCHAR) AS token_b, MIN(closed_at) AS first_seen
FROM stellar.contract_data
WHERE contract_id IN ({lit(BLEND_FACTORIES)}) AND closed_at_date >= {since}
  AND contract_key_type = 'ScValTypeScvVec' AND json_extract_scalar(key_decoded, '$.vec[0].symbol') = 'Contracts'
  AND json_extract_scalar(key_decoded, '$.vec[1].address') IS NOT NULL
GROUP BY 1, 2, 3
UNION ALL
SELECT 'soroswap', 'pair', json_extract_scalar(val_decoded, '$.address'), NULL, NULL, MIN(closed_at)
FROM stellar.contract_data
WHERE contract_id = '{SOROSWAP_FACTORY}' AND closed_at_date >= {since}
  AND contract_key_type = 'ScValTypeScvVec' AND json_extract_scalar(key_decoded, '$.vec[0].symbol') = 'PairAddressesNIndexed'
  AND json_extract_scalar(val_decoded, '$.address') IS NOT NULL
GROUP BY 1, 2, 3
UNION ALL
SELECT 'phoenix', 'pool', json_extract_scalar(val_decoded, '$.address'),
       MAX(regexp_extract(key_decoded, '"token_a"\\}},"val":\\{{"address":"(C[A-Z2-7]{{55}})"', 1)),
       MAX(regexp_extract(key_decoded, '"token_b"\\}},"val":\\{{"address":"(C[A-Z2-7]{{55}})"', 1)), MIN(closed_at)
FROM stellar.contract_data
WHERE contract_id = '{PHOENIX_FACTORY}' AND closed_at_date >= {since}
  AND contract_key_type = 'ScValTypeScvMap' AND json_extract_scalar(val_decoded, '$.address') IS NOT NULL
GROUP BY 1, 2, 3
UNION ALL
SELECT 'aquarius', 'pool', regexp_extract(he.data_decoded, '"address":"(C[A-Z2-7]{{55}})"', 1), NULL, NULL, MIN(he.closed_at)
FROM stellar.history_contract_events he
WHERE he.contract_id IN ({lit(AQUARIUS_ROUTERS)}) AND he.closed_at_date >= {since}
  {EVENT_FILTERS}
  AND he.topics_decoded LIKE '[{{"symbol":"add_pool"}}%'
  AND regexp_extract(he.data_decoded, '"address":"(C[A-Z2-7]{{55}})"', 1) IS NOT NULL
GROUP BY 1, 2, 3
UNION ALL
-- SushiSwap: two GetPool entries per pool, one per token order. token_a is the pool's token0, the
-- token with the lower address bytes (58 of 58 pools against their params.token0, 2026-09-22; string
-- order fails on 3). Always scanned from the factory's start: 0,08 cr, so no incremental window.
SELECT 'sushiswap', 'pool', json_extract_scalar(val_decoded, '$.address'),
       MAX(CASE WHEN from_base32(json_extract_scalar(key_decoded, '$.vec[1].address')) < from_base32(json_extract_scalar(key_decoded, '$.vec[2].address'))
                THEN json_extract_scalar(key_decoded, '$.vec[1].address') ELSE json_extract_scalar(key_decoded, '$.vec[2].address') END),
       MAX(CASE WHEN from_base32(json_extract_scalar(key_decoded, '$.vec[1].address')) < from_base32(json_extract_scalar(key_decoded, '$.vec[2].address'))
                THEN json_extract_scalar(key_decoded, '$.vec[2].address') ELSE json_extract_scalar(key_decoded, '$.vec[1].address') END),
       MIN(closed_at)
FROM stellar.contract_data
WHERE contract_id = '{SUSHI_FACTORY}' AND closed_at_date >= DATE '{SUSHI_START}'
  AND contract_key_type = 'ScValTypeScvVec' AND json_extract_scalar(key_decoded, '$.vec[0].symbol') = 'GetPool'
  AND json_extract_scalar(val_decoded, '$.address') IS NOT NULL
GROUP BY 1, 2, 3
"""


def contracts(protocol, kind=None):
    rows = list(csv.DictReader(open(REGISTRY_CSV)))
    return [r for r in rows if r['protocol'] == protocol and (kind is None or r['kind'] == kind)]


# ---------------------------------------------------------------------------------------------
# Sources. Each returns the normalized columns of docs/modelo-de-datos.md; win(col) is the date
# predicate on a partition column.

def blend(win):
    pools = [r['contract_id'] for r in contracts('blend', 'pool')]
    return f"""WITH ev AS (
  SELECT DISTINCT
    CASE WHEN he.contract_id IN ({lit(BLEND_BACKSTOPS)}) THEN 'backstop' ELSE 'pool' END AS kind,
    he.contract_id, he.closed_at, lower(to_hex(he.transaction_hash)) AS tx_hash, he.topics_decoded, he.data_decoded
  FROM stellar.history_contract_events he
  WHERE {win('he.closed_at_date')}
    AND he.contract_id IN ({lit(pools + BLEND_BACKSTOPS)})
    {EVENT_FILTERS}
),
parsed AS (
  SELECT kind, contract_id, closed_at, tx_hash,
    json_extract_scalar(topics_decoded, '$[0].symbol')  AS action,
    json_extract_scalar(topics_decoded, '$[1].address') AS t1_addr,
    json_extract_scalar(topics_decoded, '$[2].address') AS t2_addr,
    json_extract_scalar(data_decoded, '$.vec[0].address') AS d0_addr,
    COALESCE(
      TRY(CAST(COALESCE(json_extract_scalar(data_decoded, '$.vec[0].i128'), json_extract_scalar(data_decoded, '$.i128')) AS DECIMAL(38,0))),
      TRY(CAST(json_extract_scalar(data_decoded, '$.vec[0].i128.hi') AS DECIMAL(38,0)) * DECIMAL '18446744073709551616'
          + CAST(json_extract_scalar(data_decoded, '$.vec[0].i128.lo') AS DECIMAL(38,0)))
    ) AS d0_i128
  FROM ev
)
SELECT 'blend' AS protocol, contract_id, closed_at, tx_hash,
  CASE
    WHEN kind = 'pool' AND action = 'fill_auction' THEN d0_addr
    WHEN action = 'claim' THEN t1_addr
    ELSE t2_addr
  END AS user_address,
  CASE WHEN kind = 'backstop' THEN 'backstop_' || action ELSE action END AS action,
  CASE
    WHEN kind = 'pool' AND action IN ('supply', 'withdraw', 'supply_collateral', 'withdraw_collateral') THEN 'lender'
    WHEN kind = 'pool' AND action IN ('borrow', 'repay', 'flash_loan') THEN 'borrower'
    WHEN kind = 'pool' AND action = 'fill_auction' THEN 'liquidator'
    WHEN action = 'claim' THEN 'claimer'
    ELSE 'backstop_provider'
  END AS role,
  CASE WHEN kind = 'backstop' THEN t1_addr ELSE contract_id END AS pool,
  CASE
    WHEN kind = 'pool' AND action IN ('supply', 'withdraw', 'supply_collateral', 'withdraw_collateral', 'borrow', 'repay', 'flash_loan') THEN t1_addr
    WHEN kind = 'backstop' AND action IN ('deposit', 'withdraw', 'donate') THEN '{COMET_BLND_USDC}'
  END AS token_a,
  CASE
    WHEN (kind = 'pool' AND action IN ('supply', 'withdraw', 'supply_collateral', 'withdraw_collateral', 'borrow', 'repay', 'flash_loan'))
      OR (kind = 'backstop' AND action IN ('deposit', 'withdraw', 'donate'))
    THEN CAST(d0_i128 * DECIMAL '0.0000001' AS DECIMAL(38,7))
  END AS amount_a,
  CAST(NULL AS VARCHAR) AS token_b, CAST(NULL AS DECIMAL(38,7)) AS amount_b
FROM parsed
WHERE (kind = 'pool' AND action IN ('supply', 'withdraw', 'supply_collateral', 'withdraw_collateral', 'borrow', 'repay', 'flash_loan', 'fill_auction', 'claim'))
   OR (kind = 'backstop' AND action IN ('deposit', 'withdraw', 'queue_withdrawal', 'dequeue_withdrawal', 'donate', 'claim'))"""


def aquarius(win):
    """Router events plus pool events. In a 7-day sample (2026-09-21) 736 of 904 deposit_liquidity
    txs and 71.851 of 113.543 trade txs had no router event. Pool trade: topics [trade, token_in,
    token_out, caller], the caller is the router itself when routed (dropped here, the router event
    has the user). deposit/withdraw_liquidity carry no user: the invoking operation's source account
    is used, looked up only among operations that call a pool directly (a literal contract list, so it
    prunes; a deposit routed through another contract has no signer here and is not counted). Pool
    amount positions for deposit ([a, b, shares]) and withdraw ([shares, a, b]) come from one sample
    and are not verified against Aquarius docs. Measured 2026-09-22 on one day: 1,78 cr; deduplicating
    on extracted fields instead of the raw event measured worse (2,98) and was reverted."""
    pools = [r['contract_id'] for r in contracts('aquarius', 'pool')]
    i128 = lambda path, col='data_decoded': f"TRY(CAST(COALESCE(json_extract_scalar({col}, '{path}.i128'), json_extract_scalar({col}, '{path}.u128')) AS DECIMAL(38,0)))"
    return f"""WITH ev AS (
  SELECT he.contract_id, he.closed_at, lower(to_hex(he.transaction_hash)) AS tx_hash, he.topics_decoded, he.data_decoded,
         MAX(he.transaction_id) AS transaction_id,
         he.contract_id IN ({lit(AQUARIUS_ROUTERS)}) AS is_router,
         json_extract_scalar(he.topics_decoded, '$[0].symbol') AS action
  FROM stellar.history_contract_events he
  WHERE {win('he.closed_at_date')}
    AND he.contract_id IN ({lit(AQUARIUS_ROUTERS + pools)})
    {EVENT_FILTERS}
    AND json_extract_scalar(he.topics_decoded, '$[0].symbol') IN ('swap', 'deposit', 'withdraw', 'claim',
        'trade', 'deposit_liquidity', 'withdraw_liquidity', 'claim_reward', 'position_update')
  GROUP BY 1, 2, 3, 4, 5, 7, 8
),
routed AS (SELECT DISTINCT tx_hash FROM ev WHERE is_router),
positioned AS (SELECT DISTINCT tx_hash FROM ev WHERE action = 'position_update'),
direct_lp AS (
  SELECT e.* FROM ev e
  WHERE NOT e.is_router AND e.action IN ('deposit_liquidity', 'withdraw_liquidity')
    AND e.tx_hash NOT IN (SELECT tx_hash FROM routed) AND e.tx_hash NOT IN (SELECT tx_hash FROM positioned)
),
signer AS (
  SELECT o.transaction_id, MIN(o.source_account) AS source_account
  FROM stellar.history_operations o
  WHERE {win('o.closed_at_date')} AND o.type_string = 'invoke_host_function'
    AND o.contract_id IN ({lit(pools)})
  GROUP BY 1
)
SELECT 'aquarius' AS protocol, contract_id, closed_at, tx_hash,
       json_extract_scalar(topics_decoded, '$[2].address') AS user_address, action,
       CASE action WHEN 'swap' THEN 'swapper' WHEN 'claim' THEN 'claimer' ELSE 'lp' END AS role,
       json_extract_scalar(data_decoded, '$.vec[0].address') AS pool,
       CASE WHEN action IN ('swap', 'claim') THEN json_extract_scalar(data_decoded, '$.vec[1].address')
            ELSE json_extract_scalar(topics_decoded, '$[1].vec[0].address') END AS token_a,
       CAST(CASE action WHEN 'swap' THEN {i128('$.vec[3]')} WHEN 'deposit' THEN {i128('$.vec[1].vec[0]')}
                        WHEN 'withdraw' THEN {i128('$.vec[2].vec[0]')} WHEN 'claim' THEN {i128('$.vec[2]')} END
            * DECIMAL '0.0000001' AS DECIMAL(38,7)) AS amount_a,
       CASE action WHEN 'swap' THEN json_extract_scalar(data_decoded, '$.vec[2].address')
                   WHEN 'claim' THEN NULL ELSE json_extract_scalar(topics_decoded, '$[1].vec[1].address') END AS token_b,
       CAST(CASE action WHEN 'swap' THEN {i128('$.vec[4]')} WHEN 'deposit' THEN {i128('$.vec[1].vec[1]')}
                        WHEN 'withdraw' THEN {i128('$.vec[2].vec[1]')} END
            * DECIMAL '0.0000001' AS DECIMAL(38,7)) AS amount_b
FROM ev WHERE is_router AND action IN ('swap', 'deposit', 'withdraw', 'claim')
UNION ALL
SELECT 'aquarius', contract_id, closed_at, tx_hash, json_extract_scalar(topics_decoded, '$[3].address'), 'pool_trade', 'swapper',
       contract_id, json_extract_scalar(topics_decoded, '$[1].address'), CAST({i128('$.vec[0]')} * DECIMAL '0.0000001' AS DECIMAL(38,7)),
       json_extract_scalar(topics_decoded, '$[2].address'), CAST({i128('$.vec[1]')} * DECIMAL '0.0000001' AS DECIMAL(38,7))
FROM ev WHERE NOT is_router AND action = 'trade'
  AND json_extract_scalar(topics_decoded, '$[3].address') NOT IN ({lit(AQUARIUS_ROUTERS)})
UNION ALL
SELECT 'aquarius', contract_id, closed_at, tx_hash, json_extract_scalar(topics_decoded, '$[2].address'), 'claim_reward', 'claimer',
       contract_id, json_extract_scalar(topics_decoded, '$[1].address'), CAST({i128('$.vec[0]')} * DECIMAL '0.0000001' AS DECIMAL(38,7)),
       NULL, NULL
FROM ev WHERE NOT is_router AND action = 'claim_reward' AND tx_hash NOT IN (SELECT tx_hash FROM routed)
UNION ALL
SELECT 'aquarius', contract_id, closed_at, tx_hash, json_extract_scalar(topics_decoded, '$[1].address'), 'position_update', 'lp',
       contract_id, NULL, NULL, NULL, NULL
FROM ev WHERE NOT is_router AND action = 'position_update'
UNION ALL
SELECT 'aquarius', d.contract_id, d.closed_at, d.tx_hash, s.source_account,
       CASE d.action WHEN 'deposit_liquidity' THEN 'pool_deposit' ELSE 'pool_withdraw' END, 'lp', d.contract_id,
       json_extract_scalar(d.topics_decoded, '$[1].address'),
       CAST(CASE d.action WHEN 'deposit_liquidity' THEN {i128('$.vec[0]', 'd.data_decoded')} ELSE {i128('$.vec[1]', 'd.data_decoded')} END
            * DECIMAL '0.0000001' AS DECIMAL(38,7)),
       json_extract_scalar(d.topics_decoded, '$[2].address'),
       CAST(CASE d.action WHEN 'deposit_liquidity' THEN {i128('$.vec[1]', 'd.data_decoded')} ELSE {i128('$.vec[2]', 'd.data_decoded')} END
            * DECIMAL '0.0000001' AS DECIMAL(38,7))
FROM direct_lp d JOIN signer s ON s.transaction_id = d.transaction_id"""


def soroswap(win):
    """One row per event (grain includes the event payload): pivoting per transaction merged
    several swaps of one tx and kept only one recipient.

    The aggregator also routes through the classic SDEX, which emits no Soroban event: successful
    txs with memo 'SoroswapAggregator-<apiUser>' and their path payments, same criterion as
    paltalabs/dune-dashboards (queries 8395684 and 8395746). The tx account is the user; the path
    payment recipient counts too when it differs, in a row without amounts so volume is not doubled.
    A Soroban tx holds a single operation, so no tx is in both sources. Classic amounts are already
    in token units; tokens are 'native' or 'CODE:ISSUER'. 30 days to 2026-09-22 (probe 8808241,
    4,9 cr): 27.534 path payments, 226 addresses, 138 of them absent from every other layer."""
    pairs = [r['contract_id'] for r in contracts('soroswap', 'pair')]
    kinds = f"""CASE WHEN he.contract_id = '{SOROSWAP_ROUTER}' THEN 'router'
         WHEN he.contract_id IN ({lit(SOROSWAP_AGGREGATORS)}) THEN 'aggregator' ELSE 'pair' END"""
    return f"""WITH ev AS (
  SELECT DISTINCT {kinds} AS kind,
    he.contract_id, he.closed_at, lower(to_hex(he.transaction_hash)) AS tx_hash,
    json_extract_scalar(he.topics_decoded, '$[1].symbol') AS action, he.data_decoded
  FROM stellar.history_contract_events he
  WHERE {win('he.closed_at_date')}
    AND he.contract_id IN ({lit([SOROSWAP_ROUTER] + SOROSWAP_AGGREGATORS + pairs)})
    {EVENT_FILTERS}
    AND he.topics_decoded LIKE '[{{"string":"Soroswap%'
),
kv AS (
  SELECT e.kind, e.contract_id, e.closed_at, e.tx_hash, e.action, xxhash64(to_utf8(e.data_decoded)) AS event_key,
         json_extract_scalar(elem, '$.key.symbol') AS k,
         json_extract_scalar(elem, '$.val.address') AS v_addr,
         COALESCE(
           TRY(CAST(json_extract_scalar(elem, '$.val.i128') AS DECIMAL(38,0))),
           TRY(CAST(json_extract_scalar(elem, '$.val.i128.hi') AS DECIMAL(38,0)) * DECIMAL '18446744073709551616'
               + CAST(json_extract_scalar(elem, '$.val.i128.lo') AS DECIMAL(38,0)))
         ) AS v_i128,
         json_extract_scalar(elem, '$.val.vec[0].address') AS v_first_addr,
         json_extract_scalar(elem, '$.val.vec[' || CAST(json_array_length(json_extract(elem, '$.val.vec')) - 1 AS VARCHAR) || '].address') AS v_last_addr,
         TRY(CAST(json_extract_scalar(elem, '$.val.vec[0].i128') AS DECIMAL(38,0))) AS v_first_i128,
         TRY(CAST(json_extract_scalar(elem, '$.val.vec[' || CAST(json_array_length(json_extract(elem, '$.val.vec')) - 1 AS VARCHAR) || '].i128') AS DECIMAL(38,0))) AS v_last_i128
  FROM ev e
  CROSS JOIN UNNEST(CAST(json_extract(e.data_decoded, '$.map') AS array(json))) AS t(elem)
),
pivoted AS (
  SELECT kind, contract_id, closed_at, tx_hash, action, event_key,
    MAX(CASE WHEN k = 'to' THEN v_addr END) AS to_addr,
    MAX(CASE WHEN k = 'pair' THEN v_addr END) AS pair,
    MAX(CASE WHEN k = 'token_a' THEN v_addr END) AS token_a,
    MAX(CASE WHEN k = 'token_b' THEN v_addr END) AS token_b,
    MAX(CASE WHEN k = 'token_in' THEN v_addr END) AS token_in,
    MAX(CASE WHEN k = 'token_out' THEN v_addr END) AS token_out,
    MAX(CASE WHEN k = 'amount_a' THEN v_i128 END) AS amount_a,
    MAX(CASE WHEN k = 'amount_b' THEN v_i128 END) AS amount_b,
    MAX(CASE WHEN k = 'amount_in' THEN v_i128 END) AS amount_in,
    MAX(CASE WHEN k = 'amount_out' THEN v_i128 END) AS amount_out,
    MAX(CASE WHEN k = 'path' THEN v_first_addr END) AS path_first,
    MAX(CASE WHEN k = 'path' THEN v_last_addr END) AS path_last,
    MAX(CASE WHEN k = 'amounts' THEN v_first_i128 END) AS amounts_first,
    MAX(CASE WHEN k = 'amounts' THEN v_last_i128 END) AS amounts_last,
    MAX(CASE WHEN k = 'amount_0_in' THEN v_i128 END) AS amount_0_in,
    MAX(CASE WHEN k = 'amount_1_in' THEN v_i128 END) AS amount_1_in,
    MAX(CASE WHEN k = 'amount_0_out' THEN v_i128 END) AS amount_0_out,
    MAX(CASE WHEN k = 'amount_1_out' THEN v_i128 END) AS amount_1_out,
    MAX(CASE WHEN k = 'amount_0' THEN v_i128 END) AS amount_0,
    MAX(CASE WHEN k = 'amount_1' THEN v_i128 END) AS amount_1
  FROM kv
  GROUP BY 1, 2, 3, 4, 5, 6
),
routed_txs AS (SELECT DISTINCT tx_hash FROM pivoted WHERE kind IN ('router', 'aggregator')),
normalized AS (
  SELECT contract_id, closed_at, tx_hash, to_addr AS user_address,
         CASE action WHEN 'add' THEN 'add_liquidity' WHEN 'remove' THEN 'remove_liquidity' ELSE action END AS action,
         CASE action WHEN 'swap' THEN 'swapper' ELSE 'lp' END AS role,
         pair AS pool,
         CASE action WHEN 'swap' THEN path_first ELSE token_a END AS token_a,
         CASE action WHEN 'swap' THEN amounts_first ELSE amount_a END AS amount_a_raw,
         CASE action WHEN 'swap' THEN path_last ELSE token_b END AS token_b,
         CASE action WHEN 'swap' THEN amounts_last ELSE amount_b END AS amount_b_raw
  FROM pivoted WHERE kind = 'router' AND action IN ('swap', 'add', 'remove')
  UNION ALL
  SELECT contract_id, closed_at, tx_hash, to_addr, 'aggregator_swap', 'aggregator_user', NULL,
         token_in, amount_in, token_out, amount_out
  FROM pivoted WHERE kind = 'aggregator' AND action = 'swap'
  UNION ALL
  SELECT p.contract_id, p.closed_at, p.tx_hash, p.to_addr,
         CASE p.action WHEN 'swap' THEN 'pair_swap' WHEN 'deposit' THEN 'add_liquidity' WHEN 'withdraw' THEN 'remove_liquidity' END,
         CASE p.action WHEN 'swap' THEN 'swapper' ELSE 'lp' END,
         p.contract_id,
         NULL, COALESCE(p.amount_0, p.amount_0_in + p.amount_0_out),
         NULL, COALESCE(p.amount_1, p.amount_1_in + p.amount_1_out)
  FROM pivoted p
  WHERE p.kind = 'pair' AND p.action IN ('swap', 'deposit', 'withdraw')
    AND p.tx_hash NOT IN (SELECT tx_hash FROM routed_txs)
),
sdex_txs AS (
  SELECT id AS transaction_id, lower(to_hex(transaction_hash)) AS tx_hash, account
  FROM stellar.history_transactions
  WHERE {win('closed_at_date')} AND successful = TRUE AND memo LIKE 'SoroswapAggregator%'
),
sdex AS (
  SELECT o.closed_at, t.tx_hash, t.account, o."to" AS recipient,
    CASE WHEN o.source_asset_type = 'native' THEN 'native' ELSE o.source_asset_code || ':' || o.source_asset_issuer END AS token_a,
    o.source_amount AS amount_a,
    CASE WHEN o.asset_type = 'native' THEN 'native' ELSE o.asset_code || ':' || o.asset_issuer END AS token_b,
    o.amount AS amount_b
  FROM stellar.history_operations o
  JOIN sdex_txs t ON t.transaction_id = o.transaction_id
  WHERE {win('o.closed_at_date')} AND o.type_string IN ('path_payment_strict_send', 'path_payment_strict_receive')
)
SELECT 'soroswap' AS protocol, contract_id, closed_at, tx_hash, user_address, action, role, pool,
  token_a, CAST(amount_a_raw * DECIMAL '0.0000001' AS DECIMAL(38,7)) AS amount_a,
  token_b, CAST(amount_b_raw * DECIMAL '0.0000001' AS DECIMAL(38,7)) AS amount_b
FROM normalized
UNION ALL
SELECT 'soroswap', NULL, closed_at, tx_hash, account, 'aggregator_sdex_swap', 'aggregator_user', NULL,
  token_a, CAST(amount_a AS DECIMAL(38,7)), token_b, CAST(amount_b AS DECIMAL(38,7))
FROM sdex
UNION ALL
SELECT 'soroswap', NULL, closed_at, tx_hash, recipient, 'aggregator_sdex_recipient', 'aggregator_user', NULL,
  token_a, NULL, token_b, NULL
FROM sdex WHERE recipient <> account"""


def phoenix(win):
    """Modern format: one event per action, pivoted per event. Legacy format: one event per field,
    so fields of one action are grouped per (pool, tx, action); when a tx holds several senders for
    the same pool and action, each sender gets a row without amounts instead of a merged one."""
    rows = contracts('phoenix', 'pool')
    pools = [r['contract_id'] for r in rows]
    tokens = ',\n    '.join(f"('{r['contract_id']}', '{r['token_a']}', '{r['token_b']}')" for r in rows)
    return f"""WITH pools AS (SELECT * FROM (VALUES
    {tokens}) AS v(pool, token_a, token_b)),
ev AS (
  SELECT DISTINCT
    he.contract_id AS pool, he.closed_at, lower(to_hex(he.transaction_hash)) AS tx_hash,
    COALESCE(json_extract_scalar(he.topics_decoded, '$[0].string'), json_extract_scalar(he.topics_decoded, '$[0].symbol')) AS action,
    json_extract_scalar(he.topics_decoded, '$[1].string') AS field,
    he.data_decoded
  FROM stellar.history_contract_events he
  WHERE {win('he.closed_at_date')}
    AND he.contract_id IN ({lit(pools)})
    {EVENT_FILTERS}
    AND COALESCE(json_extract_scalar(he.topics_decoded, '$[0].string'), json_extract_scalar(he.topics_decoded, '$[0].symbol'))
        IN ('swap', 'provide_liquidity', 'withdraw_liquidity')
),
legacy AS (
  SELECT pool, closed_at, tx_hash, action, CAST(NULL AS VARBINARY) AS event_key,
         replace(replace(field, ' ', '_'), '-', '_') AS k,
         json_extract_scalar(data_decoded, '$.address') AS v_addr,
         TRY(CAST(json_extract_scalar(data_decoded, '$.i128') AS DECIMAL(38,0))) AS v_i128
  FROM ev WHERE field IS NOT NULL
),
modern AS (
  SELECT e.pool, e.closed_at, e.tx_hash, e.action, xxhash64(to_utf8(e.data_decoded)) AS event_key,
         replace(replace(json_extract_scalar(elem, '$.key.symbol'), ' ', '_'), '-', '_') AS k,
         json_extract_scalar(elem, '$.val.address') AS v_addr,
         TRY(CAST(json_extract_scalar(elem, '$.val.i128') AS DECIMAL(38,0))) AS v_i128
  FROM ev e
  CROSS JOIN UNNEST(CAST(json_extract(e.data_decoded, '$.map') AS array(json))) AS t(elem)
  WHERE e.field IS NULL AND e.data_decoded LIKE '{{"map":%'
),
kv AS (SELECT * FROM legacy UNION ALL SELECT * FROM modern),
pivoted AS (
  SELECT pool, tx_hash, action, event_key, MIN(closed_at) AS closed_at,
    COUNT(DISTINCT CASE WHEN k = 'sender' THEN v_addr END) AS senders,
    MAX(CASE WHEN k = 'sender' THEN v_addr END) AS sender,
    MAX(CASE WHEN k = 'sell_token' THEN v_addr END) AS sell_token,
    MAX(CASE WHEN k = 'buy_token' THEN v_addr END) AS buy_token,
    MAX(CASE WHEN k = 'token_a' THEN v_addr END) AS token_a,
    MAX(CASE WHEN k = 'token_b' THEN v_addr END) AS token_b,
    SUM(CASE WHEN k = 'offer_amount' THEN v_i128 END) AS offer_amount,
    SUM(CASE WHEN k = 'return_amount' THEN v_i128 END) AS return_amount,
    SUM(CASE WHEN k = 'token_a_amount' THEN v_i128 END) AS token_a_amount,
    SUM(CASE WHEN k = 'token_b_amount' THEN v_i128 END) AS token_b_amount,
    SUM(CASE WHEN k = 'return_amount_a' THEN v_i128 END) AS return_amount_a,
    SUM(CASE WHEN k = 'return_amount_b' THEN v_i128 END) AS return_amount_b
  FROM kv
  GROUP BY 1, 2, 3, 4
)
SELECT 'phoenix' AS protocol, p.pool AS contract_id, p.closed_at, p.tx_hash, p.sender AS user_address, p.action,
  CASE p.action WHEN 'swap' THEN 'swapper' ELSE 'lp' END AS role, p.pool,
  CASE p.action WHEN 'swap' THEN p.sell_token ELSE COALESCE(p.token_a, r.token_a) END AS token_a,
  CAST(CASE p.action WHEN 'swap' THEN p.offer_amount WHEN 'provide_liquidity' THEN p.token_a_amount ELSE p.return_amount_a END * DECIMAL '0.0000001' AS DECIMAL(38,7)) AS amount_a,
  CASE p.action WHEN 'swap' THEN p.buy_token ELSE COALESCE(p.token_b, r.token_b) END AS token_b,
  CAST(CASE p.action WHEN 'swap' THEN p.return_amount WHEN 'provide_liquidity' THEN p.token_b_amount ELSE p.return_amount_b END * DECIMAL '0.0000001' AS DECIMAL(38,7)) AS amount_b
FROM pivoted p LEFT JOIN pools r ON r.pool = p.pool
WHERE p.senders = 1
UNION ALL
SELECT DISTINCT 'phoenix', l.pool, l.closed_at, l.tx_hash, l.v_addr, l.action,
  CASE l.action WHEN 'swap' THEN 'swapper' ELSE 'lp' END, l.pool, NULL, CAST(NULL AS DECIMAL(38,7)), NULL, CAST(NULL AS DECIMAL(38,7))
FROM legacy l JOIN pivoted p ON p.pool = l.pool AND p.tx_hash = l.tx_hash AND p.action = l.action AND p.event_key IS NULL
WHERE p.senders > 1 AND l.k = 'sender'"""


def fxdao(win):
    return f"""WITH ops AS (
  SELECT o.contract_id, o.closed_at, o.transaction_id, o.source_account,
         json_extract_scalar(o.parameters_json_decoded, '$[1].symbol') AS fn,
         o.parameters_json_decoded AS params
  FROM stellar.history_operations o
  WHERE {win('o.closed_at_date')}
    AND o.type_string = 'invoke_host_function'
    AND o.contract_id IN ('{FXDAO_VAULTS}', '{FXDAO_LOCKING}')
),
tx AS (
  SELECT id, lower(to_hex(transaction_hash)) AS tx_hash
  FROM stellar.history_transactions
  WHERE {win('closed_at_date')} AND successful = TRUE
)
SELECT 'fxdao' AS protocol, o.contract_id, o.closed_at, t.tx_hash, o.source_account AS user_address,
  CASE WHEN o.contract_id = '{FXDAO_LOCKING}' THEN 'locking_' || o.fn ELSE o.fn END AS action,
  CASE
    WHEN o.contract_id = '{FXDAO_LOCKING}' THEN 'lp'
    WHEN o.fn IN ('new_vault', 'increase_collateral', 'increase_debt', 'pay_debt', 'withdraw_collateral') THEN 'vault_owner'
    WHEN o.fn = 'redeem' THEN 'redeemer'
    WHEN o.fn IN ('liquidate', 'evict') THEN 'liquidator'
  END AS role,
  CAST(NULL AS VARCHAR) AS pool,
  regexp_extract(o.params, '"denomination"\\}},"val":\\{{"symbol":"([A-Z]+)"', 1) AS token_a,
  CAST(CASE WHEN o.contract_id = '{FXDAO_LOCKING}' AND o.fn = 'deposit'
            THEN TRY(CAST(json_extract_scalar(o.params, '$[4].u128') AS DECIMAL(38,0))) * DECIMAL '0.0000001' END AS DECIMAL(38,7)) AS amount_a,
  CAST(NULL AS VARCHAR) AS token_b, CAST(NULL AS DECIMAL(38,7)) AS amount_b
FROM ops o JOIN tx t ON t.id = o.transaction_id
WHERE (o.contract_id = '{FXDAO_LOCKING}' AND o.fn IN ('deposit', 'withdraw'))
   OR (o.contract_id = '{FXDAO_VAULTS}' AND o.fn IN ('new_vault', 'increase_collateral', 'increase_debt', 'pay_debt', 'withdraw_collateral', 'redeem', 'liquidate', 'evict'))"""


def etherfuse(win):
    """Classic asset issuer: payments, path payments and offers from history_operations, SDEX
    trades from history_trades (both counterparties). Trades carry 'op:<id>' as tx_hash."""
    I = ETHERFUSE_ISSUER
    return f"""WITH ops AS (
  SELECT o.type_string, o.closed_at, o.transaction_id, o.source_account, o."from" AS from_acct, o."to" AS to_acct, o.amount, o.source_amount,
    CASE WHEN o.asset_issuer = '{I}' THEN o.asset_code END AS dest_code,
    CASE WHEN o.source_asset_issuer = '{I}' THEN o.source_asset_code END AS src_code,
    CASE WHEN o.selling_asset_issuer = '{I}' THEN o.selling_asset_code
         WHEN o.buying_asset_issuer = '{I}' THEN o.buying_asset_code END AS offer_code
  FROM stellar.history_operations o
  WHERE {win('o.closed_at_date')}
    AND o.type_string IN ('payment', 'path_payment_strict_send', 'path_payment_strict_receive', 'manage_sell_offer', 'manage_buy_offer', 'create_passive_sell_offer')
    AND (o.asset_issuer = '{I}' OR o.source_asset_issuer = '{I}' OR o.selling_asset_issuer = '{I}' OR o.buying_asset_issuer = '{I}')
),
tx AS (
  SELECT id, lower(to_hex(transaction_hash)) AS tx_hash
  FROM stellar.history_transactions
  WHERE {win('closed_at_date')} AND successful = TRUE
),
rows_ AS (
  SELECT o.closed_at, o.transaction_id, o.to_acct AS user_address,
         CASE WHEN COALESCE(o.from_acct, o.source_account) = '{I}' THEN 'mint' ELSE 'receive' END AS action,
         CASE WHEN COALESCE(o.from_acct, o.source_account) = '{I}' THEN 'minter' ELSE 'holder' END AS role,
         o.dest_code AS token_a, o.amount AS amount_a, o.src_code AS token_b, o.source_amount AS amount_b
  FROM ops o
  WHERE o.type_string IN ('payment', 'path_payment_strict_send', 'path_payment_strict_receive')
    AND o.dest_code IS NOT NULL AND o.to_acct <> '{I}'
  UNION ALL
  SELECT o.closed_at, o.transaction_id, COALESCE(o.from_acct, o.source_account),
         CASE WHEN o.to_acct = '{I}' THEN 'redeem' ELSE 'send' END,
         CASE WHEN o.to_acct = '{I}' THEN 'redeemer' ELSE 'holder' END,
         COALESCE(o.src_code, o.dest_code), COALESCE(o.source_amount, o.amount), NULL, NULL
  FROM ops o
  WHERE o.type_string IN ('payment', 'path_payment_strict_send', 'path_payment_strict_receive')
    AND COALESCE(o.src_code, CASE WHEN o.type_string = 'payment' THEN o.dest_code END) IS NOT NULL
    AND COALESCE(o.from_acct, o.source_account) <> '{I}'
  UNION ALL
  SELECT o.closed_at, o.transaction_id, o.source_account, 'offer', 'trader', o.offer_code, o.amount, NULL, NULL
  FROM ops o
  WHERE o.type_string IN ('manage_sell_offer', 'manage_buy_offer', 'create_passive_sell_offer') AND o.offer_code IS NOT NULL
),
trades AS (
  SELECT MIN(tr.closed_at) AS closed_at, tr.history_operation_id, acct AS user_address,
    CASE WHEN tr.selling_asset_issuer = '{I}' THEN tr.selling_asset_code ELSE tr.buying_asset_code END AS token_a,
    SUM(CASE WHEN tr.selling_asset_issuer = '{I}' THEN tr.selling_amount ELSE tr.buying_amount END) AS amount_a,
    CASE WHEN tr.selling_asset_issuer = '{I}' THEN COALESCE(NULLIF(tr.buying_asset_code, ''), 'XLM') ELSE COALESCE(NULLIF(tr.selling_asset_code, ''), 'XLM') END AS token_b,
    SUM(CASE WHEN tr.selling_asset_issuer = '{I}' THEN tr.buying_amount ELSE tr.selling_amount END) AS amount_b
  FROM stellar.history_trades tr
  CROSS JOIN UNNEST(ARRAY[tr.selling_account_address, tr.buying_account_address]) AS u(acct)
  WHERE {win('tr.closed_at_date')}
    AND (tr.selling_asset_issuer = '{I}' OR tr.buying_asset_issuer = '{I}')
    AND acct IS NOT NULL AND acct <> ''
  GROUP BY 2, 3, 4, 6
)
SELECT 'etherfuse' AS protocol, CAST(NULL AS VARCHAR) AS contract_id, r.closed_at, t.tx_hash, r.user_address, r.action, r.role,
  CAST(NULL AS VARCHAR) AS pool, r.token_a, CAST(r.amount_a AS DECIMAL(38,7)) AS amount_a,
  NULLIF(r.token_b, '') AS token_b, CAST(r.amount_b AS DECIMAL(38,7)) AS amount_b
FROM rows_ r JOIN tx t ON t.id = r.transaction_id
WHERE r.user_address IS NOT NULL AND r.user_address <> ''
UNION ALL
SELECT 'etherfuse', NULL, closed_at, 'op:' || CAST(history_operation_id AS VARCHAR), user_address, 'trade', 'trader', NULL,
       token_a, CAST(amount_a AS DECIMAL(38,7)), token_b, CAST(amount_b AS DECIMAL(38,7))
FROM trades"""


def sushiswap(win):
    """Uniswap-v3-style CLMM, pool events only (checked on 2026-09-22 over 30 days). swap carries the
    user as sender, also when the default router routes it (the router passes the wallet as sender),
    so the router's own swap event is not read. Amounts are signed: positive went into the pool
    (304 of 304 single-hop routed swaps matched the router's amount_in). mint carries the wallet as
    sender (51 of 51 equal to the signer when the position manager is invoked directly; most mints
    come through another contract with no signer to read). burn is not read: it carries no user, runs
    in a different tx than its collect, and moves no tokens; the tokens leave the pool in collect,
    which carries the recipient (30 days to 2026-09-22: 505 burns, 504 collects)."""
    rows = contracts('sushiswap', 'pool')
    pools = [r['contract_id'] for r in rows]
    tokens = ',\n    '.join(f"('{r['contract_id']}', '{r['token_a']}', '{r['token_b']}')" for r in rows)
    return f"""WITH pools AS (SELECT * FROM (VALUES
    {tokens}) AS v(pool, token0, token1)),
ev AS (
  SELECT DISTINCT he.contract_id, he.closed_at, lower(to_hex(he.transaction_hash)) AS tx_hash,
    json_extract_scalar(he.topics_decoded, '$[0].symbol') AS action, he.data_decoded
  FROM stellar.history_contract_events he
  WHERE {win('he.closed_at_date')}
    AND he.contract_id IN ({lit(pools)})
    {EVENT_FILTERS}
    AND json_extract_scalar(he.topics_decoded, '$[0].symbol') IN ('swap', 'mint', 'collect')
),
kv AS (
  SELECT e.contract_id, e.closed_at, e.tx_hash, e.action, xxhash64(to_utf8(e.data_decoded)) AS event_key,
         json_extract_scalar(elem, '$.key.symbol') AS k,
         json_extract_scalar(elem, '$.val.address') AS v_addr,
         COALESCE(TRY(CAST(json_extract_scalar(elem, '$.val.i128') AS DECIMAL(38,0))),
                  TRY(CAST(json_extract_scalar(elem, '$.val.u128') AS DECIMAL(38,0)))) AS v_int
  FROM ev e
  CROSS JOIN UNNEST(CAST(json_extract(e.data_decoded, '$.map') AS array(json))) AS t(elem)
),
pivoted AS (
  SELECT contract_id, closed_at, tx_hash, action, event_key,
    MAX(CASE WHEN k = 'sender' THEN v_addr END) AS sender,
    MAX(CASE WHEN k = 'recipient' THEN v_addr END) AS recipient,
    MAX(CASE WHEN k = 'amount0' THEN v_int END) AS amount0,
    MAX(CASE WHEN k = 'amount1' THEN v_int END) AS amount1
  FROM kv
  GROUP BY 1, 2, 3, 4, 5
)
SELECT 'sushiswap' AS protocol, p.contract_id, p.closed_at, p.tx_hash,
  CASE p.action WHEN 'collect' THEN p.recipient ELSE p.sender END AS user_address,
  CASE p.action WHEN 'mint' THEN 'add_liquidity' ELSE p.action END AS action,
  CASE p.action WHEN 'swap' THEN 'swapper' ELSE 'lp' END AS role,
  p.contract_id AS pool,
  CASE WHEN p.action <> 'swap' OR p.amount0 > 0 THEN r.token0 ELSE r.token1 END AS token_a,
  CAST(CASE WHEN p.action <> 'swap' THEN p.amount0 WHEN p.amount0 > 0 THEN p.amount0 ELSE p.amount1 END
       * DECIMAL '0.0000001' AS DECIMAL(38,7)) AS amount_a,
  CASE WHEN p.action <> 'swap' OR p.amount0 > 0 THEN r.token1 ELSE r.token0 END AS token_b,
  CAST(CASE WHEN p.action <> 'swap' THEN p.amount1 WHEN p.amount0 > 0 THEN -p.amount1 ELSE -p.amount0 END
       * DECIMAL '0.0000001' AS DECIMAL(38,7)) AS amount_b
FROM pivoted p
LEFT JOIN pools r ON r.pool = p.contract_id"""


SOURCES = {'blend': blend, 'aquarius': aquarius, 'soroswap': soroswap, 'phoenix': phoenix,
           'fxdao': fxdao, 'etherfuse': etherfuse, 'sushiswap': sushiswap}


def history_start(protocol):
    return HISTORY_STARTS.get(protocol, HISTORY_START)


def archive_table(p):
    return f'dune.paltalabs.result_scf_{p}_activity_archive'


def live_table(p):
    return f'dune.paltalabs.result_scf_{p}_activity'


def layer(protocol, kind, window=None):
    """kind: 'archive' (full history up to the first day of the current month, monthly cron) or
    'live' (from the archive's covered_until, pruned to the last 75 days, daily cron).
    window=(start, end) literal dates overrides both, for one-day tests."""
    if window:
        start, end = (f"DATE '{d}'" for d in window)
        win = lambda col: f'{col} >= {start} AND {col} < {end}'
        cov_from, cov_until = start, end
    elif kind == 'archive':
        start, end = f"DATE '{history_start(protocol)}'", "CAST(date_trunc('month', CURRENT_DATE) AS DATE)"
        win = lambda col: f'{col} >= {start} AND {col} < {end}'
        cov_from, cov_until = start, end
    else:
        bound = f"(SELECT MAX(covered_until) FROM {archive_table(protocol)} WHERE row_kind = 'metadata')"
        prune = f"CURRENT_DATE - INTERVAL '{LIVE_PRUNE_DAYS}' DAY"
        # The literal prune lets Dune skip partitions; the archive bound makes it exact.
        win = lambda col: f'{col} >= {prune} AND {col} >= {bound} AND {col} < CURRENT_DATE'
        cov_from, cov_until = f'GREATEST({bound}, CAST({prune} AS DATE))', 'CURRENT_DATE'
    return f"""-- Generated by scripts/activity_sql.py. Normalized activity, docs/modelo-de-datos.md.
-- {kind}: one row per user action plus one metadata row with the covered range.
WITH src AS (
{SOURCES[protocol](win)}
)
SELECT protocol, contract_id, closed_at, tx_hash, user_address, action, role, pool, token_a, amount_a, token_b, amount_b,
       'activity' AS row_kind, {cov_from} AS covered_from, {cov_until} AS covered_until,
       CURRENT_TIMESTAMP AS refreshed_at, '{kind}' AS source_layer
FROM src
WHERE regexp_like(user_address, '^[GC][A-Z2-7]{{55}}$') AND role IS NOT NULL
UNION ALL
SELECT '{protocol}', NULL, CAST(NULL AS TIMESTAMP WITH TIME ZONE), NULL, NULL, NULL, NULL, NULL, NULL, CAST(NULL AS DECIMAL(38,7)), NULL, CAST(NULL AS DECIMAL(38,7)),
       'metadata', {cov_from}, {cov_until}, CURRENT_TIMESTAMP, '{kind}'
"""


def archive_incremental(protocol):
    """Steady-state SQL of the archive, set after its first full build. Dune rejects monthly crons
    (weekly at most), so the matview runs every Monday: on the first Monday of the month it appends
    the month that just closed from the raw tables; on the other Mondays the date gate is false,
    Dune skips the scan (measured 0,01 cr against 0,66 open) and the table is copied as it was.
    A full rescan of the history is the first build (runbook) and can be repeated by hand."""
    own = archive_table(protocol)
    month_start = "CAST(date_trunc('month', CURRENT_DATE) AS DATE)"
    gate = 'day_of_month(CURRENT_DATE) <= 7'
    prev_until = f"(SELECT MAX(covered_until) FROM {own} WHERE row_kind = 'metadata')"
    prune = f"CURRENT_DATE - INTERVAL '{LIVE_PRUNE_DAYS}' DAY"
    win = lambda col: f'{col} >= {prune} AND {col} >= {prev_until} AND {col} < {month_start} AND {gate}'
    new_until = f'CASE WHEN {gate} THEN GREATEST({prev_until}, {month_start}) ELSE {prev_until} END'
    return f"""-- Generated by scripts/activity_sql.py. Archive, incremental: previous snapshot of this matview
-- plus, on the first Monday of the month only, the month that just closed.
WITH prev AS (SELECT * FROM {own} WHERE row_kind = 'activity'),
src AS (
{SOURCES[protocol](win)}
)
SELECT protocol, contract_id, closed_at, tx_hash, user_address, action, role, pool, token_a, amount_a, token_b, amount_b,
       'activity' AS row_kind, covered_from, {new_until} AS covered_until, refreshed_at, source_layer
FROM prev
UNION ALL
SELECT protocol, contract_id, closed_at, tx_hash, user_address, action, role, pool, token_a, amount_a, token_b, amount_b,
       'activity', DATE '{history_start(protocol)}', {new_until}, CURRENT_TIMESTAMP, 'archive'
FROM src
WHERE regexp_like(user_address, '^[GC][A-Z2-7]{{55}}$') AND role IS NOT NULL
UNION ALL
SELECT '{protocol}', NULL, CAST(NULL AS TIMESTAMP WITH TIME ZONE), NULL, NULL, NULL, NULL, NULL, NULL, CAST(NULL AS DECIMAL(38,7)), NULL, CAST(NULL AS DECIMAL(38,7)),
       'metadata', DATE '{history_start(protocol)}', {new_until}, CURRENT_TIMESTAMP, 'archive'
"""


def all_activity(columns='*', where="row_kind = 'activity'"):
    """Union of the twelve layers. Archive and live are disjoint by construction (live starts at
    the archive's covered_until), so nothing is deduplicated here."""
    return '\nUNION ALL\n'.join(f'SELECT {columns} FROM {t(p)} WHERE {where}'
                                for p in PROTOCOLS for t in (archive_table, live_table))


def users():
    """result_scf_users keeps its schema (daily user grain) so every metric on top is unchanged."""
    return f"""-- Daily user grain derived from the twelve normalized activity layers (CLAUDE.md rules 2 and 3).
WITH act AS (
{all_activity('protocol, closed_at, user_address, role, covered_from, covered_until, refreshed_at, source_layer')}
), meta AS (
{all_activity('protocol, covered_from, covered_until, refreshed_at, source_layer', "row_kind = 'metadata'")}
)
SELECT protocol, CAST(closed_at AT TIME ZONE 'UTC' AS DATE) AS activity_date, user_address, role,
       MAX(closed_at) AS last_activity_at, 'activity' AS row_kind,
       covered_from, covered_until, MAX(refreshed_at) AS refreshed_at, source_layer
FROM act
GROUP BY 1, 2, 3, 4, 7, 8, 10
UNION ALL
SELECT protocol, CAST(NULL AS DATE), CAST(NULL AS VARCHAR), CAST(NULL AS VARCHAR),
       CAST(NULL AS TIMESTAMP WITH TIME ZONE), 'metadata', covered_from, covered_until, refreshed_at, source_layer
FROM meta
"""


def integrity():
    """How concentrated each protocol's activity is, over the last 28 complete days, and how it
    compares with the total. Explains why a protocol with more volume can show fewer addresses."""
    return f"""-- Activity concentration per protocol vs all protocols, last 28 complete days (UTC).
WITH act AS (
{all_activity('protocol, user_address, closed_at', "row_kind = 'activity' AND CAST(closed_at AT TIME ZONE 'UTC' AS DATE) >= CURRENT_DATE - INTERVAL '28' DAY AND CAST(closed_at AT TIME ZONE 'UTC' AS DATE) < CURRENT_DATE")}
), per_addr AS (
  SELECT protocol, user_address, COUNT(*) AS actions FROM act GROUP BY 1, 2
  UNION ALL
  SELECT 'all protocols', user_address, COUNT(*) FROM act GROUP BY 1, 2
), ranked AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY protocol ORDER BY actions DESC, user_address) AS rn,
         SUM(actions) OVER (PARTITION BY protocol ORDER BY actions DESC, user_address ROWS UNBOUNDED PRECEDING) AS running,
         SUM(actions) OVER (PARTITION BY protocol) AS total
  FROM per_addr
), stats AS (
  SELECT protocol,
         MAX(total) AS actions,
         COUNT(*) AS addresses,
         COUNT_IF(user_address LIKE 'G%') AS g_addresses,
         COUNT_IF(user_address LIKE 'C%') AS c_addresses,
         CAST(SUM(CASE WHEN rn <= 10 THEN actions END) AS DOUBLE) / MAX(total) AS top10_action_share,
         COUNT_IF(running - actions < 0.9 * total) AS addresses_for_90pct_of_actions,
         CAST(SUM(CASE WHEN user_address LIKE 'C%' THEN actions END) AS DOUBLE) / MAX(total) AS contract_action_share,
         CAST(SUM(CASE WHEN user_address IN ({lit(AGGREGATORS)}) THEN actions END) AS DOUBLE) / MAX(total) AS router_or_aggregator_action_share
  FROM ranked GROUP BY 1
)
SELECT s.*,
       CAST(s.actions AS DOUBLE) / t.actions AS share_of_all_actions,
       CAST(s.addresses AS DOUBLE) / t.addresses AS share_of_all_addresses,
       CAST(s.actions AS DOUBLE) / s.addresses AS actions_per_address,
       CAST(CURRENT_DATE - INTERVAL '28' DAY AS DATE) AS window_from, CURRENT_DATE AS window_until,
       CURRENT_TIMESTAMP AS refreshed_at
FROM stats s CROSS JOIN (SELECT actions, addresses FROM stats WHERE protocol = 'all protocols') t
ORDER BY CASE WHEN s.protocol = 'all protocols' THEN 1 ELSE 0 END, s.actions DESC
"""


def chart_integrity():
    return """-- Chart source: activity concentration table, protocols by actions, the total last.
SELECT protocol, actions, share_of_all_actions, addresses, share_of_all_addresses, g_addresses, c_addresses,
       actions_per_address, top10_action_share, addresses_for_90pct_of_actions, contract_action_share,
       COALESCE(router_or_aggregator_action_share, 0) AS router_or_aggregator_action_share, window_from, window_until
FROM dune.paltalabs.result_scf_integrity
ORDER BY CASE WHEN protocol = 'all protocols' THEN 1 ELSE 0 END, actions DESC
"""


def registered_literals():
    rows = list(csv.DictReader(open(REGISTRY_CSV)))
    return [r['contract_id'] for r in rows]
