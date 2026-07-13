import os
from fastapi import APIRouter, Request, Depends, HTTPException, Form, status, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from database import get_db
from models import User, Subscription, DigitalBox

router = APIRouter(prefix="/admin", tags=["admin"])

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
templates = Jinja2Templates(directory=os.path.join(parent_dir, "templates"))

def verify_admin_password(request: Request):
    admin_cookie = request.cookies.get("admin_session")
    admin_pw = os.getenv("ADMIN_PASSWORD", "supersecret123")
    if admin_cookie != admin_pw:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/admin/login"})
    return True

@router.get("/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    return templates.TemplateResponse(request=request, name="admin_login.html", context={})

@router.post("/login")
async def admin_login(response: Response, password: str = Form(...)):
    admin_pw = os.getenv("ADMIN_PASSWORD", "supersecret123")
    if password == admin_pw:
        res = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        res.set_cookie(key="admin_session", value=password, httponly=True)
        return res
    return RedirectResponse(url="/admin/login?error=Invalid password", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/logout")
async def admin_logout():
    res = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    res.delete_cookie("admin_session")
    return res

@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    try:
        verify_admin_password(request)
    except HTTPException as e:
        return RedirectResponse(url="/admin/login")

    # Gather Metrics
    users = db.query(User).all()
    active_subs = db.query(Subscription).filter(Subscription.status == "active").all()
    
    total_mrr = 0.0
    for sub in active_subs:
        if sub.plan_name == "mini":
            total_mrr += 1.99 + (1.50 if sub.has_crypto_addon else 0.0)
        elif sub.plan_name == "medi":
            total_mrr += 3.49 + (2.00 if sub.has_crypto_addon else 0.0)
        elif sub.plan_name == "maxi":
            total_mrr += 4.99 + (3.00 if sub.has_crypto_addon else 0.0)
            
    storage_bytes = db.query(func.sum(DigitalBox.current_storage_bytes)).filter(DigitalBox.is_active == True).scalar()
    if storage_bytes is None:
        storage_bytes = 0
    total_gb = storage_bytes / (1024 * 1024 * 1024)
    b2_cost = total_gb * 0.005
    net_profit = total_mrr - b2_cost
    
    # User Management Table
    customers = []
    for u in users:
        sub = next((s for s in u.subscriptions if s.status == "active"), None)
        box = u.digitalbox
        
        customers.append({
            "id": u.id,
            "email": u.email,
            "created_at": u.created_at.strftime("%Y-%m-%d") if u.created_at else "N/A",
            "tier": sub.plan_name.capitalize() if sub else "None",
            "has_addon": sub.has_crypto_addon if sub else False,
            "status": sub.status if sub else "Inactive",
            "usage_gb": (box.current_storage_bytes / (1024*1024*1024)) if box else 0.0,
            "is_blocked": not box.is_active if box else True
        })
        
    return templates.TemplateResponse(request=request, name="admin_dashboard.html", context={
        "total_active": len(active_subs),
        "total_mrr": total_mrr,
        "total_gb": total_gb,
        "net_profit": net_profit,
        "customers": customers
    })

@router.post("/deactivate/{user_id}")
async def deactivate_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    verify_admin_password(request)
    
    box = db.query(DigitalBox).filter(DigitalBox.user_id == user_id).first()
    if box:
        box.is_active = False
        db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/test_whatsapp")
async def test_whatsapp(request: Request):
    verify_admin_password(request)
    
    from services.whatsapp import send_whatsapp_report
    send_whatsapp_report()
    return RedirectResponse(url="/admin/dashboard?msg=whatsapp_sent", status_code=status.HTTP_303_SEE_OTHER)
