from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

API_KEY = 'ptlc_j1FM7HAOkIZrLLsP6ERDO4Q5RVYUzjTgZ7pH4qCNGFc'

# API الجديد من البوت
INFO_API_URL = "http://raw.thug4ff.xyz/info"

@app.route('/')
def home():
    return jsonify({'status': 'FF API Running'})

@app.route('/api/player/<uid>')
def get_player(uid):
    key = request.args.get('key') or request.headers.get('x-api-key')
    
    if key != API_KEY:
        return jsonify({'success': False, 'error': 'مفتاح غير صالح'})
    
    if not uid or not uid.isdigit() or len(uid) < 6:
        return jsonify({'success': False, 'error': 'UID غير صالح'})
    
    try:
        # استخدام API الجديد
        url = f"{INFO_API_URL}?uid={uid}&key=great"
        r = requests.get(url, timeout=15)
        data = r.json()
        
        if data and 'basic' in data:
            basic = data.get('basic', {})
            social = data.get('social', {})
            clan = data.get('clan', {})
            
            return jsonify({
                'success': True,
                'data': {
                    'uid': uid,
                    'nickname': basic.get('nickname', 'غير معروف'),
                    'level': basic.get('level', 0),
                    'likes': social.get('likes', 0),
                    'clan': clan.get('clanName', 'بدون قبيلة'),
                    'lastLogin': basic.get('lastLoginAt', 'غير متاح'),
                    'region': basic.get('region', 'ME')
                }
            })
        else:
            return jsonify({'success': False, 'error': 'لم يتم العثور على اللاعب'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port)
