# 🚀 Telegram Trading & Automated Payment Bot

An asynchronous, enterprise-grade Telegram financial ecosystem engineered with Python and Aiogram 3.x.

## 🏛️ Core Architecture & Features
- **Modular Routing:** Decoupled architecture (`trading_router`, `flashrouter`, `external_payment_router`) for clean, scalable code.
- **Secure FSM Workflows:** Multi-step user interaction pipelines for deposits, withdrawals, and admin authentication.
- **Financial Precision & Safety:** Uses `Decimal` to eliminate rounding errors and `BEGIN IMMEDIATE` transactions via `aiosqlite` to prevent race conditions during balance updates.
- **Automated Lifecycles:** End-to-end deposit proof submission and step-by-step withdrawal validation.

## 🛠️ Tech Stack
- Python, Asyncio, Aiogram 3.x, SQLite, aiosqlite, python-dotenv.
