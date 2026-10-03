import asyncio
import logging
import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator
from datetime import datetime
import calendar
import aiosqlite

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

BASE_DIR = Path().resolve().parent
DB_FILE = Path(os.getenv("DATABASE_PATH", str(BASE_DIR / "database.db"))).resolve()

BUSY_TIMEOUT_SECONDS = 30.0

logger = logging.getLogger("database")


# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


# ---------------------------------------------------------
# Database connection
# ---------------------------------------------------------


async def configure_connection(db: aiosqlite.Connection) -> None:
    """
    Configure one SQLite connection safely.

    Important:
    PRAGMA foreign_keys is connection-specific and must be enabled
    for every new connection.
    """

    await db.execute("PRAGMA foreign_keys = ON")
    await db.execute("PRAGMA busy_timeout = 30000")
    await db.execute("PRAGMA journal_mode = WAL")
    await db.execute("PRAGMA synchronous = NORMAL")
    await db.execute("PRAGMA temp_store = MEMORY")

    db.row_factory = sqlite3.Row


@asynccontextmanager
async def get_db() -> AsyncIterator[aiosqlite.Connection]:
    """
    Open and safely close a database connection.
    """

    DB_FILE.parent.mkdir(parents=True, exist_ok=True)

    db = await aiosqlite.connect(
        database=str(DB_FILE),
        timeout=BUSY_TIMEOUT_SECONDS,
    )

    try:
        await configure_connection(db)
        yield db
    finally:
        await db.close()


# ---------------------------------------------------------
# Schema
# ---------------------------------------------------------

SCHEMA_SQL = (
    "CREATE TABLE IF NOT EXISTS users ("
    "user_id INTEGER PRIMARY KEY, "
    "full_name TEXT, "
    "email TEXT, "
    "wallet_address TEXT, "
    "balance_minor INTEGER NOT NULL DEFAULT 0 CHECK (balance_minor >= 0), "
    "flash_balance INTEGER NOT NULL DEFAULT 0, "
    "expires_at TEXT, "
    "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, "
    "updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"
    ");"
    "CREATE INDEX IF NOT EXISTS idx_users_updated_at ON users(updated_at);"
    "CREATE TABLE IF NOT EXISTS trades_history ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT, "
    "user_id INTEGER NOT NULL, "
    "market_type TEXT NOT NULL, "
    "pair TEXT NOT NULL, "
    "amount_minor INTEGER NOT NULL CHECK (amount_minor > 0), "
    "direction TEXT NOT NULL, "
    "result TEXT NOT NULL, "
    "profit_minor INTEGER NOT NULL DEFAULT 0, "
    "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, "
    "FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE"
    ");"
    "CREATE INDEX IF NOT EXISTS idx_trades_user "
    "ON trades_history(user_id);"
    "CREATE INDEX IF NOT EXISTS idx_trades_created "
    "ON trades_history(created_at);"
)


async def init_db():
    async with get_db() as db:
        await db.execute(SCHEMA_SQL)

        await db.execute(
            "CREATE TABLE IF NOT EXISTS deposits ("
            "id INTEGER PRIMARY KEY, "
            "user_id INTEGER NOT NULL, "
            "amount REAL NOT NULL CHECK (amount > 0), "
            "network TEXT NOT NULL, "
            "txid TEXT, "
            "status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'rejected')), "
            "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )

        await db.execute(
            "CREATE TABLE IF NOT EXISTS withdrawals ("
            "id INTEGER PRIMARY KEY, "
            "user_id INTEGER NOT NULL, "
            "amount REAL NOT NULL CHECK (amount > 0), "
            "network TEXT NOT NULL, "
            "wallet_address TEXT NOT NULL, "
            "status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'rejected')), "
            "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )

        await db.commit()


# ---------------------------------------------------------
# User operations
# ---------------------------------------------------------


def validate_user_id(user_id: int) -> int:
    if isinstance(user_id, bool) or not isinstance(user_id, int):
        raise TypeError("user_id must be an integer")

    if user_id <= 0:
        raise ValueError("user_id must be greater than zero")

    return user_id


def validate_amount(amount_minor: int) -> int:
    if isinstance(amount_minor, bool) or not isinstance(amount_minor, int):
        raise TypeError("amount_minor must be an integer")

    if amount_minor <= 0:
        raise ValueError("amount_minor must be greater than zero")

    return amount_minor


async def create_user(user_id: int) -> bool:

    user_id = validate_user_id(user_id)

    async with get_db() as db:
        cursor = await db.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,)
        )
        await db.commit()
        return cursor.rowcount == 1


async def get_balance(user_id: int) -> int | None:

    user_id = validate_user_id(user_id)

    async with get_db() as db:
        async with db.execute(
            "SELECT balance_minor FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return None if row is None else int(row["balance_minor"])


async def deposit(user_id: int, amount_minor: int) -> int:
    user_id = validate_user_id(user_id)
    amount_minor = validate_amount(amount_minor)
    async with get_db() as db:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute(
            "UPDATE users SET balance_minor = balance_minor + ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (amount_minor, user_id),
        )
        if cursor.rowcount == 0:
            await db.rollback()
            raise LookupError(f"User {user_id} does not exist")
        async with db.execute(
            "SELECT balance_minor FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                await db.rollback()
                raise LookupError(f"User {user_id} does not exist")
            await db.commit()
            return int(row["balance_minor"])


async def withdraw(user_id: int, amount_minor: int) -> int:
    user_id = validate_user_id(user_id)
    amount_minor = validate_amount(amount_minor)
    async with get_db() as db:
        try:
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute(
                "UPDATE users SET balance_minor = balance_minor - ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ? AND balance_minor >= ?",
                (amount_minor, user_id, amount_minor),
            )
            if cursor.rowcount != 1:
                async with db.execute(
                    "SELECT user_id, balance_minor FROM users WHERE user_id = ?",
                    (user_id,),
                ) as check_cursor:
                    row = await check_cursor.fetchone()
                if row is None:
                    raise LookupError(f"User {user_id} does not exist")
                raise ValueError("Insufficient balance")

            async with db.execute(
                "SELECT balance_minor FROM users WHERE user_id = ?", (user_id,)
            ) as balance_cursor:
                row = await balance_cursor.fetchone()
                if row is None:
                    raise LookupError(f"User {user_id} does not exist")
                await db.commit()
                return int(row["balance_minor"])
        except Exception:
            await db.rollback()
            raise


# ---------------------------------------------------------
# Example
# ---------------------------------------------------------


async def init_db():
    async with get_db() as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.execute(
            "CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance_minor INTEGER DEFAULT 0, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )
        await db.execute(
            "CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, type TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (user_id) REFERENCES users (user_id))"
        )
        await db.commit()


async def main() -> None:
    await init_db()


async def get_balance(user_id: int) -> int:
    async with get_db() as db:
        async with db.execute(
            "SELECT balance_minor FROM users WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return int(row[0]) if row else 0


async def add_flash_balance_to_user(user_id: int, flash_amount: int) -> None:
    user_id = validate_user_id(user_id)
    flash_amount = validate_amount(flash_amount)

    # حساب 8 أشهر تقويمية بشكل دقيق مع التعامل مع تجاوز الشهر 12
    now = datetime.now()
    target_month = now.month + 8
    target_year = now.year + (target_month - 1) // 12
    target_month = (target_month - 1) % 12 + 1

    # ضبط اليوم ليتناسب مع نهايات الشهور القصيرة (مثل فبراير)
    import calendar
    last_day_of_target_month = calendar.monthrange(target_year, target_month)[1]
    target_day = min(now.day, last_day_of_target_month)

    expires_at = now.replace(
        year=target_year,
        month=target_month,
        day=target_day
    ).strftime("%Y-%m-%d %H:%M:%S")

    async with get_db() as db:
        try:
            await db.execute("BEGIN IMMEDIATE")

            async with db.execute(
                "SELECT 1 FROM users WHERE user_id = ?",
                (user_id,),
            ) as cursor:
                if not await cursor.fetchone():
                    raise ValueError(f"User {user_id} does not exist.")

            await db.execute(
                """
                UPDATE users
                SET flash_balance = flash_balance + ?,
                    expires_at = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (flash_amount, expires_at, user_id),
            )

            await db.commit()

        except Exception:
            await db.rollback()
            raise


async def add_flash_balance_to_user(user_id: int, flash_amount: int) -> None:
    user_id = validate_user_id(user_id)
    flash_amount = validate_amount(flash_amount)

    # الحد الأقصى لعملات الفلاش (2 ترليون) حسب طلب الزبون
    MAX_FLASH_LIMIT = 2_000_000_000_000
    if flash_amount > MAX_FLASH_LIMIT:
        flash_amount = MAX_FLASH_LIMIT

    # حساب 8 أشهر تقويمية بشكل دقيق مع التعامل مع تجاوز الشهر 12
    now = datetime.now()
    target_month = now.month + 8
    target_year = now.year + (target_month - 1) // 12
    target_month = (target_month - 1) % 12 + 1

    # ضبط اليوم ليتناسب مع نهايات الشهور القصيرة (مثل فبراير)
    import calendar
    last_day_of_target_month = calendar.monthrange(target_year, target_month)[1]
    target_day = min(now.day, last_day_of_target_month)

    expires_at = now.replace(
        year=target_year,
        month=target_month,
        day=target_day
    ).strftime("%Y-%m-%d %H:%M:%S")

    async with get_db() as db:
        try:
            await db.execute("BEGIN IMMEDIATE")

            async with db.execute(
                "SELECT 1 FROM users WHERE user_id = ?",
                (user_id,),
            ) as cursor:
                if not await cursor.fetchone():
                    raise ValueError(f"User {user_id} does not exist.")

            await db.execute(
                """
                UPDATE users
                SET flash_balance = flash_balance + ?,
                    expires_at = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (flash_amount, expires_at, user_id),
            )

            await db.commit()

        except Exception:
            await db.rollback()
            raise


async def add_flash_balance_to_user(user_id: int, flash_amount: int) -> None:
    user_id = validate_user_id(user_id)
    flash_amount = validate_amount(flash_amount)

    MAX_FLASH_LIMIT = 2_000_000_000_000
    if flash_amount > MAX_FLASH_LIMIT:
        flash_amount = MAX_FLASH_LIMIT

    now = datetime.now()
    target_month = now.month + 8
    target_year = now.year + (target_month - 1) // 12
    target_month = (target_month - 1) % 12 + 1

    last_day_of_target_month = calendar.monthrange(target_year, target_month)[1]
    target_day = min(now.day, last_day_of_target_month)

    expires_at = now.replace(
        year=target_year,
        month=target_month,
        day=target_day
    ).strftime("%Y-%m-%d %H:%M:%S")

    async with get_db() as db:
        try:
            await db.execute("BEGIN IMMEDIATE")

            async with db.execute(
                "SELECT 1 FROM users WHERE user_id = ?",
                (user_id,),
            ) as cursor:
                if not await cursor.fetchone():
                    raise ValueError(f"User {user_id} does not exist.")

            await db.execute(
                """
                UPDATE users
                SET flash_balance = flash_balance + ?,
                    expires_at = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (flash_amount, expires_at, user_id),
            )

            await db.commit()

        except Exception:
            await db.rollback()
            raise


async def check_and_deduct_flash(user_id: int, amount: int) -> bool:
    user_id = validate_user_id(user_id)
    amount = validate_amount(amount)

    async with get_db() as db:
        try:
            await db.execute("BEGIN IMMEDIATE")

            async with db.execute(
                "SELECT flash_balance, expires_at FROM users WHERE user_id = ?",
                (user_id,),
            ) as cursor:
                row = await cursor.fetchone()

            if not row:
                await db.rollback()
                return False

            flash_balance = row["flash_balance"]
            expires_at_str = row["expires_at"]

            if expires_at_str:
                expires_at = datetime.strptime(
                    expires_at_str,
                    "%Y-%m-%d %H:%M:%S",
                )

                if datetime.now() > expires_at:
                    await db.execute(
                        """
                        UPDATE users
                        SET flash_balance = 0,
                            expires_at = NULL,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = ?
                        """,
                        (user_id,),
                    )
                    await db.commit()
                    return False

            if flash_balance < amount:
                await db.rollback()
                return False

            await db.execute(
                """
                UPDATE users
                SET flash_balance = flash_balance - ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND flash_balance >= ?
                """,
                (amount, user_id, amount),
            )
            
            if db.total_changes == 0:
                await db.rollback()
                return False

            await db.commit()
            return True

        except Exception:
            await db.rollback()
            raise