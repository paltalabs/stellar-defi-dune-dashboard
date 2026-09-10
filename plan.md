# Plan: Stellar DeFi Dune Dashboards (SCF #35)

Actualizado 2026-09-10. La submission está en `scf/submission-scf35.md`. Este archivo es el
único lugar donde se marca avance y gasto.

## Lo que se decidió el 2026-09-10

1. **Nadie mantiene esto a mano.** Todo lo recurrente es una matview con cron creado por API.
2. **Dos capas por protocolo.** Archive con historia completa, refresh mensual automático.
   Ventana viva desde el último `closed_at` del archive, refresh diario. Los gráficos leen la unión.
3. **Un esquema para los seis protocolos** (`docs/modelo-de-datos.md`). Las tablas crudas se
   escanean una vez por período, y de ahí salen los cuatro entregables.
4. **Los pools se descubren solos** desde el storage de cada factory (0,3 créditos).
5. **Gasto gradual y medido.** Cada paso anota su costo acá. Los pasos caros (archives) se
   corren de a uno por día, mirando el uso antes del siguiente.

## Presupuesto

Cuenta Dune: plan Plus, 25.000 créditos por período (9 de cada mes). Al 2026-09-10 a las 13:00
UTC iban 1.788 usados por otros proyectos. Costos medidos, engine medium:

| Qué | Medido | De dónde sale |
|---|---|---|
| Eventos, 7 días, 14 contratos | 1,33 cr | query 8666280 |
| Eventos, 30 días, un protocolo | 1,6 a 4,2 cr | 8666378 Blend 3,78 · 8666399 Aquarius 4,17 · 8666417 Soroswap 1,56 · 8666420 Phoenix 1,88 |
| Operaciones, 30 días | 0,7 cr · 180 días 1,2 cr | 8666340, 8666431 (FxDAO) |
| Operaciones y trades clásicos, 30 días | 0,43 cr | 8666440 (Etherfuse) |
| Storage de una factory, historia completa | 0,32 cr | 8666382 |
| **Eventos, historia completa (desde 2024-02), 6 contratos** | **37,4 cr** | 8666314. Es el costo de un archive, casi independiente de cuántos contratos |

Proyección con esos números:

| Pieza | Costo unitario | Frecuencia | Por mes |
|---|---|---|---|
| 6 archives (historia completa) | ~40 cr cada uno | mensual, automático | ~240 |
| 6 ventanas vivas (promedio 15 días de datos) | ~2,5 cr cada una | diaria | ~450 |
| Unión + métricas del dashboard (leen matviews) | ~5 a 10 cr en total | diaria | ~250 |
| **Total régimen** | | | **~950 cr/mes, 4% de la cuota** |
| Alternativa: métricas cada 6 h como dice la submission | | 4 por día | ~+600 cr/mes |

Gasto del proyecto hasta ahora: **52,8 cr** en 11 sondeos (todos temporales, ninguno programado).

Tope acordado para la construcción del Entregable 1: **500 cr**. Los archives (~240) se corren
uno por día. Si un archive mide más de 80 cr se para y se revisa antes de seguir.

## Entregable 1: Weekly & Monthly Active Users (Tranche 1, USD 8.333)

Qué promete la submission: wallets únicas por período, desglose por protocolo, segmentación por
acción (swappers, LPs, aggregator users, lenders, borrowers, liquidators), nuevos vs
recurrentes, tasa de crecimiento semanal y mensual. Medida de completitud: la query está en el
dashboard público, verificable, y se actualiza sola.

### Paso 0: diseño validado con sondeos baratos ✅ 2026-09-10, 52,8 cr

- [x] Tablas y esquemas Stellar en Dune, con particiones (`closed_at_date` en todas las history_*).
- [x] Cómo emite eventos cada protocolo y dónde va el usuario (`docs/modelo-de-datos.md`).
- [x] Registro de contratos (`protocols.yml`) desde stellar.expert, docs oficiales y factories.
- [x] Pools: Blend 15 v1 + 12 v2 (storage de factories), Phoenix 14 (storage), Aquarius 400 (`data/`).
- [x] Prototipos de 30 días de las seis queries de actividad, sin usuarios nulos.

### Paso 1: queries de actividad, capa viva (estimado 30 cr)

Una query por protocolo, no temporal, ventana `closed_at_date >= current_date - 45 días`, con el
esquema normalizado. Se ejecuta, se mide, se guarda en `queries/<protocolo>/`. Todavía sin matview.

- [ ] Blend (pools desde storage de las 2 factories + 2 backstops)
- [ ] Aquarius (3 routers)
- [ ] Soroswap (pares desde storage de la factory + 10 aggregators)
- [ ] Phoenix (pools desde storage de la factory, dos formatos de evento)
- [ ] FxDAO (operaciones a vaults y locking pool)
- [ ] Etherfuse (path payments, payments, trades del issuer)

### Paso 2: archives, uno por día (estimado 240 cr) ⏸ requiere OK de Esteban

Misma query sin el filtro de ventana, `is_temp: false`, matview `result_scf_<p>_activity_archive`
con cron `0 3 1 * *`. Se crea, se espera la primera ejecución, se anota el costo real.

- [ ] Etherfuse (operaciones, el más barato: prueba el patrón)
- [ ] FxDAO
- [ ] Phoenix
- [ ] Blend
- [ ] Soroswap
- [ ] Aquarius (el de más filas)

### Paso 3: capa viva apuntada al archive y unión (estimado 20 cr)

- [ ] Reescribir cada query viva: `closed_at > (SELECT MAX(closed_at) FROM archive)` más la poda
      `closed_at_date >= current_date - 75 días`. Matview `result_scf_<p>_activity`, cron `0 5 * * *`.
- [ ] `SCF35 · activity (all protocols)`: UNION ALL de las 12 matviews. Matview `result_scf_activity`, cron `0 6 * * *`.

### Paso 4: métricas y dashboard (estimado 30 cr)

Todas leen solo `result_scf_activity`. Cada una con matview y cron `30 6 * * *`.

- [ ] WAU y MAU por protocolo (wallets G y contratos C por separado)
- [ ] WAU y MAU por rol, por protocolo
- [ ] Nuevos vs recurrentes por semana y por mes, con primera aparición por (protocolo, usuario)
- [ ] Crecimiento semana a semana y mes a mes
- [ ] Salud: último evento por protocolo y edad del dato
- [ ] Dashboard público `dune.com/paltalabs/stellar-defi` con texto de metodología y links a este repo
- [ ] Reporte de la tranche: qué se entregó, links, costos, y lo que quedó fuera

## Entregable 2: solapamiento de usuarios (Tranche 2, USD 3.333)

Sale de `result_scf_activity` sin escanear nada nuevo: matriz protocolo × protocolo de usuarios
compartidos, primer protocolo de cada wallet, viajes entre protocolos. Costo esperado < 30 cr.

## Entregable 3: actividad de LPs (Tranche 2, USD 5.000)

Necesita precios en USD. Se hace una tabla diaria propia acotada a los tokens que aparecen en la
actividad LP (patrón de `dune-dashboards`: 8 assets 1,35 cr/día). LPs activos, top LPs, valor por
transacción. Las columnas `token_*` y `amount_*` ya están en la actividad.

## Entregable 4: flujos y migraciones de liquidez (Tranche 3, USD 8.333)

Entradas y salidas por protocolo y pool desde `add`/`remove`, `deposit`/`withdraw`,
`provide_liquidity`/`withdraw_liquidity`, `supply`/`withdraw`. Migración: misma wallet retira en
un protocolo y deposita en otro dentro de una ventana. Todo desde `result_scf_activity` más precios.

## Lo que la submission promete y acá se hace distinto

- **"Runs every 6 hours".** El diseño refresca los datos crudos una vez al día y las métricas
  una vez al día. Pasar las métricas a 6 h cuesta ~600 cr/mes más y no cambia lo que se ve, porque
  los datos de abajo son diarios. Decidir antes de cerrar la tranche y decirlo en el reporte.
- **Usuarios = direcciones.** Un contrato que opera (bot, vault de DeFindex, el aggregator) cuenta
  como usuario del protocolo que toca. Se muestra separado de las wallets G para no inflar.
- **Soroswap.** Los usuarios salen de los eventos de los pares (cubre router y llamadas directas)
  más el aggregator. Los usuarios del aggregator por el canal SDEX (memo) quedan fuera de T1;
  están medidos en `dune-dashboards` si hace falta sumarlos.
- **FxDAO** está casi inactivo (decenas de operaciones por mes). Se incluye igual y se dice.
- **Etherfuse** no es un protocolo Soroban: se mide como asset clásico (path payments, trades,
  redeems al issuer).
