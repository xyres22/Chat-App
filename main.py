from flask import render_template,redirect, Flask, request, session,url_for
from flask_socketio import SocketIO, leave_room, join_room, send, emit
from datetime import datetime
current_datetime = datetime.now()
import random
from string import  ascii_letters, digits



app = Flask(__name__)
app.config['SECRET_KEY'] = 'asdasdsad'
socketio = SocketIO(app)


chat_rooms = {}
################################################
username_to_sid = {}
captured_images = []
################################################
def create_room_code():
    code = ''.join(random.choice(ascii_letters+digits) for _ in range(6))
    return code



@app.route('/',methods=['GET','POST'])
def main():
    session.clear()
    if request.method == 'POST':
        username = request.form.get('username')
        code = request.form.get('room_code')
        join_room = request.form.get('join_btn')
        create_room = request.form.get('create_btn')

        if not username:
            return render_template('setup.html',alert='Please enter username!', username=username, room_code = code)
        if join_room != None and not code:
            return render_template('setup.html',alert='Please enter code!', username=username, room_code = code)
        elif join_room != None and code in chat_rooms: 
            if chat_rooms[code]['max_users'] != 0 and chat_rooms[code]['users'] >= chat_rooms[code]['max_users']:
                return render_template('setup.html',alert='Room is full!', username=username, room_code = code)
            elif username in chat_rooms[code]['list']:
                return render_template('setup.html',alert ='Username already exists',username = username, room_code = code)

        room = code
        if create_room != None:
            room = create_room_code()
            max_users = request.form.get('members_quantity')
            chat_rooms[room]= {'users': 0 ,'messages':[],'max_users':0,'list':[],'leader':username}
            if max_users:
                chat_rooms[room]['max_users'] = int(max_users)
        elif room not in chat_rooms:
            return render_template('setup.html',alert='Room does not exist! Try again or create a new one.', username=username, room_code = code)

        
        session["room"] = room
        session["name"] = username
        return redirect(url_for("chat_room"))

    return render_template('setup.html')







@app.route('/room')
def chat_room():
    room = session.get('room')
    curr_name = session.get('name') 
    if room is None or session.get('name') is None or room not in chat_rooms:
        return redirect(url_for("main"))
    else:
        users_count = chat_rooms.get(session.get('room'), {}).get('users', 0)
        return render_template('chat.html',users_count=users_count, room = room, curr_user = curr_name ,messages = chat_rooms[room]['messages'])

########################### CHANGE LEADER SOCKET ###########################

@socketio.on('changeLeader')
def changeLeader(data):
    room = session.get('room')
    users = chat_rooms[room]['list']
    current_user = session.get('name')
    new_Leader = data['user']

    if current_user == chat_rooms[room]['leader']:
        chat_rooms[room]['leader'] = new_Leader
        emit('update_user_list', {'users_list': users, 'current_user': current_user, 'leader': new_Leader}, broadcast=True)
    else:
        emit('no_permission',{'message':'You are not a leader.'})

########################### CONNECT SOCKET  ###########################

@socketio.on("connect")
def connect(auth):
    room = session.get('room')
    username = session.get('name')

    if not room or not username:
        return
    
    if room not in chat_rooms:
        leave_room(room)
        return
    
    join_room(room)
################################################
    username_to_sid[username] = request.sid
################################################
    chat_rooms[room]['users'] += 1
    chat_rooms[room]['list'].append(username)
    update_user_list(room,username)
    update_user_count(room)

    current_datetime = datetime.now()
    connect_time = current_datetime.strftime("%H:%M:%S %d-%m-%Y ")
    send({'name':username,'message':' has entered a room.','time':connect_time,'type':'connection'}, to =room)

def update_user_count(room):
    if room in chat_rooms:
        users_count = chat_rooms[room].get('users', 0)  # Use 0 as default if room exists but users count is not set
    else:
        users_count = 0  # Set users count to 0 if room doesn't exist
    emit('user_count_update', {'room': room, 'users_count': users_count}, room=room)

def update_user_list(room,leader):
    current_user_test = session.get('name')
    users_list = chat_rooms.get(room, {}).get('list', [])  # Get the list of users in the room
    leader = chat_rooms[room].get('leader')
    emit('update_user_list', {'users_list': users_list, 'leader' : leader, 'current_user' : current_user_test}, room=room)



@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    username = session.get('name')
    leave_room(room)
    if room in chat_rooms:
        chat_rooms[room]['users'] -= 1
        if username in chat_rooms[room]['list']:
            chat_rooms[room]['list'].remove(username)
        update_user_list(room,username)
        update_user_count(room)
        if chat_rooms[room]['users'] <= 0:
            del chat_rooms[room]
    #################################### DEL USERS AND ROOM  ####################################3
    current_datetime = datetime.now()
    connect_time = current_datetime.strftime("%H:%M:%S %d-%m-%Y ")
    send({'name':username,'message':' has left the room.','time':connect_time,'type':'connection'}, to =room)
    return render_template('setup.html')

@socketio.on("leave room")
def handle_leave_room():
    room = session.get("room")
    username = session.get('name')
    leave_room(room)
    if room in chat_rooms:
        chat_rooms[room]['users'] -= 1
        if username in chat_rooms[room]['list']:
            chat_rooms[room]['list'].remove(username)
        update_user_list(room,username)
        update_user_count(room)
        if chat_rooms[room]['users'] <= 0:
            del chat_rooms[room]
    #################################### DEL USERS AND ROOM  ####################################3
    current_datetime = datetime.now()
    connect_time = current_datetime.strftime("%H:%M:%S %d-%m-%Y ")
    send({'name':username,'message':' has left the room.','time':connect_time,'type':'connection'}, to =room)
    emit('redirect', {'url': '/'}, room=request.sid)
    session.clear()

########################### MESSAGE SOCKET ###########################

@socketio.on('message')
def message(data):
    room = session.get("room")
    if room not in chat_rooms:
        return
    current_datetime = datetime.now()
    connect_time = current_datetime.strftime("%H:%M:%S %d-%m-%Y ")
    content = {
        'name':session.get('name')+':',
        'message': data['data'],
        'time':connect_time,
        'type':'message'
    }
    send(content, to=room)
    chat_rooms[room]['messages'].append(content)

########################### KICK SOCKET ###########################

@socketio.on('kick_user')
def handle_kick_user(data):
    current_user = session.get('name')
    user_to_kick = data['user']
    room = session.get('room')
    users = chat_rooms[room]['list']
    if current_user == chat_rooms[room]['leader']:  ################################################3 >>>>>>>>??????????###########################3
        if user_to_kick in users:
            if user_to_kick == current_user:
                emit('no_permission',{'message':'Can not kick yourself.'})
            else:
                users.remove(user_to_kick)
                emit('update_user_list', {'users_list': users, 'current_user': current_user}, broadcast=True)
                emit('user_count_update', {'users_count': len(users)}, broadcast=True)
                    ################################################
                sid_to_kick = username_to_sid.get(user_to_kick)
                if sid_to_kick:
                    emit('redirect', {'url': '/'}, room=sid_to_kick)
                    send({'name':user_to_kick,'message':' has been kicked.','time':'','type':'connection'}, to =room)
                    ################################################
    else:
        emit('no_permission',{'message':'You do not have permission to kick users.'})


if __name__ == "__main__":
    socketio.run(app,debug=True)