# Minuta Tranche 1: Weekly & Monthly Active Users

SCF #35, Stellar DeFi Dune Dashboards. Entregable 1 (USD 8.333).
Fecha de cierre técnico: 2026-09-22. Estado: construido y validado en Dune; dashboard **privado**
a la espera de revisión y publicación.

- Dashboard: https://dune.com/paltalabs/stellar-defi
- Repositorio: https://github.com/paltalabs/stellar-defi-dune-dashboard
- Submission: `scf/submission-scf35.md`. Plan y gasto: `plan.md`. Operación: `docs/runbook.md`.
  Esquema y reglas de atribución: `docs/modelo-de-datos.md`.

## 1. Qué pedía la SCF y qué se entrega

| Pide la submission | Entregado | Dónde se ve |
|---|---|---|
| Wallets únicas por período | WAU y MAU del ecosistema, direcciones únicas entre los 6 protocolos, separando cuentas G y contratos C | [WAU](https://dune.com/queries/8797598/12827594), [MAU](https://dune.com/queries/8797599/12827595) |
| Desglose por protocolo | WAU y MAU de Blend, Aquarius, Soroswap, Phoenix, FxDAO y Etherfuse | [WAU](https://dune.com/queries/8796719/12826611), [MAU](https://dune.com/queries/8796720/12826616) |
| Segmentación por acción (swappers, LPs, aggregator users, lenders, borrowers, liquidators) | WAU y MAU por rol, más claimers, backstop providers, vault owners, minters, redeemers, holders y traders | [WAU por rol](https://dune.com/queries/8796721/12826614), [MAU por rol](https://dune.com/queries/8796722/12826620) |
| Nuevos vs recurrentes | Por semana y por mes | [semanal](https://dune.com/queries/8796719/12826613), [mensual](https://dune.com/queries/8796720/12826619) |
| Tasa de crecimiento semanal y mensual | WoW y MoM por protocolo, solo entre períodos completos | [WoW](https://dune.com/queries/8796719/12826612), [MoM](https://dune.com/queries/8796720/12826617) |
| Verificable y que se actualice sola | SQL público en Dune y espejado en el repo; matviews con cron; validación diaria | [salud](https://dune.com/queries/8796723/12826621), [validación](https://dune.com/queries/8796540) |
| Protocolos: Blend, FxDAO, Soroswap, Aquarius, Phoenix, Etherfuse | Los 6, con historia desde 2024-02-01 | tabla de salud |

Agregado fuera de lo pedido: tabla de integridad (concentración de la actividad por protocolo),
[8798732](https://dune.com/queries/8798732/12828796).

## 2. Cómo se mide una dirección activa

1. **Qué es un usuario.** Una dirección de Stellar: cuenta clásica (`G...`) o contrato (`C...`).
   Se cuentan las dos porque en Soroban hay smart wallets (contratos) que son personas; los
   gráficos las muestran por separado cuando importa. No se intenta unir direcciones de una
   misma persona.
2. **Qué es actividad.** Una acción de usuario en el protocolo, leída de la cadena:
   swap, agregar o retirar liquidez, supply, withdraw, borrow, repay, liquidación, backstop,
   claim de recompensas, mint, redeem, pagos y trades en el SDEX del asset (Etherfuse). Los
   eventos administrativos se descartan. La tabla completa de acciones y roles por protocolo
   está en `docs/modelo-de-datos.md`.
3. **De dónde sale el usuario en cada acción.**

   | Protocolo | Fuente | Usuario |
   |---|---|---|
   | Blend | eventos de 27 pools y 2 backstops | `from` del evento; en liquidaciones, quien llena la subasta |
   | Aquarius | eventos de 3 routers y 431 pools | usuario del evento del router; en trades directos al pool, quien llama; en depósitos directos (el evento no trae usuario), la cuenta que firma la operación |
   | Soroswap | router, 10 versiones del aggregator y 214 pares; aggregator por el SDEX (transacciones con memo `SoroswapAggregator-<apiUser>` y sus path payments) | campo `to` de cada evento; los pares solo cuentan si la transacción no pasó por router ni aggregator. Por el SDEX: la cuenta que firma la transacción y, si es distinta, el receptor del path payment |
   | Phoenix | eventos de 14 pools | `sender` de cada evento |
   | FxDAO | operaciones a vaults y locking pool | cuenta que invoca |
   | Etherfuse | pagos, ofertas y trades del issuer (asset clásico) | emisor y receptor de pagos; ambas contrapartes de cada trade |

4. **Qué es "activa en un período".** Una dirección está activa en una semana o un mes si tiene
   al menos una acción en ese período. Semanas calendario desde el lunes y meses calendario, en
   UTC. En los gráficos solo aparecen períodos completos.
5. **Nuevos vs recurrentes.** Una dirección es *nueva* en un protocolo en el primer período en
   que aparece en ese protocolo desde 2024-02-01; en los siguientes es *recurrente*. No es la
   fecha de creación de la cuenta.
6. **Crecimiento.** `(activas del período - activas del período anterior) / activas del período
   anterior`, solo cuando los dos períodos están completos.

## 3. Cómo se trata una dirección que usa más de un protocolo

Cada gráfico responde una pregunta distinta, y por eso cuenta distinto:

| Gráfico | Cómo cuenta una dirección que usa Blend y Aquarius en la misma semana |
|---|---|
| WAU/MAU por protocolo | 1 en Blend y 1 en Aquarius. Cada protocolo cuenta sus direcciones; la suma de las barras **no** es el total del ecosistema |
| WAU/MAU del ecosistema | 1. Direcciones únicas entre los 6 protocolos (`COUNT DISTINCT` sobre todo) |
| WAU/MAU por rol | 1 por cada rol que tuvo, únicas entre protocolos. Si fue lender en Blend y swapper en Aquarius, cuenta 1 en lender y 1 en swapper. Si fue swapper en Aquarius y en Soroswap, cuenta 1 en swapper |
| Nuevos vs recurrentes | Pares protocolo-dirección: puede ser nueva en Aquarius y recurrente en Blend la misma semana. La suma entre protocolos está rotulada como tal |
| Tabla de integridad | Por protocolo cuenta en cada uno; la fila "all protocols" la cuenta una vez |

Contratos intermediarios: cuando el aggregator de Soroswap o un router opera en el pool de otro
protocolo, ese pool registra al contrato, no a la persona. La persona se cuenta en el protocolo
donde firmó (por ejemplo, `aggregator_user` en Soroswap) y en el pool aparece como un solo
usuario `C`. Los trades de Aquarius que pasan por su propio router se atribuyen al usuario del
router, no al router. La columna "Actions via routers/aggregators" de la tabla de integridad mide
este efecto: 0,4% de las acciones de Aquarius en los últimos 28 días.

## 4. Arquitectura en Dune

Todo lo recurrente corre solo. Nadie ejecuta queries a mano.

```
lunes 02:00   registro de contratos (se descubren pools nuevos)
lunes 03:00   6 archives: historia desde 2024-02-01 hasta el día 1 del mes
diario 05:00  6 vivas: desde donde termina el archive hasta ayer
diario 08:00  users: grano diario (protocolo, día, dirección, rol) desde las 12 capas
diario 09:00  métricas semanales, mensuales, por rol, salud e integridad
diario 10:00  validación
diario 10:30  queries de gráficos (schedule de Dune)
```

Cada acción queda guardada una vez, en un esquema normalizado igual para los 6 protocolos, con
montos, tokens y pool. Así las tranches 2 y 3 salen de las mismas tablas sin volver a escanear la
cadena.

### Queries y matviews

| Pieza | Query | Matview | Cron |
|---|---|---|---|
| Registro de contratos | [8798252](https://dune.com/queries/8798252) | `result_scf_contracts` | lunes 02:00 |
| Blend archive / viva | [8798463](https://dune.com/queries/8798463) / [8666478](https://dune.com/queries/8666478) | `result_scf_blend_activity_archive` / `_activity` | lunes 03:00 / diario 05:00 |
| Aquarius archive / viva | [8798647](https://dune.com/queries/8798647) / [8666484](https://dune.com/queries/8666484) | `result_scf_aquarius_activity_archive` / `_activity` | lunes 03:00 / diario 05:00 |
| Soroswap archive / viva | [8798502](https://dune.com/queries/8798502) / [8666498](https://dune.com/queries/8666498) | `result_scf_soroswap_activity_archive` / `_activity` | lunes 03:00 / diario 05:00 |
| Phoenix archive / viva | [8798422](https://dune.com/queries/8798422) / [8666499](https://dune.com/queries/8666499) | `result_scf_phoenix_activity_archive` / `_activity` | lunes 03:00 / diario 05:00 |
| FxDAO archive / viva | [8798419](https://dune.com/queries/8798419) / [8666504](https://dune.com/queries/8666504) | `result_scf_fxdao_activity_archive` / `_activity` | lunes 03:00 / diario 05:00 |
| Etherfuse archive / viva | [8798538](https://dune.com/queries/8798538) / [8666506](https://dune.com/queries/8666506) | `result_scf_etherfuse_activity_archive` / `_activity` | lunes 03:00 / diario 05:00 |
| Usuarios (grano diario) | [8796528](https://dune.com/queries/8796528) | `result_scf_users` | diario 08:00 |
| Semanal / mensual | [8796533](https://dune.com/queries/8796533) / [8796534](https://dune.com/queries/8796534) | `result_scf_users_weekly` / `_monthly` | diario 09:00 |
| Roles semanal / mensual | [8796535](https://dune.com/queries/8796535) / [8796538](https://dune.com/queries/8796538) | `result_scf_users_roles_weekly` / `_monthly` | diario 09:00 |
| Salud | [8796531](https://dune.com/queries/8796531) | `result_scf_users_health` | diario 09:00 |
| Integridad | [8798721](https://dune.com/queries/8798721) | `result_scf_integrity` | diario 09:00 |
| Validación | [8796540](https://dune.com/queries/8796540) | `result_scf_users_validation` | diario 10:00 |

### Visualizaciones del dashboard

| Visualización | Link |
|---|---|
| Data coverage and pipeline health | https://dune.com/queries/8796723/12826621 |
| Activity concentration by protocol (last 28 days) | https://dune.com/queries/8798732/12828796 |
| WAU: unique active addresses across all six protocols | https://dune.com/queries/8797598/12827594 |
| MAU: unique active addresses across all six protocols | https://dune.com/queries/8797599/12827595 |
| WAU: weekly active addresses by protocol | https://dune.com/queries/8796719/12826611 |
| MAU: monthly active addresses by protocol | https://dune.com/queries/8796720/12826616 |
| Week-over-week growth by protocol | https://dune.com/queries/8796719/12826612 |
| Month-over-month growth by protocol | https://dune.com/queries/8796720/12826617 |
| New vs returning addresses, weekly | https://dune.com/queries/8796719/12826613 |
| New vs returning addresses, monthly | https://dune.com/queries/8796720/12826619 |
| WAU by role (unique across protocols) | https://dune.com/queries/8796721/12826614 |
| MAU by role (unique across protocols) | https://dune.com/queries/8796722/12826620 |

## 5. Validación y calidad de datos

`result_scf_users_validation` corre cada día. Al 2026-09-22 los 9 checks dan 0 fallos:

| Check | Qué verifica |
|---|---|
| `duplicate_daily_keys` | ninguna combinación (protocolo, día, dirección, rol) repetida |
| `invalid_addresses` | toda dirección tiene formato `G` o `C` de 56 caracteres |
| `invalid_role_or_date` | ninguna fila sin rol o sin fecha |
| `out_of_coverage` | toda fila cae dentro del rango que cubre su capa |
| `missing_protocol_metadata` | los 6 protocolos informan cobertura, aunque no tengan actividad |
| `archive_live_gap` | no hay hueco entre el archive y la capa viva |
| `unregistered_contracts` | el SQL incluye todos los contratos que encontró el registro |
| `cohort_partition_weekly` / `_monthly` | nuevos + recurrentes = activas, y G + C = activas |

Salud al 2026-09-22 (direcciones observadas desde 2024-02-01): Blend 40.382, Aquarius 30.183,
Etherfuse 6.548, Phoenix 5.704, Soroswap 4.192 (2.652 antes de sumar el SDEX), FxDAO 119. Los 6 en estado OK, última
actividad el 2026-09-20 (FxDAO el 2026-09-14).

### Correcciones hechas durante la tranche

- **Soroswap no contaba el aggregator por el SDEX.** Cuando la API del aggregator rutea por el
  SDEX clásico, la operación no emite eventos Soroban y el usuario no aparecía en ningún
  protocolo. Ahora se lee por el memo de la transacción, con el mismo criterio que el dashboard
  de Soroswap en `paltalabs/dune-dashboards`. Desde el primer swap (2025-09-10): 62.038 swaps y
  1.888 direcciones; 970 no aparecían en ningún protocolo. En los últimos 28 días Soroswap pasa
  de 1.051 a 1.256 direcciones y de 35.692 a 61.883 acciones.
- **Aquarius estaba subcontado.** Solo se leían los routers. En una muestra de 7 días, 736 de
  904 depósitos y 71.851 de 113.543 trades ocurrían directo en los pools. Ahora se leen los 431
  pools.
- **31 pools de Aquarius faltaban** en la lista de septiembre. Ahora el registro los descubre
  cada semana y un check avisa si falta alguno en el SQL.
- **Soroswap y Phoenix** fundían varias acciones de una misma transacción en una sola, con un
  solo usuario. Ahora hay una fila por evento.
- **FxDAO verificado:** una sola dirección activa desde junio de 2026. No hubo llamadas a vaults
  ni `mint` de USDx, EURx, GBPx o FXG. Es inactividad real, no un error de la query.
- **Blend verificado:** el 68% de los lenders estuvo activo un solo día y el 85% de las acciones
  de los últimos 28 días vienen de contratos.

### Cómo leer los datos: direcciones no es volumen

En los gráficos Soroswap parecía tener más actividad que Aquarius, aunque Aquarius mueve mucho
más volumen y TVL. Las dos cosas son ciertas a la vez. Últimos 28 días:

| Protocolo | Acciones | % de todas | Direcciones | Direcciones que hacen el 90% | Acciones por dirección |
|---|---|---|---|---|---|
| Etherfuse | 639.414 | 51,0% | 525 | 16 | 1.217,9 |
| Aquarius | 498.371 | 39,8% | 993 | 68 | 501,9 |
| Blend | 78.808 | 6,3% | 2.423 | 21 | 32,5 |
| Soroswap | 35.692 | 2,8% | 1.051 | 672 | 34,0 |
| Phoenix | 1.342 | 0,1% | 43 | 3 | 31,2 |
| FxDAO | 1 | 0,0% | 1 | 1 | 1,0 |
| Todos | 1.253.628 | 100% | 4.793 | 73 | 261,6 |

Tabla medida antes de sumar el SDEX. Con el SDEX, Soroswap tiene 61.883 acciones, 1.256
direcciones y 529 que hacen el 90%; el resto de la lectura no cambia.

Para comparar protocolos se usan las acciones y la concentración, no solo el WAU. El WAU
responde cuánta gente usa un protocolo; unas pocas direcciones (bots de arbitraje y market
making) pueden generar la mayor parte del volumen. El volumen en USD es del Entregable 3.

## 6. Diferencias con la submission y con el diseño original

- **"Runs every 6 hours".** Los datos se refrescan una vez al día. Pasar a 6 horas cuesta más y
  no cambia lo que se ve, porque la cadena de matviews es diaria. Hay que decirlo en el reporte
  a la SCF.
- **Archive mensual.** Dune no acepta crons mensuales en matviews (el máximo es semanal). Los
  archives corren cada lunes y solo escanean la cadena el primer lunes del mes, para agregar el
  mes que cerró. Los demás lunes se copian a sí mismos sin escanear.
- **Gráficos con schedule de Dune.** El refresco de una matview no actualiza lo que muestra su
  query, así que los gráficos cuelgan de queries propias con schedule diario a las 10:30 UTC.
  La API de Dune no puede crear ni leer esos schedules; están listados en `docs/runbook.md`.
  Es la única excepción a la regla 1 del CLAUDE.md.
- **La unión no se materializa.** `result_scf_users` lee directamente las 12 capas, para no
  duplicar ~15 millones de filas.
- **Etherfuse** no es un protocolo Soroban: se mide como asset clásico, y sus usuarios incluyen
  traders del SDEX (bots de market making entre ellos) y holders que transfieren los bonos.

## 7. Costos

Créditos de Dune, engine medium.

| Etapa | Créditos |
|---|---|
| Paso 0 y paso 1 (sondeos y queries de actividad, 2026-09-10) | 103,5 |
| Piloto diario (2026-09-21) | 239,5 |
| Revisión, historia de Aquarius del piloto y Fase 0 (puente) | 225,5 |
| Fase 1: registro de contratos | 82,9 |
| Fase 1: archives con historia completa | 1.135,3 |
| Fase 1: capas vivas | 59,4 |
| Fase 1: usuarios, métricas, integridad, validación y gráficos | 11,6 |
| Fase 1: retiro del piloto, sondeos y lecturas | 26,7 |
| Soroswap: aggregator por el SDEX (sondeos, archive reconstruido, capas y refrescos) | 202,2 |
| **Total construcción** | **2.086,6** |

Detalle de archives: Aquarius 519,4 · Phoenix 331,8 · Etherfuse 117,9 · Blend 87,8 ·
Soroswap 65,4 (150,5 al reconstruirlo con el SDEX) · FxDAO 11,9. El tope inicial era 500 cr; se subió a 2.000 con aprobación, para
cerrar la tranche con historia completa.

**Operación estimada: 1.300 a 1.500 cr/mes** (el presupuesto original era ~950). Las capas vivas
cuestan entre ~5 cr el día 1 del mes y ~60 cr a fin de mes; unos dos tercios son de Aquarius. Se
mide el lunes 2026-09-28 (copia semanal de archives) y el 2026-10-05 (agregado mensual).

## 8. Pendientes para cerrar la tranche

- [ ] Programar en la UI de Dune el schedule diario 10:30 UTC de las 8 queries de gráficos
      (lista en `docs/runbook.md`).
- [ ] Revisar y publicar el dashboard.
- [ ] Commit y push de este trabajo al repo.
- [ ] Reporte a la SCF: links de este documento, la frecuencia diaria en vez de 6 horas y lo
      que queda para las tranches 2 y 3.
- [ ] Decidir con Esteban el costo de operación: optimizar Aquarius y la capa viva de FxDAO o
      aceptarlo.
- [ ] Verificar contra la documentación de Aquarius el orden de los montos en depósitos y
      retiros directos a pools (no afecta el conteo de usuarios; sí el Entregable 3).
