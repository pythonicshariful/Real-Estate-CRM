from flask import request, jsonify, current_app
from app.blueprints.webhooks import webhooks_bp
import hashlib
import hmac

@webhooks_bp.route('/meta', methods=['GET'])
def verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    if mode and token:
        if mode == 'subscribe' and token == current_app.config['META_VERIFY_TOKEN']:
            return challenge, 200
        return 'Forbidden', 403
    return 'Bad Request', 400

@webhooks_bp.route('/meta', methods=['POST'])
def receive_webhook():
    payload = request.get_data()
    signature = request.headers.get('X-Hub-Signature-256')
    
    if not signature:
        return 'Missing signature', 400
        
    # Validate signature
    secret = current_app.config['META_APP_SECRET'].encode('utf-8')
    expected = 'sha256=' + hmac.new(secret, payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return 'Invalid signature', 403
        
    from app.tasks import process_meta_webhook
    process_meta_webhook(request.json)
    
    return 'EVENT_RECEIVED', 200

@webhooks_bp.route('/meta/status', methods=['GET'])
def webhook_status():
    return jsonify({
        "status": "active",
        "instructions": "Configure Meta Developer Portal with webhook URL and token."
    })
