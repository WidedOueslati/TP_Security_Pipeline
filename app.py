from flask import Flask, request, jsonify
import sqlite3
import os

app = Flask(__name__)

# Configuration
DATABASE = 'users.db'

# Initialisation de la base de données
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            role TEXT
        )
    ''')
    # Données de test
    cursor.execute("DELETE FROM users")
    cursor.execute("INSERT INTO users VALUES (1, 'admin', 'admin123', 'admin@example.com', 'admin')")
    cursor.execute("INSERT INTO users VALUES (2, 'user', 'user123', 'user@example.com', 'user')")
    conn.commit()
    conn.close()

# Route de santé
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "version": "1.0"}), 200

# VULNÉRABILITÉ 1 : SQL Injection
@app.route('/user/<user_id>', methods=['GET'])
def get_user(user_id):
    """Route vulnérable à l'injection SQL"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # DANGER : Concaténation directe sans paramètres préparés
    query = f"SELECT * FROM users WHERE id = {user_id}"
    
    try:
        cursor.execute(query)
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return jsonify({
                "id": user[0],
                "username": user[1],
                "password": user[2],  # VULNÉRABILITÉ : Exposition du mot de passe
                "email": user[3],
                "role": user[4]
            }), 200
        else:
            return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# VULNÉRABILITÉ 2 : Exposition de données sensibles
@app.route('/users', methods=['GET'])
def get_all_users():
    """Retourne tous les utilisateurs avec leurs mots de passe"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    conn.close()
    
    return jsonify([{
        "id": u[0],
        "username": u[1],
        "password": u[2],  # DANGER : Mots de passe exposés
        "email": u[3],
        "role": u[4]
    } for u in users]), 200

# VULNÉRABILITÉ 3 : Pas de validation + mot de passe en clair
@app.route('/login', methods=['POST'])
def login():
    """Authentification non sécurisée"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Requête vulnérable
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    cursor.execute(query)
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return jsonify({
            "success": True,
            "message": "Login successful",
            "user": {
                "id": user[0],
                "username": user[1],
                "password": user[2],  # DANGER
                "role": user[4]
            }
        }), 200
    else:
        return jsonify({"success": False, "message": "Invalid credentials"}), 401

# VULNÉRABILITÉ 4 : XSS (Cross-Site Scripting)
@app.route('/search', methods=['GET'])
def search():
    """Route vulnérable au XSS"""
    query = request.args.get('q', '')
    # Pas de sanitization
    return f"<h1>Search results for: {query}</h1>", 200

# VULNÉRABILITÉ 5 : Utilisation de eval() - Code Injection
@app.route('/calculate', methods=['POST'])
def calculate():
    """Route dangereuse avec eval()"""
    data = request.get_json()
    expression = data.get('expression', '')
    
    try:
        # DANGER : eval() 
        result = eval(expression)
        return jsonify({"result": result}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# VULNÉRABILITÉ 6 : Debug mode en production
if __name__ == '__main__':
    init_db()
    # DANGER : Debug activé expose des informations sensibles
    app.run(host='0.0.0.0', port=5000, debug=False)