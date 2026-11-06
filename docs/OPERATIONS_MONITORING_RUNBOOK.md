# Operations, monitoring and incident runbook

## Operating state

The Trader repository is a research and paper-signal system. Its committed promotion gate must remain `RESEARCH_HOLD`, `promotion_eligible: false`, and `live_execution_enabled: false` until every evidence and independent-review requirement is satisfied. A green CI run is not evidence of a profitable strategy and does not authorize orders.

## Daily monitoring

The weekday Daily Trader Signals workflow runs the pipeline and then invokes:

```bash
python -m trader.monitoring
```

The monitor writes `data/reports/monitoring.json`. The workflow uploads both that report and `data/reports/data_integrity.json` as a 90-day artifact, including when an earlier pipeline step fails.

The report contains:
- data-integrity, point-in-time membership and corporate-action evidence checks;
- latest signal schema, probability bounds and research-only label checks;
- alignment between the latest signal date and the latest date in the configured-symbol price audit;
- probability-mean shift monitoring when at least 40 distinct prediction sessions exist (latest 20 versus preceding 20, warning threshold 0.10);
- accuracy versus the majority-class baseline;
- SHA-256 hashes for the monitoring inputs and the GitHub Actions code revision.

### Status meanings

- `HEALTHY`: no operational errors or evidence warnings were detected. This is not a promotion pass.
- `RESEARCH_HOLD`: monitor ran, but one or more research/data warnings remain or drift history is insufficient.
- `ALERT`: malformed/missing critical inputs, unsafe signal labels, or a promotion/live-execution invariant violation. The monitor exits non-zero and the workflow fails.

The probability-shift check is a lightweight alert, not a calibrated statistical drift test. It does not detect every feature, label, regime or concept drift. It reports `INSUFFICIENT_HISTORY` until 40 distinct sessions are available. Do not interpret missing drift evidence as a pass.

## Incident response

1. Open the failed Daily Trader Signals run and inspect the first failing step.
2. Download the `trader-monitoring-reports-<run id>` artifact. Preserve the JSON files with the run URL and commit SHA.
3. If `data_integrity.json` reports missing or invalid prices, do not bypass the pipeline guard or publish new signals. Investigate source/vendor coverage, exchange calendar, symbol identity and corporate-action history.
4. If the monitoring report is `ALERT`, inspect the named check and restore the research-only signal and promotion invariants before rerunning.
5. If membership or corporate-action checks are incomplete, retain `RESEARCH_HOLD`; do not populate intervals or adjustment factors from guesses.
6. If generated-artifact publication races with a newer `main`, rerun the workflow. The publisher must rebuild on the latest `main`; never force-push or line-merge model binaries.
7. Record the incident, root cause, affected run IDs, remediation commit and verification run in the repository's audit trail.

## Recovery and rollback

- Revert a faulty code/configuration commit through a normal reviewed Git commit; do not rewrite shared history.
- Preserve failed-run artifacts before rerunning so the failure remains auditable.
- Re-run CI and the affected workflow after a fix. Verify the new run's commit SHA and each relevant step conclusion.
- Do not restore old generated model binaries or signals onto a newer code revision without rebuilding them.
- If a monitoring change causes false alerts, fix the check and add a regression test; do not silence the workflow or remove the artifact retention step.
- No automated rollback to live trading exists because live execution is disabled.

## Paper trading and approvals

Prospective paper trading has not been started. It remains blocked until the point-in-time universe, historical prices, corporate-action lineage, broker costs, locked walk-forward validation and independent research review pass. The paper ledger must record timestamped signals, intended orders, fills/rejections, costs, slippage and daily mark-to-market. A 60–90-session operational observation period does not by itself prove statistical edge.

Independent promotion approval must be supplied by an authorized reviewer and recorded with identity, date, scope and evidence references. This runbook or a passing monitor must never be treated as that approval.

## Dashboard and notifications

The machine-readable monitoring report and GitHub Actions artifact are the current observability surface. A persistent dashboard and external Telegram/email alert integration are not implemented. GitHub Actions run notifications are the current failure-notification mechanism, subject to repository/user notification settings. Do not claim external alerts are configured.
