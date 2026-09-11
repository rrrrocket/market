import time


def complete_analysis(client):
    response = client.post("/api/v1/analyses", json={"hs_code":"902620","origin_iso3":"CHN"})
    assert response.status_code == 202
    run_id=response.json()["id"]
    for _ in range(30):
        state=client.get(f"/api/v1/analyses/{run_id}").json()
        if state["status"] in ("COMPLETED","FAILED"):
            break
        time.sleep(.05)
    assert state["status"] == "COMPLETED", state
    return run_id


def test_search_and_analysis_flow(client):
    products=client.get("/api/v1/products/search?q=pressure")
    assert products.status_code == 200
    assert products.json()
    exact=client.get("/api/v1/products/search?q=902620").json()[0]
    assert exact["hs_code"] == "902620"
    assert "measuring or checking pressure" in exact["name_en"]
    alias=client.get("/api/v1/products/search?q=pressure%20sensor").json()[0]
    assert alias["hs_code"] == "902620"
    run_id=complete_analysis(client)
    assert client.get(f"/api/v1/analyses/{run_id}").json()["countries_succeeded"] >= 10
    ranking=client.get("/api/v1/opportunities?hs_code=902620")
    assert ranking.status_code == 200
    rows=ranking.json()
    assert len(rows) >= 10
    assert rows[0]["score"] >= rows[-1]["score"]
    detail=client.get(f"/api/v1/opportunities/{rows[0]['id']}")
    assert len(detail.json()["history"]) == 5
    assert len(detail.json()["evidence"]) == 4
    assert detail.json()["scores"]["structural_demand"] is not None
    assert detail.json()["scores"]["distribution_opportunity"] is None
    assert detail.json()["supply"]["status"] == "NOT_CONNECTED"
    assert detail.json()["economics"]["status"] == "NOT_ENOUGH_DATA"
    assert detail.json()["signals"]["DIGITAL"] == []
    history=client.get(f"/api/v1/trade/history?hs_code=902620&country_iso3={rows[0]['destination_iso3']}")
    assert len(history.json()) == 5
    suppliers=client.get(f"/api/v1/trade/suppliers?hs_code=902620&country_iso3={rows[0]['destination_iso3']}&year=2025")
    assert suppliers.status_code == 200


def test_analysis_rerun_does_not_duplicate_opportunities(client):
    complete_analysis(client)
    count1=len(client.get("/api/v1/opportunities?hs_code=902620").json())
    complete_analysis(client)
    count2=len(client.get("/api/v1/opportunities?hs_code=902620").json())
    assert count1 == count2


def test_data_quality_watchlist_and_provider_surfaces(client):
    providers = client.get("/api/v1/integrations/providers")
    assert providers.status_code == 200
    assert any(row["code"] == "WORLD_BANK" for row in providers.json())

    created = client.post(
        "/api/v1/watchlists",
        json={"name": "Pressure sensors in Türkiye", "hs_code": "902620", "country_iso3": "TUR"},
    )
    assert created.status_code == 201
    assert client.get("/api/v1/watchlists").json()
    assert client.delete(f"/api/v1/watchlists/{created.json()['id']}").status_code == 204

    quality = client.get("/api/v1/admin/data-quality")
    assert quality.status_code == 200
    assert "provider_health" in quality.json()
    assert "source_reliability" in quality.json()


def test_idempotent_manual_macro_import(client):
    payload = {
        "dataset_type": "MACRO",
        "provider_code": "WORLD_BANK",
        "format": "JSON",
        "records": [{
            "country_iso3": "TUR",
            "metric_key": "gdp_usd",
            "value_numeric": 100,
            "unit": "USD",
            "period_year": 2025,
        }],
    }
    first = client.post("/api/v1/admin/datasets/import", json=payload)
    second = client.post("/api/v1/admin/datasets/import", json=payload)
    assert first.status_code == second.status_code == 202
    rows = client.get("/api/v1/macro?country_iso3=TUR").json()
    assert len([row for row in rows if row["metric_key"] == "gdp_usd" and row["period_year"] == 2025]) == 1
