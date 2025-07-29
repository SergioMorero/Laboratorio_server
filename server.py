from flask import Flask, jsonify, request, render_template, session
import mysql.connector
import requests
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
from flask_cors import CORS
from credential import db_config
import uuid
from flask_mail import Mail, Message
import random
import base64
import json
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:8000"}})

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'jumpingpals@gmail.com'
app.config['MAIL_PASSWORD'] = 'jismleuofbxujlnw'
app.config['MAIL_DEFAULT_SENDER'] = 'jumpingpals@gmail.com'

mail = Mail(app)

rooms = {}

def decode_id_token(id_token):
    # El JWT tiene 3 partes separadas por puntos: header.payload.signature
    parts = id_token.split('.')
    if len(parts) != 3:
        raise ValueError("Token inválido")
    # La segunda parte (payload) es la que contiene la info codificada en base64url
    payload = parts[1]
    # base64url requiere padding correcto:
    padding = '=' * ((4 - len(payload) % 4) % 4)
    payload += padding
    decoded_bytes = base64.urlsafe_b64decode(payload)
    decoded_str = decoded_bytes.decode('utf-8')
    return json.loads(decoded_str)


# Email

def congratulate(achievement, player_email):
    special_message = ["Congratulations", "Well done", "You're amazing", "Keep it up", "Impressive", "You're Jumping, Pal"]
    congrat = special_message[random.randint(0, len(special_message) - 1)]
    message = f"You've just unlocked the {achievement} achievement! {congrat}!"
    msg = Message(
        subject = "[JumpingPals] You've unlocked an achievement!",
        recipients = [player_email],
        body = message
    )
    mail.send(msg)

def greet(player_name, player_email):
    msg = Message(
        subject = f"Welcome to JumpingPals, {player_name}!",
        recipients = [player_email],
        body = "You've just registered your brand new account on Jumping Pals!")
    mail.send(msg)


@app.route('/')
def home():
    return render_template('index.html')

def verify_user(name: str, password: str) -> bool:
    # Función que permite verificar que un usuario y una contraseña son un match
    # Para uso interno de server.py
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        query = "SELECT * FROM user WHERE name = %s AND password = %s"
        cursor.execute(query, (name, password))
        result = cursor.fetchone()

        cursor.close()
        conn.close()

        return result is not None

    except Exception as e:
        print(f"Error: {str(e)}")
        return False

@app.route('/server', methods=['GET'])
def check_connection():
    try:

        print("Attempting to connect to server")

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        print("Attempting to execute query")
        cursor.execute("SELECT * FROM user")
        print("Executed query")

        data = cursor.fetchall()

        cursor.close()
        conn.close()

        print("Successfuly connected to server")
        return jsonify(data)

    except Exception as e:
        print("Error: ", str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/login', methods=['POST'])
def get_user():
    try:
        print("Starting query")
        print(f"Got request: {request}")
        print(f"Raw body: {request.data}")
        print(f"Request content-type: {request.content_type}")
        print(f"Request body: {request.get_data(as_text=True)}")

        data = request.json
        print(f"Got JSON: {data}")
        name = data.get('name')
        password = data.get('password')

        print(f"Got name and password: {name}, {password}")

        if not name and not password:
            print("Cannot get name or password")
            return jsonify({"error": "No se proporcionaron nuevos datos"}), 400
        print("Got data")

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        print("Created cursor")

        cursor.execute("SELECT * FROM user WHERE name = %s AND password = %s", (name, password))
        print("Executed query")

        data = cursor.fetchone()
        if data:
            user = {
                "id": data[0],
                "name": data[1],
                "password": data[2], 
                "score": data[3],
                "coins": data[4],
                "email": data[9]
            }
            print("Data fetched")
            cursor.close()
            conn.close()
            print("Closed")
            print("Usuario autenticado correctamente")
            print(user)
            return jsonify(user), 200
        else:
            return jsonify({"error": "No user found"}), 404
    
    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/user', methods=['POST'])
def add_user():
    try:
        print("Starting query")
        print(f"Got request: {request}")
        print(f"Raw body: {request.data}")
        print(f"Request content-type: {request.content_type}")
        print(f"Request body: {request.get_data(as_text=True)}")

        data = request.json
        print(f"Got JSON: {data}")
        name = data.get('name')
        password = data.get('password')
        print(f"Got name and password: {name}, {password}")
        email = data.get('email')

        if not name and not password and not email:
            print("Cannot get name or password")
            return jsonify({"error": "No se proporcionaron nuevos datos"}), 400

        print("Got data")

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        print("Created cursor")

        cursor.execute("INSERT INTO user (name, password, email) VALUES (%s, %s, %s)", (name, password, email))
        user_id = cursor.lastrowid # Obtiene el ID autogenerado
        print(user_id)
        print("Executed query")
        print("Commited")

        # Añade al usuario a la leaderboard al crearlo
        cursor.execute("INSERT INTO leaderboard (id, score) VALUES (%s, %s)", (user_id, 0))

        # Otorgar skin por defecto
        cursor.execute("INSERT INTO has_skin (user_id, skin_id) VALUES (%s, 0)", (user_id, ))
        conn.commit()

        cursor.close()
        conn.close()
        print("CLosed")

        greet(name, email)

        return jsonify({"message": "Usuario añadido correctamente"})
    
    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/user', methods=['DELETE'])
def deleteUser():
    try:
        data = request.json
        name = data.get('name')
        password = data.get('password')

        if not verify_user(name, password):
            return jsonify({"error": str(e)}), 401

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user WHERE name = %s", (name,))
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({"error": "Usuario no encontrado"}), 404

        cursor.close()
        conn.close()

        return jsonify({"message": "Usuario eliminado correctamente"})
    
    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/user', methods=['PUT'])
def update_user():
    try:
        print("Starting query")
        print(f"Got request: {request}")
        print(f"Raw body: {request.data}")
        print(f"Request content-type: {request.content_type}")
        print(f"Request body: {request.get_data(as_text=True)}")

        data = request.get_json()
        print(f"Got JSON: {data}")
        current_name = data.get('name')
        current_password = data.get('password')
        new_name = data.get('newName')
        new_password = data.get('newPassword')
        new_email = data.get('newEmail')

        print(f"Got Old name and password: {current_name}, {current_password}")
        print(f"Got New name and password: {new_name}, {new_password}")

        if not new_name and not new_password and not new_email:
            print("Cannot get name or password")
            return jsonify({"error": "No se proporcionaron nuevos datos"}), 400

        print("Got data")

        if not verify_user(current_name, current_password):
            print("Mismatch")
            return jsonify({"error": "Unauthorized"}), 401

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        if new_password:
            cursor.execute("UPDATE user SET password = %s WHERE name = %s", (new_password, current_name))

        if new_name:
            cursor.execute("UPDATE user SET name = %s WHERE name = %s", (new_name, current_name))
        if new_email:
            cursor.execute("UPDATE user SET email = %s WHERE name = %s", (new_email, current_name))

        conn.commit()

        """if cursor.rowcount == 0:
            return jsonify({"error": "Usuario no encontrado"}), 404"""

        cursor.close()
        conn.close()

        return jsonify({"message": "Usuario actualizado correctamente"})
    
    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/set-score', methods=['PUT'])
def set_score():
    try:
        data = request.json
        user_id = data.get('id')
        score = data.get('score')

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute("UPDATE leaderboard SET score = %s WHERE id = %s", (score, user_id))
        conn.commit()
        cursor.execute("UPDATE user SET score = %s WHERE id = %s", (score, user_id))

        conn.commit()       
        cursor.close()
        conn.close()

        return jsonify({"message": "Puntaje actualizado correctamente"})
    
    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/achievements', methods=['PUT'])
def check_achievements():
    try:
        data = request.json
        user_id = data.get('id')

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute("SELECT coins, totalJumps, enemiesKilled FROM user WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        coins = result[0]
        jumps = result[1]
        kills = result[2]

        cursor.execute("""SELECT achv.id FROM achievement achv LEFT JOIN userHasAchievement uha ON 
                        achv.id = uha.achievement_id AND uha.user_id = %s 
                        WHERE achv.totalJumpsRequired <= %s AND uha.achievement_id IS NULL AND achv.id < 11
                        """, (user_id, jumps))

        new_achievements = cursor.fetchall()

        cursor.execute("""SELECT achv.id FROM achievement achv LEFT JOIN userHasAchievement uha ON 
                        achv.id = uha.achievement_id AND uha.user_id = %s 
                        WHERE achv.enemiesRequired <= %s AND uha.achievement_id IS NULL AND achv.id BETWEEN 11 AND 20
                        """, (user_id, kills))

        new_achievements.extend(cursor.fetchall())

        cursor.execute("""SELECT achv.id FROM achievement achv LEFT JOIN userHasAchievement uha ON 
                        achv.id = uha.achievement_id AND uha.user_id = %s 
                        WHERE achv.coinsRequired <= %s AND uha.achievement_id IS NULL AND achv.id BETWEEN 21 AND 30
                        """, (user_id, coins))

        new_achievements.extend(cursor.fetchall())

        # Get player email to send a notification
        cursor.execute("""SELECT email FROM user WHERE user.id = %s""", (user_id,))
        player_email= cursor.fetchone()[0]


        for achv in new_achievements:
            achv_id = achv[0]
            cursor.execute("""INSERT INTO userHasAchievement (user_id, achievement_id) 
                           VALUES (%s, %s)""", (user_id, achv_id))

            # Get achievement name and sen an email
            cursor.execute("""SELECT name FROM achievement WHERE achievement.id = %s""", (achv_id,))
            ach_name = cursor.fetchone()[0]
            congratulate(ach_name, player_email)

        conn.commit()
        cursor.close()
        if len(new_achievements) != 0:
            return f"Se asignaron {len(new_achievements)} logro/s nuevo/s."
        else:
            return "No hay nuevos logros asignados"

    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/achievements/<int:user_id>', methods=['GET'])
def show_achievements(user_id):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute("""SELECT achv.id, achv.name, achv.description FROM achievement achv 
                        INNER JOIN userHasAchievement uha ON uha.achievement_id = achv.id 
                        WHERE uha.user_id = %s""", (user_id,))

        achievements = cursor.fetchall()

        achievement_list = []
        for achv in achievements:
            achievement_list.append({
                'id': achv[0],
                'name': achv[1],
                'desc': achv[2]
            })

        cursor.close()
        conn.close()

        return jsonify(achievement_list)

    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/set-stats', methods=['PUT'])
def set_stats():
    try:
        data = request.json
        user_id = data.get('id')
        jumps = data.get('jumps')
        enemies_killed = data.get('enemiesKilled')

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute("UPDATE user SET totalJumps = totalJumps + %s WHERE id = %s", (jumps, user_id))
        conn.commit()
        cursor.execute("UPDATE user SET enemiesKilled = enemiesKilled + %s WHERE id = %s", (enemies_killed, user_id))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": "Estadísticas actualizadas correctamente"})

    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500


@app.route('/give-coin', methods=['PUT'])
def give_coins():
    try:
        data = request.json
        user_id = data.get('id')

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute("UPDATE user SET coins = coins + 1 WHERE id = %s", (user_id, ))

        conn.commit()       
        cursor.close()
        conn.close()

        print("gave coin")

        return jsonify({"message": "Monedas actualizadas correctamente"})
    
    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/buy-character', methods=['PUT'])
def buy_character():
    try:
        data = request.json
        user_id = data.get('UserId')
        character_id = data.get('CharId')
        coin_amount = data.get('CoinAmount')

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute("UPDATE user SET coins = coins - %s WHERE id = %s", (coin_amount, user_id))
        cursor.execute("INSERT INTO has_skin(user_id, skin_id) VALUES(%s, %s)", (user_id, character_id))

        conn.commit()       
        cursor.close()
        conn.close()

        return jsonify({"message": "Pago realizado correctamente"})
    
    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/has-character', methods=['PUT'])
def char_list():
    try:
        data = request.json
        user_id = data.get('id')

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute("""SELECT skin.id as id, 
                        CASE WHEN has_skin.user_id IS NULL THEN FALSE ELSE TRUE END AS has
                        FROM skin
                        LEFT JOIN has_skin ON skin.id = has_skin.skin_id
                        AND has_skin.user_id = %s
                        ORDER BY id ASC""",
                        (user_id, ))

        columns = [desc[0] for desc in cursor.description]
        result = [dict(zip(columns, row)) for row in cursor.fetchall()]

        conn.commit()       
        cursor.close()
        conn.close()

        return jsonify({"characters": result})
    
    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/leaderboard', methods=['GET'])
def leaderboard():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""SELECT user.name, leaderboard.score FROM leaderboard JOIN user ON leaderboard.id = user.id
                       ORDER BY leaderboard.score DESC LIMIT 5""")
        rows = cursor.fetchall()

        cursor.close()
        conn.close()
        return jsonify(rows)

    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500



@app.route('/create-room', methods=['POST'])
def create_room():
    try:
        ip = request.form.get("ip")
        port = request.form.get("port")
        host = request.form.get("host")

        if ip and port:
            room_id = str(uuid.uuid4())[:8]
            rooms[room_id] = {
                "ip": ip,
                "port": port,
                "host": host
            }
            return jsonify({"status": "success", "room_id": room_id}), 200
        else:
            return jsonify({"status": "error", "message": "Missing parameters"}), 400

    except Exception as e:
        print("Error en /create-room:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/delete-room/<roomId>', methods=['DELETE'])
def delete_room(roomId):
    if roomId in rooms:
        del rooms[roomId]
        return jsonify({"status": "success"}), 200
    else:
        return jsonify({"status": "error", "message": "room not found"}), 404

@app.route('/get-room/<roomId>', methods=['GET'])
def get_room(roomId):
    room = rooms.get(roomId)
    if room:
        return jsonify({
            "status": "success",
            "ip": room["ip"],
            "port": room["port"],
            "host": room["host"]
        }), 200
    else:
        return jsonify({
            "status": "error"
        }), 404

@app.route('/get-all-rooms', methods=['GET'])
def get_rooms():
    room_list = []
    for roomId, data in rooms.items():
        room_list.append({
            "roomId": roomId,
            "ip": data["ip"],
            "port": data["port"],
            "host": data["host"]
        })
    return jsonify(room_list), 200


@app.route('/count-game', methods=['PUT'])
def count_game():
    data = request.json
    user_id = data.get('id')

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    cursor.execute("UPDATE user SET games_played = games_played + 1 WHERE id = %s ", (user_id,))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Game succesfully counted"})

@app.route('/won-game', methods=['PUT'])
def won_game():
    data = request.json
    user_id = data.get('id')

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    cursor.execute("UPDATE user SET games_won = games_won + 1 WHERE id = %s ", (user_id,))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Victory succesfully added"})

@app.route('/get-all-stats/<int:userId>', methods=['GET'])
def get_all_stats(userId):

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    cursor.execute("""SELECT score, coins, totalJumps, enemiesKilled, games_played, games_won
                   FROM user WHERE id = %s""", (userId, ))
    normalStats = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) FROM userHasAchievement WHERE user_id = %s", (userId, ))
    currentAchievements = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) FROM achievement")
    totalAchievements = cursor.fetchone()

    cursor.close()
    conn.close()

    return jsonify({
        'score': normalStats[0],
        'coins': normalStats[1],
        'jumps': normalStats[2],
        'kills': normalStats[3],
        'games_played': normalStats[4],
        'games_won': normalStats[5],
        'current': currentAchievements[0],
        'total': totalAchievements[0]
    })


# Google Authentication

''' 
    This dictionary stores all session IDs with a value:
        * 0: Not finished
        * 1: Approved
        * -1: Not approved (or non-existing)
'''

session_status = {} # mapa con cada session_id y su estado
session_info = {} # mapa con cada session_id asociado a la información requerida del usuario

@app.route('/next_session_id', methods=['GET'])
def next_session_id():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    while True:
        session_id = random.randint(0, 1000000)
        cursor.execute("SELECT 1 FROM session WHERE id = %s LIMIT 1", (session_id,))
        if not cursor.fetchone():  # Id is available
            try:
                cursor.execute("INSERT INTO session(id, state, username, email) VALUES(%s, 0, '', '')", (session_id,))
                conn.commit()
                cursor.close()
                conn.close()
                return str(session_id), 200
            except mysql.connector.IntegrityError:  # Colission
                conn.rollback()
                continue

@app.route('/get_session_status', methods=['GET'])
def get_session_status():
    session_id: int = request.args.get('session_id', type=int)
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT state FROM session WHERE id = %s", (session_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        if result:
            return str(result[0]), 200
        else:
            return str(-1), 404
    except mysql.connector.Error as err:
        cursor.close()
        conn.close()
        return jsonify({'error': f'Database error: {str(err)}'}), 500

@app.route('/remove_session_id', methods=['DELETE'])
def remove_session_id() -> None:
    session_id: int = request.args.get('session_id', type=int)
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM session WHERE id = %s", (session_id,))
        conn.commit()
        code = 204
    except mysql.connector.Error as err:
        code = 400
    finally:
        cursor.close()
        conn.close()
        return '', code


@app.route("/googlelogin")  # callback para google
def google_login():
    code = request.args.get('code')
    session_id = request.args.get('state')
    response = requests.post("https://oauth2.googleapis.com/token", data={
        "code": code,
        "client_id": os.getenv('GOOGLE_CLIENT_ID'),
        "client_secret": os.getenv('GOOGLE_CLIENT_SECRET'),
        "redirect_uri": "https://jumping-pals.onrender.com/googlelogin",
        "grant_type": "authorization_code"
    })
    token_response = response.json()
    print(f"token recibido: {token_response}")  # para depurar
    id_token = token_response.get("id_token")
    if not id_token:
        return '{"error": "No se recibió id_token", "detalle": token_response}', 400
    user_info = decode_id_token(response.json()['id_token'])

    try:
        user_name = user_info.get('name')
        user_email = user_info.get("email")
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE session
            SET
                state = 1,
                username = %s,
                email = %s
            WHERE id = %s"""
                       , (user_name, user_email, session_id,))
        conn.commit()
        return "Sign in successful. You can close this window", 200
    except mysql.connector.Error as err:
        return 'Error, please try again', 400
    finally:
        cursor.close()
        conn.close()


"""
def google_login():

    code = request.args.get('code')
    session_id = request.args.get('state')
    print(session_id)
    response = requests.post("https://oauth2.googleapis.com/token", data={
        "code": code,
        "client_id": os.getenv('GOOGLE_CLIENT_ID'),
        "client_secret": os.getenv('GOOGLE_CLIENT_SECRET'),
        "redirect_uri": "https://jumping-pals.onrender.com/googlelogin",
        "grant_type": "authorization_code"
    })
    token_response = response.json()
    print(f"Token response: {token_response}")  # para depurar
    id_token = token_response.get("id_token")
    if not id_token:
        return {"error": "No se recibió id_token", "detalle": token_response}, 400
    user_info = decode_id_token(id_token)
    user_name = user_info.get('name')
    user_email = user_info.get("email")

    print(f"[DEBUG] Usuario autenticado: {user_name} ({user_email})")

    session_info[session_id] = [user_name[:10], user_email]
    session_status[session_id] = 1
    return f"{session_status[session_id]}"
"""


@app.route("/google_user_info", methods=["GET"])
def get_user_info():
    session_id = request.args.get('session_id', type=int)
    field = request.args.get('field')
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        if field == "name":
            cursor.execute("SELECT username FROM session WHERE id = %s", (session_id,))
        elif field == "email":
            cursor.execute("SELECT email FROM session WHERE id = %s", (session_id,))
        else:
            raise Exception("Error in field")

        result = cursor.fetchone()

        if result:
            return result[0], 200
        else:
            return '', 404
    except mysql.connector.Error as err:
        return jsonify({'error': f'Database error: {str(err)}'}), 500
    finally:
        cursor.close()
        conn.close()



@app.route('/user_exists', methods=['GET'])
def user_exists():
    user_name = request.args.get('user_name')
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user WHERE name = %s", (user_name, ))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return jsonify({'exists': result is not None}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': 'Database error'}), 400

# Friends

@app.route('/friends', methods=['PUT'])
def add_friend():
    data = request.json
    sender_id = data.get("sender_id")
    sender_name = data.get("sender_name")
    receiver_name = data.get("receiver_name")

    if not sender_id or not sender_name or not receiver_name:
        return jsonify({"error": "Faltan datos"}), 400

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM user WHERE name = %s", (receiver_name, ))
    result = cursor.fetchone()

    if not result:
        return jsonify({"error": "Usuario no encontrado"}), 404

    receiver_id = result[0]
    cursor.execute("""INSERT INTO friends (sender_id, sender_name, receiver_id, receiver_name, accepted)
                          VALUES (%s, %s, %s, %s, %s)""",
                   (sender_id, sender_name, receiver_id, receiver_name, 0))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Amigo añadido correctamente"}), 200


@app.route('/friends', methods=['POST'])
def get_friends():
    try:
        data = request.json
        user_id = data.get('user_id')
        acceptance = data.get('aceppted')

        if not user_id:
            return jsonify({'error': 'user_id requerido'}), 400

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        senderQuery = """
            SELECT sender_id AS friend_id, sender_name AS friend_name FROM friends 
            WHERE receiver_id = %s AND accepted = %s
            """

        cursor.execute(senderQuery, (user_id, acceptance))
        senderFriends = cursor.fetchall()

        receiverQuery = """
                    SELECT receiver_id AS friend_id, receiver_name AS friend_name FROM friends 
                    WHERE sender_id = %s AND accepted = %s
                    """
        if (acceptance == 1):
            cursor.execute(receiverQuery, (user_id, acceptance))
        elif (acceptance == 0)
            cursor.execute(receiverQuery, (user_id, -2))

        receiverFriends = cursor.fetchall()

        friends = senderFriends + receiverFriends

        cursor.close()
        conn.close()

        return jsonify(friends)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/friends', methods=['DELETE'])
def delete_friend():
    data = request.json
    user_id = data.get('user_id')
    friend_id = data.get('friend_id')

    if not user_id or not friend_id:
        return jsonify({'error': 'user_id y friend_id requeridos'}), 400

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    cursor.execute("""
                DELETE FROM friends 
                WHERE 
                (sender_id = %s AND receiver_id = %s) OR 
                (sender_id = %s AND receiver_id = %s)
            """, (user_id, friend_id, friend_id, user_id))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'message': 'Amistad eliminada correctamente'}), 200


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)