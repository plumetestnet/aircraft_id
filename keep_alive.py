"""
Keep Alive + NOWPayments Webhook Handler
"""

from flask import Flask, jsonify, request
from threading import Thread
import logging

logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def home():
    """Health check"""
    return "Bot is alive! ✅"

@app.route('/nowpayments/webhook', methods=['POST'])
def nowpayments_webhook():
    """
    Handle NOWPayments IPN callbacks
    This endpoint receives payment notifications
    """
    try:
        # Import here to avoid circular imports
        from payment_nowpayments import process_ipn_callback
        
        # Get signature from header
        signature = request.headers.get('x-nowpayments-sig', '')
        
        # Get IPN data
        ipn_data = request.json
        
        logger.info(f"📥 IPN received: {ipn_data.get('payment_id')} - Status: {ipn_data.get('payment_status')}")
        
        # Process callback
        success = process_ipn_callback(ipn_data, signature)
        
        if success:
            return jsonify({'status': 'ok'}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Processing failed'}), 400
            
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/razorpay/webhook', methods=['POST'])
def razorpay_webhook():
    """Handle Razorpay webhook for INR payments"""
    try:
        import config
        import razorpay
        from payment_razorpay import process_payment_success, process_payment_failed
        
        logger.info("🔥 RAZORPAY WEBHOOK RECEIVED")
        
        razorpay_client = razorpay.Client(auth=(config.RAZORPAY_KEY_ID, config.RAZORPAY_KEY_SECRET))
        webhook_data = request.get_json()
        webhook_signature = request.headers.get('X-Razorpay-Signature')
        
        if not webhook_signature:
            logger.error("❌ No signature")
            return jsonify({'status': 'error'}), 400
        
        event = webhook_data.get('event', 'unknown')
        logger.info(f"📦 Event: {event}")
        
        # Verify signature
        try:
            razorpay_client.utility.verify_webhook_signature(
                request.get_data().decode('utf-8'),
                webhook_signature,
                config.RAZORPAY_KEY_SECRET
            )
            logger.info("✅ Signature verified")
        except Exception as e:
            logger.error(f"❌ Invalid signature: {e}")
            return jsonify({'status': 'invalid_signature'}), 400
        
        # Process payment_link.paid
        if event == 'payment_link.paid':
            payment_link = webhook_data.get('payload', {}).get('payment_link', {}).get('entity', {})
            payment_link_id = payment_link.get('id')
            
            # Try to get payment_id from payments array
            payments = payment_link.get('payments', [])
            payment_id = None
            
            if payments and len(payments) > 0:
                # Get payment_id from first payment
                if isinstance(payments[0], dict):
                    payment_id = payments[0].get('payment_id')
                else:
                    # Sometimes it's just the ID string
                    payment_id = payments[0]
            
            # Fallback: try to get from payment_link object itself
            if not payment_id:
                payment_id = payment_link.get('payment_id')
            
            # Last resort: use payment_link_id
            if not payment_id:
                payment_id = f"plink_{payment_link_id}"
                logger.warning(f"⚠️ Payment ID not found in webhook, using link ID")
            
            logger.info(f"💰 Payment link paid: {payment_link_id}")
            logger.info(f"🆔 Payment ID: {payment_id}")
            
            success = process_payment_success(payment_link_id, payment_id)
            
            if success:
                logger.info(f"✅ Balance credited")
                return jsonify({'status': 'success'}), 200
            else:
                logger.error(f"❌ Processing failed")
                return jsonify({'status': 'failed'}), 500
        
        # Process other events
        elif event == 'payment.captured':
            payment = webhook_data.get('payload', {}).get('payment', {}).get('entity', {})
            order_id = payment.get('order_id')
            payment_id = payment.get('id')
            success = process_payment_success(order_id, payment_id)
            return jsonify({'status': 'success' if success else 'failed'}), 200
        
        elif event in ['payment.failed', 'payment_link.cancelled']:
            payment_data = webhook_data.get('payload', {})
            if 'payment_link' in payment_data:
                order_id = payment_data['payment_link']['entity']['id']
            else:
                order_id = payment_data['payment']['entity'].get('order_id')
            process_payment_failed(order_id)
            return jsonify({'status': 'acknowledged'}), 200
        
        return jsonify({'status': 'acknowledged'}), 200
            
    except Exception as e:
        logger.error(f"❌ Razorpay webhook error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error'}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'telegram-bot'}), 200

def run():
    """Run Flask app"""
    app.run(host='0.0.0.0', port=8080, debug=False)

def keep_alive():
    """Start Flask server in background thread"""
    t = Thread(target=run)
    t.daemon = True
    t.start()
    logger.info("✅ Keep-alive server started on port 8080")
    logger.info("✅ Webhook endpoint: /nowpayments/webhook")
    logger.info("✅ Webhook endpoint: /razorpay/webhook")