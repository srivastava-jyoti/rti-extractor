import hashlib
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..config import get_settings
from ..extract.client import extract_from_images, extract_from_text
from ..extract.schema import DataStatus
from ..logging import log, setup_logging
from ..pdf.reader import TextLayer, inspect, render_pages
from ..strapi.client import build_component, create_budget_rti_draft

BASE_DIR = Path(__file__).parent
WORK_DIR = Path("data/work")
UPLOAD_DIR = WORK_DIR / "uploads"

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

QUESTIONS: dict[str, str] = {
    "annual_budget_for_prisons": "1. Total annual budget for prisons",
    "break_up_for_budget": "2. Major heads / break-up of that total",
    "sanctioned_individual_cost": "3. Sanctioned cost per prisoner, per month",
    "annual_individual_cost_sanctioned": "4. Sanctioned cost per prisoner, per year",
    "incurred_individual_cost": "5. Incurred cost per prisoner, per month",
    "annual_individual_cost_incurred": "6. Incurred cost per prisoner, per year",
}

setup_logging()
app = FastAPI(title="RTI Extractor")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "upload.html", {})


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

    if info.text_layer is TextLayer.NATIVE:
        answers = extract_from_text("\n\n".join(info.text_by_page))
    else:
        pages = render_pages(stored, WORK_DIR / digest[:16])
        answers = extract_from_images(pages)

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
    entry_id = create_budget_rti_draft(fields)
    log.info("submitted", sha256=sha[:16], entry_id=entry_id)

    return templates.TemplateResponse(
        request,
        "done.html",
        {"rows": rows, "sha": sha, "entry_id": entry_id, "dry_run": get_settings().dry_run},
    )
