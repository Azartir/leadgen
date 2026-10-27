"""Offline tests for Russian map-source adapters."""
from leadgen import ru_sources


class FakeResponse:
    status_code = 200

    def json(self):
        return {
            "meta": {"code": 200},
            "result": {
                "items": [{
                    "id": "test-id",
                    "name": "Тестовая компания",
                    "type": "branch",
                    "point": {"lat": 45.0, "lon": 42.0},
                    "full_address_name": "Ставрополь, тестовая улица, 1",
                    "rubrics": [{"name": "Услуги"}],
                    "contact_groups": [{
                        "contacts": [
                            {"type": "phone", "value": "+7 900 000-00-00"},
                            {"type": "email", "value": "info@example.ru"},
                            {"type": "website", "value": "https://example.ru"},
                        ]
                    }],
                }]
            },
        }


def test_dgis_without_key_skips_source(monkeypatch):
    monkeypatch.delenv("DGIS_API_KEY", raising=False)
    monkeypatch.delenv("TWO_GIS_API_KEY", raising=False)
    records = ru_sources.dgis_collect((44.9, 41.8, 45.1, 42.2), log=lambda _: None)
    assert records == []


def test_dgis_normalizes_business_record(monkeypatch):
    monkeypatch.setattr(ru_sources.requests, "get", lambda *a, **k: FakeResponse())
    records = ru_sources.dgis_collect(
        (44.9, 41.8, 45.1, 42.2),
        api_key="test-key",
        queries=["услуги"],
        limit=5,
        log=lambda _: None,
    )
    assert len(records) == 1
    assert records[0]["name"] == "Тестовая компания"
    assert records[0]["source"] == "2gis"
    assert records[0]["phone"] == "+7 900 000-00-00"
    assert records[0]["website"] == "https://example.ru"


def test_yandex_requires_explicit_processing_permission(monkeypatch):
    monkeypatch.setenv("YANDEX_MAPS_API_KEY", "test-key")
    monkeypatch.delenv("YANDEX_MAPS_ALLOW_PROCESSING", raising=False)
    calls = []
    monkeypatch.setattr(ru_sources.requests, "get", lambda *a, **k: calls.append(1))
    records = ru_sources.yandex_collect(
        (44.9, 41.8, 45.1, 42.2), log=lambda _: None
    )
    assert records == []
    assert calls == []
