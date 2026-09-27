# Apex | Mobile-First Personal Productivity & Expense Management Tool WITH USER AUTHENTICATION

Apex is a clean, minimal, production-ready web application designed strictly **Mobile-First** for smartphones and modern browsers. It features secure **User Authentication (Register/Login/Logout)**, complete **multi-user data isolation**, a responsive **To-Do List Tracker**, and an **Expense Calculator** configured for Japanese Yen (¥).

---

## 📱 Mobile-First Design Principles
- **Touch-Optimized Targets**: All interactive elements (buttons, checkboxes, inputs, tabs, logout action) have a minimum tap area of **44px** to ensure seamless thumb operation.
- **Tailored Viewport**: Styled specifically for smartphone viewports (`<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">`), preventing accidental zoom and horizontal scroll leaks.
- **Neutral, High-Contrast Utility Aesthetic**: Built using Tailwind CSS with a clean slate and dark indigo palette. Zero non-functional fluff.
- **Offline & Fallback Resiliency**: Automatically synchronizes with the Flask REST backend when online, and caches user-isolated data locally in browser `localStorage` if network connectivity drops.

---

## 🛠️ Technology Stack
- **Backend**: Python 3.9+ with **Flask**
- **Authentication**: **Werkzeug** security (`generate_password_hash`, `check_password_hash`) + Flask Session management
- **Database / ORM**: **SQLite** via **Flask-SQLAlchemy** with foreign-key user relationships
- **Frontend Styling**: **Tailwind CSS** (via official CDN) + Google Fonts (Inter)
- **Frontend Logic**: **Vanilla JavaScript (ES6+)** with Fetch API (`credentials: 'same-origin'`)
- **Security**: Strict client-side HTML sanitization (XSS prevention), server-side input validation, password hashing, and session authentication guards
- **Deployment**: WSGI-ready (`gunicorn`), compatible with virtual environments (`venv`) and Vercel / Render / Railway

---

## 📁 Project Directory Structure
```text
finance-todo-app/
│
├── app.py                  # Flask backend, User models, Auth & REST APIs
├── requirements.txt        # Production Python dependencies
├── README.md               # Complete setup, usage, and deployment guide
└── templates/
    └── index.html          # Mobile-First Auth + Dashboard UI (Tailwind + JS)
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
Ensure you have **Python 3.9+** installed:
```bash
python --version
```

### 2. (Optional) Create & Activate a Virtual Environment
```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
python app.py
```
By default, the server listens on `http://0.0.0.0:5000`:
- **On your computer**: Open your browser at `http://localhost:5000`.
- **On your smartphone (Same Wi-Fi network)**: Open your smartphone browser and navigate to `http://<YOUR_LOCAL_IP>:5000` (e.g. `http://192.168.1.18:5000`).

---

## 🔐 Authentication & Multi-User Architecture

1. **Account Registration (`POST /api/register`)**:
   - Registers a unique username and securely hashed password.
   - Automatically initializes a server-side session and directs the user to their private dashboard.
2. **Account Login (`POST /api/login`)**:
   - Validates credentials against Werkzeug password hashes.
   - Sets secure session cookies (`HttpOnly`, `SameSite=Lax`).
3. **Session Verification (`GET /api/me`)**:
   - Verifies active session on page boot to transition between the Auth view and Dashboard seamlessly without page refreshes.
4. **Data Isolation**:
   - Each Task and Expense record contains a strict `user_id` Foreign Key.
   - All CRUD queries enforce `filter_by(user_id=current_user.id)` to guarantee privacy.
5. **Logout (`POST /api/logout`)**:
   - Clears the active session and cached local storage, returning to the login view.

---

## 💡 Core Features

### 1. Feature A: User Authentication & Security
- Sleek smartphone-optimized Sign In and Registration screens.
- Password visibility toggle (eye icon).
- Inline error banners for immediate feedback (e.g., username taken, invalid credentials).

### 2. Feature B: Navigation & App Shell
- Top header displaying active `@username` badge, connection status, and quick touch-friendly **Exit (Logout)** button.
- Segmented tab toggle for switching between **Tasks** and **Expenses** with live item count and spending preview badges.

### 3. Feature C: To-Do List Tracker (User-Isolated)
- **Task Creation**: High-contrast input field with a prominent 44px+ "Add" button.
- **Touchable Toggle**: Large custom checkbox that strikes through text and reduces opacity when completed.
- **Productivity Progress Bar**: Live calculation of completed vs. total tasks with completion percentage.
- **Filters**: Quickly filter tasks by `All`, `Active`, and `Done`.
- **Individual Deletion**: Instant item removal.
- **Clean Empty State**: Minimalist illustration when all tasks are complete.

### 4. Feature D: Expense Calculator & Log (User-Isolated)
- **Currency Support**: Formatted for Japanese Yen (**¥**) with thousand separators.
- **Live Dynamic Summary Card**: Displays **Total Spent**, total entries count, and average item cost.
- **Input Form**: Clean description and currency decimal input.
- **Itemized Log**: Mobile card feed showing description, formatted timestamp, price tag, and individual delete button.
- **Reset Data with Confirmation Modal**: Dedicated "Reset Data" option with a touch-friendly confirmation dialog to prevent accidental data loss.

---

## 📡 REST API Reference

| Method | Endpoint | Auth Required | Description | Payload Example |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/register` | No | Create user account & login | `{"username": "alex", "password": "secretpassword"}` |
| `POST` | `/api/login` | No | Authenticate user credentials | `{"username": "alex", "password": "secretpassword"}` |
| `POST` | `/api/logout` | Yes | Terminate current session | - |
| `GET` | `/api/me` | No | Check session authentication state | - |
| `GET` | `/api/tasks` | Yes | Get tasks for current user | - |
| `POST` | `/api/tasks` | Yes | Create task for current user | `{"title": "Buy groceries"}` |
| `PUT` | `/api/tasks/<id>` | Yes | Update completion state or title | `{"completed": true}` |
| `DELETE` | `/api/tasks/<id>` | Yes | Delete a specific task | - |
| `GET` | `/api/expenses` | Yes | Get expenses for current user | - |
| `POST` | `/api/expenses` | Yes | Log expense for current user | `{"description": "Coffee", "amount": 150.00}` |
| `DELETE` | `/api/expenses/<id>` | Yes | Delete a specific expense | - |
| `DELETE` | `/api/expenses/clear` | Yes | Clear all user expense records (Reset) | - |
| `GET` | `/api/health` | No | Service health check | - |
