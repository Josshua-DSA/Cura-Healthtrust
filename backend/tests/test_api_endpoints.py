import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from backend.app.main import app


@pytest.mark.asyncio
async def test_health_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"

        res_api = await ac.get("/api/v1/health")
        assert res_api.status_code == 200
        assert res_api.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_wilayah_and_choropleth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. List Wilayah
        res = await ac.get("/api/v1/wilayah")
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert len(body["data"]) == 38

        # 2. Detail Wilayah Surabaya (3578)
        res_det = await ac.get("/api/v1/wilayah/3578")
        assert res_det.status_code == 200
        det_body = res_det.json()
        assert det_body["data"]["nama_wilayah"] == "Kota Surabaya"
        assert det_body["data"]["agregat"]["total_rs"] > 0

        # 3. Choropleth GeoJSON (Leaflet integration)
        res_geo = await ac.get("/api/v1/wilayah/choropleth/geojson")
        assert res_geo.status_code == 200
        geo_body = res_geo.json()
        assert geo_body["type"] == "FeatureCollection"
        assert len(geo_body["features"]) == 38


@pytest.mark.asyncio
async def test_faskes_and_spatial_radius():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. List Faskes (Pagination)
        res = await ac.get("/api/v1/faskes?page=1&page_size=10")
        assert res.status_code == 200
        body = res.json()
        assert body["pagination"]["total_records"] >= 1400
        assert len(body["data"]) == 10

        # 2. Map GeoJSON Points
        res_map = await ac.get("/api/v1/faskes/map/geojson")
        assert res_map.status_code == 200
        map_body = res_map.json()
        assert len(map_body["features"]) >= 1300

        # 3. PostGIS Radius Query (Surabaya: -7.2575, 112.7521)
        res_near = await ac.get("/api/v1/faskes/nearby?lat=-7.2575&lng=112.7521&radius_km=5.0&limit=5")
        assert res_near.status_code == 200
        near_body = res_near.json()
        assert near_body["success"] is True
        assert len(near_body["data"]) > 0
        assert "distance_km" in near_body["data"][0]


@pytest.mark.asyncio
async def test_katalog_and_download():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/katalog")
        assert res.status_code == 200
        body = res.json()
        assert len(body["data"]) == 4

        # Test download parquet
        res_dl = await ac.get("/api/v1/katalog/bed_ratio_38_kab/download?format=parquet")
        assert res_dl.status_code == 200
        assert len(res_dl.content) > 0


@pytest.mark.asyncio
async def test_statistik_and_ask_data():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Executive Summary
        res_stat = await ac.get("/api/v1/statistik/executive-summary")
        assert res_stat.status_code == 200
        stat_body = res_stat.json()
        assert stat_body["data"]["total_rs"] == 447
        assert stat_body["data"]["total_puskesmas"] == 977

        # 2. Ask Data AI Endpoint
        res_ask = await ac.post("/api/v1/ask", json={"query": "Bagaimana rasio ketersediaan dokter di Surabaya?", "target_wilayah": "3578"})
        assert res_ask.status_code == 200
        ask_body = res_ask.json()
        assert ask_body["success"] is True
        assert "Surabaya" in ask_body["data"]["answer"]
        assert len(ask_body["data"]["citations"]) > 0
