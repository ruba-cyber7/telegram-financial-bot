from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_balance, add_flash_balance_to_user, check_and_deduct_flash

flashrouter = Router()

@flashrouter.message(F.text == "⚡ رصيد الفلاش")
async def show_flash_menu(message: Message):
    user_id = message.from_user.id
    balance = await get_balance(user_id)
    
    # معالجة حالة إذا كان الرصيد None لتجنب أخطاء وقت التشغيل
    safe_balance = balance if balance is not None else 0.0
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 تحويل لمحفظة", callback_data="flash_transfer")],
        [InlineKeyboardButton(text="🆔 إرسال (ID / شبكة)", callback_data="flash_send")],
        [InlineKeyboardButton(text="🌐 شحن مواقع", callback_data="flash_pay")],
        [InlineKeyboardButton(text="📈 تداول (بايينري / فوركس)", callback_data="flash_trade")],
        [InlineKeyboardButton(text="🏧 سحب السيولة", callback_data="flash_withdraw")]
    ])
    
    await message.answer(
        "⚡ نظام الفلاش المؤقت (عالي السيولة)\n\n"
        f"💰 الرصيد المتاح: {safe_balance:,.2f} USDT\n"
        "⏳ المدة: 8 أشهر (قابلة للاستخدام والتداول)\n\n"
        "اختر العملية المطلوبة من القائمة أدناه:",
        reply_markup=keyboard
    )

@flashrouter.callback_query(F.data.startswith("flash_"))
async def handle_flash_actions(callback: CallbackQuery):
    if not callback.data:
        await callback.answer()
        return
        
    parts = callback.data.split("_")
    action = parts[1] if len(parts) > 1 else ""
    
    actions_dict = {
        "transfer": "💸 تحويل لمحفظة: يرجى إرسال عنوان المحفظة والمبلغ المراد تحويله.",
        "send": "🆔 إرسال رصيد: أدخل معرف البايننس (Binance ID) أو عنوان الشبكة المستهدفة.",
        "pay": "🌐 شحن مواقع: أرسل رابط الموقع أو تفاصيل الفاتورة المراد دفعها بالـ USDT.",
        "trade": "📈 التداول المؤقت: تم تفعيل جلسة التداول (باينري / فوركس) بنجاح على رصيد الفلاش.",
        "withdraw": "🏧 سحب السيولة: جاري معالجة أمر سحب السيولة الضخمة..."
    }
    
    text = actions_dict.get(action, "عملية غير معروفة.")
    await callback.message.answer(text)
    await callback.answer()