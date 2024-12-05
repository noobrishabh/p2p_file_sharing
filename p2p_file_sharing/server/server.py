from flask import Flask, request, jsonify
import sqlite3
import threading
import time
from datetime import datetime, timedelta

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('p2p.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS peers
                (username TEXT PRIMARY KEY, password TEXT, ip TEXT, port INTEGER,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS files
                (filename TEXT, username TEXT, peer_ip TEXT, peer_port INTEGER,
                shared_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(username) REFERENCES peers(username))''')
    
    c.execute('CREATE INDEX IF NOT EXISTS idx_filename ON files(filename)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_username ON files(username)')
    
    conn.commit()
    conn.close()

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    if not all(key in data for key in ['username', 'password', 'ip', 'port']):
        return jsonify({"message": "Missing required fields!"}), 400
    
    conn = sqlite3.connect('p2p.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO peers (username, password, ip, port) VALUES (?, ?, ?, ?)',
                 (data['username'], data['password'], data['ip'], data['port']))
        conn.commit()
        return jsonify({"message": "Registration successful!"})
    except sqlite3.IntegrityError:
        return jsonify({"message": "Username already exists!"}), 400
    finally:
        conn.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    if not all(key in data for key in ['username', 'password']):
        return jsonify({"message": "Missing credentials!"}), 400

    conn = sqlite3.connect('p2p.db')
    c = conn.cursor()
    try:
        c.execute('''SELECT username, ip, port FROM peers 
                    WHERE username = ? AND password = ?''', 
                    (data['username'], data['password']))
        result = c.fetchone()
        
        if result:
            # Update last_seen timestamp
            c.execute('''UPDATE peers SET last_seen = ?, ip = ?, port = ? 
                        WHERE username = ?''',
                     (datetime.now(), data['ip'], data['port'], data['username']))
            conn.commit()
            return jsonify({"message": "Login successful!", "username": result[0]})
        return jsonify({"message": "Invalid credentials!"}), 401
    finally:
        conn.close()
    
def cleanup_inactive_peers():
    """Remove files of inactive peers"""
    while True:
        try:
            conn = sqlite3.connect('p2p.db')
            c = conn.cursor()
            
            threshold_time = datetime.now() - timedelta(seconds=60)  # 60 second grace period
            
            # Get inactive peers
            c.execute('''SELECT username FROM peers 
                        WHERE last_heartbeat < ?''', (threshold_time,))
            inactive_peers = c.fetchall()
            
            for peer in inactive_peers:
                username = peer[0]
                print(f"Removing files for inactive peer: {username}")
                
                # Remove their files
                c.execute('DELETE FROM files WHERE username = ?', (username,))
                
                # Optionally, remove the peer (uncomment if you want to remove peer entry)
                c.execute('DELETE FROM peers WHERE username = ?', (username,))
            
            conn.commit()
        except Exception as e:
            print(f"Cleanup error: {str(e)}")
        finally:
            conn.close()
            time.sleep(30)  # Run cleanup every 30 seconds

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    data = request.json
    if not all(key in data for key in ['username', 'ip', 'port']):
        return jsonify({"message": "Missing required fields!"}), 400
    
    conn = sqlite3.connect('p2p.db')
    c = conn.cursor()
    try:
        c.execute('''UPDATE peers 
                    SET last_heartbeat = ?, ip = ?, port = ?
                    WHERE username = ?''',
                 (datetime.now(), data['ip'], data['port'], data['username']))
        conn.commit()
        return jsonify({"message": "Heartbeat received"})
    except Exception as e:
        return jsonify({"message": f"Error processing heartbeat: {str(e)}"}), 500
    finally:
        conn.close()

@app.route('/disconnect', methods=['POST'])
def disconnect():
    data = request.json
    if 'username' not in data:
        return jsonify({"message": "Missing username!"}), 400
    
    conn = sqlite3.connect('p2p.db')
    c = conn.cursor()
    try:
        # Remove their files
        c.execute('DELETE FROM files WHERE username = ?', (data['username'],))
        conn.commit()
        return jsonify({"message": "Disconnected successfully"})
    except Exception as e:
        return jsonify({"message": f"Error processing disconnect: {str(e)}"}), 500
    finally:
        conn.close()

@app.route('/files', methods=['GET'])
def get_files():
    filename_query = request.args.get('filename', default='', type=str)
    username_query = request.args.get('username', default='', type=str)
    
    conn = sqlite3.connect('p2p.db')
    c = conn.cursor()
    try:
        # Only return files from peers that have sent a heartbeat in the last minute
        threshold_time = datetime.now() - timedelta(seconds=60)
        query = '''SELECT files.filename, files.username, files.peer_ip,
                          files.peer_port, files.shared_time
                   FROM files 
                   JOIN peers ON files.username = peers.username
                   WHERE peers.last_heartbeat >= ?'''
        params = [threshold_time]
        
        if filename_query:
            query += " AND files.filename LIKE ?"
            params.append(f"%{filename_query}%")
        
        if username_query:
            query += " AND files.username LIKE ?"
            params.append(f"%{username_query}%")
        
        c.execute(query, tuple(params))
        files = c.fetchall()
        return jsonify({"files": files})
    finally:
        conn.close()


@app.route('/search_files', methods=['GET'])
def search_files():
    # If using a separate search endpoint
    filename_query = request.args.get('filename', default='', type=str)
    username_query = request.args.get('username', default='', type=str)
    
    conn = sqlite3.connect('p2p.db')
    c = conn.cursor()
    try:
        # Only return files from peers that have sent a heartbeat in the last minute
        threshold_time = datetime.now() - timedelta(seconds=60)
        query = '''SELECT files.filename, files.username, files.peer_ip,
                          files.peer_port, files.shared_time
                   FROM files 
                   JOIN peers ON files.username = peers.username
                   WHERE peers.last_heartbeat >= ?'''
        params = [threshold_time]
        
        if filename_query:
            query += " AND files.filename LIKE ?"
            params.append(f"%{filename_query}%")
        
        if username_query:
            query += " AND files.username LIKE ?"
            params.append(f"%{username_query}%")
        
        c.execute(query, tuple(params))
        files = c.fetchall()
        return jsonify({"files": files})
    except Exception as e:
        return jsonify({"message": f"Error searching files: {str(e)}"}), 500
    finally:
        conn.close()


@app.route('/share_files', methods=['POST'])
def share_files():
    data = request.json
    if not all(key in data for key in ['username', 'filename', 'peer_ip', 'peer_port']):
        return jsonify({"message": "Missing required fields!"}), 400

    conn = sqlite3.connect('p2p.db')
    c = conn.cursor()
    try:
        # Clear previous files shared by this peer
        c.execute('DELETE FROM files WHERE username = ?', (data['username'],))
        
        # Add new files
        for filename in data['filename']:
            c.execute('''INSERT INTO files (filename, username, peer_ip, peer_port)
                        VALUES (?, ?, ?, ?)''',
                     (filename, data['username'], data['peer_ip'], data['peer_port']))
        conn.commit()
        return jsonify({"message": "Files shared successfully!"})
    except Exception as e:
        return jsonify({"message": f"Error sharing files: {str(e)}"}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    init_db()
    
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_inactive_peers, daemon=True)
    cleanup_thread.start()
    
    app.run(host='0.0.0.0', port=5001)