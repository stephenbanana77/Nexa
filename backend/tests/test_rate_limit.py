"""Rate limiter tests."""
from middleware import RateLimiter


def test_rate_limiter_allows_requests():
    rl = RateLimiter()
    for _ in range(5):
        assert rl.check_general("user1")


def test_rate_limiter_blocks_after_limit():
    rl = RateLimiter()
    for _ in range(60):
        rl.check_general("user2")
    assert not rl.check_general("user2")


def test_rate_limiter_chat_separate_bucket():
    rl = RateLimiter()
    # Fill general bucket
    for _ in range(60):
        rl.check_general("user3")
    # Chat should still work (separate bucket)
    assert rl.check_chat("user3")


def test_rate_limiter_upload_separate_bucket():
    rl = RateLimiter()
    for _ in range(60):
        rl.check_general("user4")
    assert rl.check_upload("user4")


def test_rate_limiter_per_user_isolation():
    rl = RateLimiter()
    for _ in range(60):
        rl.check_general("user5")
    assert rl.check_general("user6")  # Different user unaffected
