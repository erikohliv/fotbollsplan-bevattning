#!/usr/bin/env python3
"""
User Management Web UI
Enkelt webbgränssnitt för att hantera användare
"""
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from flask_cors import CORS
import os
import requests
from dotenv import load_dotenv
from functools import wraps
import secrets

load_dotenv("api_.env")

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))
CORS(app)

# Konfiguration
API_BASE = os.getenv('API_URL', 'http://localhost:8000')
API_KEY = os.getenv('API_KEY', 'kamp')


def require_login(f):
    """Decorator för att kräva inloggning"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
@require_login
def index():
    """Huvudsida med användarlista"""
    return render_template_string(MAIN_TEMPLATE)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login-sida"""
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        # Verifiera mot API
        try:
            r = requests.get(
                f'{API_BASE}/users/list',
                auth=(username, password),
                timeout=2
            )
            
            if r.status_code == 200:
                session['logged_in'] = True
                session['username'] = username
                session['password'] = password  # Behövs för vidare API-anrop
                return jsonify({'ok': True})
            else:
                return jsonify({'ok': False, 'error': 'Felaktigt användarnamn eller lösenord'}), 401
        except Exception as e:
            return jsonify({'ok': False, 'error': f'Anslutningsfel: {str(e)}'}), 500
    
    return render_template_string(LOGIN_TEMPLATE)


@app.route('/logout')
def logout():
    """Logga ut"""
    session.clear()
    return redirect(url_for('login'))


@app.route('/api/users')
@require_login
def get_users():
    """Hämta alla användare"""
    try:
        r = requests.get(
            f'{API_BASE}/users/list',
            auth=('superadmin', session.get('password', '')),
            timeout=2
        )
        
        if r.status_code == 200:
            return jsonify(r.json())
        else:
            return jsonify({'ok': False, 'error': 'Kunde inte hämta användare'}), r.status_code
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/users/create', methods=['POST'])
@require_login
def create_user():
    """Skapa ny användare"""
    data = request.get_json()
    
    try:
        r = requests.post(
            f'{API_BASE}/users/create',
            auth=('superadmin', session.get('password', '')),
            json=data,
            timeout=2
        )
        
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/users/delete', methods=['POST'])
@require_login
def delete_user():
    """Ta bort användare"""
    data = request.get_json()
    
    try:
        r = requests.post(
            f'{API_BASE}/users/delete',
            auth=('superadmin', session.get('password', '')),
            json=data,
            timeout=2
        )
        
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/assets/logo')
def serve_logo():
    """Servera IK Kamp logga"""
    from flask import send_file, abort
    import pathlib
    logo_path = os.path.join(os.path.dirname(__file__), 'assets', 'ik_kamp_logo.jpg')
    
    # Verifiera att filen finns
    if not pathlib.Path(logo_path).exists():
        abort(404, description="Logo not found")
    
    return send_file(logo_path, mimetype='image/jpeg')


LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Användarhantering</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .login-container {
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            max-width: 400px;
            width: 100%;
        }
        
        h1 {
            text-align: center;
            color: #2d3748;
            margin-bottom: 10px;
            font-size: 28px;
        }
        
        .subtitle {
            text-align: center;
            color: #666;
            font-size: 14px;
            margin-bottom: 30px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            color: #4a5568;
            font-weight: 600;
            margin-bottom: 8px;
            font-size: 14px;
        }
        
        input {
            width: 100%;
            padding: 12px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 14px;
            transition: all 0.3s;
        }
        
        input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        button {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(102, 126, 234, 0.3);
        }
        
        button:disabled {
            background: #cbd5e0;
            cursor: not-allowed;
            transform: none;
        }
        
        .error {
            background: #fed7d7;
            color: #c53030;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
            text-align: center;
            display: none;
        }
        
        .error.visible {
            display: block;
        }
        
        @media (max-width: 480px) {
            .login-container {
                padding: 30px 20px;
            }
            h1 {
                font-size: 24px;
            }
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div style="text-align: center; margin-bottom: 20px;">
            <img src="/assets/logo" alt="IK Kamp" style="width: 80px; height: 80px;">
        </div>
        <h1>🔐 Inloggning</h1>
        <div class="subtitle">Användarhantering</div>
        
        <div id="error" class="error"></div>
        
        <form id="loginForm" onsubmit="handleLogin(event)">
            <div class="form-group">
                <label for="username">Användarnamn</label>
                <input type="text" id="username" name="username" value="superadmin" required>
            </div>
            
            <div class="form-group">
                <label for="password">Lösenord</label>
                <input type="password" id="password" name="password" required autofocus>
            </div>
            
            <button type="submit" id="loginBtn">Logga in</button>
        </form>
    </div>
    
    <script>
        async function handleLogin(e) {
            e.preventDefault();
            
            const btn = document.getElementById('loginBtn');
            const errorEl = document.getElementById('error');
            
            btn.disabled = true;
            btn.textContent = 'Loggar in...';
            errorEl.classList.remove('visible');
            
            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        username: document.getElementById('username').value,
                        password: document.getElementById('password').value
                    })
                });
                
                const data = await response.json();
                
                if (data.ok) {
                    window.location.href = '/';
                } else {
                    errorEl.textContent = data.error || 'Inloggning misslyckades';
                    errorEl.classList.add('visible');
                    btn.disabled = false;
                    btn.textContent = 'Logga in';
                }
            } catch (error) {
                errorEl.textContent = 'Nätverksfel: ' + error.message;
                errorEl.classList.add('visible');
                btn.disabled = false;
                btn.textContent = 'Logga in';
            }
        }
    </script>
</body>
</html>
"""


MAIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Användarhantering</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);
            color: white;
            padding: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header h1 {
            font-size: 28px;
            margin: 0;
        }
        
        .logout-btn {
            background: rgba(255,255,255,0.1);
            color: white;
            border: 1px solid rgba(255,255,255,0.3);
            padding: 8px 16px;
            border-radius: 6px;
            text-decoration: none;
            font-size: 14px;
            transition: all 0.3s;
        }
        
        .logout-btn:hover {
            background: rgba(255,255,255,0.2);
        }
        
        .content {
            padding: 30px;
        }
        
        .user-list {
            margin-bottom: 30px;
        }
        
        .user-card {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 20px;
            margin-bottom: 10px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #4CAF50;
            transition: all 0.3s;
        }
        
        .user-card:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transform: translateX(4px);
        }
        
        .user-card.admin {
            border-left-color: #667eea;
            background: linear-gradient(135deg, #f0f4ff 0%, #e8eeff 100%);
        }
        
        .user-info {
            flex: 1;
        }
        
        .user-name {
            font-weight: bold;
            font-size: 16px;
            color: #2d3748;
        }
        
        .user-role {
            font-size: 12px;
            color: #666;
            margin-top: 4px;
        }
        
        .user-badge {
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: bold;
            margin-left: 10px;
        }
        
        .badge-admin {
            background: #e0e7ff;
            color: #4c51bf;
        }
        
        .badge-operator {
            background: #e2e8f0;
            color: #4a5568;
        }
        
        .delete-btn {
            background: #f44336;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 600;
            transition: all 0.3s;
        }
        
        .delete-btn:hover {
            background: #da190b;
            transform: scale(1.05);
        }
        
        .add-user-section {
            background: linear-gradient(135deg, #f0f4ff 0%, #e8eeff 100%);
            padding: 25px;
            border-radius: 12px;
            border: 2px solid #667eea;
        }
        
        .add-user-section h3 {
            color: #2d3748;
            margin-bottom: 20px;
        }
        
        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 15px;
        }
        
        .form-group {
            margin-bottom: 15px;
        }
        
        .form-group label {
            display: block;
            color: #4a5568;
            font-weight: 600;
            margin-bottom: 6px;
            font-size: 13px;
        }
        
        .form-group input,
        .form-group select {
            width: 100%;
            padding: 10px;
            border: 2px solid #e2e8f0;
            border-radius: 6px;
            font-size: 14px;
            transition: all 0.3s;
        }
        
        .form-group input:focus,
        .form-group select:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
            width: 100%;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(102, 126, 234, 0.3);
        }
        
        .message {
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
            display: none;
        }
        
        .message.visible {
            display: block;
        }
        
        .message.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .message.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .empty-state {
            text-align: center;
            padding: 40px;
            color: #999;
        }
        
        /* Mobil-anpassning */
        @media (max-width: 768px) {
            body {
                padding: 10px;
            }
            .header {
                padding: 20px;
                flex-direction: column;
                gap: 15px;
                text-align: center;
            }
            .header h1 {
                font-size: 22px;
            }
            .content {
                padding: 20px;
            }
            .form-row {
                grid-template-columns: 1fr;
                gap: 10px;
            }
            .user-card {
                flex-direction: column;
                align-items: flex-start;
                gap: 10px;
            }
            .delete-btn {
                width: 100%;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <img src="/assets/logo" alt="IK Kamp" style="width: 50px; height: 50px; position: absolute; left: 30px; top: 50%; transform: translateY(-50%);">
            <h1>👥 Användarhantering</h1>
            <a href="/logout" class="logout-btn">Logga ut</a>
        </div>
        
        <div class="content">
            <div id="message" class="message"></div>
            
            <div class="user-list">
                <h2 style="margin-bottom: 20px; color: #2d3748;">Användare</h2>
                <div id="users-container">
                    <div class="empty-state">Laddar användare...</div>
                </div>
            </div>
            
            <div class="add-user-section">
                <h3>➕ Lägg till ny användare</h3>
                
                <form id="addUserForm" onsubmit="handleAddUser(event)">
                    <div class="form-row">
                        <div class="form-group">
                            <label for="newUsername">Användarnamn *</label>
                            <input type="text" id="newUsername" required minlength="3" maxlength="32"
                                   pattern="[a-zA-Z0-9][a-zA-Z0-9_-]*" 
                                   placeholder="operator1">
                        </div>
                        
                        <div class="form-group">
                            <label for="newRole">Roll *</label>
                            <select id="newRole" required>
                                <option value="false">Operatör</option>
                                <option value="true">Admin</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="newPassword">Lösenord *</label>
                            <input type="password" id="newPassword" required minlength="8" 
                                   placeholder="Minst 8 tecken">
                        </div>
                        
                        <div class="form-group">
                            <label for="confirmPassword">Bekräfta lösenord *</label>
                            <input type="password" id="confirmPassword" required minlength="8" 
                                   placeholder="Bekräfta lösenord">
                        </div>
                    </div>
                    
                    <button type="submit" class="btn-primary" id="addUserBtn">Skapa användare</button>
                </form>
            </div>
        </div>
    </div>
    
    <script>
        function showMessage(text, isError = false) {
            const msg = document.getElementById('message');
            msg.className = 'message visible ' + (isError ? 'error' : 'success');
            msg.textContent = text;
            setTimeout(() => msg.classList.remove('visible'), 5000);
        }
        
        async function loadUsers() {
            try {
                const response = await fetch('/api/users');
                const data = await response.json();
                
                if (!data.ok) {
                    showMessage('Kunde inte ladda användare: ' + data.error, true);
                    return;
                }
                
                const container = document.getElementById('users-container');
                
                if (!data.users || data.users.length === 0) {
                    container.innerHTML = '<div class="empty-state">Inga användare skapade än</div>';
                    return;
                }
                
                let html = '';
                for (const user of data.users) {
                    const roleClass = user.is_admin ? 'admin' : '';
                    const roleBadge = user.is_admin ? 
                        '<span class="user-badge badge-admin">ADMIN</span>' : 
                        '<span class="user-badge badge-operator">OPERATÖR</span>';
                    
                    html += `
                        <div class="user-card ${roleClass}">
                            <div class="user-info">
                                <div class="user-name">
                                    ${user.username}
                                    ${roleBadge}
                                </div>
                                <div class="user-role">
                                    Skapad: ${new Date(user.created_at || Date.now()).toLocaleDateString('sv-SE')}
                                </div>
                            </div>
                            <button class="delete-btn" onclick="deleteUser('${user.username}')">
                                🗑️ Ta bort
                            </button>
                        </div>
                    `;
                }
                
                container.innerHTML = html;
            } catch (error) {
                showMessage('Fel vid laddning: ' + error.message, true);
            }
        }
        
        async function handleAddUser(e) {
            e.preventDefault();
            
            const username = document.getElementById('newUsername').value;
            const password = document.getElementById('newPassword').value;
            const confirmPassword = document.getElementById('confirmPassword').value;
            const isAdmin = document.getElementById('newRole').value === 'true';
            const btn = document.getElementById('addUserBtn');
            
            // Validera lösenord
            if (password !== confirmPassword) {
                showMessage('Lösenorden matchar inte!', true);
                return;
            }
            
            if (password.length < 8) {
                showMessage('Lösenordet måste vara minst 8 tecken', true);
                return;
            }
            
            btn.disabled = true;
            btn.textContent = 'Skapar...';
            
            try {
                const response = await fetch('/api/users/create', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        username: username,
                        password: password,
                        is_admin: isAdmin
                    })
                });
                
                const data = await response.json();
                
                if (data.ok) {
                    showMessage(`✅ Användare "${username}" skapad!`);
                    document.getElementById('addUserForm').reset();
                    loadUsers();
                } else {
                    showMessage(data.detail || 'Kunde inte skapa användare', true);
                }
            } catch (error) {
                showMessage('Fel: ' + error.message, true);
            } finally {
                btn.disabled = false;
                btn.textContent = 'Skapa användare';
            }
        }
        
        async function deleteUser(username) {
            if (!confirm(`Ta bort användaren "${username}"?`)) {
                return;
            }
            
            try {
                const response = await fetch('/api/users/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ username: username })
                });
                
                const data = await response.json();
                
                if (data.ok) {
                    showMessage(`✅ Användare "${username}" borttagen`);
                    loadUsers();
                } else {
                    showMessage(data.detail || 'Kunde inte ta bort användare', true);
                }
            } catch (error) {
                showMessage('Fel: ' + error.message, true);
            }
        }
        
        // Initial load
        loadUsers();
        
        // Auto-refresh var 10:e sekund
        setInterval(loadUsers, 10000);
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    port = int(os.getenv('USER_MGMT_PORT', '8082'))
    print(f"Starting User Management Web UI on port {port}")
    print(f"Open: http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)

