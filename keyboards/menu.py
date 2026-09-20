from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu() -> InlineKeyboardMarkup:
    """Return the streamlined customer interface for product and API use."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛍 Products", callback_data="products_menu")],
            [InlineKeyboardButton(text="📦 Orders", callback_data="orders_menu")],
            [InlineKeyboardButton(text="🔑 API Access", callback_data="api_key_menu")],
        ]
    )


def get_admin_main_menu() -> InlineKeyboardMarkup:
    """Return the streamlined interface with the administrator entry point."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛍 Products", callback_data="products_menu")],
            [InlineKeyboardButton(text="📦 Orders", callback_data="orders_menu")],
            [InlineKeyboardButton(text="🔑 API Access", callback_data="api_key_menu")],
            [InlineKeyboardButton(text="👑 Admin", callback_data="admin_panel")],
        ]
    )
