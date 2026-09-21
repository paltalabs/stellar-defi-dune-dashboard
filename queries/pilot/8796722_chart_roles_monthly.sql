-- Query: https://dune.com/queries/8796722
-- Matview: None   cron: None
-- Última ejecución: 01M32WY9TYFK3TGAX0AZWGTF0T
-- Costo: 0.084 cr; filas: 320; engine medium
-- Chart source: unique addresses per role across all protocols, complete calendar months.
SELECT CAST(date_trunc('month', activity_date) AS DATE) AS period_start, role,
       COUNT(DISTINCT user_address) AS active_addresses,
       COUNT(DISTINCT CASE WHEN user_address LIKE 'C%' THEN user_address END) AS c_addresses
FROM dune.paltalabs.result_scf_users
WHERE row_kind = 'activity' AND activity_date >= DATE '2024-02-01'
  AND activity_date < CAST(date_trunc('month', CURRENT_DATE) AS DATE)
GROUP BY 1, 2
ORDER BY 1, 2
