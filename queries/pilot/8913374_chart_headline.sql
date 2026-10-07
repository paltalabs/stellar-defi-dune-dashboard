-- Query: https://dune.com/queries/8913374
-- Matview: ninguna (gráfico, schedule de Dune)
-- Última ejecución: 01M4C1X5GN2TEC7HKGWVN802WN
-- Costo: 0.16 cr; filas: 1; engine medium
-- Chart source: headline counters. Unique addresses across all protocols in the last complete
-- calendar week (Monday to Sunday, UTC) and month, with the previous period for growth.
WITH b AS (
  SELECT CAST(date_trunc('week', CURRENT_DATE) AS DATE) AS w, CAST(date_trunc('month', CURRENT_DATE) AS DATE) AS m
), u AS (
  SELECT activity_date, user_address FROM dune.paltalabs.result_scf_users
  WHERE row_kind = 'activity' AND activity_date >= (SELECT date_add('month', -2, m) FROM b)
), c AS (
  SELECT
    COUNT(DISTINCT CASE WHEN activity_date >= date_add('day', -7, w) AND activity_date < w THEN user_address END) AS wau,
    COUNT(DISTINCT CASE WHEN activity_date >= date_add('day', -7, w) AND activity_date < w AND user_address LIKE 'G%' THEN user_address END) AS wau_g,
    COUNT(DISTINCT CASE WHEN activity_date >= date_add('day', -14, w) AND activity_date < date_add('day', -7, w) THEN user_address END) AS wau_prev,
    COUNT(DISTINCT CASE WHEN activity_date >= date_add('month', -1, m) AND activity_date < m THEN user_address END) AS mau,
    COUNT(DISTINCT CASE WHEN activity_date >= date_add('month', -1, m) AND activity_date < m AND user_address LIKE 'G%' THEN user_address END) AS mau_g,
    COUNT(DISTINCT CASE WHEN activity_date >= date_add('month', -2, m) AND activity_date < date_add('month', -1, m) THEN user_address END) AS mau_prev,
    MIN(date_add('day', -7, w)) AS week_start, MIN(date_add('month', -1, m)) AS month_start
  FROM u CROSS JOIN b
)
SELECT wau, wau_g, wau_prev, CAST(wau - wau_prev AS DOUBLE) / NULLIF(wau_prev, 0) AS wau_growth,
       ROUND(100.0 * (wau - wau_prev) / NULLIF(wau_prev, 0), 1) AS wau_growth_pct,
       mau, mau_g, mau_prev, CAST(mau - mau_prev AS DOUBLE) / NULLIF(mau_prev, 0) AS mau_growth,
       ROUND(100.0 * (mau - mau_prev) / NULLIF(mau_prev, 0), 1) AS mau_growth_pct,
       week_start, month_start
FROM c
