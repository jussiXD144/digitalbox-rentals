from fastapi import APIRouter, Depends, Request, HTTPException, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from database import get_db
from models import NichePage
import json
import os

router = APIRouter(tags=["seo"])

@router.get("/loesungen/{nische}", response_class=HTMLResponse)
async def get_niche_page(request: Request, nische: str, db: Session = Depends(get_db)):
    # Lazy import to avoid circular dependency
    from main import templates
    
    page = db.query(NichePage).filter(NichePage.slug == nische).first()
    if not page:
        raise HTTPException(status_code=404, detail="Niche not found")
        
    try:
        benefits = json.loads(page.solution_benefits)
    except:
        benefits = []
        
    return templates.TemplateResponse(
        request=request, 
        name="niche.html", 
        context={
            "page": page,
            "benefits": benefits
        }
    )

@router.get("/sitemap.xml")
async def sitemap(request: Request, db: Session = Depends(get_db)):
    pages = db.query(NichePage).all()
    base_url = str(request.base_url).rstrip("/")
    
    xml = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    
    # Static pages
    for path in ["", "/login"]:
        xml.append(f'  <url><loc>{base_url}{path}</loc></url>')
        
    # Dynamic niches
    for p in pages:
        xml.append(f'  <url><loc>{base_url}/loesungen/{p.slug}</loc></url>')
        
    xml.append('</urlset>')
    
    return Response(content="\n".join(xml), media_type="application/xml")

@router.get("/robots.txt", response_class=Response)
async def robots(request: Request):
    base_url = str(request.base_url).rstrip("/")
    content = f"User-agent: *\nDisallow: /dashboard\nAllow: /\n\nSitemap: {base_url}/sitemap.xml"
    return Response(content=content, media_type="text/plain")
