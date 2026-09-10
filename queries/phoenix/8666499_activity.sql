-- Query: SCF35 · Phoenix activity          https://dune.com/queries/8666499
-- Matview: ninguna   cron: ninguno
-- Lee: stellar.history_contract_events, stellar.contract_data
-- Costo medido: 2026-09-10 11.13 cr, 3506 filas, engine medium, ventana 45 days
-- Notas: la más cara por fila; dos caminos de parseo (formato viejo y nuevo) sobre 14 pools
-- Espejo escrito a mano el 2026-09-10 (el endpoint REST de lectura devolvió 401; ver docs/runbook.md). El SQL manda en Dune.

-- SCF35 · Phoenix activity. Schema: docs/modelo-de-datos.md in github.com/paltalabs/defi-dune-dashboards
WITH pools AS (
  SELECT pool, MAX(token_a) AS token_a, MAX(token_b) AS token_b
  FROM (
    SELECT json_extract_scalar(val_decoded, '$.address') AS pool,
           regexp_extract(key_decoded, '"token_a"\},"val":\{"address":"(C[A-Z2-7]{55})"', 1) AS token_a,
           regexp_extract(key_decoded, '"token_b"\},"val":\{"address":"(C[A-Z2-7]{55})"', 1) AS token_b
    FROM stellar.contract_data
    WHERE contract_id = 'CB4SVAWJA6TSRNOJZ7W2AWFW46D5VR4ZMFZKDIKXEINZCZEGZCJZCKMI'   -- factory
      AND closed_at_date >= DATE '2024-02-01'
      AND contract_key_type = 'ScValTypeScvMap'
      AND json_extract_scalar(val_decoded, '$.address') IS NOT NULL
  )
  GROUP BY pool
),
ev AS (
  SELECT DISTINCT
    he.contract_id AS pool, he.closed_at, lower(to_hex(he.transaction_hash)) AS tx_hash,
    COALESCE(json_extract_scalar(he.topics_decoded, '$[0].string'), json_extract_scalar(he.topics_decoded, '$[0].symbol')) AS action,
    json_extract_scalar(he.topics_decoded, '$[1].string') AS field,
    he.data_decoded
  FROM stellar.history_contract_events he
  WHERE he.contract_id IN (SELECT pool FROM pools)
    AND he.closed_at_date >= CURRENT_DATE - INTERVAL '45' DAY      -- WINDOW
    AND he.type_string = 'ContractEventTypeContract'
    AND he.successful = TRUE
    AND he.in_successful_contract_call = TRUE
    AND (he.topics_decoded LIKE '[{"string":"swap"}%' OR he.topics_decoded LIKE '[{"string":"provide_liquidity"}%' OR he.topics_decoded LIKE '[{"string":"withdraw_liquidity"}%'
         OR he.topics_decoded LIKE '[{"symbol":"swap"}%' OR he.topics_decoded LIKE '[{"symbol":"provide_liquidity"}%' OR he.topics_decoded LIKE '[{"symbol":"withdraw_liquidity"}%')
),
-- legacy format: one event per field, value in data
legacy AS (
  SELECT pool, closed_at, tx_hash, action,
         replace(replace(field, ' ', '_'), '-', '_') AS k,
         json_extract_scalar(data_decoded, '$.address') AS v_addr,
         TRY(CAST(json_extract_scalar(data_decoded, '$.i128') AS DECIMAL(38,0))) AS v_i128
  FROM ev WHERE field IS NOT NULL
),
-- new format: one event, all fields in a map
modern AS (
  SELECT e.pool, e.closed_at, e.tx_hash, e.action,
         replace(replace(json_extract_scalar(elem, '$.key.symbol'), ' ', '_'), '-', '_') AS k,
         json_extract_scalar(elem, '$.val.address') AS v_addr,
         TRY(CAST(json_extract_scalar(elem, '$.val.i128') AS DECIMAL(38,0))) AS v_i128
  FROM ev e
  CROSS JOIN UNNEST(CAST(json_extract(e.data_decoded, '$.map') AS array(json))) AS t(elem)
  WHERE e.field IS NULL AND e.data_decoded LIKE '{"map":%'
),
kv AS (SELECT * FROM legacy UNION ALL SELECT * FROM modern),
pivoted AS (
  SELECT pool, tx_hash, action, MIN(closed_at) AS closed_at,
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
  GROUP BY 1, 2, 3
)
SELECT
  'phoenix' AS protocol,
  p.pool AS contract_id,
  p.closed_at,
  p.tx_hash,
  p.sender AS user_address,
  p.action,
  CASE p.action WHEN 'swap' THEN 'swapper' ELSE 'lp' END AS role,
  p.pool,
  CASE p.action WHEN 'swap' THEN p.sell_token ELSE COALESCE(p.token_a, r.token_a) END AS token_a,
  CAST(CASE p.action WHEN 'swap' THEN p.offer_amount WHEN 'provide_liquidity' THEN p.token_a_amount ELSE p.return_amount_a END * DECIMAL '0.0000001' AS DECIMAL(38,7)) AS amount_a,
  CASE p.action WHEN 'swap' THEN p.buy_token ELSE COALESCE(p.token_b, r.token_b) END AS token_b,
  CAST(CASE p.action WHEN 'swap' THEN p.return_amount WHEN 'provide_liquidity' THEN p.token_b_amount ELSE p.return_amount_b END * DECIMAL '0.0000001' AS DECIMAL(38,7)) AS amount_b
FROM pivoted p
LEFT JOIN pools r ON r.pool = p.pool
WHERE p.sender IS NOT NULL
