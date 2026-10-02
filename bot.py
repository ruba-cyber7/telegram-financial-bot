import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from dotenv import load_dotenv
from database import init_db, create_user, get_balance, get_db
from trading import trading_router
from flashrouter import flashrouter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import F
import aiosqlite
from decimal import Decimal, InvalidOperation
from aiogram import Router
from aiogram.types import (
    CallbackQuery,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

# ==================== إعدادات البيئة ====================
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

print(f"DEBUG TOKEN: {repr(BOT_TOKEN)}")

if not BOT_TOKEN:
    raise ValueError("⛔ BOT_TOKEN غير موجود!")


# ==================== إعداد Logging ====================
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)
logger = logging.getLogger("bot")
logger.setLevel(getattr(logging, LOG_LEVEL))
formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
)

if not logger.handlers:
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    logger.addHandler(sh)
    fh = logging.FileHandler(logs_dir / "bot.log", encoding="utf-8")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

# ==================== إعداد البوت ====================
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
dp.include_router(trading_router)
dp.include_router(flashrouter)
# ==================== خامساً: الدفع للمواقع الخارجية ====================

external_payment_router = Router()


class ExternalPaymentStates(StatesGroup):
    waiting_for_platform = State()
    waiting_for_destination = State()
    waiting_for_amount = State()


FOREX_PLATFORM = "📈 فوركس Forex"
BINARY_PLATFORM = "📊 باينري Binary"

ALLOWED_PLATFORMS = {
    FOREX_PLATFORM,
    BINARY_PLATFORM,
}

NETWORK_FEE_USDT = Decimal("1.00")
USDT_SCALE = 1_000_000
MAX_AMOUNT = Decimal("5000.00")


def amount_to_minor_units(amount: Decimal) -> int:
    return int(amount * USDT_SCALE)


def is_valid_destination(destination: str) -> bool:
    destination = destination.strip()

    if not destination:
        return False

    if destination.startswith("T") and 25 <= len(destination) <= 35:
        return True

    if destination.startswith("0x") and len(destination) == 42:
        return True

    if destination.startswith(("http://", "https://")):
        return True

    return False


@external_payment_router.callback_query(F.data == "pay_external")
async def start_external_payment(callback: CallbackQuery, state: FSMContext) -> None:

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=FOREX_PLATFORM)],
            [KeyboardButton(text=BINARY_PLATFORM)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    await callback.message.answer(
        "🌐 خامساً: الدفع للمواقع الخارجية\n\n"
        "⚠️ الدفع مسموح فقط لمنصات الفوركس والباينري.\n\n"
        "اختار نوع المنصة:",
        reply_markup=keyboard,
    )

    await state.set_state(ExternalPaymentStates.waiting_for_platform)

    await callback.answer()


@external_payment_router.message(ExternalPaymentStates.waiting_for_platform)
async def process_platform(message: Message, state: FSMContext) -> None:

    platform = (message.text or "").strip()

    if platform not in ALLOWED_PLATFORMS:
        await message.answer("❌ اختار من الأزرار فقط.")
        return

    await state.update_data(platform=platform)

    await message.answer(
        "تمام. الحين أرسل عنوان المحفظة أو رابط الفاتورة:",
        reply_markup=ReplyKeyboardRemove(),
    )

    await state.set_state(ExternalPaymentStates.waiting_for_destination)


@external_payment_router.message(ExternalPaymentStates.waiting_for_destination)
async def process_external_destination(message: Message, state: FSMContext) -> None:

    destination = (message.text or "").strip()

    if not is_valid_destination(destination):
        await message.answer(
            "❌ العنوان غير صالح!\n"
            "يرجى التأكد أن العنوان يتبع TRC20 أو BEP20 "
            "أو أنه رابط فاتورة صحيح."
        )
        return

    await state.update_data(destination=destination)

    await message.answer(
        "💵 أدخل المبلغ المراد دفعه " "(سيتم خصم المبلغ + رسوم الشبكة 1 USDT):"
    )

    await state.set_state(ExternalPaymentStates.waiting_for_amount)


@external_payment_router.message(ExternalPaymentStates.waiting_for_amount)
async def process_external_amount(message: Message, state: FSMContext) -> None:

    raw_amount = (message.text or "").strip().replace(",", ".")

    try:
        amount = Decimal(raw_amount)

        if not amount.is_finite() or amount <= 0 or amount > MAX_AMOUNT:
            raise InvalidOperation

    except (InvalidOperation, ValueError):
        await message.answer(
            f"⚠️ يرجى إدخال رقم صحيح وموجب.\n" f"الحد الأقصى: {MAX_AMOUNT} USDT"
        )
        return

    user_id = message.from_user.id

    amount_minor = amount_to_minor_units(amount)
    network_fee_minor = amount_to_minor_units(NETWORK_FEE_USDT)
    total_required_minor = amount_minor + network_fee_minor

    balance_minor = await get_balance(user_id) or 0


waiting_proof = {}


class AdminStates(StatesGroup):
    waiting_for_password = State()


# ==================== Handlers ====================
# كود زر الإلغاء ومعالجه
cancel_button = InlineKeyboardButton(text="❌ إلغاء", callback_data="cancel_action")
cancel_kb = InlineKeyboardMarkup(inline_keyboard=[[cancel_button]])


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    from database import create_user

    await create_user(message.from_user.id)
    await message.answer(
        f"<b>🔥 أهلاً بك يا RoRo!</b>\nالبوت شغّال وجاهز لأعلى أداء 🟩",
        parse_mode="HTML",
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 فتح المنصة",
                    web_app=WebAppInfo(url="http://localhost:8000/index.html"),
                )
            ]
        ]
    )
    await message.answer("اضغط بالأسفل لفتح الواجهة:", reply_markup=keyboard)
    logger.info(f"User {message.from_user.id} started the bot.")


async def cancel_handler(callback: types.CallbackQuery):
    await callback.message.edit_text("🚫 تم إلغاء العملية.")
    await callback.answer("تم الإلغاء!")


# كيبورد الإيداع مع زر الإلغاء
deposit_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="إيداع", callback_data="deposit")],
        [cancel_button],
    ]
)
# ==================== تشغيل ====================
# قاموس لتتبع من ينتظر إرسال إثبات
waiting_proof = {}


@dp.callback_query(lambda c: c.data in ["net_trc20", "net_bep20"])
async def select_network_handler(callback: types.CallbackQuery, state: FSMContext):
    """معالجة اختيار الشبكة وعرض عنوان المحفظة للتحويل"""

    network_name = "TRC20" if callback.data == "net_trc20" else "BEP20"

    # ضع هنا عناوين المحافظ المصرح لك باستخدامها
    wallet_address = (
        "TRC20_WALLET_ADDRESS" if network_name == "TRC20" else "BEP20_WALLET_ADDRESS"
    )

    # حفظ الشبكة داخل FSM
    await state.update_data(network=network_name)

    # تفعيل انتظار إثبات المستخدم
    waiting_proof[callback.from_user.id] = True

    back_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="deposit")],
            [InlineKeyboardButton(text="❌ إلغاء", callback_data="cancel_action")],
        ]
    )

    await callback.message.edit_text(
        f"<b>📥 شبكة الإيداع المختارة:</b> {network_name}\n\n"
        f"<b>يرجى إرسال المبلغ إلى العنوان التالي:</b>\n"
        f"<code>{wallet_address}</code>\n\n"
        "<b>الخطوة الجاية:</b> ارسل هنا TXID أو صورة التحويل\n"
        "<i>بعد المراجعة سيتم تحديث رصيدك</i>",
        reply_markup=back_keyboard,
        parse_mode="HTML",
    )

    await callback.answer()


@dp.message(F.photo | (F.text & ~F.text.startswith("/")))
async def receive_proof(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    # إذا لم يكن المستخدم بانتظار إثبات
    if user_id not in waiting_proof:
        return

    data = await state.get_data()
    network = data.get("network")

    # حماية إضافية
    if not network:
        waiting_proof.pop(user_id, None)
        await state.clear()

        await message.answer("❌ حصل خطأ بسيط. ارجع واختر الشبكة من جديد.")
        return

    # إيقاف انتظار إثبات جديد
    waiting_proof.pop(user_id, None)

    # النص = TXID، الصورة = file_id
    if message.text:
        txid = message.text.strip()
    else:
        txid = message.photo[-1].file_id

    # تسجيل طلب الإيداع كمعلق للمراجعة
    async with aiosqlite.connect("bot.db") as db:
        await db.execute(
            """
            INSERT INTO deposits
            (user_id, network, txid, status)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, network, txid, "pending"),
        )

        await db.commit()

    # تنظيف حالة FSM
    await state.clear()

    await message.answer("✅ تم استلام طلبك.\n" "ستتم مراجعته قبل تحديث الرصيد.")
    # ==================== لوحة الأدمن (Admin Panel) ====================


@dp.message(Command("admin"))
async def cmd_admin(message: types.Message, state: FSMContext):
    admin_pass = os.getenv("ADMIN_PASSWORD")

    if not admin_pass:
        await message.answer("⚠️ خطأ: لم يتم تعيين كلمة مرور الأدمن في ملف البيئة.")
        return

    await state.set_state(AdminStates.waiting_for_password)

    await message.answer("🔐 يرجى إدخال الرمز السري الخاص بلوحة التحكم:")


@dp.message(AdminStates.waiting_for_password)
async def process_admin_password(message: types.Message, state: FSMContext):
    # حماية ضد إرسال صور أو محتوى بدون نص
    entered_password = (message.text or "").strip()
    admin_pass = os.getenv("ADMIN_PASSWORD")

    await state.clear()

    if entered_password == admin_pass:
        await message.answer("✅ تم تسجيل الدخول بنجاح إلى لوحة التحكم.")
        await show_admin_deposits(message)
    else:
        await message.answer("❌ الرمز السري غير صحيح. تم إلغاء المحاولة.")


async def show_admin_deposits(message: types.Message):
    async with aiosqlite.connect("bot.db") as db:
        async with db.execute(
            """
            SELECT id, user_id, network, txid
            FROM deposits
            WHERE status = ?
            """,
            ("pending",),
        ) as cursor:
            deposits = await cursor.fetchall()

    if not deposits:
        await message.answer("📭 لا توجد طلبات إيداع معلقة حالياً.")
        return

    for dep_id, user_id, network, txid in deposits:
        caption_text = (
            "<b>📦 طلب إيداع جديد!</b>\n"
            f"🆔 صاحب الطلب: <code>{user_id}</code>\n"
            f"🌐 الشبكة: {network}\n"
            f"🔢 رقم الطلب: #{dep_id}\n"
            f"🔑 الإثبات/TXID: <code>{txid}</code>"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ قبول", callback_data=f"approve_{dep_id}"
                    ),
                    InlineKeyboardButton(
                        text="❌ رفض", callback_data=f"reject_{dep_id}"
                    ),
                ]
            ]
        )

        await message.answer(caption_text, reply_markup=keyboard, parse_mode="HTML")
        import logging


from aiogram import F, types
from aiogram.exceptions import TelegramBadRequest


@dp.callback_query(F.data.startswith("approve_") | F.data.startswith("reject_"))
async def handle_deposit_action(callback: types.CallbackQuery):
    if not callback.data:
        await callback.answer("⚠️ بيانات الزر غير صالحة.", show_alert=True)
        return

    action, separator, dep_id_str = callback.data.partition("_")

    if not separator or action not in {"approve", "reject"}:
        await callback.answer("⚠️ إجراء غير صالح.", show_alert=True)
        return

    try:
        dep_id = int(dep_id_str)
    except ValueError:
        await callback.answer("⚠️ رقم الطلب غير صالح.", show_alert=True)
        return

    async with aiosqlite.connect("bot.db") as db:
        await db.execute("BEGIN IMMEDIATE")

        async with db.execute(
            """
            SELECT user_id, amount, network, txid, status
            FROM deposits
            WHERE id = ?
            """,
            (dep_id,),
        ) as cursor:
            deposit = await cursor.fetchone()

        if not deposit:
            await db.rollback()
            await callback.answer("⚠️ الطلب غير موجود.", show_alert=True)
            return

        user_id, amount, network, txid, status = deposit

        if status != "pending":
            await db.rollback()
            await callback.answer(
                "⚠️ تم اتخاذ إجراء مسبق على هذا الطلب.", show_alert=True
            )
            return

        new_status = "approved" if action == "approve" else "rejected"

        cursor = await db.execute(
            """
            UPDATE deposits
            SET status = ?
            WHERE id = ? AND status = 'pending'
            """,
            (new_status, dep_id),
        )

        if cursor.rowcount != 1:
            await db.rollback()
            await callback.answer("⚠️ تم التعامل مع الطلب مسبقاً.", show_alert=True)
            return

        if action == "approve":
            cursor = await db.execute(
                """
                UPDATE users
                SET balance = COALESCE(balance, 0) + ?
                WHERE user_id = ?
                """,
                (amount, user_id),
            )

            if cursor.rowcount != 1:
                await db.rollback()
                await callback.answer(
                    "❌ المستخدم غير موجود، لم تتم إضافة الرصيد.", show_alert=True
                )
                return

        await db.commit()

    if action == "approve":
        result_text = (
            f"✅ تم قبول الطلب بنجاح.\nتمت إضافة {amount} USDT إلى رصيد المستخدم."
        )
        user_text = (
            f"🎉 تم قبول طلب الإيداع الخاص بك بمبلغ {amount} USDT وإضافة الرصيد بنجاح."
        )
    else:
        result_text = "❌ تم رفض طلب الإيداع."
        user_text = "❌ نعتذر، تم رفض طلب الإيداع الخاص بك من قبل الإدارة."

    try:
        if callback.message:
            await callback.message.edit_text(result_text, reply_markup=None)
    except TelegramBadRequest as error:
        logging.warning("تعذر تعديل رسالة الأدمن: %s", error)

    try:
        await callback.bot.send_message(user_id, user_text)
    except Exception as error:
        logging.exception("فشل إرسال إشعار الإيداع للمستخدم %s: %s", user_id, error)

    await callback.answer("تم تنفيذ العملية.")

    async def process_withdrawal_or_send(
        user_id: int,
        amount: float,
        network: str,
        wallet_address: str,
        is_external: bool = True,
    ):
        """
        سحب أو الإرسال - النسخة النهائية المطابقة لدفترك
        """

    if amount <= 0:
        return False, "❌ المبلغ يجب أن يكون أكبر من صفر"

    fee = 1.0 if is_external else 0.0
    total_deduction = amount + fee

    async with aiosqlite.connect("bot.db") as db:
        try:
            await db.execute("BEGIN IMMEDIATE")

            cursor = await db.execute(
                "SELECT balance FROM users WHERE user_id = ?",
                (user_id,),
            )
            user_row = await cursor.fetchone()
            await cursor.close()

            if user_row is None:
                await db.rollback()
                return False, "❌ حسابك غير مسجل في النظام."

            current_balance = float(user_row[0] or 0.0)

            if current_balance < total_deduction:
                await db.rollback()
                return (
                    False,
                    f"⚠️ رصيدك الحالي ({current_balance} USDT) لا يكفي.\n"
                    f"المطلوب مع الرسوم: {total_deduction} USDT",
                )

            await db.execute(
                """
                UPDATE users
                SET balance = balance - ?
                WHERE user_id = ?
                """,
                (total_deduction, user_id),
            )

            await db.execute(
                """
                INSERT INTO withdrawals
                    (user_id, amount, network, wallet_address, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, amount, network, wallet_address, "pending"),
            )

            await db.commit()

            return (
                True,
                f"✅ تم استلام طلب السحب بنجاح!\n"
                f"💰 المبلغ: {amount} USDT\n"
                f"💸 الرسوم: {fee} USDT\n"
                f"📌 الشبكة: {network}\n"
                f"📌 العنوان: {wallet_address}",
            )

        except Exception as error:
            await db.rollback()
            print(f"Database error: {error}")
            return False, "❌ حدث خطأ تقني، حاول لاحقًا"
            # ==================== FSM للحالات الخاصة بالسحب ====================


class WithdrawalStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_network = State()
    waiting_for_address = State()


# ==================== بداية عملية السحب ====================


@dp.message(Command("withdraw"))
async def cmd_withdraw(message: types.Message, state: FSMContext):
    await state.clear()

    await message.answer(
        "💸 الرجاء إدخال المبلغ الذي تود سحبه (USDT):", reply_markup=cancel_kb
    )

    await state.set_state(WithdrawalStates.waiting_for_amount)


# ==================== استقبال مبلغ السحب ====================


@dp.message(WithdrawalStates.waiting_for_amount)
async def process_withdrawal_amount(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("⚠️ الرجاء إرسال المبلغ كرقم.", reply_markup=cancel_kb)
        return

    try:
        amount = float(message.text.strip())

        if amount <= 0:
            raise ValueError

    except ValueError:
        await message.answer(
            "⚠️ المبلغ غير صحيح، الرجاء إدخال رقم أكبر من صفر.", reply_markup=cancel_kb
        )
        return

    await state.update_data(amount=amount)

    network_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="TRC20 🌐", callback_data="withdraw_trc20"),
                InlineKeyboardButton(text="BEP20 🌐", callback_data="withdraw_bep20"),
            ],
            [cancel_button],
        ]
    )

    await message.answer("🌐 اختر الشبكة المطلوبة للسحب:", reply_markup=network_kb)

    await state.set_state(WithdrawalStates.waiting_for_network)


# ==================== اختيار شبكة السحب ====================


@dp.callback_query(lambda c: c.data in ["withdraw_trc20", "withdraw_bep20"])
async def process_withdrawal_network(callback: types.CallbackQuery, state: FSMContext):
    network_name = "TRC20" if callback.data == "withdraw_trc20" else "BEP20"

    await state.update_data(network=network_name)

    await callback.message.edit_text(
        f"📬 الشبكة المختارة للسحب: "
        f"<b>{network_name}</b>\n\n"
        "📥 الرجاء إرسال عنوان المحفظة:",
        parse_mode=ParseMode.HTML,
        reply_markup=cancel_kb,
    )

    await state.set_state(WithdrawalStates.waiting_for_address)

    await callback.answer()


# ==================== استقبال عنوان المحفظة ====================


@dp.message(WithdrawalStates.waiting_for_address)
async def process_withdrawal_address(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer(
            "⚠️ الرجاء إرسال عنوان المحفظة كنص.", reply_markup=cancel_kb
        )
        return

    wallet_address = message.text.strip()

    if not wallet_address:
        await message.answer(
            "⚠️ عنوان المحفظة لا يمكن أن يكون فارغاً.", reply_markup=cancel_kb
        )
        return

    data = await state.get_data()

    amount = data.get("amount")
    network = data.get("network")
    user_id = message.from_user.id

    if amount is None or not network:
        await state.clear()

        await message.answer("❌ انتهت جلسة السحب. يرجى البدء من جديد.")
        return

    # استدعاء دالة معالجة السحب الموجودة في مشروعك
    success, response_text = await process_withdrawal_or_send(
        bot, user_id, amount, network, wallet_address
    )

    await message.answer(response_text, parse_mode=ParseMode.HTML)

    await state.clear()


async def main():
    logger.info("🚀 Starting Bot...")
    try:
        bot_info = await bot.get_me()
        await init_db()
        logger.info(f"✅ Bot started as @{bot_info.username}")
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await bot.session.close()
        logger.info("🛑 Bot stopped.")


@dp.message(Command("balance"))
async def cmd_balance(message: types.Message):
    user_id = message.from_user.id
    balance = await get_balance(user_id)
    await message.answer(f"💰 رصيدك الحالي: {balance} USDT")


@dp.message(Command("deposit"))
async def cmd_deposit(message: types.Message):
    text = (
        "📥 إيداع رصيد USDT\n\n"
        "لشحن حسابك، يرجى التحويل على عنوان الإيداع المعتمد.\n\n"
        "🌐 الشبكات المدعومة: TRC20 / BEP20 / ERC20"
    )
    await message.answer(text)


dp.include_router(external_payment_router)
asyncio.run(main())
