from flask import Flask, render_template, request, redirect, url_for, g
from flask_socketio import SocketIO, emit, join_room, leave_room
import sqlite3
import json
import random
import math
import uuid

from game_rules import RACES, CLASSES, ALL_ACTIONS, ALL_SPELLS, SKILLS_LIST

FULL_ACTION_LIST = ALL_ACTIONS + ALL_SPELLS
FULL_ACTIONS_DICT = [vars(a) for a in FULL_ACTION_LIST]

app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = 'secret_key'
socketio = SocketIO(app)
DATABASE = 'campaign_v66.db'

# --- 5e SPELL SLOT TABLE ---
SLOT_TABLE = [[0]*9, [2]+[0]*8, [3]+[0]*8, [4,2]+[0]*7, [4,3]+[0]*7, [4,3,2]+[0]*6, [4,3,3]+[0]*6, [4,3,3,1]+[0]*5, [4,3,3,2]+[0]*5, [4,3,3,3,1]+[0]*4, [4,3,3,3,2]+[0]*4, [4,3,3,3,2,1]+[0]*3, [4,3,3,3,2,1]+[0]*3, [4,3,3,3,2,1,1,0,0], [4,3,3,3,2,1,1,0,0], [4,3,3,3,2,1,1,1,0], [4,3,3,3,2,1,1,1,0], [4,3,3,3,2,1,1,1,1], [4,3,3,3,3,1,1,1,1], [4,3,3,3,3,2,1,1,1], [4,3,3,3,3,2,2,1,1]]

# Global State: encounters = { 'campaign_id': [list_of_combatants] }
encounters = {}

def get_db():
    db = getattr(g, '_database', None)
    if db is None: db = g._database = sqlite3.connect(DATABASE); db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(e):
    db = getattr(g, '_database', None)
    if db: db.close()

def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY, 
            campaign_id TEXT, 
            name TEXT, 
            data TEXT
        )''')
        db.commit()

def get_default_char():
    return {
        'name': 'New Character', 'race': '-', 
        'base_stats': {k:10 for k in ['STR','DEX','CON','INT','WIS','CHA']}, 
        'classes': [], 'inventory': [], 'skills': [], 'saves': [],
        'alignment': 'Unaligned', 'faith': '', 'backstory': '',
        'eyes': '', 'hair': '', 'skin': '', 'height': '',
        'hp_curr': 10, 'hp_max': 10,
        'slots_used': {'1':0, '2':0, '3':0, '4':0, '5':0, '6':0, '7':0, '8':0, '9':0, 'pact':0},
        'charges': {} 
    }

# --- ROUTES ---

@app.route('/')
def lobby():
    return render_template('lobby.html')

@app.route('/create_campaign', methods=['POST'])
def create_campaign():
    c_name = request.form.get('campaign_name')
    c_id = str(uuid.uuid4())[:8]
    encounters[c_id] = []
    print(f"[DEBUG] Campaign Created: {c_id}")
    return redirect(url_for('dm_screen', room=c_id))

@app.route('/dm/<room>')
def dm_screen(room):
    return render_template('dm.html', room=room)

@app.route('/join/<room>')
def join_campaign(room):
    db = get_db()
    saved = db.execute('SELECT id, name FROM characters WHERE campaign_id=?', (room,)).fetchall()
    # --- FIX WAS HERE: Use get_default_char() instead of None ---
    return render_template('builder.html', room=room, char=get_default_char(), races=RACES, classes=CLASSES, all_actions=FULL_ACTIONS_DICT, skills_list=SKILLS_LIST, saved=saved)

@app.route('/play/<room>/<char_id>')
def sheet(room, char_id):
    db = get_db()
    row = db.execute('SELECT data FROM characters WHERE id=? AND campaign_id=?', (char_id, room)).fetchone()
    if not row: return redirect(url_for('join_campaign', room=room))
    char = json.loads(row['data'])
    char['id'] = char_id 
    return render_template('sheet.html', room=room, char=char, actions=FULL_ACTIONS_DICT, skills=SKILLS_LIST, races=RACES)

# Builder Logic
@app.route('/builder_load', methods=['GET'])
def builder_load():
    room = request.args.get('room')
    char_id = request.args.get('id')
    db = get_db()
    saved = db.execute('SELECT id, name FROM characters WHERE campaign_id=?', (room,)).fetchall()
    
    char_data = None
    if char_id:
        row = db.execute('SELECT data FROM characters WHERE id=?', (char_id,)).fetchone()
        if row: char_data = json.loads(row['data'])
    
    if not char_data: char_data = get_default_char()

    return render_template('builder.html', room=room, char=char_data, races=RACES, classes=CLASSES, all_actions=FULL_ACTIONS_DICT, skills_list=SKILLS_LIST, saved=saved)

@app.route('/save_char', methods=['POST'])
def save_char():
    room = request.form['room']
    name = request.form['name']
    try: hpc = int(request.form.get('hp_curr', 10))
    except: hpc = 10
    try: hpm = int(request.form.get('hp_max', 10))
    except: hpm = 10
    
    # Preserve slots/charges if they exist in DB? For now reset to default on edit save for simplicity or grab existing
    # Simple approach: default
    slots_used = {'1':0, '2':0, '3':0, '4':0, '5':0, '6':0, '7':0, '8':0, '9':0, 'pact':0}
    charges = {}

    data = {
        'name': name, 'race': request.form['race'],
        'base_stats': {k:int(request.form.get(f'base_{k}',10)) for k in ['STR','DEX','CON','INT','WIS','CHA']},
        'classes': json.loads(request.form.get('classes_json', '[]')),
        'inventory': json.loads(request.form.get('inventory_json', '[]')),
        'skills': json.loads(request.form.get('skills_json', '[]')),
        'saves': json.loads(request.form.get('saves_json', '[]')),
        'alignment': request.form.get('alignment', 'Unaligned'),
        'faith': request.form.get('faith', ''),
        'backstory': request.form.get('backstory', ''),
        'eyes': request.form.get('eyes', ''), 'hair': request.form.get('hair', ''), 'skin': request.form.get('skin', ''), 'height': request.form.get('height', ''),
        'hp_curr': hpc, 'hp_max': hpm, 'slots_used': slots_used, 'charges': charges
    }
    
    db = get_db()
    exists = db.execute('SELECT id FROM characters WHERE name=? AND campaign_id=?', (name, room)).fetchone()
    
    char_id = None
    if exists:
        db.execute('UPDATE characters SET data=? WHERE id=?', (json.dumps(data), exists['id']))
        char_id = exists['id']
    else:
        cur = db.execute('INSERT INTO characters (campaign_id, name, data) VALUES (?,?,?)', (room, name, json.dumps(data)))
        char_id = cur.lastrowid
    db.commit()
    
    return redirect(url_for('sheet', room=room, char_id=char_id))

def update_db_char(char_id, data_dict):
    db = sqlite3.connect(DATABASE)
    db.execute('UPDATE characters SET data=? WHERE id=?', (json.dumps(data_dict), char_id))
    db.commit()
    db.close()

def get_char_data(char_id):
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    row = db.execute('SELECT data FROM characters WHERE id=?', (char_id,)).fetchone()
    db.close()
    if row: return json.loads(row['data'])
    return None

def calc_max_slots(char_data):
    eff_lvl = 0; pact_lvl = 0; pact_slots = 0; pact_tier = 0
    for c in char_data['classes']:
        name = c['name']; lvl = c['level']
        if name in ['Bard', 'Cleric', 'Druid', 'Sorcerer', 'Wizard']: eff_lvl += lvl
        elif name in ['Paladin', 'Ranger', 'Artificer']: eff_lvl += math.floor(lvl / 2)
        elif name in ['Fighter', 'Rogue']: eff_lvl += math.floor(lvl / 3)
        if name == 'Warlock': pact_lvl = lvl
    max_slots = {str(i+1): 0 for i in range(9)}
    if eff_lvl > 0:
        row = SLOT_TABLE[min(eff_lvl, 20)]
        for i, val in enumerate(row): max_slots[str(i+1)] = val
    if pact_lvl >= 1:
        if pact_lvl >= 1: pact_slots = 1; pact_tier = 1
        if pact_lvl >= 2: pact_slots = 2; 
        if pact_lvl >= 11: pact_slots = 3; 
        if pact_lvl >= 17: pact_slots = 4;
        # Fixed syntax error
        if pact_lvl >= 3: pact_tier = 2
        if pact_lvl >= 5: pact_tier = 3
        if pact_lvl >= 7: pact_tier = 4
        if pact_lvl >= 9: pact_tier = 5
    return max_slots, pact_slots, pact_tier

# --- SOCKET EVENTS ---

@socketio.on('join_campaign')
def handle_join(d):
    room = d['room']
    join_room(room)
    print(f"[DEBUG] Client {request.sid} joined Room: {room}")
    if d.get('is_dm'): join_room(f"dm_{room}")
    if room not in encounters: encounters[room] = []
    # Force Global Emit to Room
    socketio.emit('update_encounter', encounters[room], room=room)

@socketio.on('dm_add_combatant')
def handle_add_c(d):
    room = d['room']
    d['id'] = str(random.randint(10000, 99999))
    if room not in encounters: encounters[room] = []
    encounters[room].append(d)
    socketio.emit('update_encounter', encounters[room], room=room)

@socketio.on('dm_update_combatant')
def handle_upd_c(d):
    room = d['room']
    if room in encounters:
        for c in encounters[room]:
            if c['id'] == d['id']: c[d['key']] = d['val']; break
        socketio.emit('update_encounter', encounters[room], room=room)

@socketio.on('dm_remove_combatant')
def handle_rem_c(d):
    room = d['room']
    if room in encounters:
        encounters[room] = [c for c in encounters[room] if c['id'] != d['id']]
        socketio.emit('update_encounter', encounters[room], room=room)

@socketio.on('dm_sort_init')
def handle_sort(d):
    room = d['room']
    if room in encounters:
        encounters[room].sort(key=lambda x: int(x['init']), reverse=True)
        socketio.emit('update_encounter', encounters[room], room=room)

@socketio.on('dm_clear')
def handle_clear(d):
    room = d['room']
    encounters[room] = []
    socketio.emit('update_encounter', encounters[room], room=room)

@socketio.on('update_char_data')
def handle_char_upd(d):
    c = get_char_data(d['char_id'])
    if c:
        c[d['key']] = d['val']
        update_db_char(d['char_id'], c)

@socketio.on('roll_action')
def handle_roll(d):
    room = d.get('room')
    if not room: 
        print("[ERROR] Roll received with NO ROOM ID")
        return

    char_name = d.get('user')
    char_id = d.get('char_id')
    print(f"[DEBUG] Roll from {char_name} in Room {room}")
    
    def emit_res(res):
        if d.get('private'): socketio.emit('roll_result', res, room=f"dm_{room}")
        else: socketio.emit('roll_result', res, room=room)

    if d.get('lbl') == 'Initiative':
        total = random.randint(1, 20) + d['mod']
        emit_res({'user': char_name, 'lbl': 'Initiative', 'val': total})
        
        if room not in encounters: encounters[room] = []
        found = False
        for c in encounters[room]:
            if c['name'] == char_name: c['init'] = total; found = True
        if not found:
            hp = 0
            if char_id:
                cd = get_char_data(char_id)
                if cd: hp = cd['hp_max']
            encounters[room].append({'id': str(random.randint(1000,9999)), 'name': char_name, 'init': total, 'hp': hp, 'max_hp': hp, 'type': 'player'})
        socketio.emit('update_encounter', encounters[room], room=room)
        return

    cast_lvl = d.get('cast_lvl', 0)
    if cast_lvl > 0 and char_id:
        c_data = get_char_data(char_id)
        if c_data:
            max_slots, max_pact, pact_tier = calc_max_slots(c_data)
            std = str(cast_lvl); consumed = False
            
            if c_data['slots_used'].get(std,0) < max_slots.get(std,0):
                c_data['slots_used'][std] += 1; consumed = True
            elif max_pact > 0 and pact_tier >= cast_lvl and c_data['slots_used']['pact'] < max_pact:
                c_data['slots_used']['pact'] += 1; consumed = True
            
            if not consumed:
                emit_res({'user': 'System', 'lbl': f"Fizzle! No slots for Lvl {cast_lvl}!"}); return
            else:
                update_db_char(char_id, c_data)
                socketio.emit('update_slots_client', c_data['slots_used'], room=room)

    d20 = random.randint(1, 20)
    if d.get('sub_type') == 'hit':
        total = d20 + d['hit_mod']
        emit_res({'user': char_name, 'lbl': d['lbl'], 'sub_type': 'hit', 'val': total, 'formula': f"{d20}+{d['hit_mod']}", 'nat20': d20==20})
    
    elif d.get('sub_type') in ['dmg', 'heal', 'dice_effect']:
        base = str(d.get('dice', '0')); scale = d.get('scale_dice'); dmod = d.get('dmg_mod', 0)
        if '+' in base:
            try: p=base.split('+'); base=p[0].strip(); dmod+=int(p[1].strip())
            except: pass
        cnt = 0; sides = 0
        if 'd' in base:
            p = base.split('d'); cnt = int(p[0]) if p[0] else 1; sides = int(p[1])
            if scale and cast_lvl > d.get('base_lvl',0): 
                ex = cast_lvl - d.get('base_lvl',0)
                if 'd' in scale: sp = scale.split('d'); cnt += (int(sp[0] if sp[0] else 1) * ex)
                else: dmod += (int(scale) * ex)
            r_list = [random.randint(1, sides) for _ in range(cnt)]
            total = sum(r_list) + dmod
            form = f"[{','.join(map(str, r_list))}] + {dmod}"
        else: total = int(base) + dmod; form = f"{base} + {dmod}"
        emit_res({'user': char_name, 'lbl': d['lbl'], 'sub_type': d.get('sub_type'), 'val': total, 'formula': form})
    
    elif d.get('type') == 'skill':
        total = d20 + d['mod']
        emit_res({'user': char_name, 'lbl': d['lbl'], 'sub_type': 'skill', 'val': total})

if __name__ == '__main__':
    init_db()
    print("D&D Server V73 Running...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)