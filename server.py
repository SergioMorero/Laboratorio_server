from flask import Flask, jsonify, request, render_template
import mysql.connector
from flask_mysqldb import MySQL
from flask_cors import CORS
from credential import db_config

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:8000"}})

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
        conn.commit()
        print("Commited")

        # Añade al usuario a la leaderboard al crearlo
        cursor.execute("INSERT INTO leaderboard (id, maxscore) VALUES (%s, %s)", (user_id, 0))
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

        cursor.execute("UPDATE leaderboard SET maxscore = %s WHERE id = %s", (score, user_id))
        cursor.execute("UPDATE user SET score = %s WHERE id = %s", (score, user_id))

        conn.commit()       
        cursor.close()
        conn.close()

        return jsonify({"message": "Puntaje actualizado correctamente"})
    
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

        return jsonify({"message": "Monedas actualizadas correctamente"})
    
    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host="127.0.0.1", port=5000)