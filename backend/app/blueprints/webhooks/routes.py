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
        from app.models import SystemSetting
        verify_token = SystemSetting.get('meta_verify_token') or current_app.config.get('META_VERIFY_TOKEN')
        if mode == 'subscribe' and token == verify_token:
            return challenge, 200
        return 'Forbidden', 403
    return 'Bad Request', 400

@webhooks_bp.route('/meta', methods=['POST'])
def receive_webhook():
    payload = request.get_data()
    signature = request.headers.get('X-Hub-Signature-256')
    from app.models import SystemSetting
    
    if not signature:
        SystemSetting.set('meta_webhook_last_error', 'Missing X-Hub-Signature-256 header in request')
        return 'Missing signature', 400
        
    # Validate signature
    secret_str = SystemSetting.get('meta_app_secret') or current_app.config.get('META_APP_SECRET', '')
    secret = secret_str.encode('utf-8')
    expected = 'sha256=' + hmac.new(secret, payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        SystemSetting.set('meta_webhook_last_error', 'Invalid signature. The App Secret does not match.')
        return 'Invalid signature', 403
        
    try:
        from app.tasks import process_meta_webhook
        process_meta_webhook(request.json)
        # Clear the error on success
        SystemSetting.set('meta_webhook_last_error', '')
    except Exception as e:
        import traceback
        current_app.logger.error(f'Error processing webhook: {traceback.format_exc()}')
        SystemSetting.set('meta_webhook_last_error', f'Internal error processing lead: {str(e)}')
        return 'Internal error', 500
    
    return 'EVENT_RECEIVED', 200

@webhooks_bp.route('/meta/status', methods=['GET'])
def webhook_status():
    return jsonify({
        "status": "active",
        "instructions": "Configure Meta Developer Portal with webhook URL and token."
    })
