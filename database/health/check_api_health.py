import time
import requests
import yaml
import os
import sys

from typing import Optional, List, Dict, Any

def check_endpoint(name: str, url: str, method: str = "GET", expected_codes: Optional[List[int]] = None, headers: Optional[Dict[str, str]] = None, timeout: int = 10) -> Dict[str, Any]:
    if expected_codes is None:
        expected_codes = [200]
    start_time = time.time()
    result = {
        "name": name,
        "url": url,
        "status": "DOWN",
        "status_code": None,
        "response_time_ms": None,
        "error": None
    }
    try:
        resp = requests.request(method, url, headers=headers, timeout=timeout)
        elapsed_ms = int((time.time() - start_time) * 1000)
        result["status_code"] = resp.status_code
        result["response_time_ms"] = elapsed_ms
        if resp.status_code in expected_codes:
            result["status"] = "HEALTHY"
        else:
            result["status"] = "DEGRADED"
            result["error"] = f"Unexpected status code: {resp.status_code}"
    except requests.exceptions.Timeout:
        result["error"] = f"Timeout after {timeout}s"
    except requests.exceptions.RequestException as e:
        result["error"] = str(e)
    return result

def run_health_checks():
    print("=" * 60)
    print(" [HealthTrust] Checking External Data Sources & APIs Health")
    print("=" * 60)

    # List of targets
    targets = [
        {
            "name": "SIRS Kemenkes (Data RS Jatim)",
            "url": "https://sirs.kemkes.go.id/fo/home/list_prop_noncovid?id=35",
            "method": "GET",
            "expected": [200],
            "headers": {"User-Agent": "Mozilla/5.0 (HealthTrust HealthCheck)"}
        },
        {
            "name": "SIRS Kemenkes (Rekap RS Jatim)",
            "url": "https://sirs.kemkes.go.id/fo/home/rekap_rs_all?id=35",
            "method": "GET",
            "expected": [200],
            "headers": {"User-Agent": "Mozilla/5.0 (HealthTrust HealthCheck)"}
        },
        {
            "name": "SIRS Kemenkes (GeoJSON Jatim)",
            "url": "https://sirs.kemkes.go.id/fo/mapgeo/koordinat?id=35&mapfile=json%2Fprovinsi.json",
            "method": "GET",
            "expected": [200],
            "headers": {"User-Agent": "Mozilla/5.0 (HealthTrust HealthCheck)"}
        },
        {
            "name": "Open Data Jatim Portal",
            "url": "https://opendata.jatimprov.go.id/api/datasets",
            "method": "GET",
            "expected": [200, 301, 302],
            "headers": {"User-Agent": "Mozilla/5.0 (HealthTrust HealthCheck)"}
        },
        {
            "name": "BPS Jawa Timur Portal",
            "url": "https://jatim.bps.go.id",
            "method": "GET",
            "expected": [200, 301, 302],
            "headers": {"User-Agent": "Mozilla/5.0 (HealthTrust HealthCheck)"}
        },
        {
            "name": "GeoJSON Batas Jatim (GitHub Backup)",
            "url": "https://raw.githubusercontent.com/carissafarry/JatimGeoJSON/master/GeoJSON/Jawa_Timur.json",
            "method": "GET",
            "expected": [200]
        }
    ]

    results = []
    for target in targets:
        print(f"Pinging {target['name']} ...", end=" ", flush=True)
        res = check_endpoint(
            name=target["name"],
            url=target["url"],
            method=target.get("method", "GET"),
            expected_codes=target.get("expected", [200]),
            headers=target.get("headers", None)
        )
        results.append(res)
        if res["status"] == "HEALTHY":
            print(f"[OK] ({res['status_code']}) - {res['response_time_ms']}ms")
        else:
            print(f"[{res['status']}] ({res['status_code']}) - {res['error']}")

    print("=" * 60)
    print(" Summary:")
    healthy_count = sum(1 for r in results if r["status"] == "HEALTHY")
    print(f" Total: {len(results)} | Healthy: {healthy_count} | Down/Degraded: {len(results) - healthy_count}")
    print("=" * 60)

if __name__ == "__main__":
    run_health_checks()
