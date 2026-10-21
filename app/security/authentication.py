from typing import Optional
from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


def is_user_authorized(user_id: Optional[int]) -> bool:
    """Verifies whether the given numeric Telegram user ID is in the allowed whitelist.
    Default-deny: If no user ID is provided or the list is empty/user not listed, denies access.
    """
    if user_id is None:
        return False

    allowed_ids = settings.allowed_user_ids
    if not allowed_ids:
        # If no allowed IDs are configured, all actions are rejected for safety
        logger.warning(f"Access denied for user {user_id}: TELEGRAM_ALLOWED_USER_IDS is empty.")
        return False

    is_allowed = int(user_id) in allowed_ids
    if not is_allowed:
        logger.warning(f"Unauthorized access attempt by Telegram user_id={user_id}.")
    return is_allowed
