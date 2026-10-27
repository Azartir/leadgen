"""
Vertical: Russian-market B2B prospecting for websites and business automation.

Designed for Russian-speaking outreach: Russian labels, Russian pitch angles,
and a score that prioritizes independent local businesses with a weak digital
presence. Collection remains based on public OSM/Overture data; this module does
not claim to query Yandex Maps, 2GIS, or company registries.
"""
from __future__ import annotations

from .. import register, Vertical
from ..audit import is_weak_url
from ._common import audit_enrich, BROAD_OSM_TAGS, is_social


def _score(rec: dict) -> tuple[int, str, str]:
    score, reasons = 0, []
    site = (rec.get("website") or "").strip()
    audit = rec.get("audit") or {}

    if not site:
        score += 55
        reasons.append("Нет собственного сайта")
    else:
        weak, weak_reason = is_weak_url(site)
        if weak or is_social(site):
            score += 42
            reasons.append("Вместо сайта соцсеть/каталог" if is_social(site)
                           else f"Слабая ссылка: {weak_reason}")
        elif not audit.get("reachable"):
            score += 38
            reasons.append("Сайт не открывается")
        else:
            if not audit.get("https"):
                score += 15
                reasons.append("Нет HTTPS")
            if not audit.get("mobile_viewport"):
                score += 12
                reasons.append("Сайт не адаптирован под мобильные")
            if (audit.get("load_ms") or 0) > 4500:
                score += 8
                reasons.append("Медленная загрузка")

    if rec.get("phone"):
        score += 10
        reasons.append("Есть телефон для первичного контакта")
    if rec.get("email"):
        score += 8
        reasons.append("Есть email")
    if not rec.get("phone") and not rec.get("email"):
        score -= 8
        reasons.append("Контакт не найден в источнике")

    tier = "A" if score >= 45 else "B" if score >= 20 else "C"
    if not reasons:
        reasons.append("Явных проблем с цифровым присутствием не найдено")
    return max(0, score), tier, "; ".join(reasons)


def _opener(rec: dict) -> str:
    name = rec.get("name") or "Здравствуйте"
    category = rec.get("category") or "вашей сферы"
    city = rec.get("city") or rec.get("state") or "вашего города"
    site = (rec.get("website") or "").strip()
    if not site:
        return (f"Добрый день! Увидел компанию «{name}» ({category}, {city}). "
                "Подскажите, привлекаете ли вы клиентов через сайт? Могу показать "
                "короткий вариант решения под вашу задачу.")
    if is_social(site):
        return (f"Добрый день! Увидел «{name}» в открытом каталоге. Есть идея, "
                "как дополнить соцсети отдельной страницей для заявок и поиска.")
    audit = rec.get("audit") or {}
    if not audit.get("reachable"):
        return (f"Добрый день! Похоже, сайт «{name}» сейчас недоступен. "
                "Кто у вас отвечает за сайт и входящие заявки?")
    if not audit.get("https") or not audit.get("mobile_viewport"):
        return (f"Добрый день! Посмотрел сайт «{name}» и заметил пару технических "
                "моментов, которые могут мешать получать заявки. Кому можно "
                "отправить краткий разбор?")
    return (f"Добрый день! Увидел «{name}». Подскажите, есть ли сейчас задачи "
            "по автоматизации обработки заявок или клиентских процессов?")


COLUMNS = [
    ("Приоритет", "tier"), ("Балл", "score"), ("Компания", "name"),
    ("Сфера", "category"), ("Город", "city"), ("Регион", "state"),
    ("Телефон", "phone"), ("Email", "email"), ("Сайт", "website"),
    ("Почему в списке", "why"), ("Первое сообщение", "opener"),
    ("Адрес", "address"), ("Яндекс Карты", "yandex_maps_url"), ("Поиск в 2ГИС", "dgis_search_url"),
    ("Источник", "source"), ("Все источники", "verified_sources"),
    ("Источников совпало", "source_match_count"), ("Расхождения", "source_conflicts"),
    ("Ссылка на источник", "source_url"),
]

register(Vertical(
    key="ru_b2b",
    label="Россия: B2B-сайты и автоматизация",
    description=("Российский рынок: независимые локальные компании с отсутствующим "
                 "или слабым сайтом, которым можно предложить сайт, заявки или автоматизацию."),
    overture_categories=[],
    osm_tags=BROAD_OSM_TAGS,
    keep_chains=False,
    score_fn=_score,
    enrich_fn=audit_enrich,
    opener_fn=_opener,
    columns=COLUMNS,
))
