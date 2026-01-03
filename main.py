import string
import random
import os
import json
from flask import Flask, request, jsonify, send_from_directory
from Acc_Gen import InstagramAccountCreator
from gmail_mgr import GmailManager

app = Flask(__name__, static_folder='static')

# File-based storage for sessions to handle serverless/restarts
SESSION_FILE = 'sessions.json'

def load_sessions():
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_sessions(sessions_data):
    try:
        with open(SESSION_FILE, 'w') as f:
            json.dump(sessions_data, f)
    except Exception as e:
        print(f"Error saving sessions: {e}")

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory(app.static_folder, path)

# Global settings for Gmail
GMAIL_CONFIG = {
    'email': os.environ.get('GMAIL_ADDRESS', 'navautsender@gmail.com'),
    'password': os.environ.get('GMAIL_APP_PASSWORD', 'ipzv ugyl sqjc fvel'),
    'stats': {'created': 0, 'failed': 0}
}

@app.route('/admin')
def admin_panel():
    return send_from_directory(app.static_folder, 'admin.html')

@app.route('/api/admin/config', methods=['GET', 'POST'])
def admin_config():
    if request.method == 'POST':
        data = request.json
        GMAIL_CONFIG['email'] = data.get('email', GMAIL_CONFIG['email'])
        GMAIL_CONFIG['password'] = data.get('password', GMAIL_CONFIG['password'])
        return jsonify({'success': True})
    return jsonify({
        'email': GMAIL_CONFIG['email'],
        'stats': GMAIL_CONFIG['stats']
    })

def auto_create_worker(count, results_list, target_follow=None):
    if not GMAIL_CONFIG['email'] or not GMAIL_CONFIG['password']:
        print("Gmail not configured")
        return

    gmail = GmailManager(GMAIL_CONFIG['email'], GMAIL_CONFIG['password'])
    if not gmail.connect():
        print("Failed to connect to Gmail")
        return

    for i in range(count):
        try:
            # Undr.cash alias logic: random+digits@undr.cash
            # User specified to create with @undr.cash
            random_prefix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
            alias_email = f"{random_prefix}@undr.cash"
            
            creator = InstagramAccountCreator(country='US', language='en')
            creator.generate_headers()
            
            if creator.send_verification_email(alias_email):
                print(f"Email sent to {alias_email}, waiting for OTP (forwarded to {GMAIL_CONFIG['email']})...")
                # Wait for OTP to arrive in the central Gmail inbox
                otp = gmail.get_otp(alias_email)
                if otp:
                    print(f"OTP received: {otp}")
                    signup_code = creator.validate_verification_code(alias_email, otp)
                    if signup_code:
                        credentials = creator.create_account(alias_email, signup_code)
                        if credentials:
                            if target_follow:
                                creator.follow_user(target_follow)
                            
                            GMAIL_CONFIG['stats']['created'] += 1
                            results_list.append({
                                'username': credentials.username,
                                'password': credentials.password,
                                'email': alias_email,
                                'session_id': credentials.session_id,
                                'csrf_token': credentials.csrf_token
                            })
                        else:
                            GMAIL_CONFIG['stats']['failed'] += 1
                else:
                    GMAIL_CONFIG['stats']['failed'] += 1
        except Exception as e:
            print(f"Error: {e}")
            GMAIL_CONFIG['stats']['failed'] += 1
    gmail.disconnect()

@app.route('/gen', methods=['GET'])
def gen_api():
    count = request.args.get('count', default=1, type=int)
    target_follow = request.args.get('follow')
    
    if count > 10: count = 10 # Safety limit
    
    results = []
    # Using the same worker logic
    auto_create_worker(count, results, target_follow)
    
    return jsonify({
        'success': True,
        'count': len(results),
        'accounts': results
    })

@app.route('/api/auto-generate', methods=['POST'])
def auto_generate():
    data = request.json
    count = int(data.get('count', 1))
    target_follow = data.get('target_follow')
    if count > 10: count = 10 # Safety limit
    
    results = []
    auto_create_worker(count, results, target_follow)
    
    return jsonify({'success': True, 'accounts': results})

@app.route('/api/request-otp', methods=['POST'])
def request_otp():
    data = request.json
    email = data.get('email', '').lower()
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    creator = InstagramAccountCreator(country='US', language='en')
    try:
        creator.generate_headers()
        if creator.send_verification_email(email):
            sessions_data = load_sessions()
            sessions_data[email] = creator.get_state()
            save_sessions(sessions_data)
            print(f"Session persisted for {email}")
            return jsonify({'success': True, 'message': 'OTP sent to email'})
        else:
            return jsonify({'error': 'Failed to send OTP'}), 500
    except Exception as e:
        print(f"Error in request_otp: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    email = data.get('email', '').lower()
    otp = data.get('otp')
    
    if not email or not otp:
        return jsonify({'error': 'Email and OTP are required'}), 400
        
    sessions_data = load_sessions()
    state = sessions_data.get(email)
    
    if not state:
        print(f"Session not found for {email}. Available: {list(sessions_data.keys())}")
        return jsonify({'error': f'Session for {email} expired or not found. Please request a new OTP.'}), 404
        
    try:
        creator = InstagramAccountCreator()
        creator.load_state(state)
        
        signup_code = creator.validate_verification_code(email, otp)
        if signup_code:
            credentials = creator.create_account(email, signup_code)
            if credentials:
                # Remove from persistent storage after successful creation
                del sessions_data[email]
                save_sessions(sessions_data)
                return jsonify({
                    'success': True, 
                    'credentials': {
                        'username': credentials.username,
                        'password': credentials.password,
                        'email': credentials.email,
                        'session_id': credentials.session_id,
                        'csrf_token': credentials.csrf_token
                    }
                })
            else:
                return jsonify({'error': 'Account creation failed'}), 500
        else:
            return jsonify({'error': 'Invalid OTP'}), 400
    except Exception as e:
        print(f"Error in verify_otp: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/manual-create', methods=['POST'])
def manual_create():
    data = request.json
    email = data.get('email', '').lower()
    target_follow = data.get('target_follow')
    
    if not email:
        return jsonify({'error': 'Email is required'}), 400
        
    if not GMAIL_CONFIG['email'] or not GMAIL_CONFIG['password']:
        return jsonify({'error': 'Gmail not configured. Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD.'}), 400

    gmail = GmailManager(GMAIL_CONFIG['email'], GMAIL_CONFIG['password'])
    if not gmail.connect():
        return jsonify({'error': 'Failed to connect to Gmail'}), 500

    try:
        creator = InstagramAccountCreator(country='US', language='en')
        creator.generate_headers()
        
        if creator.send_verification_email(email):
            print(f"Email sent to {email}, waiting for OTP...")
            otp = gmail.get_otp(email)
            if otp:
                print(f"OTP received: {otp}")
                signup_code = creator.validate_verification_code(email, otp)
                if signup_code:
                    credentials = creator.create_account(email, signup_code)
                    if credentials:
                        if target_follow:
                            creator.follow_user(target_follow)
                        
                        gmail.disconnect()
                        return jsonify({
                            'success': True,
                            'credentials': {
                                'username': credentials.username,
                                'password': credentials.password,
                                'email': email,
                                'session_id': credentials.session_id,
                                'csrf_token': credentials.csrf_token
                            }
                        })
        gmail.disconnect()
        return jsonify({'error': 'Account creation failed or OTP not received. Check if your Gmail allows IMAP and the app password is correct.'}), 500
    except Exception as e:
        if gmail: gmail.disconnect()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
