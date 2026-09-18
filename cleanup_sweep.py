from datetime import datetime, timezone

from infrai_client import InfraiClient


def is_stale(order: dict, now: datetime, ttl_days: int = 30) -> bool:
    updated = datetime.fromisoformat(order["updated_at"].replace("Z", "+00:00"))
    return order.get("status") == "fulfilled" and (now - updated).days >= ttl_days


def run_sweep(client: InfraiClient, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    removed = 0
    for message in client.consume(max_messages=100, visibility_timeout=60):
        order = message["payload"]
        if is_stale(order, now):
            client.publish({"order_id": order["order_id"], "event": "cleanup"}, key=f"cleanup:{order['order_id']}")
            removed += 1
        client.ack(message["message_id"])
    return removed


def schedule(client: InfraiClient, task_url: str) -> str:
    return client.create_cron("0 * * * *", task_url)


if __name__ == "__main__":
    client = InfraiClient()
    job_id = schedule(client, "https://example.com/cleanup-sweep")
    print(f"scheduled cleanup sweep: {job_id}")
    print(f"cleaned orders: {run_sweep(client)}")
