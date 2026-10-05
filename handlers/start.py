# handlers/start.py — FULLY FIXED + MAX SPEED + EXACT WALLET BALANCE

import asyncio
import logging
import uuid
from types import SimpleNamespace

from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import SessionLocal, transaction, retry_on_write_conflict
from models.user import User
from config import ADMIN_IDS

from keyboards.menu import get_main_menu, get_admin_main_menu
from utils.ui import show

# Membership check
from middleware.membership import check_user_membership, get_join_keyboard

logger = logging.getLogger(__name__)

router = Router()


def generate_ref_code() -> str:
    return uuid.uuid4().hex[:8].upper()


# ╔══════════════════════════════════════════════════════════════╗
# ║  MODERN /start BUILDER — TERMINAL STYLE                     ║
# ╚══════════════════════════════════════════════════════════════╝

def _build_start_welcome(user, full_name: str) -> str:
    """A single lightweight welcome card for the main menu."""
    return "<blockquote>🛍 <b>Welcome to Rain Store Bot!</b></blockquote>"


# ╔══════════════════════════════════════════════════════════════╗
# ║  CALLBACK HANDLERS                                         ║
# ╚══════════════════════════════════════════════════════════════╝

@router.callback_query(F.data == "main_menu")
async def main_menu_cb(callback: CallbackQuery, state: FSMContext):
    """Back to main menu — edits the current message."""
    await state.clear()

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            await callback.answer("User not found.", show_alert=True)
            return

        text = _build_start_welcome(user, callback.from_user.full_name)
        is_admin = callback.from_user.id in ADMIN_IDS
        keyboard = get_admin_main_menu() if is_admin else get_main_menu()

        await show(callback, text, reply_markup=keyboard, parse_mode="HTML")
    finally:
        db.close()

    await callback.answer()


# ╔══════════════════════════════════════════════════════════════╗
# ║  MEMBERSHIP RETRY CALLBACK                                 ║
# ╚══════════════════════════════════════════════════════════════╝

@router.callback_query(F.data == "check_membership_retry")
async def retry_membership_check(callback: CallbackQuery):
    """Run a fresh check after a user joins a required chat."""
    is_member = await check_user_membership(
        callback.bot,
        callback.from_user.id,
        force_refresh=True,
    )

    if is_member:
        await callback.message.delete()
        await callback.message.answer(
            "✅ <b>Verification Successful!</b>\n\n"
            "Send /start to begin using the bot.",
            parse_mode="HTML"
        )
        await callback.answer("✅ Verified! Send /start", show_alert=True)
    else:
        await callback.answer(
            "❌ Membership is not active yet. Join every required chat, then try again.",
            show_alert=True
        )


# ╔══════════════════════════════════════════════════════════════╗
# ║  USER CREATION                                             ║
# ╚══════════════════════════════════════════════════════════════╝

@retry_on_write_conflict(max_attempts=3)
def _get_or_create_user(telegram_id: int, username: str, full_name: str, ref_payload: str) -> dict:
    with transaction() as db:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        is_new = False
        referral_bonus = False

        if not user:
            is_new = True
            referred_by = None

            if ref_payload:
                referrer = (
                    db.query(User)
                    .filter(User.referral_code == ref_payload)
                    .with_for_update()
                    .first()
                )
                if referrer is not None and referrer.telegram_id != telegram_id:
                    referred_by = referrer.telegram_id
                    referrer.total_referrals = (referrer.total_referrals or 0) + 1
                    referral_bonus = True

            user = User(
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
                balance=0,
                referral_code=generate_ref_code(),
                referred_by=referred_by,
                total_referrals=0,
                referral_earnings=0,
                total_orders=0,
                total_spent=0,
                total_deposited=0,
                is_banned=False,
            )
            db.add(user)
            db.flush()
        else:
            user.username = username
            user.full_name = full_name

        return {
            "is_new": is_new,
            "referral_bonus": referral_bonus,
            "referral_code": user.referral_code,
            "referred_by": getattr(user, "referred_by", None),
            # Return the dashboard values from the same transaction. This
            # removes the second remote database query from every /start.
            "profile": {
                "balance": user.balance,
                "total_orders": user.total_orders,
                "total_referrals": user.total_referrals,
            },
        }


# ╔══════════════════════════════════════════════════════════════╗
# ║  /start COMMAND — With Membership Check                     ║
# ╚══════════════════════════════════════════════════════════════╝

@router.message(CommandStart())
async def start_cmd(message: Message, command: CommandObject):
    telegram_id = message.from_user.id
    start_payload = (command.args or "").strip() if command else ""
    deep_link_product_id = None
    if start_payload.startswith("product_"):
        product_id_text = start_payload.removeprefix("product_")
        if product_id_text.isdigit():
            deep_link_product_id = int(product_id_text)

    # ═══════════════════════════════════════════════════════
    # CHANNEL MEMBERSHIP CHECK (skip for admins)
    # ═══════════════════════════════════════════════════════
    if telegram_id not in ADMIN_IDS:
        is_member = await check_user_membership(
            message.bot,
            telegram_id,
            fast=deep_link_product_id is not None,
        )
        if not is_member:
            await message.answer(
                "⚠️ <b>Access Restricted</b>\n\n"
                "You must join every required chat to use the bot.\n\n"
                "👇 Join below, then press <b>Try Again</b>",
                reply_markup=get_join_keyboard(),
                parse_mode="HTML"
            )
            return

    username = message.from_user.username
    full_name = message.from_user.full_name
    ref_payload = "" if deep_link_product_id is not None else start_payload
    is_admin = telegram_id in ADMIN_IDS

    db_task = asyncio.to_thread(
        _get_or_create_user, telegram_id, username, full_name, ref_payload
    )

    try:
        result = await db_task
    except Exception:
        logger.exception("Failed to create/update user %s on /start", telegram_id)
        await message.answer(
            "❌ <b>Startup Error</b>\n\nSomething went wrong starting your session.\nPlease try again with /start",
            parse_mode="HTML"
        )
        return

    user = SimpleNamespace(**result["profile"])
    if deep_link_product_id is not None:
        from handlers.products import product_info

        await product_info(message, deep_link_product_id)
        return

    text = _build_start_welcome(user, full_name)
    keyboard = get_admin_main_menu() if is_admin else get_main_menu()
    await message.answer(
        text, reply_markup=keyboard, parse_mode="HTML",
        disable_web_page_preview=True
    )
