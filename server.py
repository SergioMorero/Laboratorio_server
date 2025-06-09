from flask import Flask, jsonify, request, render_template
import mysql.connector
from flask_cors import CORS
from credential import db_config
import uuid

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:8000"}})

rooms = {}

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
                "coins": data[4]
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

        if not name and not password:
            print("Cannot get name or password")
            return jsonify({"error": "No se proporcionaron nuevos datos"}), 400

        print("Got data")

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        print("Created cursor")

        cursor.execute("INSERT INTO user (name, password) VALUES (%s, %s)", (name, password))
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

        print(f"Got Old name and password: {current_name}, {current_password}")
        print(f"Got New name and password: {new_name}, {new_password}")

        if not new_name and not new_password:
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

        for achv in new_achievements:
            achv_id = achv[0]
            cursor.execute("""INSERT INTO userHasAchievement (user_id, achievement_id) 
                           VALUES (%s, %s)""", (user_id, achv_id))

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


"""
@app.route('/create-room', methods=['POST'])
def create-room():
    try:
        ip = request.form.get("ip")
        port = request.form.get("port")
        if ip and port:
            room_id = str(uuid.uuid4())[:8]
            rooms[room_id] = {
                "ip": ip,
                "port": port
            }
            return jsonify({"status": "success", "room_id": room_id}), 200
        else:
            return jsonify({"status": "error", "message": "missing parameters"}), 400

    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500
"""

@app.route('/get-room/<roomId>', methods=['GET'])
def get-room(roomId):
    room = rooms.get(roomId)
    if room:
        return jsonify({
            "status": "success",
            "ip": room["ip"],
            "port": room["port"]
        }), 200
    else:
        return jsonify({
            "status": "error"
        }), 404

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)