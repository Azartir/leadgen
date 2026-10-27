"""Offline tests for the Russian-market B2B vertical."""
from leadgen.verticals.ru_b2b import _opener, _score


def test_missing_site_with_phone_is_high_priority():
    score, tier, why = _score({"name": "Тест", "phone": "+7 900 000-00-00"})
    assert score >= 45
    assert tier == "A"
    assert "Нет собственного сайта" in why


def test_social_profile_is_not_treated_as_owned_website():
    score, tier, why = _score({"website": "https://vk.com/example", "phone": "+7 900 000-00-00"})
    assert score >= 45
    assert tier == "A"
    assert "соцсеть/каталог" in why


def test_pitch_is_in_russian_and_uses_business_name():
    pitch = _opener({"name": "Мастерская", "category": "craft", "city": "Ставрополь"})
    assert "Мастерская" in pitch
    assert "Добрый день" in pitch


def test_good_site_does_not_get_missing_site_reason():
    score, tier, why = _score({
        "website": "https://example.ru",
        "phone": "+7 900 000-00-00",
        "audit": {"reachable": True, "https": True, "mobile_viewport": True, "load_ms": 1000},
    })
    assert score < 45
    assert tier in {"B", "C"}
    assert "Нет собственного сайта" not in why
