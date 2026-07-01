from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

API_KEY = 'ptlc_j1FM7HAOkIZrLLsP6ERDO4Q5RVYUzjTgZ7pH4qCNGFc'

# كل روابط API الممكنة
API_URLS = [
    "http://raw.thug4ff.xyz/info?uid={uid}&key=great",
    "https://free-ff-api-src-77.vercel.app/api/v1/account?region=ME&uid={uid}",
    "https://free-ff-api-src-77.vercel.app/api/v1/account?region=IND&uid={uid}",
]

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
    
    # نجرب كل API حتى نجد البيانات
    for url_template in API_URLS:
        try:
            url = url_template.format(uid=uid)
            r = requests.get(url, timeout=10)
            data = r.json()
            
            # تحقق من الصيغ المختلفة للرد
            nickname = None
            level = 0
            likes = 0
            
            # صيغة thug4ff
            if 'basic' in data:
                nickname = data['basic'].get('nickname')
                level = data['basic'].get('level', 0)
                likes = data['social'].get('likes', 0)
            # صيغة vercel
            elif 'Nickname' in data:
                nickname = data['Nickname']
                level = data.get('Level', 0)
                likes = data.get('Likes', 0)
            
            if nickname:
                return jsonify({
                    'success': True,
                    'data': {
                        'uid': uid,
                        'nickname': nickname,
                        'level': level,
                        'likes': likes
                    }
                })
        except:
            continue
    
    return jsonify({'success': False, 'error': 'لم يتم العثور على اللاعب في أي سيرفر'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port)
