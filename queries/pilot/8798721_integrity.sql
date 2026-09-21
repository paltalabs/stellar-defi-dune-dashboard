-- Query: https://dune.com/queries/8798721
-- Matview: dune.paltalabs.result_scf_integrity   cron: 0 9 * * *
-- Última ejecución: 01M32WV8GHZ5T1PV85SGDF08K2
-- Costo: 1.109 cr; filas: 7; engine medium
-- Activity concentration per protocol vs all protocols, last 28 complete days (UTC).
WITH act AS (
SELECT protocol, user_address, closed_at FROM dune.paltalabs.result_scf_blend_activity_archive WHERE row_kind = 'activity' AND CAST(closed_at AT TIME ZONE 'UTC' AS DATE) >= CURRENT_DATE - INTERVAL '28' DAY AND CAST(closed_at AT TIME ZONE 'UTC' AS DATE) < CURRENT_DATE
UNION ALL
SELECT protocol, user_address, closed_at FROM dune.paltalabs.result_scf_blend_activity WHERE row_kind = 'activity' AND CAST(closed_at AT TIME ZONE 'UTC' AS DATE) >= CURRENT_DATE - INTERVAL '28' DAY AND CAST(closed_at AT TIME ZONE 'UTC' AS DATE) < CURRENT_DATE
UNION ALL
SELECT protocol, user_address, closed_at FROM dune.paltalabs.result_scf_aquarius_activity_archive WHERE row_kind = 'activity' AND CAST(closed_at AT TIME ZONE 'UTC' AS DATE) >= CURRENT_DATE - INTERVAL '28' DAY AND CAST(closed_at AT TIME ZONE 'UTC' AS DATE) < CURRENT_DATE
UNION ALL
SELECT protocol, user_address, closed_at FROM dune.paltalabs.result_scf_aquarius_activity WHERE row_kind = 'activity' AND CAST(closed_at AT TIME ZONE 'UTC' AS DATE) >= CURRENT_DATE - INTERVAL '28' DAY AND CAST(closed_at AT TIME ZONE 'UTC' AS DATE) < CURRENT_DATE
UNION ALL
SELECT protocol, user_address, closed_at FROM dune.paltalabs.result_scf_soroswap_activity_archive WHERE row_kind = 'activity' AND CAST(closed_at AT TIME ZONE 'UTC' AS DATE) >= CURRENT_DATE - INTERVAL '28' DAY AND CAST(closed_at AT TIME ZONE 'UTC' AS DATE) < CURRENT_DATE
UNION ALL
SELECT protocol, user_address, closed_at FROM dune.paltalabs.result_scf_soroswap_activity WHERE row_kind = 'activity' AND CAST(closed_at AT TIME ZONE 'UTC' AS DATE) >= CURRENT_DATE - INTERVAL '28' DAY AND CAST(closed_at AT TIME ZONE 'UTC' AS DATE) < CURRENT_DATE
UNION ALL
SELECT protocol, user_address, closed_at FROM dune.paltalabs.result_scf_phoenix_activity_archive WHERE row_kind = 'activity' AND CAST(closed_at AT TIME ZONE 'UTC' AS DATE) >= CURRENT_DATE - INTERVAL '28' DAY AND CAST(closed_at AT TIME ZONE 'UTC' AS DATE) < CURRENT_DATE
UNION ALL
SELECT protocol, user_address, closed_at FROM dune.paltalabs.result_scf_phoenix_activity WHERE row_kind = 'activity' AND CAST(closed_at AT TIME ZONE 'UTC' AS DATE) >= CURRENT_DATE - INTERVAL '28' DAY AND CAST(closed_at AT TIME ZONE 'UTC' AS DATE) < CURRENT_DATE
UNION ALL
SELECT protocol, user_address, closed_at FROM dune.paltalabs.result_scf_fxdao_activity_archive WHERE row_kind = 'activity' AND CAST(closed_at AT TIME ZONE 'UTC' AS DATE) >= CURRENT_DATE - INTERVAL '28' DAY AND CAST(closed_at AT TIME ZONE 'UTC' AS DATE) < CURRENT_DATE
UNION ALL
SELECT protocol, user_address, closed_at FROM dune.paltalabs.result_scf_fxdao_activity WHERE row_kind = 'activity' AND CAST(closed_at AT TIME ZONE 'UTC' AS DATE) >= CURRENT_DATE - INTERVAL '28' DAY AND CAST(closed_at AT TIME ZONE 'UTC' AS DATE) < CURRENT_DATE
UNION ALL
SELECT protocol, user_address, closed_at FROM dune.paltalabs.result_scf_etherfuse_activity_archive WHERE row_kind = 'activity' AND CAST(closed_at AT TIME ZONE 'UTC' AS DATE) >= CURRENT_DATE - INTERVAL '28' DAY AND CAST(closed_at AT TIME ZONE 'UTC' AS DATE) < CURRENT_DATE
UNION ALL
SELECT protocol, user_address, closed_at FROM dune.paltalabs.result_scf_etherfuse_activity WHERE row_kind = 'activity' AND CAST(closed_at AT TIME ZONE 'UTC' AS DATE) >= CURRENT_DATE - INTERVAL '28' DAY AND CAST(closed_at AT TIME ZONE 'UTC' AS DATE) < CURRENT_DATE
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
         CAST(SUM(CASE WHEN user_address IN ('CCHCH6XVKTMKTYCTKKTKNE2TFP5CMORNY77TA6XSRAD2XM7I2SJBUH3H', 'CC2CMNKAFI3KKL6ROMIYJKKX2WE2MV5QAF7DZDWC57ENHV6DQTHT3W64', 'CBFAORZNK4JSCJYT3ZLWFQ5QEI4IHOIYY6XCYT3E47AK6ZMZFKFP6ZKA', 'CACITNMTUSTZYKKH4TJVXNH4C4XHGYFVAPQ2EE3D5LTL3HIA32QY4Q6X', 'CDPJAUHPMJBOPUHBWBHO7NKSTR6J5EXZZ2OX4QGSXIHEJLBDY2JABM3L', 'CCXNPJPNWT4WDWKTUNRPKNUHFYKZW6XBJAOHKAW2KLY5PBBGX6ZCFUJC', 'CAWTTRKV7N4MBFSFU7BBZVMOAFEVYMZEDUS4ULBGUQH5YMFKPOFUWPF3', 'CCWLXIBMONXFCXELPFHXPT4VSXKUSSP67DXNXWQ4YIPFGNBHQWEX4W4P', 'CDEM2W2D2SC7VU3NOCIKHZWCUNCAUWI5GUGHSWBJNBENRHSVIMUT6EM2', 'CAYP3UWLJM7ZPTUKL6R6BFGTRWLZ46LRKOXTERI2K6BIJAWGYY62TXTO', 'CAG5LRYQ5JVEUI5TEID72EYOVX44TTUJT5BQR2J6J77FH65PCCFAJDDH', 'CBQDHNBFBZYE4MKPWBSJOPIYLW4SFSXAXUTSXJN76GNKYVYPCKWC6QUK', 'CA7RQDMMV6E53P5EDZA5GPWBZ33AMW2ZNO42XLI2RGRIAP4QXIARUOJQ', 'CB4YHF4ESRJ4XZRXISLXSUZTYY6YPBPZ73MZWSTUWY46DKYW7IGLHGF7') THEN actions END) AS DOUBLE) / MAX(total) AS router_or_aggregator_action_share
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
