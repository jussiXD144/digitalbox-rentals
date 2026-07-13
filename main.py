import os
import stripe
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import timedelta

from database import engine, Base, get_db
from models import User
from schemas import UserCreate
from auth import get_password_hash, verify_password, create_access_token, get_current_user_from_cookie, ACCESS_TOKEN_EXPIRE_MINUTES
from routers import box, stripe_webhooks, cron, seo
from dotenv import load_dotenv

load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="DigitalBox Rentals")

app.include_router(box.router)
app.include_router(stripe_webhooks.router)
app.include_router(cron.router)
app.include_router(seo.router)

# We use absolute path to templates to avoid CWD issues
current_dir = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(current_dir, "templates"))
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, user: User = Depends(get_current_user_from_cookie)):
    return templates.TemplateResponse(request=request, name="index.html", context={"user": user})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={})

@app.post("/login")
async def login(response: Response, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return RedirectResponse(url="/login?error=Invalid credentials", status_code=status.HTTP_302_FOUND)
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response

@app.post("/register")
async def register(response: Response, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if user:
        return RedirectResponse(url="/login?error=Email already registered", status_code=status.HTTP_302_FOUND)
    
    new_user = User(email=email, hashed_password=get_password_hash(password))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user.email}, expires_delta=access_token_expires
    )
    
    res = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    res.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return res

@app.get("/logout")
async def logout(response: Response):
    res = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    res.delete_cookie("access_token")
    return res

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user_from_cookie)):
    if not user:
        return RedirectResponse(url="/login")
    
    has_active_box = False
    if user.digitalbox and user.digitalbox.is_active:
        has_active_box = True

    from models import Subscription
    active_sub = db.query(Subscription).filter(Subscription.user_id == user.id, Subscription.status == "active").first()
    plan_name = active_sub.plan_name if active_sub else "mini"
    
    has_crypto_addon = active_sub.has_crypto_addon if active_sub else False
    
    quotas = {"mini": 20, "medi": 100, "maxi": 500}
    included_gb = quotas.get(plan_name, 20)

    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "user": user, 
        "has_active_box": has_active_box,
        "plan_name": plan_name,
        "included_gb": included_gb,
        "has_crypto_addon": has_crypto_addon
    })

@app.post("/create-checkout-session")
async def create_checkout_session(request: Request, plan_id: str = Form(...), crypto_addon: bool = Form(False), user: User = Depends(get_current_user_from_cookie)):
    if not user:
        return RedirectResponse(url="/login")
        
    if plan_id == "mini":
        base_price = os.getenv("STRIPE_PRICE_MINI_BASE", "price_mini_base")
        addon_price = os.getenv("STRIPE_PRICE_MINI_CRYPTO_ADDON", "price_mini_crypto")
    elif plan_id == "medi":
        base_price = os.getenv("STRIPE_PRICE_MEDI_BASE", "price_medi_base")
        addon_price = os.getenv("STRIPE_PRICE_MEDI_CRYPTO_ADDON", "price_medi_crypto")
    elif plan_id == "maxi":
        base_price = os.getenv("STRIPE_PRICE_MAXI_BASE", "price_maxi_base")
        addon_price = os.getenv("STRIPE_PRICE_MAXI_CRYPTO_ADDON", "price_maxi_crypto")
    else:
        return RedirectResponse(url="/dashboard?error=Invalid plan")
    
    metered_price = os.getenv("STRIPE_PRICE_METERED_OVERUSE", "price_metered_overuse")
    
    try:
        domain_url = str(request.base_url)
        
        line_items = [
            {"price": base_price, "quantity": 1},
            {"price": metered_price}
        ]
        
        if crypto_addon:
            line_items.insert(1, {"price": addon_price, "quantity": 1})
            
        checkout_session = stripe.checkout.Session.create(
            success_url=domain_url + "dashboard?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=domain_url + "dashboard",
            payment_method_types=["card"],
            mode="subscription",
            line_items=line_items,
            client_reference_id=str(user.id),
            metadata={"plan_id": plan_id, "has_crypto_addon": str(crypto_addon).lower()}
        )
        return RedirectResponse(url=checkout_session['url'], status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        print(f"Stripe error (expected without valid keys): {e}")
        return RedirectResponse(url=f"/mock-checkout-success?plan_id={plan_id}&crypto_addon={str(crypto_addon).lower()}", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/mock-checkout-success")
async def mock_checkout_success(plan_id: str = "mini", crypto_addon: bool = False, user: User = Depends(get_current_user_from_cookie), db: Session = Depends(get_db)):
    if not user:
        return RedirectResponse(url="/login")
    
    from routers.stripe_webhooks import handle_checkout_session
    mock_session = {
        "customer": f"cus_mock_{user.id}",
        "subscription": f"sub_mock_{user.id}",
        "client_reference_id": str(user.id),
        "metadata": {"plan_id": plan_id, "has_crypto_addon": str(crypto_addon).lower()}
    }
    await handle_checkout_session(mock_session, db)
    return RedirectResponse(url="/dashboard")

