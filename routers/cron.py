import os
import stripe
import time
import math
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Subscription, DigitalBox
from dotenv import load_dotenv

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
CRON_SECRET = os.getenv("CRON_SECRET", "default_secret_please_change")

router = APIRouter(prefix="/cron", tags=["cron"])

@router.post("/report-usage")
async def report_usage(authorization: str = Header(None), db: Session = Depends(get_db)):
    if authorization != f"Bearer {CRON_SECRET}":
        raise HTTPException(status_code=401, detail="Unauthorized cron invocation")
        
    active_subs = db.query(Subscription).filter(Subscription.status == "active").all()
    
    reports = []
    for sub in active_subs:
        box = db.query(DigitalBox).filter(DigitalBox.user_id == sub.user_id).first()
        if not box:
            continue
            
        # Determine quota based on plan
        included_gb = 20
        if sub.plan_name == "mini":
            included_gb = 20
        elif sub.plan_name == "medi":
            included_gb = 100
        elif sub.plan_name == "maxi":
            included_gb = 500
            
        current_gb = box.current_storage_bytes / (1024 * 1024 * 1024)
        extra_gb = max(0.0, current_gb - included_gb)
        billable_gb = math.ceil(extra_gb)
            
        try:
            stripe_sub = stripe.Subscription.retrieve(sub.stripe_subscription_id)
            
            # Find the metered item in the subscription
            metered_item_id = None
            for item in stripe_sub.get('items', {}).get('data', []):
                if item['price']['recurring']['usage_type'] == 'metered':
                    metered_item_id = item['id']
                    break
                    
            if not metered_item_id:
                print(f"No metered item found for sub {sub.id}")
                continue
            
            stripe.SubscriptionItem.create_usage_record(
                metered_item_id,
                quantity=billable_gb, 
                timestamp=int(time.time()),
                action='set'
            )
            reports.append({"user_id": sub.user_id, "plan": sub.plan_name, "extra_gb_reported": billable_gb})
        except Exception as e:
            print(f"Failed to report usage for sub {sub.id}: {e}")
            
    return {"status": "success", "reports": reports}
