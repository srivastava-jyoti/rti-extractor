import hashlib
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from ..config import get_settings
from ..extract.client import extract_from_images, extract_from_text
from ..extract.schema import DataStatus
from ..logging import log, setup_logging
from ..pdf.reader import TextLayer, inspect, render_pages
from ..rti_type import get_rti_type
from ..strapi.client import (
    build_component,
    create_draft,
    find_rti_form,
    strapi_entry_url,
)

BASE_DIR = Path(__file__).parent
WORK_DIR = Path("data/work")
UPLOAD_DIR = WORK_DIR / "uploads"

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Only one RTI type is implemented. Type detection is not in scope yet.
RTI_TYPE = get_rti_type("budget-rti")
QUESTIONS: dict[str, str] = RTI_TYPE.labels

setup_logging()
app = FastAPI(title="RTI Extractor")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "upload.html", {})


@app.get("/pdf/{sha}")
async def serve_pdf(sha: str) -> FileResponse:
    """Serve back the scan that was uploaded, so it can be checked without hunting for it."""
    if not re.fullmatch(r"[0-9a-f]{64}", sha):
        raise HTTPException(status_code=404, detail="Not found")
    path = UPLOAD_DIR / f"{sha}.pdf"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(path, media_type="application/pdf", content_disposition_type="inline")


@app.post("/extract", response_class=HTMLResponse)
async def do_extract(request: Request, pdf: UploadFile) -> HTMLResponse:
    """Take an uploaded PDF, extract the six answers, and show them for checking."""
    data = await pdf.read()
    digest = hashlib.sha256(data).hexdigest()

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored = UPLOAD_DIR / f"{digest}.pdf"
    stored.write_bytes(data)

    info = inspect(stored)
    log.info("upload", filename=pdf.filename, sha256=digest[:16], layer=info.text_layer.value)

    form_match = find_rti_form(RTI_TYPE, pdf.filename) if pdf.filename else None

    if info.text_layer is TextLayer.NATIVE:
        answers = extract_from_text(RTI_TYPE, "\n\n".join(info.text_by_page))
    else:
        pages = render_pages(stored, WORK_DIR / digest[:16])
        answers = extract_from_images(RTI_TYPE, pages)

    context: dict[str, Any] = {
        "filename": pdf.filename,
        "sha": digest,
        "page_count": info.page_count,
        "text_layer": info.text_layer.value,
        "rows": [
            {"key": key, "label": label, "answer": getattr(answers, key)}
            for key, label in QUESTIONS.items()
        ],
        "statuses": [status.value for status in DataStatus],
        "form": form_match,
    }
    return templates.TemplateResponse(request, "review.html", context)


@app.post("/submit", response_class=HTMLResponse)
async def submit(request: Request) -> HTMLResponse:
    """Take the reviewer's corrected values and create a Budget-RTI draft."""
    form = await request.form()

    rows: list[dict[str, str]] = []
    fields: dict[str, dict[str, Any]] = {}

    for key, label in QUESTIONS.items():
        number = str(form.get(f"{key}__number", ""))
        status = str(form.get(f"{key}__status", ""))
        other = str(form.get(f"{key}__other_specify", ""))
        rows.append({"label": label, "number": number, "status": status, "other_specify": other})
        fields[key] = build_component(number, status, other)

    sha = str(form.get("sha", ""))
    raw_form_id = str(form.get("rti_form_id", "")).strip()
    rti_form_id = int(raw_form_id) if raw_form_id.isdigit() else None

    entry_id = create_draft(RTI_TYPE, fields, rti_form_id=rti_form_id)
    log.info("submitted", sha256=sha[:16], entry_id=entry_id, rti_form_id=rti_form_id)

    settings = get_settings()
    return templates.TemplateResponse(
        request,
        "done.html",
        {
            "rows": rows,
            "sha": sha,
            "entry_id": entry_id,
            "dry_run": settings.dry_run,
            "entry_url": strapi_entry_url(RTI_TYPE, entry_id) if entry_id else None,
        },
    )
