# 🚀 Telegram Trading & Automated Payment Bot

An asynchronous, enterprise-grade Telegram financial ecosystem engineered with Python and Aiogram 3.x.

## 🏛️ Core Architecture & Features
- **Modular Routing:** Decoupled architecture (`trading_router`, `flashrouter`, `external_payment_router`) for clean, scalable code.
- **Secure FSM Workflows:** Multi-step user interaction pipelines for deposits, withdrawals, and admin authentication.
- **Financial Precision & Safety:** Uses `Decimal` to eliminate rounding errors and `BEGIN IMMEDIATE` transactions via `aiosqlite` to prevent race conditions during balance updates.
- **Automated Lifecycles:** End-to-end deposit proof submission and step-by-step withdrawal validation.

## 🛠️ Tech Stack
- Python, Asyncio, Aiogram 3.x, SQLite, aiosqlite, python-dotenv.
---

## 🤖 bot.py — Application Core

`bot.py` serves as the primary orchestration layer of the application. It connects the Telegram interface with the database, trading router, flash router, payment and withdrawal workflows, FSM state management, and administrative processes.

### Core Responsibilities

* Application and bot initialization.
* Modular router integration.
* FSM-based multi-step workflows.
* Deposit and withdrawal management.
* Administrative workflow.
* External payment request handling.
* Balance and transaction coordination.
* Logging and application lifecycle management.

### Technology

**Python · asyncio · Aiogram 3.x · FSM · python-dotenv · aiosqlite**

---

## 🗄️ database.py — Database Layer

`database.py` provides the asynchronous SQLite data layer using `aiosqlite`. It manages users, balances, transactions, trading history, deposits, withdrawals, and flash-balance operations.

### Core Responsibilities

* Asynchronous SQLite connection management.
* User and balance management.
* Deposit and withdrawal operations.
* Trading and transaction data storage.
* Flash-balance management with expiration handling.
* Input validation and transactional database operations.
* SQLite WAL mode and foreign-key enforcement.

### Technology

**SQLite · aiosqlite · asyncio · datetime · calendar**

​⚡ flashrouter.py – Flash Balance Router
​This layer acts as the specialized dynamic router for managing the temporary high-liquidity flash balance system in the bot. It handles transparent inline button interactions, allows users to securely view their available balances, and executes operations such as wallet transfers, website top-ups, trading session management, and liquidity withdrawals.
​Core Responsibilities
​Receiving and executing temporary flash balance commands.
​Displaying interactive menus and dynamic inline keyboards.
​Safely fetching and processing user balances while preventing runtime errors.
​Managing financial operation workflows such as wallet transfers, top-ups, and trading.
​Efficiently routing withdrawal requests and rapid transaction processes.
​Technology
​Aiogram 3.x (Router & Callbacks) • Asyncio • F (Filters) • Python

### 🧪 test.py – Testing & Verification Script

This script serves as an automated test utility for verifying core functionalities and database integrations. It initializes the database schema asynchronously and performs test operations (such as simulating a user deposit) to ensure the system logic executes smoothly without runtime exceptions.

#### Core Responsibilities
* Initializing the SQLite database asynchronously for testing[span_3](start_span)[span_3](end_span).
* Executing automated test cases (e.g., simulating deposits) against database functions[span_4](start_span)[span_4](end_span).
* Catching and reporting runtime exceptions or integration errors[span_5](start_span)[span_5](end_span).
* Validating backend readiness before full deployment.

#### Technology
* Asyncio • SQLite / Aiosqlite • Python

