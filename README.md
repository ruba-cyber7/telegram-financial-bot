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
flashrouter.py – موجه رصيد الفلاش
​تعد هذه الطبقة بمثابة الموجه الديناميكي المتخصص لإدارة نظام رصيد الفلاش المؤقت (عالي السيولة) في البوت. فهي تتعامل مع تفاعلات الأزرار الشفافة، وتتيح للمستخدمين استعراض أرصدتهم المتاحة بأمان، وتنفيذ عمليات التحويل، وشحن المواقع، وإدارة جلسات التداول وسحب السيولة.
​المسؤوليات الأساسية
​استقبال وتنفيذ أوامر رصيد الفلاش المؤقت.
​عرض القوائم التفاعلية والأزرار اللحظية (Inline Keyboards).  
​جلب ومعالجة أرصدة المستخدمين بشكل آمن وتجنب أخطاء التشغيل.  
​إدارة مسارات العمليات المالية مثل: التحويل للمحافظ، الشحن، والتداول.  
​توجيه طلبات السحب والمعاملات السريعة بكفاءة عالية.
​تكنولوجيا
​Aiogram 3.x (Router & Callbacks) • Asyncio • F (Filters) • Python 
