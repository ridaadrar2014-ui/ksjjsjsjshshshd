from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

API_KEY = 'ptlc_j1FM7HAOkIZrLLsP6ERDO4Q5RVYUzjTgZ7pH4qCNGFc'

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
    
    apis = [
        f"http://raw.thug4ff.xyz/info?uid={uid}&key=great",
        f"https://free-ff-api-src-77.vercel.app/api/v1/account?region=ME&uid={uid}"
    ]
    
    for url in apis:
        try:
            r = requests.get(url, timeout=15)
            if r.status_code != 200:
                continue
            data = r.json()
            
            # صيغة thug4ff - basicInfo
            if 'basicInfo' in data:
                info = data['basicInfo']
                return jsonify({'success': True, 'data': {
                    'uid': uid,
                    'nickname': info.get('nickname', '?'),
                    'level': info.get('level', 0),
                    'likes': info.get('liked', 0)
                }})
            
            # صيغة thug4ff - basic (قديمة)
            if 'basic' in data:
                info = data['basic']
                return jsonify({'success': True, 'data': {
                    'uid': uid,
                    'nickname': info.get('nickname', '?'),
                    'level': info.get('level', 0),
                    'likes': data.get('social', {}).get('likes', 0)
                }})
            
            # صيغة vercel
            if 'Nickname' in data:
                return jsonify({'success': True, 'data': {
                    'uid': uid,
                    'nickname': data['Nickname'],
                    'level': data.get('Level', 0),
                    'likes': data.get('Likes', 0)
                }})
                
        except Exception as e:
            continue
    
    return jsonify({'success': False, 'error': 'لم يتم العثور على اللاعب'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port)
