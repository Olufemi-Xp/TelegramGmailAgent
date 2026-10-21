import time
from collections import defaultdict
from typing import Dict, List
from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


class UserRateLimiter:
    """In-memory rate limiter using sliding window of timestamps."""

    def __init__(self, max_requests_per_minute: int = 30):
        self.max_requests = max_requests_per_minute
        self.user_history: Dict[int, List[float]] = defaultdict(list)

    def is_allowed(self, user_id: int) -> bool:
        now = time.time()
        window_start = now - 60.0
        
        # Clean older requests outside the 1-minute window
        timestamps = [ts for ts in self.user_history[user_id] if ts > window_start]
        self.user_history[user_id] = timestamps

        if len(timestamps) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for user {user_id}: {len(timestamps)} requests in last 60s.")
            return False

        self.user_history[user_id].append(now)
        return True


class CostBudgetTracker:
    """Tracks daily and monthly estimated cost against configured limits."""

    def __init__(self):
        self.daily_cost: float = 0.0
        self.monthly_cost: float = 0.0
        self.current_day: int = time.gmtime().tm_yday
        self.current_month: int = time.gmtime().tm_mon

    def _refresh(self):
        now_struct = time.gmtime()
        if now_struct.tm_yday != self.current_day:
            self.daily_cost = 0.0
            self.current_day = now_struct.tm_yday
        if now_struct.tm_mon != self.current_month:
            self.monthly_cost = 0.0
            self.current_month = now_struct.tm_mon

    def record_cost(self, cost_usd: float):
        self._refresh()
        self.daily_cost += cost_usd
        self.monthly_cost += cost_usd

    def is_budget_exceeded(self) -> tuple[bool, str]:
        self._refresh()
        if self.daily_cost >= settings.DAILY_MODEL_BUDGET:
            return True, f"Daily budget reached (${self.daily_cost:.2f} / ${settings.DAILY_MODEL_BUDGET:.2f})."
        if self.monthly_cost >= settings.MONTHLY_MODEL_BUDGET:
            return True, f"Monthly budget reached (${self.monthly_cost:.2f} / ${settings.MONTHLY_MODEL_BUDGET:.2f})."
        return False, ""


rate_limiter = UserRateLimiter()
budget_tracker = CostBudgetTracker()
