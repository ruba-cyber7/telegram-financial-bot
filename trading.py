from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from decimal import Decimal, InvalidOperation
from database import get_db
import random

trading_router = Router()

USDT_SCALE = 1_000_000
MAX_TRADE_AMOUNT = Decimal("5000.00")
WIN_PROFIT_RATE = Decimal("0.85")


class TradingStates(StatesGroup):
    choosing_market = State()
    choosing_pair = State()
    entering_amount = State()
    choosing_direction = State()


@trading_router.message(F.text == "📈 تداول")
async def start_trading_menu(message: types.Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 باينري (Binary Options)", callback_data="market_binary"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💱 فوركس (Forex)", callback_data="market_forex"
                )
            ],
        ]
    )

    await message.answer(
        "Choose market:",
        reply_markup=keyboard,
    )

    await state.set_state(TradingStates.choosing_market)


@trading_router.callback_query(
    F.data.startswith("market_"), TradingStates.choosing_market
)
async def process_market_choice(callback: types.CallbackQuery, state: FSMContext):
    market_type = "الباينري" if callback.data == "market_binary" else "الفوركس"
    await state.update_data(market_type=market_type)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="EUR/USD", callback_data="pair_EURUSD"),
                InlineKeyboardButton(text="GBP/USD", callback_data="pair_GBPUSD"),
            ],
            [
                InlineKeyboardButton(text="USD/JPY", callback_data="pair_USDJPY"),
                InlineKeyboardButton(text="BTC/USDT", callback_data="pair_BTCUSDT"),
            ],
        ]
    )

    try:
        await callback.message.edit_text(
            f"✅ السوق: {market_type}\n\nاختر الزوج:",
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            f"✅ السوق: {market_type}\n\nاختر الزوج:",
            reply_markup=keyboard,
            parse_mode="HTML",
        )

    await state.set_state(TradingStates.choosing_pair)
    await callback.answer()


@trading_router.callback_query(F.data.startswith("pair_"), TradingStates.choosing_pair)
async def process_pair_choice(callback: types.CallbackQuery, state: FSMContext):
    pair = callback.data.replace("pair_", "", 1)
    await state.update_data(pair=pair)

    await callback.message.edit_text(
        f"📊 الزوج: {pair}\n\n💰 ارسل مبلغ الايداع USDT:",
        parse_mode="HTML",
    )
    await state.set_state(TradingStates.entering_amount)
    await callback.answer()


@trading_router.message(TradingStates.entering_amount)
async def process_trading_amount(message: types.Message, state: FSMContext):
    raw_amount = (message.text or "").strip().replace(",", ".")

    try:
        amount = Decimal(raw_amount)
        if not amount.is_finite() or amount <= 0 or amount > MAX_TRADE_AMOUNT:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        await message.answer(
            "❌ <b>أرسل مبلغ التداول بشكل صالح.\n\nالمبلغ غير صالح:</b> USDT:",
            parse_mode="HTML",
        )
        return

    amount_minor = int(amount * USDT_SCALE)
    user_id = message.from_user.id

    async with get_db() as db:
        async with db.execute(
            """
            SELECT balance_minor
            FROM users
            WHERE user_id = ?
            """,
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()

    if not row or row["balance_minor"] < amount_minor:
        await message.answer("❌ رصيدك الحالي لا يكفي لإتمام هذه الصفقة.")
        await state.clear()
        return
        await state.update_data(amount=str(amount), amount_minor=amount_minor)

    data = await state.get_data()
    market_type = data.get("market_type", "الباينري")

    if market_type == "الباينري":
        action_name = "الصعود/الهبوط"
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🟢 صعود (Call)", callback_data="dir_buy")],
                [InlineKeyboardButton(text="🔴 هبوط (Put)", callback_data="dir_sell")],
                [InlineKeyboardButton(text="❌ الغاء", callback_data="cancel_trade")],
            ]
        )
    else:
        action_name = "الشراء/البيع"
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📈 شراء (Buy)", callback_data="dir_buy")],
                [InlineKeyboardButton(text="📉 بيع (Sell)", callback_data="dir_sell")],
                [InlineKeyboardButton(text="❌ الغاء", callback_data="cancel_trade")],
            ]
        )

    await state.set_state(TradingStates.choosing_direction)
    await message.answer(
        f"💵 المبلغ: {amount:.6f} USDT\n📊 اختر {action_name}:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


@trading_router.callback_query(
    F.data.startswith("dir_"), TradingStates.choosing_direction
)
async def execute_trade(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()

    if not all(
        key in data for key in ("amount", "amount_minor", "pair", "market_type")
    ):
        await callback.answer("انتهت جلسة التداول، ابدأ من جديد.", show_alert=True)
        await state.clear()
        return

    user_id = callback.from_user.id
    amount = Decimal(str(data["amount"]))
    amount_minor = int(data["amount_minor"])
    pair = data["pair"]
    market_type = data["market_type"]

    is_buy = callback.data == "dir_buy"

    if market_type == "الباينري":
        direction = "صعود 🟢" if is_buy else "هبوط 🔴"
    else:
        direction = "شراء 🟢" if is_buy else "بيع 🔴"

    is_win = random.choice([True, False])

    if is_win:
        result_text = "ربح ✅"
        profit_minor = int(amount_minor * WIN_PROFIT_RATE)
        display_profit = amount * WIN_PROFIT_RATE
        balance_change = profit_minor
    else:
        result_text = "خسارة ❌"
        profit_minor = -amount_minor
        display_profit = -amount
        balance_change = -amount_minor

    try:
        async with get_db() as db:
            await db.execute("BEGIN IMMEDIATE")

            async with db.execute(
                """
                SELECT balance_minor
                FROM users
                WHERE user_id = ?
                """,
                (user_id,),
            ) as cursor:
                row = await cursor.fetchone()

            if not row or int(row["balance_minor"]) < amount_minor:
                await db.rollback()
                await callback.answer(
                    "الرصيد لم يعد كافياً.",
                    show_alert=True,
                )
                await state.clear()
                return

            await db.execute(
                """
                UPDATE users
                SET balance_minor = balance_minor + ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (balance_change, user_id),
            )

            await db.execute(
                """
                INSERT INTO trades_history (
                    user_id,
                    market_type,
                    pair,
                    amount_minor,
                    direction,
                    result,
                    profit_minor
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    market_type,
                    pair,
                    amount_minor,
                    direction,
                    result_text,
                    int(profit_minor if is_win else -amount_minor),
                ),
            )
            await db.commit()

    except Exception:
        await db.rollback()
        await callback.answer(
            "حدث خطأ اثناء تنفيذ الصفقة ⚠️",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        f"📊 نتيجة التداول (محاكاة)\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔹 السوق: {market_type}\n"
        f"💱 الزوج: {pair}\n"
        f"💰 المبلغ: {amount:.6f} USDT\n"
        f"📈 الاتجاه: {direction}\n"
        f"🏷 النتيجة: {result_text}\n"
        f"💵 الصافي: {display_profit:.6f} USDT\n"
        f"━━━━━━━━━━━━━━━\n"
        f"تم تحديث الرصيد وحفظ العملية. 🚀",
        parse_mode="Markdown",
    )

    await callback.answer()
    await state.clear()
