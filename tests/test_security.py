import pytest
from app.config import settings
from app.security.authentication import is_user_authorized
from app.security.encryption import TokenEncryptor
from app.security.rate_limits import UserRateLimiter, CostBudgetTracker
from app.security.url_safety import is_safe_url


def test_url_safety_ssrf_blocking():
    # Localhost and loopback
    safe, _ = is_safe_url("http://localhost:8000/secret")
    assert not safe

    safe, _ = is_safe_url("http://127.0.0.1/admin")
    assert not safe

    # Private IP ranges
    safe, _ = is_safe_url("http://192.168.1.1/router")
    assert not safe

    safe, _ = is_safe_url("http://10.0.0.5/internal")
    assert not safe

    # Cloud metadata
    safe, _ = is_safe_url("http://metadata.google.internal/computeMetadata/v1/")
    assert not safe

    # Unsupported schemes
    safe, _ = is_safe_url("file:///etc/passwd")
    assert not safe

    safe, _ = is_safe_url("ftp://example.com/file")
    assert not safe

    # Safe external URL
    safe, reason = is_safe_url("https://example.com")
    assert safe, f"Expected safe URL but got reason: {reason}"


def test_token_encryption():
    encryptor = TokenEncryptor()
    secret = "ya29.a0AfH6SMD_very_secret_oauth_token"
    
    encrypted = encryptor.encrypt(secret)
    assert encrypted != secret
    assert len(encrypted) > len(secret)

    decrypted = encryptor.decrypt(encrypted)
    assert decrypted == secret

    # Empty string handling
    assert encryptor.encrypt("") == ""
    assert encryptor.decrypt("") == ""


def test_user_authorization():
    settings.TELEGRAM_ALLOWED_USER_IDS = [12345, 67890]
    
    assert is_user_authorized(12345) is True
    assert is_user_authorized(67890) is True
    assert is_user_authorized(99999) is False
    assert is_user_authorized(None) is False


def test_rate_limiter():
    limiter = UserRateLimiter(max_requests_per_minute=3)
    user_id = 42

    assert limiter.is_allowed(user_id) is True
    assert limiter.is_allowed(user_id) is True
    assert limiter.is_allowed(user_id) is True
    # 4th request in the same window should be blocked
    assert limiter.is_allowed(user_id) is False


def test_cost_budget_tracker():
    tracker = CostBudgetTracker()
    settings.DAILY_MODEL_BUDGET = 1.0

    exceeded, _ = tracker.is_budget_exceeded()
    assert not exceeded

    tracker.record_cost(0.50)
    exceeded, _ = tracker.is_budget_exceeded()
    assert not exceeded

    tracker.record_cost(0.60)
    exceeded, reason = tracker.is_budget_exceeded()
    assert exceeded
    assert "Daily budget reached" in reason
