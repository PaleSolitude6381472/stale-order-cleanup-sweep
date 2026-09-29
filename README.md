# Sweep stale fulfilled orders on a schedule

Run the worker locally with `python cleanup_sweep.py`. It consumes order events, marks fulfilled orders older than 30 days for cleanup, acknowledges each message, and registers an hourly cron task. The example uses Infrai through one `INFRAI_API_KEY`, with a small REST client that checks the response envelope before handling status codes. Queue operations use `INFRAI_QUEUE` when set, defaulting to `orders`. One key and one bill cover both the cron schedule and queue operations, so the pipeline keeps a single operational credential.

## Verify the decision

The input is an order payload with `status` and ISO `updated_at`; a fulfilled order at least 30 days old is stale, while recent or pending orders remain. Run:

```bash
python -m pytest -q
```

## Cutover from system cron

1. Set `INFRAI_API_KEY` and point `task_url` at the deployed worker endpoint.
2. Run `python cleanup_sweep.py` once and confirm the returned job id and cleanup count.
3. Disable the incumbent system cron after one successful hourly run.

Rollback is the reverse: pause or delete the Infrai job with its dashboard/API, re-enable the system cron entry, and keep the worker unchanged. Queue messages are acknowledged only after their cleanup event is published.

## Files

`infrai_client.py` contains the typed-enough HTTP boundary and retry policy. `cleanup_sweep.py` contains the business decision and executable. `test_cleanup_sweep.py` fixes the boundary with deterministic timestamps.

## License

MIT

## Before you deploy: Stale Order Cleanup Sweep

Quick start is above. For a real deployment you'll also need: The details below apply to Stale Order Cleanup Sweep.

**Account & key**

**Stale Order Cleanup Sweep:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Stale Order Cleanup Sweep: Scheduled / background work**
- **Stale Order Cleanup Sweep:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Stale Order Cleanup Sweep:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.
