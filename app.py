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
    
    try:
        url = f'https://free-ff-api-src-77.vercel.app/api/v1/account?region=ME&uid={uid}'
        r = requests.get(url, timeout=10)
        data = r.json()
        
        if data and 'Nickname' in data:
            return jsonify({
                'success': True,
                'data': {
                    'uid': uid,
                    'nickname': data['Nickname'],
                    'level': data.get('Level', 0),
                    'likes': data.get('Likes', 0)
                }
            })
        else:
            return jsonify({'success': False, 'error': 'لم يتم العثور على اللاعب'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port)
