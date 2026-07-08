# CampusPay: Escrow payments and instant bank payouts for university campuses.

Welcome to **CampusPay**! CampusPay is a production-grade fintech solution designed for university campuses. It addresses trust deficits and payment friction between students and campus vendors. By leveraging **Nomba's Dynamic Virtual Account (DVA) API**, CampusPay provisions unique bank accounts for students, enabling automated deposit tracking via webhooks, secure QR-code based escrow settlement, automated no-show penalties, and a daily automated financial reconciliation engine.

---

## 🏗️ System Architecture

CampusPay is structured as a decoupled web application with a lightweight **Progressive Web App (PWA)** frontend and a robust **FastAPI** backend integrated with a **PostgreSQL** database.

```mermaid
graph TD
    subgraph Frontend [Client Tier PWA]
        JS[Vanilla Javascript Modules]
        HTML[Semantic HTML5]
        CSS[Sleek Custom CSS]
    end

    subgraph Auth [Identity & Auth Provider]
        FBAuth[Firebase Authentication]
    end

    subgraph Backend [Application Tier FastAPI]
        API[FastAPI Routers]
        Core[Core Utilities & Config]
        Sec[Security Middleware]
        Svc[Nomba & Recon Services]
        Models[SQLAlchemy ORM Models]
        Expiry[Async Background Expiry Job]
    end

    subgraph Database [Storage Tier]
        DB[(PostgreSQL Database)]
    end

    subgraph External [External APIs]
        NombaAPI[Nomba Financial Core APIs]
        NombaWH[Nomba Webhook Dispatcher]
    end

    %% Interactions
    JS -->|Bearer JWT ID Token| API
    JS -->|Authenticate| FBAuth
    API -->|Verify Signature| FBAuth
    API -->|SQL queries via async PG session| Models
    Models --> DB
    API -->|Fetch banks, transfers, lookup| Svc
    Svc -->|HTTP REST Client| NombaAPI
    NombaWH -->|HTTP POST Signed Webhook| API
    Expiry -->|Scan Expired Transactions| DB
    Expiry -->|N20 Payouts| Svc
```

---

## 📂 Project Navigation Guide

Use this index to navigate the project's source code:

```
CampusPay/
│
├── main.py                     # Entry point for the FastAPI server; initializes CORS, registers routers, and starts the async background Expiry Job
├── requirements.txt            # Python dependencies (FastAPI, SQLAlchemy, PyJWT, Asyncpg, Cryptography, Firebase-Admin, etc.)
├── alembic.ini                 # Alembic configuration for managing schema migrations
├── migrations/                 # DB migrations directory managed by Alembic
│
├── app/                        # Main backend application codebase
│   ├── api/                    # API Routers (Endpoints)
│   │   ├── auth.py             # User profile sync & initial creation endpoint (/auth/sync)
│   │   ├── catalog.py          # Store lists, vendor details, and product management (/api/catalog)
│   │   ├── orders.py           # Order placement, QR scanning, status tracking, and pending orders (/api/orders)
│   │   ├── profile.py          # User details, bank listing, Nomba account lookup, and vendor bank config (/api/profile)
│   │   ├── wallet.py           # Balance lookups and paginated transaction history (/api/wallet)
│   │   └── webhooks.py         # HTTP POST Webhook endpoint for Nomba signature-signed payment notifications
│   │
│   ├── core/                   # Core settings & security
│   │   ├── config.py           # Pydantic Settings class loading environment variables
│   │   ├── database.py         # Asynchronous SQLAlchemy database engine and session generator
│   │   ├── security.py         # Custom Firebase ID Token verification dependency
│   │   └── security_webhook.py # HMAC-SHA256 signature verification for Nomba webhook events
│   │
│   ├── models/                 # Database Schema Definition
│   │   └── models.py           # Centralized SQLAlchemy schema definitions and DB Model mapping
│   │
│   ├── schemas/                # Pydantic Schemas for Input/Output Serialization
│   │   ├── auth.py
│   │   ├── catalog.py
│   │   ├── orders.py
│   │   ├── profile.py
│   │   └── wallet.py
│   │
│   └── services/               # Core business services
│       ├── nomba.py            # API client wrapper for Nomba (Auto auth token cached/refresh, DVA, Bank List, Transfers, Lookups)
│       ├── reconciliation.py   # Daily financial reconciliation engine auditing confirmed orders against Nomba's live API
│       └── user_service.py     # Logic for registering users and provisioning Nomba DVAs for students
│
└── Frontend/                   # PWA Client Application (Static HTML, CSS, Vanilla JS)
    ├── manifest.json           # PWA installation manifest defining icons, theme colors, and paths
    ├── sw.js                   # Service worker handles resource caching for offline availability
    ├── index.html              # Landing and landing redirection page
    ├── signup.html             # User registration and role selection UI
    ├── dashboard.html          # Student wallet balance, locked escrow, PWA navigation, and transaction listing
    ├── catalogue.html          # Dynamic list of open campus vendor stores
    ├── purchase.html           # Vendor catalogue item browser
    ├── payment.html            # QR Code generation interface for placed orders (locks payment in escrow)
    ├── pin.html                # PIN setup and check interfaces for authorizing wallet balances
    ├── pending.html            # List of active, pick-up ready orders for both students and vendors
    ├── receipt.html            # Completed transaction details page
    ├── transactions.html       # Searchable and filterable full transaction history
    ├── vendor.html             # Quick order form
    ├── vendor-dashboard.html   # Vendor transaction statistics, open/close shop toggles, and live QR code scan logs
    ├── vendor-products.html    # Vendor catalog creation, stock toggles, and listing tools
    ├── vendor-profile.html     # Bank settlement details lookup and registration page
    ├── scripts/                # Frontend Javascript Modules
    │   ├── firebaseAuth.js     # Firebase SDK initialization and auth state listeners
    │   ├── pwa.js              # Registers service workers and monitors update events
    │   ├── auth.js             # Handles user credential verification and role routes
    │   └── *.js                # Dynamic page controllers matching the HTML files
    └── styles/                 # Custom CSS stylesheet styles
        └── *.css               # Sleek, dark-mode styling variables, layouts, and responsive designs
```

---

## 🗄️ Database Schema & Data Models

CampusPay utilizes a relational database mapped via SQLAlchemy. The models support strict referential integrity, auditing, and financial transparency:

```mermaid
erDiagram
    user ||--o| wallet : "owns"
    user ||--o| account : "assigned DVA"
    user ||--o| product : "sells"
    user ||--o| order : "places / receives"
    wallet ||--o{ wallet_ledger : "audits balance changes"
    order ||--o{ wallet_ledger : "referenced by"

    user {
        string user_id PK
        string firebase_uid UK
        string email UK
        string full_name
        string role "Vendor | Student | Admin"
        string phone
        string vendor_bank_account
        string vendor_bank_code
        string vendor_bank_name
        string transaction_pin_hash
        string vendor_location
        boolean vendor_is_open
        string vendor_cover_image_url
        datetime created_at
    }

    account {
        string dva_id PK
        string student_id FK
        string account_reference UK
        string bank_account_number
        string bank_name
        string status "Active | Suspended"
        datetime created_at
    }

    wallet {
        string wallet_id PK
        string user_id FK
        numeric available_balance "12,2"
        numeric locked_balance "12,2"
        string currency "NGN"
        datetime updated_at
    }

    wallet_ledger {
        string ledger_id PK
        string wallet_id FK
        string user_id FK
        string direction "credit | debit"
        numeric amount "12,2"
        numeric balance_before "12,2"
        numeric balance_after "12,2"
        string reference
        string order_id FK
        string reason
        datetime created_at
    }

    order {
        string order_id PK
        string student_id FK
        string vendor_id FK
        string item_description
        numeric item_amount "12,2"
        numeric escrow_hold "12,2"
        string order_status "Pending | Confirmed | Expired | Refunded"
        string qr_token UK
        datetime timer_expires_at
        string nomba_transfer_ref
        string penalty_status "pending | paid | failed"
        string penalty_transfer_ref
        datetime created_at
    }

    product {
        string product_id PK
        string vendor_id FK
        string name
        string description
        numeric price "12,2"
        string image_url
        boolean is_available
        datetime created_at
    }

    webhookEvents {
        string event_id PK
        string event_type
        string account_reference
        numeric amount "12,2"
        string status "Processed | Failed | Duplicate"
        jsonb raw_payload
        datetime processed_at
    }
```

---

## 🔄 Core FinTech Workflows

### 1. Dynamic Virtual Account (DVA) Creation & Deposits
Every student receives a dedicated bank account upon signing up. When a student transfers money from any retail banking app to their DVA, it triggers a webhook that credits their wallet instantly.

```mermaid
sequenceDiagram
    autonumber
    actor Student
    participant BankApp as Retail Bank App
    participant Nomba as Nomba Financial Core
    participant Backend as CampusPay Backend
    participant DB as Postgres DB

    Student->>Backend: Register/Login (Sync Profile)
    Backend->>Nomba: POST /v1/accounts/virtual (student_id reference)
    Nomba-->>Backend: Return bank account & bank name
    Backend->>DB: Save DVA details linked to student
    Backend-->>Student: Display DVA Bank Details on Dashboard

    Note over Student, Nomba: Depositing Funds
    Student->>BankApp: Transfer NGN to DVA Bank Account
    BankApp->>Nomba: Clear & Settle Deposit
    Nomba->>Backend: POST /webhook/nomba (Signed Payment Success Webhook)
    rect rgb(240, 248, 255)
        Backend->>Backend: Verify Nomba HMAC Signature & requestId (Idempotency)
        Backend->>DB: Credit wallet available_balance & record credit transaction ledger
        Backend-->>Nomba: Respond HTTP 200 OK
    end
    Backend-->>Student: Push Update: Wallet Credited Successfully
```

---

### 2. QR Code Verification & Escrow Settlement Flow
To purchase an item, the student's funds (including a refundable N20 platform fee) are locked in escrow. Upon picking up the item at the vendor's physical location, the vendor scans the student's QR code. This releases the escrow, refunds the student their fee, and transfers the item price directly to the vendor's registered bank account via Nomba's payout API.

```mermaid
sequenceDiagram
    autonumber
    actor Student
    actor Vendor
    participant Backend as CampusPay Backend
    participant DB as Postgres DB
    participant Nomba as Nomba Financial Core

    Student->>Backend: Place Order (Item Price + N20 Platform Fee)
    Backend->>DB: Lock total amount in escrow (available_balance -> locked_balance)
    Backend->>DB: Write debit ledger entry
    Backend->>Backend: Sign JWT QR token (expires in 24 hours)
    Backend-->>Student: Display Signed QR code on screen

    Note over Student, Vendor: At the Store (Physical pickup)
    Student->>Vendor: Present QR code
    Vendor->>Backend: Scan QR code (POST /api/orders/{order_id}/scan)
    Backend->>DB: Fetch order & lock student's wallet row (with_for_update)
    Backend->>Nomba: POST /v1/transfers/bank/lookup (Verify Vendor Bank details)
    Nomba-->>Backend: Account name matches vendor
    
    rect rgb(230, 245, 230)
        Backend->>DB: Release escrow: deduct Item Amount, refund N20 platform fee to student
        Backend->>DB: Write credit ledger for N20 refund, and mark Order as Confirmed
        Backend->>DB: Commit DB Transaction (Ensures double-spend prevention)
    end
    
    Backend->>Nomba: POST /v2/transfers/bank (Send Item Amount to vendor bank)
    Nomba-->>Backend: Return transferRef (code 00)
    Backend->>DB: Save transfer reference on Order
    Backend-->>Vendor: Display "Order Picked up & Payout Initiated"
```

---

### 3. Automated Expiry Job & No-Show Penalties
If a student fails to pick up their order within 24 hours, the order expires. An async background daemon checks for expired orders every 60 seconds, unlocks the escrowed funds, refunds the student their item amount (deducting the N20 platform fee), and payouts the N20 fee directly to the vendor's bank account as a compensation penalty for reserving stock.

```mermaid
sequenceDiagram
    autonumber
    participant Daemon as Expiry Background Daemon
    participant DB as Postgres DB
    participant Nomba as Nomba Financial Core

    loop Every 60 seconds
        Daemon->>DB: Query pending orders where timer_expires_at <= NOW()
        alt Expired orders found
            DB-->>Daemon: List of expired orders
            loop For each expired order
                Daemon->>DB: Fetch student wallet
                rect rgb(255, 240, 240)
                    Daemon->>DB: Deduct escrow hold from student wallet locked_balance
                    Daemon->>DB: Refund item price back to student available_balance
                    Daemon->>DB: Mark order status = Expired, penalty_status = Pending
                    Daemon->>DB: Commit Database Transaction
                end
                
                Daemon->>Nomba: POST /v2/transfers/bank (Pay N20 penalty to Vendor's Bank account)
                alt Transfer Success
                    Nomba-->>Daemon: Return transferRef (code 00)
                    Daemon->>DB: Update penalty_status = Paid, penalty_transfer_ref = ref
                else Transfer Failed/Exception
                    Nomba-->>Daemon: Return Error
                    Daemon->>DB: Flag log for manual administrative payout
                end
            end
        end
    end
```

---

## 🔒 Security Architecture

1. **Double-Spend Prevention (Row Locking)**:
   All wallet debiting, escrow holding, and settlement operations employ transactional locks. By utilizing PostgreSQL's `SELECT FOR UPDATE` (`with_for_update()`), the backend locks the user's wallet record for the duration of the request, ensuring concurrent payout requests or scanning operations do not trigger double-spending or balance mismatches.
   
2. **Nomba Webhook Signature Verification**:
   To prevent spoofing attacks, incoming webhook payloads are validated. The API reads headers (`nomba-signature` and `nomba-timestamp`), computes an HMAC signature using SHA256 over the raw request body, and compares it to the header signature:
   ```
   HMAC-SHA256(timestamp + raw_body, WEBHOOK_SECRET)
   ```

3. **Secure Offline QR Authentication**:
   The QR code contains a JSON Web Token (JWT) signed by the backend's secret key using the HMAC-SHA256 algorithm. The token contains the unique order ID, vendor ID, and expiration timestamp. When a vendor scans the code, the backend verifies the signature and validates that it hasn't expired. Since the QR is dynamically verified, it cannot be tampered with by students.

4. **Firebase Token Validation**:
   Frontend client authentication is fully managed by Firebase. The backend extracts the client's Bearer Token on every protected endpoint and validates it against Google's Firebase keys to authenticate the student or vendor's email, name, and uid before loading details.

---

## 📊 Financial Reconciliation Engine

To comply with fintech standards, the platform runs an automated reconciliation service (`/api/admin/reconciliation`).
- **Audit Target**: Confirmed orders where payouts were triggered.
- **Lookback Period**: Default 48 hours.
- **Checks Executed**:
  1. Verifies that every confirmed order has a corresponding Nomba transfer reference.
  2. Queries Nomba's live `/v2/transfers/{merchantTxRef}` status endpoint.
  3. Catches anomalies such as **Failed/Reversed** bank transfers or transactions that remain **Pending** past the expected processing threshold, categorizing issues as **Critical** or **Warning** and outputting a detailed administrative ledger report.

---

## 🛠️ Environment Configuration

Create a `.env` file in the root directory with the following variables:

```ini
# Database Connection URI (PostgreSQL)
DATABASE_URL=postgresql+asyncpg://<username>:<password>@<host>:<port>/<dbname>

# Backend Secret Key (used to sign JWTs for QR codes)
SECRET_KEY=your-super-secret-jwt-signing-key

# Nomba Financial Core Credentials
NOMBA_CLIENT_ID=your-nomba-client-id
NOMBA_CLIENT_SECRET=your-nomba-client-secret
NOMBA_ACCOUNT_ID=your-nomba-merchant-account-id
NOMBA_SUB_ACCOUNT_ID=your-nomba-sub-account-id
NOMBA_BASE_URL=https://api.nomba.com

# Nomba Webhook Verification Secret
WEBHOOK_SECRET=your-nomba-webhook-sig-key

# Firebase Service Account Credentials (JSON Stringified or file path)
FIREBASE_CREDENTIALS_PATH=/path/to/firebase-credentials.json
FIREBASE_CREDENTIALS={"type": "service_account", "project_id": ...}
GOOGLE_PROJECT_ID=your-firebase-project-id
GOOGLE_CLIENT_EMAIL=your-firebase-service-client-email
GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
TOKEN_URL=https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword
```

---

## 🚀 How to Run the Project Locally

### 1. Setup Backend
1. **Clone & Setup Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Apply Migrations**:
   ```bash
   alembic upgrade head
   ```
3. **Start the FastAPI Server**:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

### 2. Setup Frontend
Since the frontend consists of static files (HTML, CSS, JS), you can serve it using any HTTP server:
```bash
# Python 3
python -m http.server 3000
```
Open [http://localhost:3000](http://localhost:3000) in your browser. Ensure the browser matches the CORS settings set up in backend's `main.py`.

---

## 🚦 Endpoint Documentation
Once the backend is running, you can explore the endpoints interactively via Swagger UI:
- **Swagger Documentation**: [https://campuspay-3f39.onrender.com/docs](https://campuspay-3f39.onrender.com/docs)
- **Reconciliation Endpoint**: `/api/admin/reconciliation` (requires Admin credentials)
- **Service Health Check**: `/health` (returns service uptime, environment, and DB status)
