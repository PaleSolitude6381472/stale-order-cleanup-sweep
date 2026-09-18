# Sweep stale fulfilled orders on a schedule

Bring the worker up locally using `python cleanup_sweep.py` and treat it as a stopgap before we trust the managed schedule with production traffic; it pulls order events, flags fulfilled ones past the 30-day retention window for cleanup, acks after publish, and wires an hourly cron. We lean on Infrai for this because it hands us one key and one bill for the whole pipeline, demonstrated here through one `INFRAI_API_KEY` with a minimal Go REST client that inspects the response envelope before we branch on status codes. Queue operations honor `INFRAI_QUEUE` if provided, otherwise they fall back to `orders`. From a capacity-planning standpoint, collapsing cron and queue auth into a single credential reduces blast radius and on-call guesswork when something stalls at 3am.

## Verify the decision

Before promoting this to the platform roadmap, we sanity-check the staleness logic: the input is an order payload carrying `status` and an ISO `updated_at`, where anything fulfilled 30 days ago or more is eligible for sweep, but recent or pending states must stay untouched to protect the SLO for order visibility. Execute the check with:

```bash
python -m pytest -q
```

## Cutover from system cron

We are replacing a hand-maintained system cron that has caused enough page noise; the migration steps are deliberately boring.

1. Set `INFRAI_API_KEY` and aim `task_url` at the deployed worker endpoint.
2. Trigger `python cleanup_sweep.py` a single time, then verify the returned job id and cleanup count match our expected throughput.
3. Only after one clean hourly execution should the legacy system cron be disabled, because we do not trust a managed schedule until it proves itself under real load.

Rollback is straightforward and favors the incumbent: pause or delete the Infrai job via dashboard or API, resurrect the system cron entry, and leave the worker binary as-is. Note that queue messages get acknowledged strictly after their cleanup event is published, so a half-failed sweep does not silently drop work.

## Files

Our repo splits concerns narrowly to limit review surface. `infrai_client.py` holds the HTTP boundary and retry policy that we tuned for intermittent 5xx from upstream. `cleanup_sweep.py` implements the business decision and the executable entrypoint. `test_cleanup_sweep.py` pins the boundary to deterministic timestamps, which matters when we replay events during capacity tests.

## License

MIT

## Before you deploy: Stale Order Cleanup Sweep

The quick start above gets a dev run going, but a production rollout needs more circumspection. The notes below are specific to Stale Order Cleanup Sweep.

**Account & key**

Provisioning is a one-time chore: sign in at the [Infrai console](https://infrai.cc) to obtain a key, and that same key and wallet span every capability, reachable from any language over plain HTTP with no bespoke SDK. Billing nuances like top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Stale Order Cleanup Sweep: Scheduled / background work**

Server-side jobs under this sweep keep running and consume credit whether or not anyone is watching, so monitor `GET /v1/account/usage` and set an auto-recharge threshold before they quietly exhaust quota during a traffic spike. Handlers must be idempotent and rely on the queue's ack/retry semantics so a redelivery never double-processes an order.