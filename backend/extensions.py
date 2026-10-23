"""Optional productivity endpoints: imports, reports, profiles, receipts and backups."""
from __future__ import annotations

import csv
import io
import json
import os
import re
import shutil
import subprocess
import uuid
from datetime import date, datetime
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import BASE_DIR, get_db
from .gemini import extract_receipt_text, gemini_status

router = APIRouter(prefix="/api", tags=["productivity"])
UPLOADS = Path(os.getenv("PAYARC_UPLOAD_DIR", str(BASE_DIR / "uploads")))
BACKUPS = Path(os.getenv("PAYARC_BACKUP_DIR", str(BASE_DIR / "backups")))
MAX_UPLOAD = 10 * 1024 * 1024


def ensure_extensions(db: Session) -> None:
    db.execute(text("CREATE TABLE IF NOT EXISTS profiles (id INTEGER PRIMARY KEY, name TEXT NOT NULL, initials TEXT NOT NULL, color TEXT NOT NULL DEFAULT '#B8F46B', is_active BOOLEAN NOT NULL DEFAULT 0, created_at TEXT NOT NULL)"))
    db.execute(text("CREATE TABLE IF NOT EXISTS receipt_files (id INTEGER PRIMARY KEY, expense_id INTEGER NOT NULL, filename TEXT NOT NULL, stored_name TEXT NOT NULL, mime_type TEXT NOT NULL, ocr_text TEXT, created_at TEXT NOT NULL)"))
    columns = {row[1] for row in db.execute(text("PRAGMA table_info(expenses)"))}
    if "profile_id" not in columns:
        db.execute(text("ALTER TABLE expenses ADD COLUMN profile_id INTEGER"))
    count = db.execute(text("SELECT COUNT(*) FROM profiles")).scalar_one()
    if not count:
        db.execute(text("INSERT INTO profiles (name, initials, color, is_active, created_at) VALUES ('Personal space', 'PS', '#B8F46B', 1, :now)"), {"now": datetime.utcnow().isoformat()})
    default_id = db.execute(text("SELECT id FROM profiles WHERE is_active = 1 LIMIT 1")).scalar()
    if default_id:
        db.execute(text("UPDATE expenses SET profile_id = :id WHERE profile_id IS NULL"), {"id": default_id})
    db.commit()


def active_profile_id(db: Session) -> int:
    ensure_extensions(db)
    return int(db.execute(text("SELECT id FROM profiles WHERE is_active = 1 LIMIT 1")).scalar_one())


def parse_csv(raw: bytes) -> list[dict[str, str]]:
    text_data = raw.decode("utf-8-sig", errors="replace")
    return list(csv.DictReader(io.StringIO(text_data)))


def parse_xlsx(raw: bytes) -> list[dict[str, str]]:
    """Read basic .xlsx sheets without a server-side Excel dependency."""
    namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    with ZipFile(io.BytesIO(raw)) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(node.itertext()) for node in root.findall(namespace + "si")]
        sheet = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        rows = []
        for row in sheet.findall(".//" + namespace + "row"):
            values = []
            for cell in row.findall(namespace + "c"):
                value = cell.find(namespace + "v")
                raw_value = value.text if value is not None else ""
                values.append(shared[int(raw_value)] if cell.get("t") == "s" and raw_value else raw_value)
            rows.append(values)
    if not rows:
        return []
    headers = [str(item).strip().lower() for item in rows[0]]
    return [dict(zip(headers, [str(value) for value in row])) for row in rows[1:] if any(row)]


def first(item: dict[str, str], *names: str) -> str:
    lowered = {str(key).strip().lower(): value for key, value in item.items()}
    return str(next((lowered[name] for name in names if name in lowered and lowered[name] not in (None, "")), ""))


def parse_amount(value: str) -> float:
    clean = re.sub(r"[^0-9.\-]", "", value or "")
    return float(clean) if clean not in ("", "-", ".") else 0.0


@router.get("/profiles")
def list_profiles(db: Session = Depends(get_db)):
    ensure_extensions(db)
    rows = db.execute(text("SELECT id, name, initials, color, is_active FROM profiles ORDER BY is_active DESC, name")).mappings().all()
    return [dict(row) for row in rows]


@router.post("/profiles")
def create_profile(payload: dict, db: Session = Depends(get_db)):
    ensure_extensions(db)
    name = str(payload.get("name", "")).strip()
    if not name:
        raise HTTPException(422, "Profile name is required")
    initials = "".join(piece[0] for piece in name.split()[:2]).upper() or "PA"
    result = db.execute(text("INSERT INTO profiles (name, initials, color, is_active, created_at) VALUES (:name, :initials, :color, 0, :now)"), {"name": name[:80], "initials": initials, "color": payload.get("color", "#B8F46B"), "now": datetime.utcnow().isoformat()})
    db.commit()
    return {"id": result.lastrowid, "name": name, "initials": initials, "color": payload.get("color", "#B8F46B"), "is_active": False}


@router.post("/profiles/{profile_id}/activate")
def activate_profile(profile_id: int, db: Session = Depends(get_db)):
    ensure_extensions(db)
    if not db.execute(text("SELECT id FROM profiles WHERE id=:id"), {"id": profile_id}).scalar():
        raise HTTPException(404, "Profile was not found")
    db.execute(text("UPDATE profiles SET is_active=0"))
    db.execute(text("UPDATE profiles SET is_active=1 WHERE id=:id"), {"id": profile_id})
    db.commit()
    return {"active_profile_id": profile_id}


@router.post("/imports/transactions")
async def import_transactions(file: UploadFile = File(...), db: Session = Depends(get_db)):
    ensure_extensions(db)
    raw = await file.read()
    if len(raw) > MAX_UPLOAD:
        raise HTTPException(413, "Import files must be smaller than 10 MB")
    filename = (file.filename or "import.csv").lower()
    try:
        rows = parse_xlsx(raw) if filename.endswith(".xlsx") else parse_csv(raw)
    except Exception as exc:
        raise HTTPException(422, "Could not read this file. Use CSV or a standard .xlsx worksheet.") from exc
    profile_id = active_profile_id(db)
    imported, skipped, errors = 0, 0, []
    for index, row in enumerate(rows, start=2):
        amount = parse_amount(first(row, "amount", "value", "debit", "credit"))
        title = first(row, "merchant", "description", "title", "name") or "Imported transaction"
        if not amount:
            skipped += 1; errors.append({"row": index, "reason": "Amount missing or invalid"}); continue
        direction = first(row, "type", "direction").lower()
        if direction not in ("income", "expense", "transfer"):
            direction = "income" if amount < 0 and first(row, "credit") else "expense"
        category = first(row, "category") or "Other"
        existing_category = db.execute(text("SELECT id FROM categories WHERE lower(name)=lower(:name) LIMIT 1"), {"name": category}).scalar()
        if not existing_category:
            slug = re.sub(r"[^a-z0-9]+", "-", category.lower()).strip("-") or "imported"
            db.execute(text("INSERT OR IGNORE INTO categories (name, slug, kind, color, icon, is_system, created_at, updated_at) VALUES (:name, :slug, 'expense', '#8B5CF6', 'wallet', 0, :now, :now)"), {"name": category[:80], "slug": slug[:75] + '-' + uuid.uuid4().hex[:4], "now": datetime.utcnow().isoformat()})
            existing_category = db.execute(text("SELECT id FROM categories WHERE lower(name)=lower(:name) LIMIT 1"), {"name": category}).scalar()
        raw_date = first(row, "date", "transaction date", "transaction_date") or date.today().isoformat()
        try: parsed_date = date.fromisoformat(raw_date[:10]).isoformat()
        except ValueError: parsed_date = date.today().isoformat()
        db.execute(text("INSERT INTO expenses (title, merchant, amount, currency, date, direction, status, account, expense_scope, privacy, notes, is_recurring, category_id, profile_id, created_at, updated_at) VALUES (:title,:merchant,:amount,'INR',:date,:direction,'posted',:account,'personal','private',:notes,0,:category,:profile,:now,:now)"), {"title": title[:160], "merchant": title[:160], "amount": abs(amount), "date": parsed_date, "direction": direction, "account": first(row, "account", "payment method", "payment_method") or "Imported", "notes": first(row, "note", "notes"), "category": existing_category, "profile": profile_id, "now": datetime.utcnow().isoformat()})
        imported += 1
    db.commit()
    return {"imported": imported, "skipped": skipped, "errors": errors[:20], "profile_id": profile_id}


@router.get("/reports/transactions.pdf")
def transaction_report(db: Session = Depends(get_db)):
    ensure_extensions(db)
    profile_id = active_profile_id(db)
    rows = db.execute(text("SELECT merchant, amount, direction, date, account FROM expenses WHERE profile_id=:profile ORDER BY date DESC LIMIT 100"), {"profile": profile_id}).mappings().all()
    lines = ["PayArc Transaction Report", "Generated " + datetime.now().strftime("%d %b %Y, %H:%M"), ""]
    for row in rows:
        sign = "+" if row["direction"] == "income" else "-"
        lines.append(f"{row['date']}  {str(row['merchant'])[:28]:28}  {sign} INR {row['amount']:.2f}")
    lines = lines[:45]
    stream = "BT /F1 11 Tf 45 790 Td 15 TL " + " ".join("(" + line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") + ") Tj T*" for line in lines) + " ET"
    objects = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R] /Count 1 >>", "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>", "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>", f"<< /Length {len(stream.encode())} >>\nstream\n{stream}\nendstream"]
    body = "%PDF-1.4\n"; offsets = [0]
    for i, obj in enumerate(objects, 1): offsets.append(len(body.encode())); body += f"{i} 0 obj\n{obj}\nendobj\n"
    start = len(body.encode()); body += "xref\n0 6\n0000000000 65535 f \n" + "".join(f"{offset:010d} 00000 n \n" for offset in offsets[1:]) + f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{start}\n%%EOF"
    return Response(body.encode(), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=payarc-report.pdf"})


@router.post("/receipts")
async def upload_receipt(expense_id: int = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db)):
    ensure_extensions(db)
    if not db.execute(text("SELECT id FROM expenses WHERE id=:id"), {"id": expense_id}).scalar(): raise HTTPException(404, "Transaction was not found")
    raw = await file.read()
    if not raw or len(raw) > MAX_UPLOAD: raise HTTPException(413, "Receipt must be between 1 byte and 10 MB")
    suffix = Path(file.filename or "receipt.jpg").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".pdf"}: raise HTTPException(422, "Use JPG, PNG, WEBP, or PDF receipts")
    UPLOADS.mkdir(parents=True, exist_ok=True); stored = uuid.uuid4().hex + suffix; target = UPLOADS / stored; target.write_bytes(raw)
    ocr_text = ""
    ocr_provider = None
    if suffix != ".pdf" and shutil.which("tesseract"):
        try:
            ocr_text = subprocess.run(["tesseract", str(target), "stdout"], capture_output=True, text=True, timeout=25).stdout.strip()
            ocr_provider = "tesseract" if ocr_text else None
        except Exception: ocr_text = ""
    if not ocr_text and suffix != ".pdf":
        ocr_text = extract_receipt_text(raw, file.content_type or "image/jpeg") or ""
        ocr_provider = "gemini" if ocr_text else None
    result = db.execute(text("INSERT INTO receipt_files (expense_id, filename, stored_name, mime_type, ocr_text, created_at) VALUES (:expense,:filename,:stored,:mime,:ocr,:now)"), {"expense": expense_id, "filename": file.filename or "receipt", "stored": stored, "mime": file.content_type or "application/octet-stream", "ocr": ocr_text, "now": datetime.utcnow().isoformat()})
    db.execute(text("UPDATE expenses SET receipt_url=:url WHERE id=:id"), {"url": f"/api/receipts/{result.lastrowid}/file", "id": expense_id}); db.commit()
    return {"id": result.lastrowid, "expense_id": expense_id, "url": f"/api/receipts/{result.lastrowid}/file", "ocr_text": ocr_text, "ocr_available": bool(shutil.which('tesseract')) or bool(gemini_status()["configured"]), "ocr_provider": ocr_provider, "ocr_error": None if ocr_text else gemini_status()["last_error"]}


@router.get("/receipts/{receipt_id}/file")
def receipt_file(receipt_id: int, db: Session = Depends(get_db)):
    ensure_extensions(db); row = db.execute(text("SELECT stored_name, mime_type, filename FROM receipt_files WHERE id=:id"), {"id": receipt_id}).mappings().first()
    if not row or not (UPLOADS / row["stored_name"]).is_file(): raise HTTPException(404, "Receipt was not found")
    return FileResponse(UPLOADS / row["stored_name"], media_type=row["mime_type"], filename=row["filename"])


@router.post("/backups/create")
def create_backup(db: Session = Depends(get_db)):
    ensure_extensions(db); BACKUPS.mkdir(parents=True, exist_ok=True)
    db.commit(); db_path = BASE_DIR / "payarc.db"; name = "payarc-backup-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".db"; target = BACKUPS / name; shutil.copy2(db_path, target)
    return {"backup": name, "location": str(target), "created_at": datetime.now().isoformat(), "mode": "local secure backup"}


@router.get("/backups")
def list_backups(db: Session = Depends(get_db)):
    ensure_extensions(db); BACKUPS.mkdir(parents=True, exist_ok=True)
    return [{"name": item.name, "size": item.stat().st_size, "created_at": datetime.fromtimestamp(item.stat().st_mtime).isoformat()} for item in sorted(BACKUPS.glob("payarc-backup-*.db"), reverse=True)]

@router.get("/exports/transactions.csv")
def export_transactions_csv(db: Session = Depends(get_db)):
    """Portable spreadsheet export for the active profile."""
    ensure_extensions(db)
    rows = db.execute(text("SELECT date, merchant, amount, direction, account, notes FROM expenses WHERE profile_id=:profile ORDER BY date DESC"), {"profile": active_profile_id(db)}).mappings().all()
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["date", "merchant", "amount", "direction", "account", "notes"])
    writer.writeheader(); writer.writerows(rows)
    return Response(output.getvalue().encode("utf-8-sig"), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=payarc-transactions.csv"})


@router.get("/insights/anomalies")
def anomaly_insights(db: Session = Depends(get_db)):
    """Transparent unusual-spend detection: flags expenses over 2.5x category average."""
    ensure_extensions(db); profile = active_profile_id(db)
    rows = db.execute(text("SELECT e.id,e.merchant,e.amount,e.date,c.name AS category FROM expenses e LEFT JOIN categories c ON c.id=e.category_id WHERE e.profile_id=:profile AND e.direction='expense' ORDER BY e.date DESC"), {"profile": profile}).mappings().all()
    groups: dict[str, list[float]] = {}
    for row in rows: groups.setdefault(row["category"] or "Other", []).append(float(row["amount"]))
    alerts = []
    for row in rows:
        values = groups[row["category"] or "Other"]
        average = sum(values) / len(values)
        if len(values) >= 3 and float(row["amount"]) > average * 2.5:
            alerts.append({"transaction_id": row["id"], "merchant": row["merchant"], "category": row["category"], "amount": row["amount"], "average": round(average, 2), "message": "This is substantially above your usual spending in this category."})
    return {"alerts": alerts[:10], "method": "Flags spending above 2.5x the category average; review before acting."}
@router.post("/budgets/quick")
def create_quick_monthly_budget(payload: dict, db: Session = Depends(get_db)):
    """Create a monthly category budget from the dashboard without requiring internal IDs."""
    ensure_extensions(db)
    category_name = str(payload.get("category", "")).strip()
    limit = float(payload.get("limit", 0) or 0)
    alert = int(payload.get("alert_percentage", 80) or 80)
    if not category_name or limit <= 0:
        raise HTTPException(422, "Choose a category and a monthly amount greater than zero")
    category = db.execute(text("SELECT id FROM categories WHERE lower(name)=lower(:name) LIMIT 1"), {"name": category_name}).scalar()
    if not category:
        raise HTTPException(422, "Choose an existing expense category")
    db.execute(text("INSERT INTO budgets (name, limit_amount, currency, period, start_date, alert_percentage, color, category_id, created_at, updated_at) VALUES (:name,:limit,'INR','monthly',:start,:alert,:color,:category,:now,:now)"), {"name": payload.get("name") or f"{category_name} monthly", "limit": limit, "start": date.today().replace(day=1).isoformat(), "alert": max(1, min(alert, 100)), "color": payload.get("color", "#8B5CF6"), "category": category, "now": datetime.utcnow().isoformat()})
    db.commit()
    return {"created": True, "category": category_name, "limit": limit, "alert_percentage": alert}
