# PreTwin AI

> **Your Future. Your Style. Your Twin.**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Flask 3.0](https://img.shields.io/badge/Flask-3.0-green.svg)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-lightgrey.svg)](https://sqlite.org)
[![Security Tested](https://img.shields.io/badge/Security-PBKDF2%20Hashed-success.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Table of Contents
1. [Project Title & Tagline](#pretwin-ai)
2. [Project Overview & Problem Statement](#project-overview--problem-statement)
3. [Key Features Currently Implemented](#key-features-currently-implemented)
4. [Technology Stack](#technology-stack)
5. [Project Architecture & Directory Structure](#project-architecture--directory-structure)
6. [Prerequisites](#prerequisites)
7. [Installation & Setup Instructions](#installation--setup-instructions)
8. [Environment Variable Configuration](#environment-variable-configuration)
9. [Database Initialization & Migrations](#database-initialization--migrations)
10. [How to Run the Application Locally](#how-to-run-the-application-locally)
11. [Google OAuth 2.0 Setup](#google-oauth-20-setup)
12. [Authentication & Security Considerations](#authentication--security-considerations)
13. [Application UI Views & Walkthrough](#application-ui-views--walkthrough)
14. [API Endpoints Reference](#api-endpoints-reference)
15. [Testing & Troubleshooting](#testing--troubleshooting)
16. [Future Enhancements](#future-enhancements)
17. [Contribution Guidelines](#contribution-guidelines)
18. [License](#license)

---

## Project Overview & Problem Statement

### The Problem
Traditional e-commerce platforms operate on a purely reactive paradigm: a user must already know what they want, search for keywords, sift through sponsored advertisements, and manually compare complex technical specifications while guarding their budget. Furthermore, replenishment of recurring essentials, seasonal wardrobe planning, and budget management fall entirely on the shopper, resulting in decision fatigue, impulse buying, and missed discounts.

### The Solution: PreTwin AI
**PreTwin AI** is an intelligent, agentic e-commerce platform that models a personal **Digital Shopping Twin** for every customer. By observing user preferences, style tastes, financial boundaries, and historical purchasing cadence, PreTwin anticipates future requirements **before** the customer has to search for them.

Six specialized autonomous AI agents collaborate in a sequential pipeline to:
1. Construct and refine the user's living digital shopping twin.
2. Forecast replenishment dates and upcoming lifestyle needs.
3. Discover optimal catalogue matches without repetitive product listings.
4. Compare competing products side-by-side with clear trade-off analyses.
5. Enforce strict budget boundaries.
6. Provide transparent, human-readable explanations for every recommendation.

---

## Key Features Currently Implemented

### 1. Fairy-Tale Startup Opening Animation
- **Single Circular Orbit**: A graceful fairy character with fluttering wings flies in exactly one 360-degree circular round upon application launch.
- **Wand Magic & Sparkle Beam**: Halts at an upper-right vantage position, tilts its magic wand toward the center, and projects a glowing beam with animated sparkles (`✨`, `✦`, `✧`).
- **Brand Reveal & Tagline**: Dynamically reveals the glowing brand name **PreTwin** and the official motto:
  > *Your Future. Your Style. Your Twin.*
- **Accessible & Non-Intrusive**: Includes a 1-click **Skip Intro** button, respects the `prefers-reduced-motion` media query, and uses `sessionStorage` to prevent replay during internal page navigation.

### 2. Dual-Tabbed Secure Authentication (`/login`, `/signin`, `/register`)
- **Direct Login & Sign Up**: Zero forced demo accounts—visitors authenticate directly using their own credentials.
- **Sign In Tab**:
  - Email or username authentication.
  - Password visibility toggle (**SHOW / HIDE**).
  - Client-side and server-side validation.
- **Sign Up Tab**:
  - Full Name, Email Address, optional Username, Password, and Confirm Password fields.
  - Interactive **Password Strength Meter** with live character-length and complexity feedback.
  - Real-time password matching validation.
- **Google OAuth Integration**: Authentic "Continue with Google" button utilizing Google Identity Services (GIS) with built-in credential configuration guidance.

### 3. Top Navigation Bar & Profile Dropdown
- **Balanced Shortcut Bar**: Positioned alongside the 6 core shopping shortcuts:
  1. **Wishlist** (`/wishlist`)
  2. **Cart** (interactive slide-out drawer)
  3. **My Orders** (`/orders`)
  4. **Reward Points** (`/rewards`)
  5. **Savings Plan** (`/savings`)
  6. **Smart Cart** (`/smart-cart`)
  7. **Profile / Account Menu**:
     - *Unauthenticated*: Displays **Sign In** button routing to `/login`.
     - *Authenticated*: Displays the user's avatar and name with a dropdown menu offering links to **My Profile (AI Twin)**, **My Orders**, **Wishlist**, **Account Settings**, **Sign In / Switch Account**, and **Sign Out**.

### 4. 8 Intelligent AI Navigation Categories
The secondary navigation bar organizes AI capabilities into 8 distinct shopping modules:
1. **Personalization and Digital Twin** (`/twin`): View and update style affinities, preferred brands, category interests, and budget limits.
2. **Predictive Shopping Intelligence** (`/predictions`): Anticipate upcoming replenishment and seasonal needs with calculated confidence scores.
3. **Smart Product Discovery** (`/discovery`): Browse catalogue items with multi-filter sorting, category tagging, and price bracket selectors.
4. **Budget and Price Intelligence** (`/budget-intelligence`): Track price trends, monitor deal drops, and optimize spending allocations.
5. **Product Comparison and Decision Support** (`/comparison`): Compare specifications, advantages, and limitations across 2–4 selected items.
6. **Agentic AI Shopping Workflow** (`/agents`): Live telemetry visualization tracking execution duration and decision outputs of all 6 AI agents.
7. **Smart Cart and Shopping Automation** (`/smart-cart`): Automated reordering triggers, recurring basket items, and scheduled deliveries.
8. **Advanced Features for Future** (`/advanced-ai`): Visual digital shopping card, voice shopping assistant launcher, and calendar preview.

### 5. Future Predictive Shopping Calendar (`/calendar`)
- Interactive monthly and weekly calendar projecting predicted replenishment milestones, holiday sales, and planned purchases.
- Allows shoppers to schedule prospective purchases against payday cycles.

### 6. Floating AI Voice Shopping Assistant (`/chat`)
- Interactive floating assistant accessible from any page.
- Supports both text prompts and speech input via the browser's native **Web Speech API** (`webkitSpeechRecognition`).
- Synthesizes spoken vocal responses (`speechSynthesis`) alongside conversational answers and recommended product cards.

### 7. Smart Savings Plan & PreTwin Reward Points
- **Smart Savings Plan** (`/savings`): Allocate monthly savings targets toward specific high-value wishlisted items.
- **PreTwin Reward Points** (`/rewards`): Earn points on orders and convert directly at checkout (**100 Reward Points = ₹1 INR**).

### 8. Checkout & Payment Gateway Integration (`/checkout`)
- **Razorpay Sandbox Integration**: Seamless credit/debit card, UPI, and netbanking simulated payments via Razorpay modal.
- **Cash on Delivery (COD)**: Guaranteed full-featured checkout option with instant order confirmation and delivery status tracking.

---

## Technology Stack

| Layer | Technologies |
|---|---|
| **Backend Framework** | Python 3.10+ / 3.14, Flask 3.0.0, Flask-CORS |
| **Authentication & Security** | Werkzeug Security (PBKDF2 SHA-256 password hashing), Google Identity Services (GIS OAuth 2.0), HTTPOnly SameSite cookies |
| **Database** | SQLite 3 (`pretwinshop.db`) with relational schemas, Foreign Keys, and indexing |
| **Agentic Workflow** | Python OOP multi-agent pipeline (`ShoppingTwinAgent`, `PredictiveShoppingAgent`, `ProductDiscoveryAgent`, `ProductComparisonAgent`, `BudgetAwareRecommendationAgent`, `RecommendationExplanationAgent`) |
| **Frontend Framework** | HTML5, CSS3 (Custom Responsive PreTwin Design System), Vanilla JavaScript (ES6+) |
| **Audio & Voice** | Native Web Speech API (`SpeechRecognition` & `SpeechSynthesisUtterance`) |
| **Payments** | Razorpay Python SDK (`razorpay>=2.0.1`) + Cash on Delivery (COD) workflow |
| **Testing** | Pytest 9.1.1 test framework |

---

## Project Architecture & Directory Structure

```
PreTwinShopAI/
├── agents/                         # Multi-Agent AI system
│   ├── __init__.py                 # Agent exports
│   ├── orchestrator.py             # Master pipeline coordinator
│   ├── shopping_twin_agent.py      # Agent A: Digital twin builder
│   ├── predictive_shopping_agent.py# Agent B: Future needs predictor
│   ├── product_discovery_agent.py  # Agent C: Catalogue discovery engine
│   ├── product_comparison_agent.py # Agent D: Side-by-side spec comparator
│   ├── budget_recommendation_agent.py # Agent E: Budget constraint solver
│   └── explanation_agent.py        # Agent F: Justification generator
├── data/                           # Data initialization & seeds
│   ├── __init__.py
│   ├── schema.sql                  # Relational database schema
│   ├── seed_products.py            # High-variety catalogue dataset
│   └── seed_users.py               # Seed user models & preferences
├── docs/                           # Architecture specifications & documentation
│   └── architecture.md
├── static/                         # Static web assets
│   ├── css/
│   │   └── style.css               # PreTwin Master Stylesheet & Keyframes
│   ├── images/
│   │   ├── pretwin-logo.svg        # Fairytale winged brand logo
│   │   └── pretwin-wings-icon.svg  # Winged icon emblem
│   └── js/
│       ├── main.js                 # Core frontend logic & event handlers
│       ├── calendar.js             # Predictive calendar logic
│       ├── chat.js                 # AI voice chatbot engine
│       ├── discovery.js            # Product filtering & search
│       ├── comparison.js           # Multi-product comparison engine
│       ├── savings.js              # Smart savings calculations
│       ├── smart_cart.js           # Smart cart automation
│       └── twin.js                 # Digital Twin profile UI
├── templates/                      # Jinja2 HTML templates
│   ├── base.html                   # Master layout with dual navigation bars
│   ├── startup_intro.html          # Fairy-tale circular opening animation
│   ├── index.html                  # Main e-commerce storefront
│   ├── login.html                  # Direct Sign In & Sign Up tabbed view
│   ├── register.html               # Registration alias view
│   ├── twin.html                   # Digital Twin profile page
│   ├── predictions.html            # Future needs prediction page
│   ├── discovery.html              # Product discovery catalogue
│   ├── comparison.html             # Product comparison matrix
│   ├── agents.html                 # Multi-agent activity & telemetry
│   ├── smart_cart.html             # Smart Cart automation page
│   ├── calendar.html               # Predictive shopping calendar
│   ├── rewards.html                # PreTwin reward points dashboard
│   ├── savings.html                # Smart savings plan dashboard
│   ├── orders.html                 # Order history & tracking
│   ├── wishlist.html               # Saved items page
│   ├── checkout.html               # Razorpay & COD checkout page
│   ├── settings.html               # Twin & account settings
│   └── advanced_ai.html            # Advanced AI features hub
├── tests/                          # Automated Pytest test suite
│   ├── conftest.py                 # Shared test fixtures & DB mocks
│   ├── test_api.py                 # Core REST API endpoint tests
│   ├── test_auth_and_orders.py     # Auth, checkout & order tests
│   ├── test_circular_flight_and_navbar.py # Opening animation & navbar tests
│   ├── test_google_auth_and_intro.py      # Google OAuth & GIS tests
│   ├── test_signup_login_profile.py       # Login/Register tab & profile tests
│   └── test_new_features.py        # 8 AI features & rewards tests
├── .env.example                    # Safe environment template (placeholders only)
├── .gitignore                      # Comprehensive Git exclusion rules
├── app.py                          # Flask application entry point
├── config.py                       # Configuration & environment loader
├── database.py                     # SQLite connection pool & helpers
├── init_db.py                      # Database setup & seeding runner
├── requirements.txt                # Python project dependencies
├── routes_eight_features.py        # Modular routes for 8 AI modules
└── README.md                       # Project documentation
```

---

## Prerequisites

- **Python**: Version 3.10 or higher (tested on Python 3.14).
- **Git**: Version 2.25+ installed on your system.
- **Operating System**: Windows 10/11, macOS, or Linux.
- **Web Browser**: Any modern browser (Google Chrome or Microsoft Edge recommended for native Web Speech API voice support).

---

## Installation & Setup Instructions

Follow these steps in **Windows PowerShell** or terminal to set up the project locally:

### 1. Clone the Repository
```powershell
git clone https://github.com/LikithaC17/PreTwinAI.git
cd PreTwinAI
```

### 2. Create and Activate a Virtual Environment
```powershell
# Create virtual environment
python -m venv .venv

# Activate on Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# (On Linux / macOS: source .venv/bin/activate)
```

### 3. Install Required Dependencies
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Environment Variable Configuration

Create a local `.env` configuration file from the template:

```powershell
Copy-Item .env.example .env
```

Open `.env` in any text editor. Configure your environment variables using the reference below:

| Variable | Description | Default / Example Value |
|---|---|---|
| `SECRET_KEY` | Flask session cryptographic signing key | `your-secure-random-secret-key` |
| `DATABASE_PATH` | Path to the local SQLite database file | `pretwinshop.db` |
| `DEBUG` | Enable Flask debug mode & auto-reloader | `true` |
| `OPENAI_API_KEY` | *(Optional)* OpenAI API key for LLM explanations | `sk-your-openai-api-key-here` |
| `OPENAI_MODEL` | *(Optional)* OpenAI model name | `gpt-3.5-turbo` |
| `RAZORPAY_KEY_ID` | *(Optional)* Razorpay test key ID for card/UPI payments | `rzp_test_your_key_id` |
| `RAZORPAY_KEY_SECRET` | *(Optional)* Razorpay test key secret | `your_razorpay_secret_key` |
| `GOOGLE_CLIENT_ID` | *(Optional)* Google OAuth 2.0 Web Client ID | `your-id.apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | *(Optional)* Google OAuth 2.0 Web Client Secret | `your-google-client-secret` |

> **Note**: The application is 100% functional offline without paid third-party API keys. The deterministic heuristic engines, rule-based recommendation models, and COD checkout execute seamlessly out-of-the-box.

---

## Database Initialization & Migrations

PreTwin AI stores all relational data in a local SQLite database with automatic table creation and data seeding.

To initialize the database schema and populate realistic products and demo preferences, run:

```powershell
python init_db.py
```

This creates the following relational tables in `pretwinshop.db`:
- `users`: User credentials, hashed passwords, avatars, and registration timestamps.
- `products`: Multi-category catalogue items with MRP, selling price, ratings, stock, and specifications.
- `shopping_preferences`: Digital shopping twin attributes, brand affinities, and price tolerances.
- `purchase_history`: Historical orders used by Agent B to infer replenishment intervals.
- `predicted_needs`: Forward-looking replenishment and discovery events.
- `recommendation_history`: Ranked multi-agent candidate items with explanations.
- `orders` & `order_items`: Placed customer orders with payment methods (COD / Razorpay).
- `savings_plans`: Smart savings targets and scheduled allocations.
- `reward_ledger`: Point accruals, conversions, and checkout redemptions.
- `chat_messages`: Conversational transcripts for the floating voice assistant.

---

## How to Run the Application Locally

Start the Flask development server:

```powershell
python app.py
```

Once started, the console will output:
```
[app] Starting PreTwinShop AI on http://127.0.0.1:5000
 * Running on http://127.0.0.1:5000
```

Open your browser and navigate to:
- **Home / Storefront**: [http://127.0.0.1:5000/](http://127.0.0.1:5000/)
- **Sign In / Create Account**: [http://127.0.0.1:5000/login](http://127.0.0.1:5000/login) (or `/signin`)
- **Digital Shopping Twin**: [http://127.0.0.1:5000/twin](http://127.0.0.1:5000/twin)

---

## Google OAuth 2.0 Setup

To enable one-click Google Sign-In on the `/login` screen:

1. Visit the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing one.
3. Navigate to **APIs & Services > Credentials**.
4. Click **Create Credentials > OAuth Client ID**.
5. Select **Application Type: Web application**.
6. Under **Authorized JavaScript origins**, add:
   - `http://localhost:5000`
   - `http://127.0.0.1:5000`
7. Under **Authorized redirect URIs**, add:
   - `http://localhost:5000/api/auth/google/callback`
   - `http://127.0.0.1:5000/api/auth/google/callback`
8. Copy the generated **Client ID** into your `.env` file:
   ```ini
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   ```
9. Restart the Flask server. Google Identity Services will automatically activate on `/login`.

---

## Authentication & Security Considerations

PreTwin AI is engineered with defense-in-depth principles:
- **Password Security**: Passwords are never stored in plaintext. They are salted and hashed using PBKDF2 SHA-256 via `werkzeug.security.generate_password_hash`.
- **Session Protection**: Flask session cookies are signed with `SECRET_KEY`, flagged with `HttpOnly=True` to mitigate XSS cookie theft, and use `SameSite="Lax"` to prevent cross-site request forgery.
- **Credential Isolation**: Secrets are kept exclusively in `.env` (ignored by Git) and exposed via `config.py`.
- **No Mock User Bleed**: Unauthenticated sessions are strictly treated as guest sessions. The demo seed user is never automatically injected into anonymous sessions.
- **SQL Injection Prevention**: All database queries use parameterized SQL statements (`?` placeholders).

---

## Application UI Views & Walkthrough

| View | Route | Key Elements |
|---|---|---|
| **Magical Startup Intro** | `/` (fresh visit) | 360° circular flying fairy animation, wand particle beam, dynamic "PreTwin" text reveal, tagline fade-in, and Skip Intro button. |
| **Direct Sign In & Sign Up** | `/login`, `/signin` | Dual tab switcher, email/username login, password show/hide toggle, password strength meter, matching password checks, and Continue with Google. |
| **Top Navigation Bar** | Global | Winged fairytale logo, search bar, Wishlist, Cart, My Orders, Reward Points, Savings Plan, Smart Cart, and user Profile Icon with dropdown. |
| **Personalization Twin** | `/twin` | Brand affinity chips, category priorities, minimum & maximum budget sliders, shopping goals, and purchase history management. |
| **Predictive Intelligence** | `/predictions` | Predicted replenishment cards, confidence scores, estimated purchase dates, and direct discovery links. |
| **Smart Product Discovery** | `/discovery` | Multi-category catalogue grid, price filters, rating filters, sort options, and Add to Compare buttons. |
| **Product Comparison Matrix** | `/comparison` | Side-by-side comparison table evaluating pricing, technical specs, customer ratings, advantages, trade-offs, and Agent D's recommended pick. |
| **Multi-Agent Telemetry** | `/agents` | Sequential pipeline diagram (Agents A through F) with real-time execution duration metrics (ms) and decision audit logs. |
| **Predictive Calendar** | `/calendar` | Interactive monthly calendar displaying forecasted replenishment dates and budget milestones. |
| **Smart Savings Dashboard** | `/savings` | Goal setting, monthly automated savings allocations, and progress bars toward wishlisted items. |
| **Reward Points Center** | `/rewards` | Point balance tracking, transaction ledger, and conversion calculator (100 pts = ₹1 INR). |
| **Checkout & Order Flow** | `/checkout` | Address entry, reward points redemption, Cash on Delivery option, and Razorpay Sandbox gateway. |

---

## API Endpoints Reference

### Authentication
- `POST /api/auth/register` — Create a new user account with hashed password.
- `POST /api/auth/login` — Sign in with email or username + password.
- `POST /api/auth/logout` — Terminate session.
- `GET /api/auth/me` — Return current session authentication status.
- `POST /api/auth/google` — Verify Google OAuth ID token and establish session.

### Catalogue & Discovery
- `GET /api/products` — Retrieve products with optional `category`, `search`, `min_price`, `max_price`, `sort`, and `limit` filters.
- `GET /api/products/<id>` — Retrieve full details and specifications for a single product.
- `GET /api/categories` — List all distinct product categories and counts.

### Digital Twin & AI Workflow
- `GET /api/profile` — Fetch digital twin preferences and budget parameters.
- `PUT /api/profile` — Update category priorities, brand affinities, and price bounds.
- `GET /api/predictions` — Trigger Agent B and fetch predicted upcoming shopping needs.
- `POST /api/recommendations` — Execute the full 6-agent pipeline and return personalized recommendations with justification chains.
- `GET /api/agents/runs` — Fetch telemetry audit logs for recent multi-agent executions.

### Orders, Savings & Rewards
- `POST /api/checkout/calculate` — Validate basket prices, calculate discounts, apply reward point conversions, and return final order summary.
- `POST /api/orders` — Create a new order (Cash on Delivery or Razorpay).
- `GET /api/orders` — Retrieve user order history and tracking statuses.
- `GET /api/rewards/balance` — Get user reward points balance and equivalent rupee value.
- `GET /api/savings` — Fetch active savings plans and progress.
- `POST /api/savings` — Create a new smart savings plan.

### Chat & Voice Assistant
- `POST /api/chat` — Submit query to AI assistant; returns conversational response, voice text, and recommended product cards.
- `GET /api/chat/history` — Fetch recent session chat messages.

---

## Testing & Troubleshooting

### Running the Automated Test Suite
PreTwin AI includes a test suite covering database models, multi-agent pipelines, authentication, checkout, reward conversions, and UI keyframes:

```powershell
python -m pytest tests/ -v
```

### Common Issues & Solutions

1. **`ModuleNotFoundError: No module named 'flask'`**
   - Ensure your virtual environment is active (`.\.venv\Scripts\Activate.ps1`).
   - Run `pip install -r requirements.txt`.

2. **Database locked or table missing**
   - Run `python init_db.py` to reset and seed the SQLite tables.

3. **Google Sign-In shows configuration modal**
   - Add your Google Client ID to `.env` (`GOOGLE_CLIENT_ID=...`).
   - Ensure `http://localhost:5000` is listed under Authorized JavaScript origins in the Google Cloud Console.

4. **Speech Recognition not responding**
   - Ensure microphone permissions are allowed in your browser settings.
   - Use Google Chrome or Microsoft Edge for native Web Speech API compatibility.

---

## Future Enhancements

- [ ] **Multi-Vendor Marketplace Integration**: Seller onboarding portal with inventory sync.
- [ ] **Augmented Reality (AR) Preview**: 3D in-room furniture placement and virtual clothing try-on.
- [ ] **Federated Learning**: On-device twin preference updates preserving maximum user privacy.
- [ ] **Automated Bank UPI Auto-Pay**: Recurring monthly replenishment dispatch for household goods.

---

## Contribution Guidelines

Contributions are welcome! Please follow these steps:
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/smart-feature`).
3. Commit your changes with descriptive commit messages (`git commit -m 'Add smart feature'`).
4. Ensure all automated tests pass (`python -m pytest`).
5. Push to the branch (`git push origin feature/smart-feature`).
6. Open a Pull Request detailing your changes.

---

## License

This project is licensed under the **MIT License**. Feel free to use, modify, and distribute this software for personal or commercial projects.
