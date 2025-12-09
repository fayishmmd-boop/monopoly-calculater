"""
Monopoly Game Helper - Flask Backend
Manages game rooms, players, bank, debts, and transactions.
"""

from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import os
import uuid
from datetime import datetime
from functools import wraps

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func

app = Flask(__name__)
app.secret_key = os.environ.get('MONOPOLY_SECRET', 'monopoly-game-secret-2025')

# SQLite database in the project directory
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'monopoly.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

def generate_room_code():
    """Generate a random 6-character room code."""
    return str(uuid.uuid4()).split('-')[0][:6].upper()

def login_required(f):
    """Decorator to ensure player is logged in."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'room_code' not in session or 'player_name' not in session:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


# ============ DB MODELS ============
class Room(db.Model):
    __tablename__ = 'rooms'
    code = db.Column(db.String(12), primary_key=True)
    totalMoney = db.Column(db.Integer, default=20580)
    items = db.Column(db.JSON, default=list)
    money = db.Column(db.JSON, default=list)
    properties = db.Column(db.JSON, default=list)
    cards = db.Column(db.JSON, default=list)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

class Player(db.Model):
    __tablename__ = 'players'
    id = db.Column(db.Integer, primary_key=True)
    room_code = db.Column(db.String(12), db.ForeignKey('rooms.code'), index=True)
    name = db.Column(db.String(128), nullable=False)
    balance = db.Column(db.Float, default=1500.0)
    slot = db.Column(db.Integer, default=0)

class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    room_code = db.Column(db.String(12), db.ForeignKey('rooms.code'), index=True)
    ts = db.Column(db.DateTime(timezone=True), server_default=func.now())
    from_player = db.Column(db.String(128))
    to_player = db.Column(db.String(128))
    amount = db.Column(db.Float)
    note = db.Column(db.String(256))

class Debt(db.Model):
    __tablename__ = 'debts'
    id = db.Column(db.Integer, primary_key=True)
    room_code = db.Column(db.String(12), db.ForeignKey('rooms.code'), index=True)
    from_player = db.Column(db.String(128))
    to_player = db.Column(db.String(128))
    amount = db.Column(db.Float)
    note = db.Column(db.String(256))


def init_db():
    # Ensure we create tables within the Flask application context
    with app.app_context():
        db.create_all()


def _room_to_dict(room_code):
    room = Room.query.get(room_code)
    if not room:
        return None

    players = Player.query.filter_by(room_code=room_code).order_by(Player.slot).all()
    transactions = Transaction.query.filter_by(room_code=room_code).order_by(Transaction.ts).all()
    debts = Debt.query.filter_by(room_code=room_code).all()

    return {
        'code': room.code,
        'totalMoney': room.totalMoney,
        'players': [{'name': p.name, 'balance': p.balance} for p in players],
        'transactions': [
            {'ts': t.ts.isoformat(), 'from': t.from_player, 'to': t.to_player, 'amount': t.amount, 'note': t.note}
            for t in transactions
        ],
        'debts': [
            {'id': d.id, 'from': d.from_player, 'to': d.to_player, 'amount': d.amount, 'note': d.note}
            for d in debts
        ],
        'items': room.items or [],
        'money': room.money or [],
        'properties': room.properties or [],
        'cards': room.cards or []
    }


def get_or_create_room(room_code):
    room = Room.query.get(room_code)
    if not room:
        room = Room(code=room_code)
        db.session.add(room)
        db.session.commit()
    return _room_to_dict(room_code)


def init_bank(room_code, admin_name, player_count=4):
    room = Room.query.get(room_code)
    if not room:
        room = Room(code=room_code)
        db.session.add(room)
        db.session.commit()

    # remove existing players for this room
    Player.query.filter_by(room_code=room_code).delete()
    db.session.commit()

    for i in range(player_count):
        name = admin_name if i == 0 else ''
        p = Player(room_code=room_code, name=name, balance=1500.0, slot=i)
        db.session.add(p)
    db.session.commit()
    return _room_to_dict(room_code)

# ============ ROUTES ============

@app.route('/')
def index():
    """Home page - create or join room."""
    return render_template('index.html')

@app.route('/api/create-room', methods=['POST'])
def api_create_room():
    """Create a new room and initialize as admin."""
    data = request.json
    admin_name = data.get('admin_name', '').strip()
    
    if not admin_name:
        return jsonify({'error': 'Admin name required'}), 400
    
    room_code = generate_room_code()
    init_bank(room_code, admin_name, 4)
    
    session['room_code'] = room_code
    session['player_name'] = admin_name
    session['user_role'] = 'admin'
    
    return jsonify({
        'room_code': room_code,
        'redirect': url_for('admin_panel')
    })

@app.route('/api/join-room', methods=['POST'])
def api_join_room():
    """Join an existing room as a player."""
    data = request.json
    player_name = data.get('player_name', '').strip()
    room_code = data.get('room_code', '').strip().upper()
    
    if not player_name or not room_code:
        return jsonify({'error': 'Player name and room code required'}), 400
    
    # Ensure room exists
    room_obj = Room.query.get(room_code)
    if not room_obj:
        return jsonify({'error': 'Room not found'}), 404

    # Find first empty player slot
    empty_player = Player.query.filter_by(room_code=room_code, name='').order_by(Player.slot).first()
    if empty_player:
        empty_player.name = player_name
        db.session.add(empty_player)
    else:
        max_slot = db.session.query(db.func.max(Player.slot)).filter_by(room_code=room_code).scalar() or 0
        new_slot = (max_slot + 1) if max_slot is not None else 0
        new_player = Player(room_code=room_code, name=player_name, balance=1500.0, slot=new_slot)
        db.session.add(new_player)

    db.session.commit()
    
    session['room_code'] = room_code
    session['player_name'] = player_name
    session['user_role'] = 'player'
    
    return jsonify({
        'room_code': room_code,
        'redirect': url_for('game')
    })

@app.route('/api/admin/init', methods=['POST'])
def api_admin_init():
    """Initialize admin and bank for a room."""
    if session.get('user_role') != 'admin':
        return jsonify({'error': 'Admin only'}), 403
    
    data = request.json
    room_code = session.get('room_code')
    admin_name = data.get('admin_name', '').strip()
    player_count = int(data.get('player_count', 4))
    
    if not admin_name:
        return jsonify({'error': 'Admin name required'}), 400
    
    init_bank(room_code, admin_name, player_count)
    return jsonify({'success': True})

@app.route('/admin')
@login_required
def admin_panel():
    """Admin panel to configure room and players."""
    if session.get('user_role') != 'admin':
        return redirect(url_for('index'))
    
    room_code = session.get('room_code')
    room = get_or_create_room(room_code)
    
    return render_template('admin.html', room_code=room_code, room=room)

@app.route('/bank')
@login_required
def bank_panel():
    """Bank editor for admin."""
    if session.get('user_role') != 'admin':
        return redirect(url_for('index'))
    
    room_code = session.get('room_code')
    room = get_or_create_room(room_code)
    
    return render_template('bank.html', room_code=room_code, room=room)

@app.route('/game')
@login_required
def game():
    """Main game view - shows players, debts, transactions."""
    room_code = session.get('room_code')
    player_name = session.get('player_name')
    room = get_or_create_room(room_code)
    
    # Calculate owes/owed for this player
    owes = sum(d['amount'] for d in room['debts'] if d['from'] == player_name)
    owed = sum(d['amount'] for d in room['debts'] if d['to'] == player_name)
    
    return render_template('game.html', 
                         room_code=room_code,
                         player_name=player_name,
                         room=room,
                         owes=owes,
                         owed=owed)

@app.route('/calculator')
def calculator():
    """Bank calculator tool."""
    room_code = session.get('room_code')
    if not room_code:
        return redirect(url_for('index'))
    
    room = get_or_create_room(room_code)
    return render_template('calculator.html', room_code=room_code, room=room)

# ============ API ENDPOINTS ============

@app.route('/api/room/<room_code>', methods=['GET'])
def get_room(room_code):
    """Get room data."""
    room = get_or_create_room(room_code)
    return jsonify(room)

@app.route('/api/room/<room_code>/update-bank', methods=['POST'])
def update_bank(room_code):
    """Update bank details (money, properties, cards)."""
    if session.get('user_role') != 'admin':
        return jsonify({'error': 'Admin only'}), 403
    
    data = request.json
    room_obj = Room.query.get(room_code)
    if not room_obj:
        return jsonify({'error': 'Room not found'}), 404

    if 'money' in data:
        room_obj.money = data['money']
    if 'properties' in data:
        room_obj.properties = data['properties']
    if 'cards' in data:
        room_obj.cards = data['cards']

    db.session.add(room_obj)
    db.session.commit()
    return jsonify({'success': True, 'room': _room_to_dict(room_code)})

@app.route('/api/room/<room_code>/add-debt', methods=['POST'])
def add_debt(room_code):
    """Record a new debt."""
    data = request.json
    from_player = data.get('from')
    to_player = data.get('to')
    amount = float(data.get('amount', 0))
    note = data.get('note', '')
    
    if amount <= 0 or not from_player or not to_player:
        return jsonify({'error': 'Invalid debt data'}), 400
    
    room_obj = Room.query.get(room_code)
    if not room_obj:
        return jsonify({'error': 'Room not found'}), 404

    d = Debt(room_code=room_code, from_player=from_player, to_player=to_player, amount=amount, note=note)
    db.session.add(d)
    db.session.commit()
    debts = Debt.query.filter_by(room_code=room_code).all()
    return jsonify({'success': True, 'debts': [ {'id': dd.id, 'from': dd.from_player, 'to': dd.to_player, 'amount': dd.amount, 'note': dd.note} for dd in debts ]})

@app.route('/api/room/<room_code>/settle-debt', methods=['POST'])
def settle_debt(room_code):
    """Settle a debt by transferring money."""
    data = request.json
    debt_id = data.get('id')
    debt_idx = data.get('idx')

    # Find debt by id or index
    if debt_id:
        debt = Debt.query.filter_by(id=int(debt_id), room_code=room_code).first()
    elif debt_idx is not None:
        debts = Debt.query.filter_by(room_code=room_code).order_by(Debt.id).all()
        try:
            debt = debts[int(debt_idx)]
        except Exception:
            debt = None
    else:
        debt = None

    if not debt:
        return jsonify({'error': 'Debt not found'}), 400

    # Apply balances
    payer = Player.query.filter_by(room_code=room_code, name=debt.from_player).first()
    payee = Player.query.filter_by(room_code=room_code, name=debt.to_player).first()
    if payer:
        payer.balance = (payer.balance or 0) - debt.amount
        db.session.add(payer)
    if payee:
        payee.balance = (payee.balance or 0) + debt.amount
        db.session.add(payee)

    # Record transaction
    t = Transaction(room_code=room_code, from_player=debt.from_player, to_player=debt.to_player, amount=debt.amount, note=f"settle: {debt.note}")
    db.session.add(t)

    # Remove debt
    db.session.delete(debt)
    db.session.commit()

    return jsonify({'success': True, 'room': _room_to_dict(room_code)})

@app.route('/api/room/<room_code>/transaction', methods=['POST'])
def add_transaction(room_code):
    """Record a transaction between players."""
    data = request.json
    from_player = data.get('from')
    to_player = data.get('to')
    amount = float(data.get('amount', 0))
    note = data.get('note', '')
    
    if amount <= 0 or not from_player or not to_player:
        return jsonify({'error': 'Invalid transaction data'}), 400
    
    room_obj = Room.query.get(room_code)
    if not room_obj:
        return jsonify({'error': 'Room not found'}), 404

    payer = Player.query.filter_by(room_code=room_code, name=from_player).first()
    payee = Player.query.filter_by(room_code=room_code, name=to_player).first()
    if payer:
        payer.balance = (payer.balance or 0) - amount
        db.session.add(payer)
    if payee:
        payee.balance = (payee.balance or 0) + amount
        db.session.add(payee)

    t = Transaction(room_code=room_code, from_player=from_player, to_player=to_player, amount=amount, note=note)
    db.session.add(t)
    db.session.commit()

    transactions = Transaction.query.filter_by(room_code=room_code).order_by(Transaction.ts).all()
    return jsonify({'success': True, 'transactions': [ {'ts': tr.ts.isoformat(), 'from': tr.from_player, 'to': tr.to_player, 'amount': tr.amount, 'note': tr.note} for tr in transactions ]})

@app.route('/api/room/<room_code>/players', methods=['GET'])
def get_players(room_code):
    """Get all players in a room."""
    players = Player.query.filter_by(room_code=room_code).order_by(Player.slot).all()
    return jsonify([{'name': p.name, 'balance': p.balance} for p in players])

@app.route('/api/room/<room_code>/players/<player_name>', methods=['PUT'])
def update_player(room_code, player_name):
    """Update a player's data."""
    data = request.json
    player = Player.query.filter_by(room_code=room_code, name=player_name).first()
    if not player:
        return jsonify({'error': 'Player not found'}), 404

    if 'balance' in data:
        player.balance = float(data['balance'])
    if 'name' in data:
        player.name = data['name']

    db.session.add(player)
    db.session.commit()
    return jsonify({'success': True, 'player': {'name': player.name, 'balance': player.balance}})

@app.route('/api/room/<room_code>/bank-transfer', methods=['POST'])
def bank_transfer(room_code):
    """Transfer money between bank and a player.
    - direction='to_bank': player gives money to bank
    - direction='from_bank': bank gives money to player
    """
    data = request.json
    player_name = data.get('player')
    amount = float(data.get('amount', 0))
    direction = data.get('direction', 'from_bank')  # 'from_bank' or 'to_bank'
    note = data.get('note', '')

    if amount <= 0 or not player_name:
        return jsonify({'error': 'Invalid transfer data'}), 400

    if direction not in ('from_bank', 'to_bank'):
        return jsonify({'error': 'Invalid direction (use from_bank or to_bank)'}), 400

    room_obj = Room.query.get(room_code)
    if not room_obj:
        return jsonify({'error': 'Room not found'}), 404

    player = Player.query.filter_by(room_code=room_code, name=player_name).first()
    if not player:
        return jsonify({'error': 'Player not found'}), 404

    # Update bank money and player balance
    if direction == 'from_bank':
        # Bank gives money to player
        room_obj.totalMoney = (room_obj.totalMoney or 0) - amount
        player.balance = (player.balance or 0) + amount
        transaction_note = f"Bank → {player_name}: {note}" if note else f"Bank → {player_name}"
    else:
        # Player gives money to bank
        room_obj.totalMoney = (room_obj.totalMoney or 0) + amount
        player.balance = (player.balance or 0) - amount
        transaction_note = f"{player_name} → Bank: {note}" if note else f"{player_name} → Bank"

    db.session.add(room_obj)
    db.session.add(player)

    # Record transaction
    t = Transaction(
        room_code=room_code,
        from_player='Bank' if direction == 'from_bank' else player_name,
        to_player=player_name if direction == 'from_bank' else 'Bank',
        amount=amount,
        note=transaction_note
    )
    db.session.add(t)
    db.session.commit()

    return jsonify({'success': True, 'room': _room_to_dict(room_code)})

if __name__ == '__main__':
    # Ensure database and tables exist
    init_db()
    app.run(debug=True, host='0.0.0.0', port=8080)
