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


### 📈 trading.py – Trading & Market Simulation Engine

This module handles the complete trading lifecycle within the Telegram bot, supporting both Binary Options and Forex markets. It implements a multi-step Finite State Machine (FSM) workflow to guide users through market selection, currency/crypto pair choice, amount entry with precise decimal validation, direction selection (Call/Put or Buy/Sell), and simulated trade execution with automatic balance updates and transaction history logging.

#### Core Responsibilities
* Managing the FSM states for market, pair, amount, and direction selection[span_2](start_span)[span_2](end_span).
* Handling binary options and forex market workflows with dynamic interactive keyboards[span_3](start_span)[span_3](end_span).
* Validating input amounts against liquidity and maximum trade limits using the Decimal library[span_4](start_span)[span_4](end_span).
* Executing secure database transactions with row-level locking (`BEGIN IMMEDIATE`) and balance verification[span_5](start_span)[span_5](end_span).
* Simulating trade outcomes (win/loss), calculating profits, updating user balances atomically, and recording results in the trade history[span_6](start_span)[span_6](end_span).

#### Technology
* Aiogram 3.x (Router, FSM Context, StatesGroup, Callbacks) • Decimal • Asyncio • SQLite / Aiosqlite • Random[span_7](start_span)[span_7](end_span)


### 🌐 index.html – Web Frontend & User Interface

This file represents the frontend web interface component of the ecosystem, designed with modern CSS styles (featuring animations and responsive media queries) and interactive JavaScript. It provides a clean dashboard layout presenting digital funding packages, supported blockchain networks (such as ERC20, BEP20, and TRC20), expiry details, and interactive purchase buttons with loading states and notification toasts.

#### Core Responsibilities
* Delivering a responsive user interface with CSS animations and mobile-friendly media queries[span_2](start_span)[span_2](end_span).
* Displaying professional digital funding packages, pricing, and expiration details[span_3](start_span)[span_3](end_span).
* Highlighting supported cryptocurrency networks (ERC20, BEP20, TRC20)[span_4](start_span)[span_4](end_span).
* Handling interactive purchase triggers, loading states, and dynamic status notification toasts using Vanilla JavaScript[span_5](start_span)[span_5](end_span).

#### Technology
* HTML5 • CSS3 (Animations & Media Queries) • JavaScript (DOM Manipulation & Event Listeners)[span_6](start_span)[span_6](end_span)
