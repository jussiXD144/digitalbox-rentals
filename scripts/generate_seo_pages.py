import os
import sys
import json
from sqlalchemy.orm import Session

# Add parent directory to path so we can import app modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from database import engine, Base, SessionLocal
from models import NichePage

# Initialize DB (in case tables don't exist)
Base.metadata.create_all(bind=engine)

niches_data = [
    {
        "slug": "fotografen",
        "target_audience": "Freelance Photographers",
        "title": "Cloud-Speicher für Fotografen | DigitalBox",
        "meta_description": "Sicherer, unlimitierter Cloud-Speicher für Freelance Fotografen. Bezahle nur, was du nutzt. Perfekt für RAW-Dateien und große Kunden-Shootings.",
        "h1": "Der sicherste Ort für deine Meisterwerke",
        "subtitle": "Unlimitierter Cloud-Speicher, der mit jedem Foto-Shooting mitwächst.",
        "problem_statement": "Als Fotograf kennst du das Problem: Festplatten gehen kaputt, lokale Speicher laufen über und Cloud-Abos zwingen dich in teure, fixe Verträge, obwohl du den Platz im Winter gar nicht brauchst. Deine RAW-Dateien und hochauflösenden Kunden-Shootings erfordern eine Lösung, die flexibel, sicher und kosteneffizient ist.",
        "solution_benefits": [
            "Dynamischer Speicherplatz: Deine DigitalBox wächst automatisch, wenn du nach einer Hochzeit hunderte Gigabytes hochlädst.",
            "Fair Pay-As-You-Go: Du bezahlst nur für die Gigabytes, die du wirklich belegst. Keine teuren Pauschal-Abos mehr.",
            "Höchste Sicherheit: S3-kompatible Infrastruktur garantiert, dass kein einziges Kundenfoto jemals verloren geht."
        ]
    },
    {
        "slug": "3d-artists",
        "target_audience": "3D Artists & Animators",
        "title": "Cloud-Speicher für 3D Artists & Animatoren | DigitalBox",
        "meta_description": "Gigantische Projektdateien, Renderings und Texturen sicher speichern. Skalierbarer Pay-as-you-go Speicher für 3D Artists.",
        "h1": "Renderings sicher speichern, ohne Limit",
        "subtitle": "Die flexibelste Cloud für gigantische Projektdateien und Textur-Bibliotheken.",
        "problem_statement": "3D-Animationen, Blender-Projekte und 8K-Texturen fressen Speicherplatz im Terabyte-Bereich. Herkömmliche Cloud-Anbieter limitieren Upload-Größen oder verlangen horrende Summen für Speicherplatz, den du nach Abschluss eines Projekts nicht mehr benötigst.",
        "solution_benefits": [
            "Keine Dateigrößen-Limits: Lade auch größte Projekt-Ordner und Caches ohne Abbruch hoch.",
            "Skaliert mit deinen Projekten: Wenn ein großes Rendering ansteht, wächst die DigitalBox automatisch mit.",
            "Schneller Zugriff: S3-kompatible APIs ermöglichen nahtlose Integration in deine Render-Pipeline."
        ]
    },
    {
        "slug": "steuerberater",
        "target_audience": "Tax Advisors (Steuerberater)",
        "title": "Sicherer Cloud-Speicher für Steuerberater | DigitalBox",
        "meta_description": "Datenschutzkonformer, verschlüsselter Cloud-Speicher für Steuerkanzleien. Mandantendaten zu 100% sicher ablegen.",
        "h1": "100% Sicherheit für Mandanten-Daten",
        "subtitle": "Zertifizierter, S3-kompatibler Cloud-Speicher für moderne Steuerkanzleien.",
        "problem_statement": "Steuerberater tragen eine enorme Verantwortung für hochsensible Mandantendaten, Bilanzen und Belege. Gewöhnliche File-Hoster erfüllen oft nicht die strengen Anforderungen an Datenschutz, Ausfallsicherheit und revisionssichere Speicherung.",
        "solution_benefits": [
            "Maximale Datensicherheit: Enterprise-grade Infrastruktur mit redundanter Speicherung in europäischen Rechenzentren.",
            "Isolierte Speicherumgebungen: Jeder Nutzer erhält einen strikt getrennten Bucket für absolute Daten-Integrität.",
            "Revisionssicher & Kosteneffizient: Die perfekten Backups deiner Kanzlei-Software (z.B. DATEV), abgerechnet auf das Gigabyte genau."
        ]
    },
    {
        "slug": "indie-game-devs",
        "target_audience": "Indie Game Developers",
        "title": "Cloud-Speicher für Indie Game Entwickler | DigitalBox",
        "meta_description": "Versioniere deine Game-Assets und Builds in der Cloud. Günstiger, skalierbarer S3-Speicher für Game Devs.",
        "h1": "Deine Assets & Builds, jederzeit abrufbereit",
        "subtitle": "Der skalierbare Cloud-Speicher für Unreal Engine, Unity und Godot Projekte.",
        "problem_statement": "Indie-Entwickler arbeiten oft remote und tauschen täglich riesige Builds, Sound-Libraries und 3D-Modelle aus. GitHub oder GitLab stoßen bei binären Assets schnell an ihre Grenzen und LFS-Speicher wird schnell unbezahlbar.",
        "solution_benefits": [
            "Perfekt für Binary Assets: Speichere riesige Unity- oder Unreal-Projektordner ohne Versions-Limits.",
            "Günstiger als LFS: Unsere Hybrid-Tiers bieten deutlich günstigere Konditionen für gigantische Repositories.",
            "S3-API Integration: Integriere deine DigitalBox direkt in deine CI/CD-Pipelines für automatisierte Build-Uploads."
        ]
    },
    {
        "slug": "architekten",
        "target_audience": "Architecture Firms",
        "title": "Cloud-Speicher für Architekten & Planer | DigitalBox",
        "meta_description": "Sichere CAD-Pläne, BIM-Modelle und Bauzeichnungen in der Cloud. DigitalBox wächst mit jedem Architektur-Projekt.",
        "h1": "Dein digitales Planarchiv ohne Grenzen",
        "subtitle": "Sicherer Speicher für CAD-Dateien, BIM-Modelle und hochauflösende Baupläne.",
        "problem_statement": "Architekturbüros arbeiten mit massiven Dateiformaten. Wenn mehrere Planer, Bauzeichner und Ingenieure Versionen von BIM-Modellen (z.B. Revit, ArchiCAD) austauschen, stoßen lokale Server an ihre Kapazitätsgrenzen und die Cloud-Kosten explodieren.",
        "solution_benefits": [
            "Zukunftssicher wachsen: Egal wie viele Projekte gleichzeitig laufen, der Speicherplatz passt sich dynamisch an.",
            "Hybride Preismodelle: Zahle nur das, was dein Büro auch wirklich verbraucht.",
            "Unzerstörbares Archiv: Dank S3-kompatibler Technologie sind deine Pläne vor Ransomware und Hardware-Defekten geschützt."
        ]
    }
]

db: Session = SessionLocal()

for niche in niches_data:
    print(f"Generiere SEO-Seite für: {niche['slug']}...")
    try:
        page = db.query(NichePage).filter(NichePage.slug == niche["slug"]).first()
        if not page:
            page = NichePage(slug=niche["slug"])
            db.add(page)
            
        page.title = niche["title"]
        page.meta_description = niche["meta_description"]
        page.h1 = niche["h1"]
        page.subtitle = niche["subtitle"]
        page.problem_statement = niche["problem_statement"]
        page.solution_benefits = json.dumps(niche["solution_benefits"])
        page.target_audience = niche["target_audience"]
        
        db.commit()
        print(f"-> Gespeichert: {niche['slug']}")
    except Exception as e:
        print(f"-> Fehler bei {niche['slug']}: {e}")

db.close()
print("Alle SEO-Seiten wurden erfolgreich generiert!")
