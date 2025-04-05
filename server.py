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

@app.route('/user', methods=['GET'])
def get_user():

    conn = sqlite3.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user WHERE name = %s AND password = %s", (name, password))
    data = cursor.fetchall()
    conn.close()

    return jsonify(data)

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

@app.route('/create-user', methods=['POST'])
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
        print("Executed query")
        conn.commit()
        print("Commited")
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

@app.route('/delete-user', methods=['POST', 'DELETE'])
def delete_user():
    # Realiza un DELETE mediante un POST para facilitar la interacción con unity
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
        cursor.close()
        conn.close()
        return jsonify({"message": "Usuario eliminado correctamente"})

    except Exception as e:
        print("Error: ", str(e))
        return jsonify({"error": str(e)}), 500

    """
    if request.method == 'POST' and request.form.get('_method') == 'DELETE':
        username = request.form.get('username')
    elif request.method == 'DELETE':
        username = request.json.get('username')  # If you go with raw DELETE + JSON body
    else:
        return jsonify({'error': 'Invalid request'}), 400

    if not username:
        return jsonify({'error': 'Username required'}), 400

    # Your DB logic here, e.g.:
    # db.execute("DELETE FROM users WHERE username = ?", (username,))
    # db.commit()

    return jsonify({'message': f'User {username} deleted successfully'})
    """

@app.route('/user', methods=['PUT'])
def update_user():
    try:
        data = request.get_json()
        current_name = data.get('name')
        current_password = data.get('password')
        new_name = data.get('newName')
        new_password = data.get('newPassword')

        if not new_name and not new_password:
            return jsonify({"error": "No se proporcionaron nuevos datos"}), 400

        if not verify_user(current_name, current_password):
            return jsonify({"error": "Unauthorized"}), 401

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        if new_password:
            cursor.execute("UPDATE user SET password = %s WHERE name = %s", (new_password, current_name))

        if new_name:
            cursor.execute("UPDATE user SET name = %s WHERE name = %s", (new_name, current_name))

        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({"error": "Usuario no encontrado"}), 404

        cursor.close()
        conn.close()

        return jsonify({"message": "Usuario actualizado correctamente"})
    
    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host="127.0.0.1", port=5000)