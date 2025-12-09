# Monopoly Project (Flask)

Small Flask-based Monopoly helper app. This repository contains the server, templates, and static assets needed to run a local test server.

**Quick Start (local)**

1. Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy environment example and set a secret:

```bash
cp .env.example .env
# edit .env to set MONOPOLY_SECRET
```

4. Run the app (development):

```bash
python3 app.py
# or
flask run --port 8080
```

5. Production (example using gunicorn):

```bash
gunicorn -w 4 "app:app" -b 0.0.0.0:8080
```

**Files you should commit**

- `app.py` — Flask app entrypoint
- `requirements.txt` — Python dependencies
- `Procfile` — for PaaS that uses Procfile (optional)
- `templates/` — Jinja2 templates
- `static/` — CSS and client assets
- `.gitignore` — ignore local artifacts (this file)
- `.env.example` — example env variables (no secrets)
- `README.md` — this file

**Notes**

- The app uses SQLite by default and creates `monopoly.db` in project root. This file is in `.gitignore`; if you want DB persisted in the repo for any reason, remove it from `.gitignore`.
- For multi-instance or production use, point `DATABASE_URL` to Postgres or other DB and install `psycopg[binary]`.
- Do NOT commit your `.env` with secrets. Keep `MONOPOLY_SECRET` private.

**Push to GitHub (example)**

```bash
git add .
git commit -m "Initial commit: add app, requirements, and docs"
git remote add origin <your-repo-url>
git push -u origin main
```

If you need, I can create a minimal `LICENSE` or help you set up a GitHub repo and push these changes.
# 🎲 Monopoly Game Helper - Python Flask Edition

A complete rewrite of the Monopoly game helper web application in **Python** using **Flask** framework.

## Features

- 🏠 **Create & Join Rooms** — Admin creates a game room, players join with a code
- 🏦 **Bank Management** — Configure money, properties, and cards
- 👥 **Player Tracking** — See all players, balances, debts, and net wealth
- 💰 **Debt System** — Record who owes whom, with settle functionality
- 📊 **Transaction History** — Track all money transfers
- 🧮 **Calculator** — Quick tools for taxes and transfers

## Project Structure

```
monopoly-project/
├── app.py                 # Flask backend with all routes and logic
├── requirements.txt       # Python dependencies
├── templates/             # Jinja2 HTML templates
│   ├── index.html        # Home page (create/join room)
│   ├── admin.html        # Admin panel
│   ├── game.html         # Main game view with players table
│   ├── bank.html         # Bank editor (money/properties/cards)
│   └── calculator.html   # Transaction calculator
└── static/
    └── styles.css        # Shared CSS styles
```

## Installation

### 1. Install Python (3.8+)

Make sure you have Python 3.8 or later installed.

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Flask Server

```bash
python app.py
```

The server will start on `http://localhost:8080`

## Usage

### For Admin
1. Go to `http://localhost:8080`
2. Click **Create Room** and enter your name
3. You'll get a room code to share with other players
4. Configure the number of players and click **Save & Open Bank Panel**
5. Set up bank details (money, properties, cards)
6. Click **Go to Game** to start

### For Players
1. Go to `http://localhost:8080`
2. Click **Join Room** 
3. Enter your name and the room code from the admin
4. Click **Join Room**
5. You'll enter the main game view

### In-Game Actions

#### Players Table
- Shows all players with their balance, debts (red), loans (green), and net wealth
- **Owe** button: Record a debt to another player
- **Loan** button: Record a loan given to another player

#### Bank Info Button
- Click the **🏦 Bank Info** button (bottom-right) to see:
  - Bank inventory (money, properties, cards)
  - All players and their balances
  - Outstanding debts
  - Recent transactions

#### Calculator
- **Tax Actions**: Deduct tax from a player
- **Transfer Money**: Move money between players
- **Record Debt**: Add a debt entry

## Data Model

### Room
```python
{
    'code': 'ABC123',
    'totalMoney': 20580,
    'players': [
        {'name': 'Alice', 'balance': 1500},
        {'name': 'Bob', 'balance': 1500}
    ],
    'debts': [
        {'from': 'Alice', 'to': 'Bob', 'amount': 100, 'note': '...'}
    ],
    'transactions': [
        {'ts': '2025-12-05T10:00:00', 'from': 'Alice', 'to': 'Bob', 'amount': 100, 'note': '...'}
    ],
    'money': [],
    'properties': [],
    'cards': []
}
```

## API Endpoints

### Authentication
- `POST /api/create-room` — Create new room as admin
- `POST /api/join-room` — Join existing room as player

### Room Management
- `GET /api/room/<room_code>` — Get room data
- `POST /api/admin/init` — Initialize room with player count
- `POST /api/room/<room_code>/update-bank` — Update bank inventory

### Players
- `GET /api/room/<room_code>/players` — List all players
- `PUT /api/room/<room_code>/players/<player_name>` — Update player data

### Debts & Transactions
- `POST /api/room/<room_code>/add-debt` — Record new debt
- `POST /api/room/<room_code>/settle-debt` — Settle a debt
- `POST /api/room/<room_code>/transaction` — Record transaction

## Technologies Used

- **Backend**: Flask (Python)
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Templating**: Jinja2
- **Storage**: In-memory (Python dictionaries)

## Future Enhancements

- 💾 Database persistence (SQLite, PostgreSQL)
- 🔐 User authentication and room protection
- 📱 Mobile app
- 🌐 Real-time multiplayer sync with WebSockets
- 📊 Game analytics and statistics
- 🎨 Dark mode and theme customization

## License

ISC

---

Made with ❤️ for Monopoly enthusiasts
