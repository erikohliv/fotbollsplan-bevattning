#!/usr/bin/env python3
"""
TODO Checklist Backend Server
Saves and retrieves TODO checkbox states to/from JSON file
"""

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import json
import os
from pathlib import Path
from datetime import datetime

app = Flask(__name__)
CORS(app)

# File paths
BASE_DIR = Path(__file__).parent
STATE_FILE = BASE_DIR / "todo_state.json"
HTML_FILE = BASE_DIR / "todo_checklist.html"

def load_state():
    """Load TODO state from JSON file"""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading state: {e}")
            return {"items": {}, "last_updated": None}
    return {"items": {}, "last_updated": None}

def save_state(state):
    """Save TODO state to JSON file"""
    try:
        state["last_updated"] = datetime.now().isoformat()
        with open(STATE_FILE, 'w') as f:
            json.dump(state, indent=2, fp=f)
        return True
    except Exception as e:
        print(f"Error saving state: {e}")
        return False

@app.route('/')
def index():
    """Serve the HTML checklist"""
    return send_file(HTML_FILE)

@app.route('/api/state', methods=['GET'])
def get_state():
    """Get current TODO state"""
    state = load_state()
    return jsonify(state)

@app.route('/api/state', methods=['POST'])
def update_state():
    """Update TODO state"""
    try:
        data = request.get_json()
        if not data or 'items' not in data:
            return jsonify({"error": "Invalid data"}), 400
        
        current_state = load_state()
        current_state['items'] = data['items']
        
        if save_state(current_state):
            return jsonify({"success": True, "state": current_state})
        else:
            return jsonify({"error": "Failed to save state"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/toggle/<item_id>', methods=['POST'])
def toggle_item(item_id):
    """Toggle a single TODO item"""
    try:
        data = request.get_json()
        checked = data.get('checked', False)
        
        state = load_state()
        state['items'][item_id] = checked
        
        if save_state(state):
            return jsonify({"success": True, "item_id": item_id, "checked": checked})
        else:
            return jsonify({"error": "Failed to save state"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get TODO statistics"""
    state = load_state()
    items = state.get('items', {})
    
    total = len([k for k in items.keys() if not k.startswith('done-')])
    completed = len([v for k, v in items.items() if v and not k.startswith('done-')])
    percentage = round((completed / total * 100) if total > 0 else 0, 1)
    
    return jsonify({
        "total": total,
        "completed": completed,
        "percentage": percentage,
        "last_updated": state.get('last_updated')
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "service": "todo-checklist"})

if __name__ == '__main__':
    # Create empty state file if it doesn't exist
    if not STATE_FILE.exists():
        save_state({"items": {}, "last_updated": None})
    
    # Run on all interfaces so it's accessible via Tailscale
    app.run(host='0.0.0.0', port=8891, debug=False)
