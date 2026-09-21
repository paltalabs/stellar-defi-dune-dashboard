-- Query: https://dune.com/queries/8796466
-- Matview: dune.paltalabs.result_scf_fxdao_users_live   cron: 0 5 * * *
-- Última ejecución: 01M32KKDTN1EGM0PBWWWKQ1C7R
-- Costo: 1.025 cr; filas: 1; engine medium
-- Generated from scripts/pilot_sql.py; T1 address activity only.
-- Daily UTC buckets. Metadata survives an empty protocol and is never a user.
WITH source AS (
WITH ops AS (
  SELECT
    o.contract_id, o.closed_at, o.transaction_id, o.source_account,
    json_extract_scalar(o.parameters_json_decoded, '$[1].symbol') AS fn,
    o.parameters_json_decoded AS params
  FROM stellar.history_operations o
  WHERE o.closed_at_date >= DATE '2026-09-17' AND o.closed_at_date < CURRENT_DATE
    AND o.type_string = 'invoke_host_function'
    AND o.contract_id IN ('CCUN4RXU5VNDHSF4S4RKV4ZJYMX2YWKOH6L4AKEKVNVDQ7HY5QIAO4UB',   -- vaults
                          'CDCART6WRSM2K4CKOAOB5YKUVBSJ6KLOVS7ZEJHA4OAQ2FXX7JOHLXIP')   -- locking pool
),
tx AS (
  SELECT id, lower(to_hex(transaction_hash)) AS tx_hash
  FROM stellar.history_transactions
  WHERE closed_at_date >= DATE '2026-09-17' AND closed_at_date < CURRENT_DATE
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
), users AS (
  SELECT protocol, CAST(closed_at AT TIME ZONE 'UTC' AS DATE) AS activity_date,
         user_address, role, MAX(closed_at) AS last_activity_at
  FROM source
  WHERE regexp_like(user_address, '^[GC][A-Z2-7]{55}$') AND role IS NOT NULL
  GROUP BY 1, 2, 3, 4
)
SELECT protocol, activity_date, user_address, role, last_activity_at,
       'activity' AS row_kind, DATE '2026-09-17' AS covered_from, CURRENT_DATE AS covered_until,
       CURRENT_TIMESTAMP AS refreshed_at, 'live' AS source_layer
FROM users
UNION ALL
SELECT 'fxdao', CAST(NULL AS DATE), CAST(NULL AS VARCHAR), CAST(NULL AS VARCHAR),
       CAST(NULL AS TIMESTAMP WITH TIME ZONE), 'metadata', DATE '2026-09-17', CURRENT_DATE, CURRENT_TIMESTAMP, 'live'
