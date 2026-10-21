from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔍 Research", callback_data="action_search"),
                InlineKeyboardButton(text="🧠 Memory", callback_data="action_memory"),
            ],
            [
                InlineKeyboardButton(text="💼 Jobs", callback_data="action_jobs"),
                InlineKeyboardButton(text="✉️ Gmail", callback_data="action_gmail"),
            ],
            [
                InlineKeyboardButton(text="⏰ Tasks", callback_data="action_tasks"),
                InlineKeyboardButton(text="📊 Status", callback_data="action_status"),
            ],
        ]
    )


def get_memory_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📄 My Documents", callback_data="mem_list_docs"),
                InlineKeyboardButton(text="🧹 Clear Summary", callback_data="mem_clear_summary"),
            ],
        ]
    )


def get_confirmation_keyboard(action_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Confirm", callback_data=f"confirm_{action_id}"),
                InlineKeyboardButton(text="❌ Cancel", callback_data=f"cancel_{action_id}"),
            ]
        ]
    )
