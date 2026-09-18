from datetime import datetime, timezone

from cleanup_sweep import is_stale


def test_only_old_fulfilled_orders_are_stale():
    now = datetime(2026, 9, 3, tzinfo=timezone.utc)
    old = {"status": "fulfilled", "updated_at": "2026-07-01T00:00:00Z"}
    recent = {"status": "fulfilled", "updated_at": "2026-08-20T00:00:00Z"}
    pending = {"status": "pending", "updated_at": "2026-01-01T00:00:00Z"}
    assert is_stale(old, now)
    assert not is_stale(recent, now)
    assert not is_stale(pending, now)
