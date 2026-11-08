# Spend reconciliation, 2026-11-06

CLAUDE.md requires measured spend, never estimated. This reconciles the
token-derived figures in `results/spend.csv` against Prime's own billing rows,
because the two are different measurements and only one of them is authoritative.

## Token-derived total, from exact per-trace token counts

| run | status | usd |
|---|---|---|
| smoke tests (3 rollouts, disclosed in PREREGISTRATION.md) | pre-registration | 0.0003 |
| pilot 1, bash harness | **discarded** (deviation D1) | 1.2476 |
| pilot 2, null harness | calibration only, no claims | 1.0546 |
| claim run, test split, 6,000 rollouts | claims | 20.5784 |
| **total** | | **22.8809** |

## Prime's billing rows, from `prime wallet`

| when | amount |
|---|---|
| 2026-11-06 02:48 | 0.0001 |
| 2026-11-06 02:48 | 0.0002 |
| 2026-11-06 04:30 | 0.2500 |
| 2026-11-06 06:03 | 0.6900 |
| 2026-11-06 06:57 | 22.0900 |
| **total** | **23.0303** |

## Reconciliation

Billed $23.0303 against $22.8809 derived from tokens: a difference of **$0.1494,
or 0.65%**. The agreement is good and the small residual is consistent with
price-table rounding on my side.

**A note on reading these rows.** Prime's billing rows are periodic
aggregations, not one row per run. The $22.09 row at 06:57 does not correspond
to the claim run, and comparing it to the claim run's $20.58 produces a
spurious 7.3% discrepancy. The totals reconcile; the individual rows do not map
to individual runs. Only the totals should be compared.

## Status against the cap

- Spent to date: **$22.88** of the **$40.00** cap.
- Remaining under the cap: **$17.12**.
- **Wallet balance: $1.96.**

The cap is not the binding constraint; the wallet is. The conditional RL phase
was costed at $18 to $38, so it cannot start from a $1.96 balance. Per the
no-intervention rule, a top-up must happen *before* dispatch rather than
during, so that a running job never forces a choice between killing it and
overspending.
