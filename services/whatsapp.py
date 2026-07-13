import os
from sqlalchemy.sql import func
from twilio.rest import Client
from database import SessionLocal
from models import Subscription, DigitalBox
from dotenv import load_dotenv

load_dotenv()

def generate_monthly_report():
    db = SessionLocal()
    try:
        active_subs = db.query(Subscription).filter(Subscription.status == "active").all()
        total_active_users = len(active_subs)
        
        # Calculate MRR locally
        total_mrr = 0.0
        for sub in active_subs:
            if sub.plan_name == "mini":
                total_mrr += 1.99 + (1.50 if sub.has_crypto_addon else 0.0)
            elif sub.plan_name == "medi":
                total_mrr += 3.49 + (2.00 if sub.has_crypto_addon else 0.0)
            elif sub.plan_name == "maxi":
                total_mrr += 4.99 + (3.00 if sub.has_crypto_addon else 0.0)
                
        # Calculate Total Storage
        storage_bytes = db.query(func.sum(DigitalBox.current_storage_bytes)).filter(DigitalBox.is_active == True).scalar()
        if storage_bytes is None:
            storage_bytes = 0
            
        total_gb = storage_bytes / (1024 * 1024 * 1024)
        
        # B2 Storage cost is roughly $0.005 per GB
        b2_cost = total_gb * 0.005
        
        net_profit = total_mrr - b2_cost
        
        message_body = (
            f"🚀 *DigitalBox Monthly Report* 🚀\n"
            f"---------------------------------\n"
            f"👥 *Active Users:* {total_active_users}\n"
            f"💰 *MRR (Revenue):* €{total_mrr:.2f}\n"
            f"💾 *Total Storage:* {total_gb:.2f} GB\n"
            f"💸 *B2 Cost:* €{b2_cost:.2f}\n"
            f"---------------------------------\n"
            f"📈 *Net Profit:* €{net_profit:.2f}\n"
        )
        
        return message_body
        
    finally:
        db.close()

def send_whatsapp_report():
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_WHATSAPP_NUMBER", "+14155238886")
    to_number = os.getenv("ADMIN_PHONE")
    
    if not all([account_sid, auth_token, to_number]):
        print("Skipping WhatsApp report: Missing Twilio credentials in .env")
        return
        
    client = Client(account_sid, auth_token)
    
    report_text = generate_monthly_report()
    
    try:
        # Twilio WhatsApp numbers must be prefixed with 'whatsapp:'
        if not from_number.startswith("whatsapp:"):
            from_number = f"whatsapp:{from_number}"
        if not to_number.startswith("whatsapp:"):
            to_number = f"whatsapp:{to_number}"
            
        message = client.messages.create(
            body=report_text,
            from_=from_number,
            to=to_number
        )
        print(f"WhatsApp message sent! SID: {message.sid}")
    except Exception as e:
        print(f"Failed to send WhatsApp message: {e}")
