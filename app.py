from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector
import requests
import random
import string
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth

app = Flask(__name__)
CORS(app)

# ==================== إعدادات MySQL ====================
DB_CONFIG = {
    'host': 'sql301.hstn.me',
    'user': 'mseet_42310483',
    'password': 'abdo2009',  # استبدلها بكلمة مرور vPanel
    'database': 'mseet_42310483_dz2024',
    'charset': 'utf8mb4',
    'use_unicode': True
}

# ==================== إعدادات Firebase (للمصادقة فقط) ====================
firebase_admin.initialize_app(credentials.Certificate("firebase-service-account.json"))

# ==================== الإعدادات ====================
API_KEY = 'ptlc_j1FM7HAOkIZrLLsP6ERDO4Q5RVYUzjTgZ7pH4qCNGFc'
INFO_API_URL = "http://raw.thug4ff.xyz/info"
ACCOUNT_NUMBER = '00799999004388586920'

# ==================== دوال مساعدة ====================
def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def generate_uid():
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return ''.join(random.choices(chars, k=8))

def verify_token(token):
    """التحقق من توكن Firebase"""
    try:
        decoded = firebase_auth.verify_id_token(token)
        return decoded['uid']
    except:
        return None

def get_user_by_firebase(firebase_uid):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute('SELECT * FROM ff_users WHERE firebase_uid = %s', (firebase_uid,))
    user = cursor.fetchone()
    db.close()
    return user

def is_banned(user):
    if user and user.get('banned_until', 0) > int(datetime.now().timestamp() * 1000):
        return True
    return False

# ==================== Routes ====================

@app.route('/')
def home():
    return jsonify({'status': 'API Running', 'db': 'MySQL', 'secure': True})

# ==================== مصادقة ====================
@app.route('/api/auth', methods=['POST'])
def auth_user():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    firebase_uid = verify_token(token)
    
    if not firebase_uid:
        return jsonify({'success': False, 'error': 'جلسة منتهية'}), 401
    
    data = request.json or {}
    email = data.get('email', '')
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute('SELECT * FROM ff_users WHERE firebase_uid = %s', (firebase_uid,))
    user = cursor.fetchone()
    
    if not user:
        custom_uid = generate_uid()
        now = int(datetime.now().timestamp() * 1000)
        cursor.execute(
            'INSERT INTO ff_users (firebase_uid, email, custom_uid, balance, created_at) VALUES (%s, %s, %s, 0, %s)',
            (firebase_uid, email, custom_uid, now)
        )
        db.commit()
        cursor.execute('SELECT * FROM ff_users WHERE firebase_uid = %s', (firebase_uid,))
        user = cursor.fetchone()
    
    db.close()
    
    if is_banned(user):
        ban_time = user['banned_until']
        remaining = datetime.fromtimestamp(ban_time / 1000).strftime('%Y-%m-%d %H:%M')
        return jsonify({'success': False, 'error': f'محظور حتى {remaining}'}), 403
    
    return jsonify({
        'success': True,
        'data': {
            'firebase_uid': user['firebase_uid'],
            'email': user['email'],
            'custom_uid': user['custom_uid'],
            'balance': float(user['balance'])
        }
    })

# ==================== فحص لاعب ====================
@app.route('/api/player/<uid>')
def get_player(uid):
    key = request.headers.get('x-api-key') or request.args.get('key')
    if key != API_KEY:
        return jsonify({'success': False, 'error': 'غير مصرح'})
    
    if not uid or not uid.isdigit() or len(uid) < 6:
        return jsonify({'success': False, 'error': 'UID غير صالح'})
    
    try:
        r = requests.get(f'{INFO_API_URL}?uid={uid}&key=great', timeout=10)
        data = r.json()
        
        if data and 'basicInfo' in data:
            info = data['basicInfo']
            return jsonify({
                'success': True,
                'data': {
                    'uid': uid,
                    'nickname': info.get('nickname', '?'),
                    'level': info.get('level', 0),
                    'likes': info.get('liked', 0)
                }
            })
        return jsonify({'success': False, 'error': 'لم يتم العثور على اللاعب'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'خطأ: {str(e)}'})

# ==================== انشاء طلب ====================
@app.route('/api/order', methods=['POST'])
def create_order():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    firebase_uid = verify_token(token)
    if not firebase_uid:
        return jsonify({'success': False, 'error': 'جلسة منتهية'}), 401
    
    user = get_user_by_firebase(firebase_uid)
    if not user:
        return jsonify({'success': False, 'error': 'مستخدم غير موجود'})
    
    if is_banned(user):
        return jsonify({'success': False, 'error': 'محظور'}), 403
    
    data = request.json
    required = ['playerUid', 'diamonds', 'price', 'paymentMethod', 'transactionId']
    for field in required:
        if field not in data:
            return jsonify({'success': False, 'error': f'حقل ناقص: {field}'}), 400
    
    if data['paymentMethod'] not in ['bridi', 'balance']:
        return jsonify({'success': False, 'error': 'طريقة دفع غير صالحة'}), 400
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    now = int(datetime.now().timestamp() * 1000)
    
    if data['paymentMethod'] == 'balance':
        if user['balance'] < data['price']:
            db.close()
            return jsonify({'success': False, 'error': 'رصيد غير كافي'}), 400
        
        cursor.execute('UPDATE ff_users SET balance = balance - %s WHERE id = %s',
                      (data['price'], user['id']))
        order_status = 'مكتمل'
    else:
        order_status = 'قيد المراجعة'
    
    cursor.execute(
        '''INSERT INTO ff_orders 
           (user_id, player_uid, diamonds, price, payment_method, transaction_id, order_status, created_at) 
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
        (user['id'], data['playerUid'], data['diamonds'], data['price'],
         data['paymentMethod'], data['transactionId'], order_status, now)
    )
    db.commit()
    
    # جلب الرصيد الجديد
    cursor.execute('SELECT balance FROM ff_users WHERE id = %s', (user['id'],))
    new_balance = float(cursor.fetchone()['balance'])
    db.close()
    
    return jsonify({
        'success': True,
        'order_status': order_status,
        'balance': new_balance
    })

# ==================== جلب الطلبات ====================
@app.route('/api/orders', methods=['GET'])
def get_orders():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    firebase_uid = verify_token(token)
    if not firebase_uid:
        return jsonify({'success': False, 'error': 'جلسة منتهية'}), 401
    
    user = get_user_by_firebase(firebase_uid)
    if not user:
        return jsonify({'orders': []})
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        'SELECT * FROM ff_orders WHERE user_id = %s ORDER BY created_at DESC LIMIT 50',
        (user['id'],)
    )
    orders = cursor.fetchall()
    db.close()
    
    # تحويل Decimal إلى float
    for o in orders:
        o['price'] = float(o['price'])
        o['diamonds'] = int(o['diamonds'])
    
    return jsonify({'success': True, 'orders': orders})

# ==================== استخدام بطاقة ====================
@app.route('/api/card', methods=['POST'])
def use_card():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    firebase_uid = verify_token(token)
    if not firebase_uid:
        return jsonify({'success': False, 'error': 'جلسة منتهية'}), 401
    
    code = request.json.get('code', '').upper().strip()
    if len(code) != 12 or not code.isalnum():
        return jsonify({'success': False, 'error': 'رمز غير صالح'}), 400
    
    user = get_user_by_firebase(firebase_uid)
    if not user:
        return jsonify({'success': False, 'error': 'مستخدم غير موجود'})
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    cursor.execute('SELECT * FROM ff_cards WHERE code = %s', (code,))
    card = cursor.fetchone()
    
    if not card:
        db.close()
        return jsonify({'success': False, 'error': 'بطاقة غير موجودة'})
    
    if card['is_used']:
        db.close()
        return jsonify({'success': False, 'error': 'البطاقة مستخدمة'})
    
    if card['expires_at'] > 0 and card['expires_at'] < int(datetime.now().timestamp() * 1000):
        db.close()
        return jsonify({'success': False, 'error': 'البطاقة منتهية'})
    
    now = int(datetime.now().timestamp() * 1000)
    
    cursor.execute(
        'UPDATE ff_cards SET is_used = TRUE, used_by = %s, used_at = %s WHERE id = %s',
        (user['id'], now, card['id'])
    )
    cursor.execute(
        'UPDATE ff_users SET balance = balance + %s WHERE id = %s',
        (card['amount'], user['id'])
    )
    db.commit()
    
    cursor.execute('SELECT balance FROM ff_users WHERE id = %s', (user['id'],))
    new_balance = float(cursor.fetchone()['balance'])
    db.close()
    
    return jsonify({
        'success': True,
        'amount': float(card['amount']),
        'balance': new_balance
    })

# ==================== معلومات المستخدم ====================
@app.route('/api/user', methods=['GET'])
def get_user_info():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    firebase_uid = verify_token(token)
    if not firebase_uid:
        return jsonify({'success': False, 'error': 'جلسة منتهية'}), 401
    
    user = get_user_by_firebase(firebase_uid)
    if not user:
        return jsonify({'success': False, 'error': 'مستخدم غير موجود'})
    
    return jsonify({
        'success': True,
        'data': {
            'custom_uid': user['custom_uid'],
            'balance': float(user['balance'])
        }
    })

# ==================== تشغيل ====================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port)
