"""Russian-market map lookup.

2GIS Places API can be used with a demo key or subscription. Yandex organization
search is intentionally not used as a bulk source because its standard license
prohibits saving/modifying response data; instead, exports contain direct links
for manual verification in Yandex Maps and 2GIS.
"""
from __future__ import annotations

import os
import re
import time
from urllib.parse import quote

import requests

from .audit import UA

DGIS_ENDPOINT = "https://catalog.api.2gis.com/3.0/items"


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bbox_center(bbox):
    south, west, north, east = bbox
    return (south + north) / 2, (west + east) / 2


def _in_bbox(lat, lon, bbox):
    if lat is None or lon is None:
        return True
    south, west, north, east = bbox
    return south <= lat <= north and west <= lon <= east


def _extract_contact_groups(groups):
    phone = email = website = ""
    for group in groups or []:
        for item in group.get("contacts", []) if isinstance(group, dict) else []:
            kind = (item.get("type") or item.get("value_type") or "").lower()
            value = item.get("value") or item.get("text") or ""
            if not value:
                continue
            if "phone" in kind and not phone:
                phone = str(value)
            elif "email" in kind and not email:
                email = str(value)
            elif ("website" in kind or "url" in kind) and not website:
                website = str(value)
    return phone, email, website


def dgis_collect(bbox, *, limit=None, log=print, queries=None, api_key=None):
    """Collect businesses from the official 2GIS Places API (demo key supported).

    Search uses the bbox's center plus its corners as a viewport; each query is
    bounded, rate-limited and normalized to the shared lead schema.
    """
    key = api_key or os.getenv("DGIS_API_KEY") or os.getenv("TWO_GIS_API_KEY")
    if not key:
        log("  2ГИС: нет ключа. Получите демо-ключ в кабинете платформы; пропускаю источник.")
        return []
    south, west, north, east = bbox
    center_lat, center_lon = _bbox_center(bbox)
    queries = queries or [
        "магазин", "автосервис", "стоматология", "салон красоты", "кафе",
        "строительная компания", "юридические услуги", "бухгалтерские услуги",
        "производство", "ремонт техники", "ветеринарная клиника", "гостиница",
    ]
    out, seen = [], set()
    per_query = max(1, min(10, limit or 10))  # demo key page-size ceiling is 10
    for query in queries:
        if limit and len(out) >= limit:
            break
        try:
            response = requests.get(
                DGIS_ENDPOINT,
                params={
                    "key": key, "q": query, "type": "branch", "locale": "ru_RU",
                    "location": f"{center_lon},{center_lat}",
                    "viewpoint1": f"{west},{north}",
                    "viewpoint2": f"{east},{south}",
                    "page_size": per_query, "page": 1,
                    "fields": "items.point,items.address,items.full_address_name,"
                              "items.rubrics,items.contact_groups,items.name_ex,"
                              "items.org,items.brand",
                },
                headers={"User-Agent": UA}, timeout=25,
            )
            if response.status_code != 200:
                log(f"  2ГИС: запрос «{query}» — HTTP {response.status_code}")
                continue
            payload = response.json()
            if payload.get("meta", {}).get("code", 200) >= 400:
                log(f"  2ГИС: API вернул ошибку для запроса «{query}».")
                continue
            items = payload.get("result", {}).get("items", []) or []
        except (requests.RequestException, ValueError) as exc:
            log(f"  2ГИС: ошибка запроса «{query}»: {type(exc).__name__}")
            continue

        for item in items:
            name = (item.get("name") or (item.get("name_ex") or {}).get("primary") or "").strip()
            if not name:
                continue
            point = item.get("point") or {}
            lon, lat = _float(point.get("lon")), _float(point.get("lat"))
            if not _in_bbox(lat, lon, bbox):
                continue
            address = item.get("full_address_name") or item.get("address_name") or item.get("address") or ""
            if isinstance(address, dict):
                address = address.get("name") or address.get("formatted") or ""
            phone, email, website = _extract_contact_groups(item.get("contact_groups"))
            rubrics = item.get("rubrics") or []
            if rubrics and isinstance(rubrics[0], dict):
                category = rubrics[0].get("name") or rubrics[0].get("short_name") or query
            else:
                category = query
            identity = (re.sub(r"\W+", "", name.casefold()), re.sub(r"\W+", "", str(address).casefold()))
            if identity in seen:
                continue
            seen.add(identity)
            out.append({
                "name": name, "category": category, "website": website or None,
                "phone": phone or None, "email": email or None,
                "address": str(address), "city": "", "state": "", "zip": "",
                "brand": ((item.get("brand") or {}).get("name") if isinstance(item.get("brand"), dict) else "") or "",
                "lat": lat, "lon": lon, "source": "2gis",
                "source_url": f"https://2gis.ru/firm/{quote(str(item.get('id') or ''))}" if item.get("id") else "",
                "source_record_id": str(item.get("id") or ""),
            })
            if limit and len(out) >= limit:
                break
        log(f"  2ГИС («{query}»): найдено {len(items)}; добавлено {len(out)} всего")
        time.sleep(0.15)
    log(f"  2ГИС: {len(out)} организаций в пределах выбранной области")
    return out[:limit] if limit else out


def add_map_lookup_links(leads):
    """Add direct search links so a person can verify a company in map services.

    Yandex Organization Search API terms prohibit storing/modifying returned
    data under the standard license, so the lead export uses a search URL instead
    of scraping and persisting Yandex results.
    """
    for rec in leads or []:
        query = " ".join(str(rec.get(k) or "").strip() for k in ("name", "address", "city") if rec.get(k))
        if not query:
            continue
        encoded = quote(query)
        rec["yandex_maps_url"] = f"https://yandex.ru/maps/?text={encoded}"
        rec["dgis_search_url"] = f"https://2gis.ru/search/{encoded}"
    return leads


def verify_records(leads, *, log=print):
    """Add source-provenance and conflict markers for cross-source verification."""
    by_name = {}
    for rec in leads:
        name = re.sub(r"\W+", "", str(rec.get("name") or "").casefold())
        if name:
            by_name.setdefault(name, []).append(rec)
    for group in by_name.values():
        sources = sorted({str(r.get("source") or "") for r in group if r.get("source")})
        if len(sources) < 2:
            continue
        for rec in group:
            rec["verified_sources"] = ", ".join(sources)
            conflicts = []
            for field, label in (("phone", "телефон"), ("website", "сайт"), ("address", "адрес")):
                values = {str(r.get(field) or "").strip().casefold() for r in group if r.get(field)}
                if len(values) > 1:
                    conflicts.append(label)
            rec["source_conflicts"] = ", ".join(conflicts)
            rec["source_match_count"] = len(sources)
    return leads
