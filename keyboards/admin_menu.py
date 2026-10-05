from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_admin_panel():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📦 Products", callback_data="admin_products", style="primary"),
                InlineKeyboardButton(text="📋 Orders", callback_data="admin_orders", style="success"),
            ],
            [InlineKeyboardButton(text="🛠 Maintenance Mode", callback_data="maintenance_mode", style="danger")],
            [InlineKeyboardButton(text="⬅ Back", callback_data="admin_back")],
        ]
    )
