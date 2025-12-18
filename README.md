# Estim - Intelligent Component Procurement System

## 1. Introduction & Theory
**Estim** is a specialized aggregator and procurement management system designed for electronics and robotics hardware. Its core philosophy is **"Unified Intelligence"**—bringing disjointed marketplace data into a single, cohesive interface.

In the current landscape, engineers and procurement managers have to manually visit multiple websites (Robu, Robocraze, ThinkRobotics, Evelta) to check prices, stock, and specifications. Estim automates this by:
1.  **Aggregating**: Sending parallel, asynchronous requests to scrape data from all vendors simultaneously.
2.  **Normalizing**: Converting different HTML structures into a standardized data model (Title, Price, SKU, Image).
3.  **Managing**: Providing a workspace to build "Purchase Orders" (POs) from these aggregated items.

## 2. System Architecture

Estim follows a **Modern Single-Page Application (SPA)** architecture with a decoupled Backend API.

```
[ User API Request ]  <--->  [ Nginx Proxy / Load Balancer ]
                                     |
                                     v
                           [ FastAPI Backend (Python) ]
                                /        \
           [ SQLite Database ] <          > [ Playwright Engine (Headless Chrome) ]
           (Auth, POs, Hist)                 (Scrapes External Vendors)
```

### Key Components

#### Frontend (`/frontend`)
-   **Framework**: React 18 + Vite (Fast HMR).
-   **Language**: TypeScript (Type safety for API responses).
-   **Styling**: Vanilla CSS with CSS Variables for a custom Design System (Orange/Black Theme).
-   **Routing**: Client-side routing for seamless transitions.

#### Backend (`/backend/app`)
-   **Core**: FastAPI (High-performance Async Python framework).
-   **Database**: SQLModel/SQLAlchemy + SQLite.
    -   *Why SQLite?* Zero-configuration, efficient for single-tenant or mid-sized internal tools.
-   **Scraper**: Playwright (Async).
    -   *Why Playwright?* It runs a real Headless Chromium browser, allowing it to render JavaScript-heavy sites (like React/Next.js store fronts) that simple `requests` cannot handle.

## 3. Directory Structure & File Guide

### Backend (`/backend`)
*   **`main.py`**: Entry point. Configures CORS and mounts routers.
*   **`models/`**: Database schemas (SQLModel).
    *   `base.py`: Defines `User`, `PurchaseOrder`, `POItem`, `SearchHistory`.
*   **`routers/`**: API Endpoints grouped by feature.
    *   `auth.py`: Login/Registration logic (JWT, Bcrypt).
    *   `marketplaces.py`: Handles search requests and scraping orchestration.
    *   `po.py`: CRUD operations for Purchase Orders and PDF generation.
*   **`services/`**: Business logic.
    *   `playwright.py`: **The Engine**. Contains the complex scraping logic, selectors, selector strategies (Generic vs Site-Specific), and page interaction code.

### Frontend (`/frontend/src`)
*   **`App.tsx`**: Main Layout and Router.
*   **`context/AuthContext.tsx`**: Manages Global Authentication State (User, Token).
*   **`components/`**:
    *   `ResultsTable.tsx`: Displays live search results.
    *   `ChosenItemsTable.tsx`: The "Cart". Logic for caching, editing SKUs, and Excel export lies here.
    *   `LoadingSpinner.tsx`: Components for the UI loading state.
    *   `ParticleLoader.tsx`: The custom canvas-based orange animation.
*   **`styles.css`**: The Global Stylesheet. Defines variables (`--color-primary`) and layout utilities.

## 4. Tech Stack

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | React 18 | UI Library |
| | TypeScript | Type Safety |
| | Vite | Build Tool |
| | XLSX | Excel Export Logic |
| **Backend** | Python 3.10+ | Runtime |
| | FastAPI | Web Framework |
| | SQLModel | ORM (Database) |
| | Playwright | Scraping Engine |
| | Jinja2 | HTML Templates (PDF) |
| | wkhtmltopdf | HTML to PDF Conversion |
| **Auth** | PyJWT | Token generation |
| | Passlib (Bcrypt) | Password Hashing |

## 5. Deployment Guide

### Prerequisites
-   Linux Server (Ubuntu 20.04/22.04 recommended).
-   Root/Sudo access.

### Step 1: Backend Setup
1.  Navigate to upload directory: `cd /var/www/estim/backend`
2.  Create Env: `python3 -m venv .venv`
3.  Activate: `source .venv/bin/activate`
4.  Install Deps: `pip install -r ../requirements.txt`
5.  **Crucial**: Install Browsers: `playwright install chromium` & `playwright install-deps`

### Step 2: Systemd Service
Create `/etc/systemd/system/estim-backend.service`:

```ini
[Unit]
Description=Estim Backend API
After=network.target

[Service]
User=root
WorkingDirectory=/var/www/estim/backend
ExecStart=/var/www/estim/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```
Enable it: `sudo systemctl enable --now estim-backend`

### Step 3: Frontend Build
1.  `cd /var/www/estim/frontend`
2.  `npm install`
3.  `npm run build` (Generates `dist/` folder)

### Step 4: Nginx Proxy
Configure Nginx to serve the static `dist` files and proxy `/api/*` requests to port 8000 (Backend).

## 6. Known Anti-Bot Limitations
The scraping engine uses "Headless" mode. Sophisticated e-commerce sites (like Robu/Robocraze) monitor for headless properties (User-Agent, Webdriver flag). If searches fail:
-   Use the **"Refresh Item"** button (retries specific URL).
-   Use the **SKU Column** manually if data is blocked.
-   The system is designed to be resilient, but external blocks are outside logic control.
