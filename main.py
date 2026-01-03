import string
import random
import os
from flask import Flask, request, jsonify, send_from_directory
from Acc_Gen import InstagramAccountCreator
from gmail_mgr import GmailManager

app = Flask(__name__, static_folder='static')

# In-memory storage for active sessions
sessions = {}

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory(app.static_folder, path)

from gmail_mgr import GmailManager

# Global settings for Gmail
GMAIL_CONFIG = {
    'email': os.environ.get('GMAIL_ADDRESS', 'navdeepsharma20070@gmail.com'),
    'password': os.environ.get('GMAIL_APP_PASSWORD', 'sfnh bhok rmes uygm'),
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
            # Gmail alias logic: username+random@gmail.com
            base_user = GMAIL_CONFIG['email'].split('@')[0]
            random_suffix = ''.join(random.choices(string.digits, k=6))
            alias_email = f"{base_user}+{random_suffix}@gmail.com"
            
            creator = InstagramAccountCreator(country='US', language='en')
            creator.generate_headers()
            
            if creator.send_verification_email(alias_email):
                print(f"Email sent to {alias_email}, waiting for OTP...")
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
    email = data.get('email')
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    creator = InstagramAccountCreator(country='US', language='en')
    try:
        creator.generate_headers()
        if creator.send_verification_email(email):
            sessions[email] = creator
            return jsonify({'success': True, 'message': 'OTP sent to email'})
        else:
            return jsonify({'error': 'Failed to send OTP'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    email = data.get('email')
    otp = data.get('otp')
    
    if not email or not otp:
        return jsonify({'error': 'Email and OTP are required'}), 400
        
    creator = sessions.get(email)
    if not creator:
        return jsonify({'error': 'Session expired or not found'}), 404
        
    try:
        signup_code = creator.validate_verification_code(email, otp)
        if signup_code:
            credentials = creator.create_account(email, signup_code)
            if credentials:
                # Remove from sessions after successful creation
                del sessions[email]
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
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
