# --- FLASK 3.0 / WERKZEUG 3.0 / SOCKETIO SHIM ---
import sys
import werkzeug.serving

if not hasattr(werkzeug.serving, 'run_with_reloader'):
    from werkzeug._reloader import run_with_reloader
    werkzeug.serving.run_with_reloader = run_with_reloader

import flask
from flask import globals as flask_globals

class StackMock:
    @property
    def top(self):
        try:
            return flask_globals._cv_request.get()
        except LookupError:
            return None

if not hasattr(flask, '_request_ctx_stack') or isinstance(flask._request_ctx_stack, type(flask_globals._cv_request)):
    mock_stack = StackMock()
    flask._request_ctx_stack = mock_stack
    flask._app_ctx_stack = mock_stack
# ---------------------------------------------------

import os
import random
import time
import cv2
import numpy as np
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import jetson.inference
import jetson.utils

app = Flask(__name__)
app.config['SECRET_KEY'] = 'jetson_scavenger_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

MODEL_PATH = "../models/scavenger_hunt/ssd-mobilenet.onnx"
LABELS_PATH = "../models/scavenger_hunt/labels.txt"

net = None
AVAILABLE_ITEMS = []

DEFAULT_ROUND_DURATION = 30  # seconds per round
DEFAULT_TOTAL_ROUNDS = 3     # how many rounds a match runs unless the host changes it
LEADERBOARD_SIZE = 5
PRE_ROUND_COUNTDOWN = 3       # seconds of "3-2-1" hype before a round's timer starts
STREAK_BONUS_PER_LEVEL = 15   # extra points per consecutive "found it first" round
STREAK_BONUS_MAX_LEVELS = 5

def load_vision_model():
    global net, AVAILABLE_ITEMS
    
    if os.path.exists(LABELS_PATH):
        with open(LABELS_PATH, 'r') as f:
            labels = [line.strip() for line in f if line.strip()]
        ignored = {'BACKGROUND', 'BACKGROUND_LOCATION', 'Extra Class', 'objects', 'Unknown'}
        AVAILABLE_ITEMS = [l for l in labels if l not in ignored]
        print(f"[*] Available items loaded: {AVAILABLE_ITEMS}")
    else:
        AVAILABLE_ITEMS = ["Cup", "Bottle", "Phone", "Book", "Glasses"]

    if os.path.exists(MODEL_PATH) and os.path.exists(LABELS_PATH):
        print(f"[*] Loading TensorRT ONNX Model: {MODEL_PATH}")
        net = jetson.inference.detectNet(
            model=MODEL_PATH,
            labels=LABELS_PATH,
            input_blob="input_0",
            output_cvg="scores",
            output_bbox="boxes",
            threshold=0.50
        )
        print("[+] Vision Model Loaded Successfully!")
    else:
        print("[!] Warning: ONNX model file not found on disk yet!")

rooms = {}

def build_leaderboard(room):
    ranked = sorted(room['players'].items(), key=lambda kv: kv[1]['score'], reverse=True)
    return [
        {'sid': sid, 'name': p['name'], 'score': p['score'], 'streak': p.get('streak', 0),
         'color': p.get('color'), 'avatar': p.get('avatar')}
        for sid, p in ranked[:LEADERBOARD_SIZE]
    ]

def conclude_round(room_id, reason):
    """Ends the current round exactly once, whatever the trigger (timeout, host skip,
    or everyone finding the target), and always leaves the room in a consistent state."""
    if room_id not in rooms:
        return
    room = rooms[room_id]
    if not room.get('round_active'):
        return  # already concluded by another trigger
    room['round_active'] = False

    # Anti-cheat: if the host skips a round, nobody keeps points from it -- even
    # players who had already found the target before the skip get reverted.
    if reason == 'skipped':
        for sid, pts in room.get('round_results', {}).items():
            if sid in room['players']:
                room['players'][sid]['score'] -= pts
        room['round_results'] = {}

    found_order = room.get('found_order', [])
    found_sids = set(found_order)
    found_list = [
        {'sid': sid, 'name': room['players'][sid]['name'], 'points': room['round_results'].get(sid, 0),
         'streak': room['players'][sid].get('streak', 0)}
        for sid in found_order if sid in room['players']
    ]
    missed_list = [
        {'sid': sid, 'name': p['name']}
        for sid, p in room['players'].items() if sid not in found_sids
    ]

    # Anyone who didn't find the target this round breaks their streak (unless the
    # round was voided by a host skip, in which case nobody's streak is penalized).
    if reason != 'skipped':
        for sid, p in room['players'].items():
            if sid not in found_sids:
                p['streak'] = 0

    messages = {
        'timeout': f"Time's up! {room['target_object']} round is over.",
        'skipped': f"Host skipped this round \u2014 no points were awarded.",
        'all_found': f"Everyone found the {room['target_object']}!"
    }

    total_rounds = room.get('total_rounds', DEFAULT_TOTAL_ROUNDS)
    is_final_round = room.get('round_number', 0) >= total_rounds

    # No more auto-advance: the leaderboard stays up until the host explicitly
    # continues (see 'continue_after_round'), so people can look at it as long as they like.
    socketio.emit('round_summary', {
        'target': room['target_object'],
        'reason': reason,
        'message': messages.get(reason, "Round over."),
        'found': found_list,
        'missed': missed_list,
        'leaderboard': build_leaderboard(room),
        'scores': room['players'],
        'round_number': room.get('round_number', 0),
        'total_rounds': total_rounds,
        'is_final_round': is_final_round
    }, room=room_id)

def round_timer_thread(room_id, round_number):
    while True:
        socketio.sleep(1)
        
        if room_id not in rooms:
            break
            
        room = rooms[room_id]
        
        if room.get('round_number') != round_number or not room.get('round_active'):
            break

        room['time_remaining'] -= 1
        current_time = room['time_remaining']

        socketio.emit('timer_tick', {
            'time_remaining': current_time,
            'duration': room['duration']
        }, room=room_id)

        if current_time <= 0:
            conclude_round(room_id, 'timeout')
            break

def start_next_round(room_id):
    """Kicks off the pre-round '3-2-1 get ready' hype beat, then hands off to
    _begin_round once it finishes. The round timer does not start ticking until
    the hype countdown is over."""
    if room_id not in rooms:
        return

    room = rooms[room_id]
    item_pool = room.get('item_pool', AVAILABLE_ITEMS)
    if not item_pool:
        item_pool = AVAILABLE_ITEMS

    target = random.choice(item_pool)
    duration = room.get('duration', DEFAULT_ROUND_DURATION)
    round_number = room.get('round_number', 0) + 1
    total_rounds = room.get('total_rounds', DEFAULT_TOTAL_ROUNDS)

    room['round_number'] = round_number
    room['round_active'] = False  # not active yet -- still in the hype countdown
    room['pending_target'] = target

    socketio.emit('round_countdown', {
        'countdown': PRE_ROUND_COUNTDOWN,
        'round_number': round_number,
        'total_rounds': total_rounds,
        'is_final_round': round_number >= total_rounds
    }, room=room_id)

    socketio.start_background_task(_begin_round, room_id, target, duration, round_number)

def _begin_round(room_id, target, duration, round_number):
    socketio.sleep(PRE_ROUND_COUNTDOWN)

    if room_id not in rooms:
        return
    room = rooms[room_id]
    # Bail out if the room moved on while we were counting down (e.g. host ended
    # the game or somehow triggered another round start in the meantime).
    if room.get('round_number') != round_number or room.get('round_active'):
        return

    room['target_object'] = target
    room['round_active'] = True
    room['start_time'] = time.time()
    room['duration'] = duration
    room['time_remaining'] = duration
    room['found_order'] = []
    room['round_results'] = {}

    socketio.emit('round_started', {
        'target': target,
        'duration': duration,
        'round_number': round_number,
        'total_rounds': room.get('total_rounds', DEFAULT_TOTAL_ROUNDS),
        'time_remaining': duration
    }, room=room_id)

    socketio.start_background_task(round_timer_thread, room_id, round_number)

@app.route('/')
def index():
    return render_template('index-v3.html')

@socketio.on('create_room')
def handle_create_room(data):
    room_id = str(random.randint(1000, 9999))
    player_name = data.get('name', 'Player 1')
    host_playing = data.get('host_playing', True)

    rooms[room_id] = {
        'host_sid': request.sid,
        'host_name': player_name,
        'host_playing': host_playing,
        'mode': data.get('mode', 'solo'),
        'players': {},
        'target_object': None,
        'round_active': False,
        'duration': data.get('duration', DEFAULT_ROUND_DURATION),
        'total_rounds': DEFAULT_TOTAL_ROUNDS,
        'item_pool': [],
        'round_number': 0,
        'time_remaining': 0,
        'locked': False
    }
    if host_playing:
        rooms[room_id]['players'][request.sid] = {
            'name': player_name, 'score': 0, 'is_host': True, 'streak': 0,
            'color': data.get('color'), 'avatar': data.get('avatar')
        }

    join_room(room_id)
    emit('room_created', {
        'room_id': room_id, 
        'host_sid': request.sid,
        'players': rooms[room_id]['players'],
        'round_active': False,
        'host_playing': host_playing,
        'locked': False
    })

@socketio.on('join_room')
def handle_join_room(data):
    room_id = str(data.get('room_id')).strip()
    player_name = data.get('name', 'Player 2')

    if room_id in rooms:
        room = rooms[room_id]
        if room.get('locked'):
            emit('error', {'message': 'This room is locked \u2014 the host has closed it to new players.'})
            return

        join_room(room_id)
        room['players'][request.sid] = {
            'name': player_name, 'score': 0, 'is_host': False, 'streak': 0,
            'color': data.get('color'), 'avatar': data.get('avatar')
        }
        
        # Notify existing room players about the new player
        emit('room_joined', {
            'room_id': room_id, 
            'host_sid': room['host_sid'],
            'players': room['players'],
            'round_active': room['round_active'],
            'locked': room.get('locked', False)
        }, room=room_id)

        # If a round is actively in progress, hop this joining player straight in
        if room['round_active']:
            emit('round_started', {
                'target': room['target_object'],
                'duration': room['duration'],
                'round_number': room['round_number'],
                'time_remaining': room['time_remaining']
            }, room=request.sid)
    else:
        emit('error', {'message': 'Room code not found!'})

@socketio.on('toggle_lock_room')
def handle_toggle_lock_room(data):
    room_id = str(data.get('room_id'))
    if room_id not in rooms:
        return
    room = rooms[room_id]
    if request.sid != room['host_sid']:
        emit('error', {'message': 'Only the host can lock the room!'})
        return
    room['locked'] = bool(data.get('locked', not room.get('locked', False)))
    socketio.emit('room_lock_updated', {'locked': room['locked']}, room=room_id)

@socketio.on('kick_player')
def handle_kick_player(data):
    room_id = str(data.get('room_id'))
    target_sid = data.get('sid')
    if room_id not in rooms:
        return
    room = rooms[room_id]
    if request.sid != room['host_sid']:
        emit('error', {'message': 'Only the host can kick players!'})
        return
    if target_sid == room['host_sid'] or target_sid not in room['players']:
        return

    kicked_name = room['players'][target_sid]['name']
    socketio.emit('kicked', {'message': 'You were removed from the room by the host.'}, room=target_sid)
    remove_player_from_room(target_sid, room_id, leave_socket_room=True)
    socketio.emit('toast_message', {'message': f'{kicked_name} was kicked from the room.'}, room=room_id)

@socketio.on('send_reaction')
def handle_send_reaction(data):
    room_id = str(data.get('room_id'))
    emoji = data.get('emoji')
    if room_id not in rooms or request.sid not in rooms[room_id]['players']:
        return
    if emoji not in ('👍', '🔥', '😂'):
        return
    name = rooms[room_id]['players'][request.sid]['name']
    socketio.emit('reaction_received', {'sid': request.sid, 'name': name, 'emoji': emoji}, room=room_id)

def remove_player_from_room(sid, room_id, leave_socket_room=False):
    if room_id not in rooms:
        return
    room = rooms[room_id]
    was_host = (room['host_sid'] == sid)

    if sid in room['players']:
        del room['players'][sid]
        leave_room(room_id, sid=sid) if leave_socket_room else leave_room(room_id)
    elif was_host:
        # Host was spectating (chose not to play) so isn't in the players dict,
        # but still needs to leave the socket.io room / be reassigned or cleaned up.
        leave_room(room_id, sid=sid) if leave_socket_room else leave_room(room_id)
    else:
        return  # sid wasn't part of this room

    if len(room['players']) == 0:
        del rooms[room_id]
    else:
        # Reassign host if original host left
        if was_host:
            new_host_sid = next(iter(room['players']))
            room['host_sid'] = new_host_sid
            room['players'][new_host_sid]['is_host'] = True

        emit('player_left', {
            'players': room['players'],
            'host_sid': room['host_sid']
        }, room=room_id)

@socketio.on('leave_room')
def handle_leave_room(data):
    room_id = str(data.get('room_id'))
    remove_player_from_room(request.sid, room_id)

@socketio.on('disconnect')
def handle_disconnect():
    for room_id in list(rooms.keys()):
        remove_player_from_room(request.sid, room_id)

@socketio.on('toggle_host_playing')
def handle_toggle_host_playing(data):
    room_id = str(data.get('room_id'))
    if room_id not in rooms:
        return
    room = rooms[room_id]
    if request.sid != room['host_sid']:
        return
    if room.get('round_active'):
        return  # can't change this mid-round

    playing = bool(data.get('playing', True))
    sid = request.sid

    if playing and sid not in room['players']:
        room['players'][sid] = {
            'name': room.get('host_name', 'Host'), 'score': 0, 'is_host': True, 'streak': 0,
            'color': data.get('color'), 'avatar': data.get('avatar')
        }
    elif not playing and sid in room['players']:
        room['host_name'] = room['players'][sid]['name']
        del room['players'][sid]

    room['host_playing'] = playing
    emit('player_list_updated', {'players': room['players']}, room=room_id)

@socketio.on('get_available_items')
def handle_get_items():
    emit('available_items_list', {'items': AVAILABLE_ITEMS})

@socketio.on('start_round')
def handle_start_round(data):
    room_id = str(data.get('room_id'))
    if room_id in rooms:
        if request.sid != rooms[room_id]['host_sid']:
            emit('error', {'message': 'Only the host can start the game!'})
            return

        if len(rooms[room_id]['players']) == 0:
            emit('error', {'message': 'Need at least one player to start!'})
            return

        selected_items = data.get('selected_items', [])
        duration = data.get('duration', DEFAULT_ROUND_DURATION)
        try:
            total_rounds = max(1, int(data.get('total_rounds', DEFAULT_TOTAL_ROUNDS)))
        except (TypeError, ValueError):
            total_rounds = DEFAULT_TOTAL_ROUNDS

        rooms[room_id]['item_pool'] = selected_items if len(selected_items) > 0 else AVAILABLE_ITEMS
        rooms[room_id]['duration'] = duration
        rooms[room_id]['total_rounds'] = total_rounds
        rooms[room_id]['round_number'] = 0
        start_next_round(room_id)

@socketio.on('skip_round')
def handle_skip_round(data):
    room_id = str(data.get('room_id'))
    if room_id not in rooms:
        return
    room = rooms[room_id]
    if request.sid != room['host_sid']:
        emit('error', {'message': 'Only the host can skip the round!'})
        return
    conclude_round(room_id, 'skipped')

def _end_match(room_id):
    if room_id not in rooms:
        return
    room = rooms[room_id]
    room['round_active'] = False
    ranked = sorted(room['players'].items(), key=lambda kv: kv[1]['score'], reverse=True)
    socketio.emit('match_ended', {
        'scores': room['players'],
        'ranking': [sid for sid, _ in ranked]
    }, room=room_id)

@socketio.on('end_game')
def handle_end_game(data):
    room_id = str(data.get('room_id'))
    if room_id not in rooms:
        return
    room = rooms[room_id]
    if request.sid != room['host_sid']:
        emit('error', {'message': 'Only the host can end the game!'})
        return
    _end_match(room_id)

@socketio.on('continue_after_round')
def handle_continue_after_round(data):
    """Host-triggered advance from the leaderboard screen -- replaces the old
    20-second auto-advance timer so the leaderboard stays up as long as the
    host wants it to."""
    room_id = str(data.get('room_id'))
    if room_id not in rooms:
        return
    room = rooms[room_id]
    if request.sid != room['host_sid']:
        emit('error', {'message': 'Only the host can continue to the next round!'})
        return
    if room.get('round_active'):
        return  # a round is already running; ignore stray/duplicate clicks

    total_rounds = room.get('total_rounds', DEFAULT_TOTAL_ROUNDS)
    if room.get('round_number', 0) >= total_rounds:
        _end_match(room_id)
    else:
        start_next_round(room_id)

@socketio.on('play_again')
def handle_play_again(data):
    room_id = str(data.get('room_id'))
    if room_id not in rooms:
        return
    room = rooms[room_id]
    if request.sid != room['host_sid']:
        emit('error', {'message': 'Only the host can start a new match!'})
        return

    for p in room['players'].values():
        p['score'] = 0
        p['streak'] = 0
    room['round_number'] = 0
    room['round_active'] = False
    socketio.emit('match_reset', {'players': room['players']}, room=room_id)

@socketio.on('process_frame')
def handle_process_frame(data):
    global net
    room_id = str(data.get('room_id'))
    if room_id not in rooms or not rooms[room_id]['round_active']:
        return
    if request.sid in rooms[room_id].get('found_order', []):
        return

    target = rooms[room_id]['target_object']
    image_bytes = data.get('image')
    if not image_bytes:
        return

    nparr = np.frombuffer(image_bytes, np.uint8)
    img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_np is None:
        return

    rgb_img = cv2.cvtColor(img_np, cv2.COLOR_BGR2RGBA)
    cuda_img = jetson.utils.cudaFromNumpy(rgb_img)

    target_found = False
    confidence = 0.0
    bbox = None
    img_h, img_w = img_np.shape[:2]

    if net is not None:
        detections = net.Detect(cuda_img)
        for det in detections:
            class_name = net.GetClassDesc(det.ClassID)
            if class_name.lower() == target.lower() and det.Confidence >= 0.50:
                target_found = True
                confidence = float(det.Confidence)
                bbox = [
                    max(0.0, det.Left / img_w),
                    max(0.0, det.Top / img_h),
                    min(1.0, det.Right / img_w),
                    min(1.0, det.Bottom / img_h)
                ]
                break

    emit('frame_result', {
        'detected': target_found, 
        'confidence': round(confidence * 100, 1),
        'bbox': bbox
    })

@socketio.on('confirm_target_found')
def handle_confirm_target(data):
    room_id = str(data.get('room_id'))
    if room_id not in rooms:
        return
    room = rooms[room_id]
    sid = request.sid

    if not room.get('round_active'):
        return
    if sid not in room['players']:
        return
    if sid in room.get('found_order', []):
        return  # this player already scored this round, ignore repeats

    elapsed_time = time.time() - room['start_time']
    time_left = max(0, room['duration'] - elapsed_time)

    base_points = 100
    speed_bonus = int(time_left * 10)
    rank = len(room['found_order']) + 1

    # Streak bonus: only the player who finds it FIRST in a round keeps/builds their
    # streak. Everyone else's streak was already reset to 0 in conclude_round the
    # last time they weren't first.
    player = room['players'][sid]
    if rank == 1:
        player['streak'] = player.get('streak', 0) + 1
    else:
        player['streak'] = 0
    streak_levels = min(player['streak'] - 1, STREAK_BONUS_MAX_LEVELS) if player['streak'] > 1 else 0
    streak_bonus = streak_levels * STREAK_BONUS_PER_LEVEL

    round_points = base_points + speed_bonus + streak_bonus

    player['score'] += round_points
    room.setdefault('found_order', []).append(sid)
    room.setdefault('round_results', {})[sid] = round_points

    socketio.emit('player_found', {
        'sid': sid,
        'name': player['name'],
        'target': room['target_object'],
        'points_earned': round_points,
        'speed_bonus': speed_bonus,
        'streak_bonus': streak_bonus,
        'streak': player['streak'],
        'elapsed_time': round(elapsed_time, 1),
        'rank': rank,
        'total_players': len(room['players']),
        'scores': room['players']
    }, room=room_id)

    # Once every current player has found it, no reason to keep the round running
    if len(room['found_order']) >= len(room['players']):
        conclude_round(room_id, 'all_found')

if __name__ == '__main__':
    load_vision_model()
    socketio.run(app, host='0.0.0.0', port=5000, ssl_context='adhoc', debug=False)
