-- Query: SCF35 · Soroswap activity          https://dune.com/queries/8666498
-- Matview: ninguna   cron: ninguno
-- Lee: stellar.history_contract_events, stellar.contract_data
-- Costo medido: 2026-09-10 7.93 cr, 31598 filas, engine medium, ventana 45 days
-- Espejo escrito a mano el 2026-09-10 (el endpoint REST de lectura devolvió 401; ver docs/runbook.md). El SQL manda en Dune.

-- SCF35 · Soroswap activity. Schema: docs/modelo-de-datos.md in github.com/paltalabs/defi-dune-dashboards
WITH pairs AS (
  SELECT DISTINCT json_extract_scalar(val_decoded, '$.address') AS contract_id, 'pair' AS kind
  FROM stellar.contract_data
  WHERE contract_id = 'CA4HEQTL2WPEUYKYKCDOHCDNIV4QHNJ7EL4J4NQ6VADP7SYHVRYZ7AW2'   -- factory
    AND closed_at_date >= DATE '2024-02-01'
    AND contract_key_type = 'ScValTypeScvVec'
    AND json_extract_scalar(key_decoded, '$.vec[0].symbol') = 'PairAddressesNIndexed'
    AND json_extract_scalar(val_decoded, '$.address') IS NOT NULL
),
contracts AS (
  SELECT contract_id, kind FROM pairs
  UNION ALL
  SELECT contract_id, kind FROM (VALUES
    ('CAG5LRYQ5JVEUI5TEID72EYOVX44TTUJT5BQR2J6J77FH65PCCFAJDDH', 'router'),
    ('CCHCH6XVKTMKTYCTKKTKNE2TFP5CMORNY77TA6XSRAD2XM7I2SJBUH3H', 'aggregator'),
    ('CC2CMNKAFI3KKL6ROMIYJKKX2WE2MV5QAF7DZDWC57ENHV6DQTHT3W64', 'aggregator'),
    ('CBFAORZNK4JSCJYT3ZLWFQ5QEI4IHOIYY6XCYT3E47AK6ZMZFKFP6ZKA', 'aggregator'),
    ('CACITNMTUSTZYKKH4TJVXNH4C4XHGYFVAPQ2EE3D5LTL3HIA32QY4Q6X', 'aggregator'),
    ('CDPJAUHPMJBOPUHBWBHO7NKSTR6J5EXZZ2OX4QGSXIHEJLBDY2JABM3L', 'aggregator'),
    ('CCXNPJPNWT4WDWKTUNRPKNUHFYKZW6XBJAOHKAW2KLY5PBBGX6ZCFUJC', 'aggregator'),
    ('CAWTTRKV7N4MBFSFU7BBZVMOAFEVYMZEDUS4ULBGUQH5YMFKPOFUWPF3', 'aggregator'),
    ('CCWLXIBMONXFCXELPFHXPT4VSXKUSSP67DXNXWQ4YIPFGNBHQWEX4W4P', 'aggregator'),
    ('CDEM2W2D2SC7VU3NOCIKHZWCUNCAUWI5GUGHSWBJNBENRHSVIMUT6EM2', 'aggregator'),
    ('CAYP3UWLJM7ZPTUKL6R6BFGTRWLZ46LRKOXTERI2K6BIJAWGYY62TXTO', 'aggregator')
  ) AS v(contract_id, kind)
),
ev AS (
  SELECT DISTINCT
    c.kind, he.contract_id, he.closed_at, lower(to_hex(he.transaction_hash)) AS tx_hash,
    json_extract_scalar(he.topics_decoded, '$[0].string') AS emitter,
    json_extract_scalar(he.topics_decoded, '$[1].symbol') AS action,
    he.data_decoded
  FROM stellar.history_contract_events he
  JOIN contracts c ON c.contract_id = he.contract_id
  WHERE he.closed_at_date >= CURRENT_DATE - INTERVAL '45' DAY      -- WINDOW
    AND he.type_string = 'ContractEventTypeContract'
    AND he.successful = TRUE
    AND he.in_successful_contract_call = TRUE
    AND he.topics_decoded LIKE '[{"string":"Soroswap%'
),
kv AS (
  SELECT e.kind, e.contract_id, e.closed_at, e.tx_hash, e.emitter, e.action,
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
  SELECT kind, contract_id, closed_at, tx_hash, emitter, action,
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
routed_txs AS (
  SELECT DISTINCT tx_hash FROM pivoted WHERE kind IN ('router', 'aggregator')
),
normalized AS (
  -- router: swap / add / remove, with tokens
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
  -- aggregator: swap
  SELECT contract_id, closed_at, tx_hash, to_addr, 'aggregator_swap', 'aggregator_user', NULL,
         token_in, amount_in, token_out, amount_out
  FROM pivoted WHERE kind = 'aggregator' AND action = 'swap'
  UNION ALL
  -- pairs called directly (no router or aggregator event in the same tx): tokens unknown here
  SELECT p.contract_id, p.closed_at, p.tx_hash, p.to_addr,
         CASE p.action WHEN 'swap' THEN 'pair_swap' WHEN 'deposit' THEN 'add_liquidity' WHEN 'withdraw' THEN 'remove_liquidity' END,
         CASE p.action WHEN 'swap' THEN 'swapper' ELSE 'lp' END,
         p.contract_id,
         NULL, COALESCE(p.amount_0, p.amount_0_in + p.amount_0_out),
         NULL, COALESCE(p.amount_1, p.amount_1_in + p.amount_1_out)
  FROM pivoted p
  LEFT JOIN routed_txs r ON r.tx_hash = p.tx_hash
  WHERE p.kind = 'pair' AND p.action IN ('swap', 'deposit', 'withdraw') AND r.tx_hash IS NULL
)
SELECT
  'soroswap' AS protocol, contract_id, closed_at, tx_hash, user_address, action, role, pool,
  token_a, CAST(amount_a_raw * DECIMAL '0.0000001' AS DECIMAL(38,7)) AS amount_a,
  token_b, CAST(amount_b_raw * DECIMAL '0.0000001' AS DECIMAL(38,7)) AS amount_b
FROM normalized
WHERE user_address IS NOT NULL
