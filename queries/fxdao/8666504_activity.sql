-- Query: SCF35 · FxDAO activity          https://dune.com/queries/8666504
-- Matview: ninguna   cron: ninguno
-- Lee: stellar.history_operations, stellar.history_transactions
-- Costo medido: 2026-09-10 0.08 cr, 0 filas, engine medium, ventana 45 days
-- Notas: cero filas porque no hubo actividad en la ventana; el join se verificó con 150 días (17 filas, sondeo 8666539)
-- Espejo escrito a mano el 2026-09-10 (el endpoint REST de lectura devolvió 401; ver docs/runbook.md). El SQL manda en Dune.

-- SCF35 · FxDAO activity. Schema: docs/modelo-de-datos.md in github.com/paltalabs/stellar-defi-dune-dashboard
WITH ops AS (
  SELECT
    o.contract_id, o.closed_at, o.transaction_id, o.source_account,
    json_extract_scalar(o.parameters_json_decoded, '$[1].symbol') AS fn,
    o.parameters_json_decoded AS params
  FROM stellar.history_operations o
  WHERE o.closed_at_date >= CURRENT_DATE - INTERVAL '45' DAY      -- WINDOW
    AND o.type_string = 'invoke_host_function'
    AND o.contract_id IN ('CCUN4RXU5VNDHSF4S4RKV4ZJYMX2YWKOH6L4AKEKVNVDQ7HY5QIAO4UB',   -- vaults
                          'CDCART6WRSM2K4CKOAOB5YKUVBSJ6KLOVS7ZEJHA4OAQ2FXX7JOHLXIP')   -- locking pool
),
tx AS (
  SELECT id, lower(to_hex(transaction_hash)) AS tx_hash
  FROM stellar.history_transactions
  WHERE closed_at_date >= CURRENT_DATE - INTERVAL '45' DAY      -- WINDOW (same as above)
    AND successful = TRUE
)
SELECT
  'fxdao' AS protocol,
  o.contract_id,
  o.closed_at,
  t.tx_hash,
  o.source_account AS user_address,
  CASE WHEN o.contract_id = 'CDCART6WRSM2K4CKOAOB5YKUVBSJ6KLOVS7ZEJHA4OAQ2FXX7JOHLXIP' THEN 'locking_' || o.fn ELSE o.fn END AS action,
  CASE
    WHEN o.contract_id = 'CDCART6WRSM2K4CKOAOB5YKUVBSJ6KLOVS7ZEJHA4OAQ2FXX7JOHLXIP' THEN 'lp'
    WHEN o.fn IN ('new_vault', 'increase_collateral', 'increase_debt', 'pay_debt', 'withdraw_collateral') THEN 'vault_owner'
    WHEN o.fn = 'redeem' THEN 'redeemer'
    WHEN o.fn IN ('liquidate', 'evict') THEN 'liquidator'
  END AS role,
  CAST(NULL AS VARCHAR) AS pool,
  regexp_extract(o.params, '"denomination"\},"val":\{"symbol":"([A-Z]+)"', 1) AS token_a,
  CAST(CASE WHEN o.contract_id = 'CDCART6WRSM2K4CKOAOB5YKUVBSJ6KLOVS7ZEJHA4OAQ2FXX7JOHLXIP' AND o.fn = 'deposit'
            THEN TRY(CAST(json_extract_scalar(o.params, '$[4].u128') AS DECIMAL(38,0))) * DECIMAL '0.0000001' END AS DECIMAL(38,7)) AS amount_a,
  CAST(NULL AS VARCHAR) AS token_b,
  CAST(NULL AS DECIMAL(38,7)) AS amount_b
FROM ops o
JOIN tx t ON t.id = o.transaction_id
WHERE (o.contract_id = 'CDCART6WRSM2K4CKOAOB5YKUVBSJ6KLOVS7ZEJHA4OAQ2FXX7JOHLXIP' AND o.fn IN ('deposit', 'withdraw'))
   OR (o.contract_id = 'CCUN4RXU5VNDHSF4S4RKV4ZJYMX2YWKOH6L4AKEKVNVDQ7HY5QIAO4UB' AND o.fn IN ('new_vault', 'increase_collateral', 'increase_debt', 'pay_debt', 'withdraw_collateral', 'redeem', 'liquidate', 'evict'))
