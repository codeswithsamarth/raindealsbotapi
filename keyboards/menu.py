from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛍 Products", callback_data="products_menu", style="primary")]
        ]
    )


def get_admin_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛍 Products", callback_data="products_menu", style="primary")],
            [InlineKeyboardButton(text="👑 Admin", callback_data="admin_panel", style="danger")],
        ]
    )
