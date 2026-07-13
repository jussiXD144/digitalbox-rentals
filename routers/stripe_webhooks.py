import os
import stripe
from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import User, Subscription, DigitalBox
from dotenv import load_dotenv

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

@router.post("/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        if endpoint_secret and sig_header:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        else:
            import json
            data = json.loads(payload)
            event = stripe.Event.construct_from(data, stripe.api_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        await handle_checkout_session(session, db)
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        await handle_subscription_deleted(subscription, db)
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        await handle_subscription_updated(subscription, db)
    
    return {"status": "success"}

async def handle_checkout_session(session: dict, db: Session):
    user_id_str = session.get("client_reference_id")
    subscription_id = session.get("subscription")
    plan_id = session.get("metadata", {}).get("plan_id", "mini")
    customer_id = session.get("customer")
    
    if not user_id_str:
        return
        
    user_id = int(user_id_str)
    user = db.query(User).filter(User.id == user_id).first()
    if user and customer_id:
        user.stripe_customer_id = customer_id
        db.commit()
    
    # Check if user already has an active box
    existing_sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    if existing_sub:
        existing_sub.status = "active"
        existing_sub.stripe_subscription_id = subscription_id
        existing_sub.plan_name = plan_id
        db.commit()
    else:
        new_sub = Subscription(
            user_id=user_id,
            stripe_subscription_id=subscription_id,
            status="active",
            plan_name=plan_id
        )
        db.add(new_sub)
        
        box_path = f"user_{user_id}/"
        
        box = DigitalBox(
            user_id=user_id,
            bucket_path=box_path,
            is_active=True,
            current_storage_bytes=0
        )
        db.add(box)
        db.commit()

async def handle_subscription_updated(subscription, db: Session):
    sub_id = subscription.get('id')
    status = subscription.get('status')
    
    sub = db.query(Subscription).filter(Subscription.stripe_subscription_id == sub_id).first()
    if sub:
        sub.status = status
        box = db.query(DigitalBox).filter(DigitalBox.user_id == sub.user_id).first()
        if box:
            box.is_active = (status == "active")
        db.commit()

async def handle_subscription_deleted(subscription, db: Session):
    sub_id = subscription.get('id')
    
    sub = db.query(Subscription).filter(Subscription.stripe_subscription_id == sub_id).first()
    if sub:
        sub.status = "canceled"
        box = db.query(DigitalBox).filter(DigitalBox.user_id == sub.user_id).first()
        if box:
            box.is_active = False
        db.commit()
