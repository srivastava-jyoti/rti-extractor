from dataclasses import dataclass
from typing import Any

import httpx

from ..config import get_settings
from ..extract.schema import DataStatus
from ..logging import log
from ..rti_type import RtiTypeDef

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


def create_draft(
    rti_type: RtiTypeDef, fields: dict[str, dict[str, Any]], rti_form_id: int | None = None
) -> int | None:
    """Create an unpublished entry, linked to its RTI Form when we know it."""
    settings = get_settings()
    data: dict[str, Any] = {**fields, "publishedAt": None}
    if rti_form_id is not None:
        data["rti_form"] = rti_form_id
    payload = {"data": data}

    if settings.dry_run:
        log.info("strapi_dry_run", rti_type=rti_type.slug, payload=payload)
        return None

    url = f"{settings.strapi_base_url.rstrip('/')}/{rti_type.collection}"
    headers = {"Authorization": f"Bearer {settings.strapi_api_token}"}

    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, json=payload, headers=headers)

    if response.status_code >= 400:
        log.error("strapi_error", status=response.status_code, body=response.text[:400])
        response.raise_for_status()

    entry_id = int(response.json()["data"]["id"])
    log.info("strapi_created", entry_id=entry_id)
    return entry_id


@dataclass(frozen=True)
class RtiFormMatch:
    """The RTI Form a scan is already attached to in Strapi."""

    id: int
    rti_name: str
    memo_number: str | None
    response_date: str | None
    existing_entry_id: int | None
    """An entry of this RTI type already attached to the form, if there is one."""

    @property
    def is_free(self) -> bool:
        return self.existing_entry_id is None


def _get(path: str, params: dict[str, str]) -> dict[str, Any]:
    settings = get_settings()
    url = f"{settings.strapi_base_url.rstrip('/')}{path}"
    headers = {"Authorization": f"Bearer {settings.strapi_api_token}"}
    with httpx.Client(timeout=20.0) as client:
        response = client.get(url, params=params, headers=headers)
    response.raise_for_status()
    payload: dict[str, Any] = response.json()
    return payload


def find_rti_form(rti_type: RtiTypeDef, filename: str) -> RtiFormMatch | None:
    """Find the RTI Form this scan is already attached to. None if there is no match."""
    stem = filename.rsplit(".", 1)[0]
    relation = rti_type.relation_field
    for field, value in (("hash", stem), ("name", filename)):
        try:
            payload = _get(
                "/rti-forms",
                {f"filters[Scanned_files][{field}][$eq]": value, "populate": relation},
            )
        except httpx.HTTPError as exc:
            log.warning("rti_form_lookup_failed", field=field, error=str(exc)[:120])
            return None

        items = payload.get("data") or []
        if not items:
            continue

        item = items[0]
        attrs: dict[str, Any] = item.get("attributes") or {}
        existing = (attrs.get(relation) or {}).get("data")
        match = RtiFormMatch(
            id=int(item["id"]),
            rti_name=str(attrs.get("RTI_Name") or "(unnamed form)"),
            memo_number=attrs.get("RTI_memo_number"),
            response_date=attrs.get("Date_of_RTI_Response"),
            existing_entry_id=int(existing["id"]) if existing else None,
        )
        log.info("rti_form_matched", form_id=match.id, on=field, free=match.is_free)
        return match

    log.info("rti_form_not_matched", filename=filename[:80])
    return None


def strapi_entry_url(rti_type: RtiTypeDef, entry_id: int) -> str:
    """Link straight to one entry in the Strapi admin."""
    base = get_settings().strapi_base_url.rstrip("/").removesuffix("/api")
    return f"{base}/admin/content-manager/collection-types/{rti_type.api_uid}/{entry_id}"
