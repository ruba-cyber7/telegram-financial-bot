import asyncio
from database import init_db, deposit

async def main():
    await init_db()
    print("قاعدة البيانات اشتغلت وتهـيأت صح!")

    try:
        # تجربة الإيداع على دالة deposit الحقيقية الموجودة عندك
        res = await deposit(user_id=123, amount_minor=500)
        print(f"يا سلام! دالة الإيداع اشتغلت والنتيجة: {res}")
    except Exception as e:
        print(f"خطأ: {e}")

asyncio.run(main())
