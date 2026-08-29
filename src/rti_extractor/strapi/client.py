from typing import Any

import httpx

from ..config import get_settings
from ..extract.schema import DataStatus
from ..logging import log

STATUS_TO_STRAPI: dict[DataStatus, str] = {
    DataStatus.AVAILABLE: "Data Available ",
    DataStatus.NOT_AVAILABLE: "Data Not Available",
    DataStatus.NOT_PROVIDED: "Data Not Provided",
    DataStatus.OTHER: "Other",
}


def build_component(number: str, status: str, other_specify: str) -> dict[str, Any]:
    """Turn one reviewed answer into the shape Strapi expects."""
    cleaned = number.replace(",", "").replace("Rs.", "").strip()
    value: float | None = None
    if cleaned:
        try:
            value = float(cleaned)
        except ValueError:
            log.warning("unparsable_number", raw=number)

    try:
        dropdown = STATUS_TO_STRAPI[DataStatus(status)]
    except ValueError:
        log.warning("unknown_status", raw=status)
        dropdown = STATUS_TO_STRAPI[DataStatus.OTHER]

    return {
        "number": value,
        "number_dropdown": dropdown,
        "other_specify": other_specify.strip() or None,
    }


def create_budget_rti_draft(fields: dict[str, dict[str, Any]]) -> int | None:
    """Create an unpublished Budget-RTI entry. Returns its id, or None in dry-run."""
    settings = get_settings()
    payload = {"data": {**fields, "publishedAt": None}}

    if settings.dry_run:
        log.info("strapi_dry_run", payload=payload)
        return None

    url = f"{settings.strapi_base_url.rstrip('/')}/budget-rtis"
    headers = {"Authorization": f"Bearer {settings.strapi_api_token}"}

    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, json=payload, headers=headers)

    if response.status_code >= 400:
        log.error("strapi_error", status=response.status_code, body=response.text[:400])
        response.raise_for_status()

    entry_id = int(response.json()["data"]["id"])
    log.info("strapi_created", entry_id=entry_id)
    return entry_id


def strapi_entry_url(entry_id: int) -> str:
    """Link straight to one Budget-RTI entry in the Strapi admin."""
    base = get_settings().strapi_base_url.rstrip("/").removesuffix("/api")
    collection = "api::budget-rti.budget-rti"
    return f"{base}/admin/content-manager/collection-types/{collection}/{entry_id}"
