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


def test_map_lookup_links_are_generated_without_api_calls():
    leads = [{"name": "Тестовая компания", "address": "Ставрополь, улица Ленина, 1"}]
    result = ru_sources.add_map_lookup_links(leads)
    assert result[0]["yandex_maps_url"].startswith("https://yandex.ru/maps/?text=")
    assert result[0]["dgis_search_url"].startswith("https://2gis.ru/search/")
    assert "%D0%A2%D0%B5%D1%81%D1%82%D0%BE%D0%B2%D0%B0%D1%8F" in result[0]["yandex_maps_url"]


def test_cross_source_merge_preserves_conflicts():
    from leadgen.quality import merge_records

    primary = {"name": "Компания", "phone": "+7 900 111-11-11", "source": "osm"}
    other = {"name": "Компания", "phone": "+7 900 222-22-22", "source": "2gis"}
    merged = merge_records(primary, other)
    assert merged["phone"] == "+7 900 111-11-11"
    assert merged["sources"] == ["osm", "2gis"]
    assert any("телефон" in item for item in merged["source_conflicts"])
