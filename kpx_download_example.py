#!/usr/bin/env python3
"""Download public South Korean power data from the KPX website.

This follows the same endpoints and parsing approach as Electricity Maps' KPX
parser.  It does not require a data.go.kr API key.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import date, datetime, timedelta
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

REAL_TIME_URL = "https://new.kpx.or.kr/powerinfoSubmain.es?mid=a10606030000"
HISTORICAL_URL = "https://new.kpx.or.kr/powerSource.es?mid=a10606030000&device=chart"


def extract_embedded_json(html: str) -> list[dict[str, str]]:
    match = re.search(r"var ictArr = (\[\{.+?\}\]);", html)
    if not match:
        raise RuntimeError("KPX response did not contain the ictArr dataset")
    return [row for row in json.loads(match.group(1)) if row.get("regDate") != "0"]


def production_rows(rows: list[dict[str, str]]) -> list[dict[str, str | float]]:
    mapping = {
        "regDate": "datetime_kst",
        "coal": "coal_mw",
        "localCoal": "domestic_coal_mw",
        "gas": "gas_mw",
        "oil": "oil_mw",
        "nuclearPower": "nuclear_mw",
        "waterPower": "hydro_mw",
        "raisingWater": "pumped_storage_mw",
        "windPower": "wind_mw",
        "sunlight": "solar_mw",
        "newRenewable": "new_renewable_mw",
        "essMw": "battery_storage_mw",
    }
    return [
        {
            target: row[source] if source == "regDate" else float(row[source])
            for source, target in mapping.items()
        }
        for row in rows
    ]


def extract_current_load(html: str) -> list[dict[str, str | float]]:
    values_match = re.search(r"var x\s*=\s*\[([\d.,\s]+)\]", html)
    times_match = re.search(r"var t_time\s*=\s*\[([\d,\s]+)\]", html)
    if not values_match or not times_match:
        raise RuntimeError("KPX response did not contain current load arrays")
    values = [float(value.strip()) for value in values_match.group(1).split(",")]
    timestamps = [value.strip() for value in times_match.group(1).split(",")]
    return [
        {
            "datetime_kst": datetime.strptime(timestamp, "%Y%m%d%H%M%S").strftime(
                "%Y-%m-%d %H:%M"
            ),
            "total_demand_mw": value,
        }
        for timestamp, value in zip(timestamps, values, strict=True)
    ]


def write_csv(destination: Path, rows: list[dict[str, str | float]]) -> None:
    if not rows:
        raise RuntimeError(f"No data returned for {destination.name}")
    with destination.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def fetch(opener, url: str, data: dict[str, str] | None = None) -> str:
    body = urlencode(data).encode() if data else None
    request = Request(
        url,
        data=body,
        headers={"User-Agent": "Mozilla/5.0 (compatible; KPX-data-example/1.0)"},
    )
    with opener.open(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=(date.today() - timedelta(days=1)).isoformat())
    parser.add_argument(
        "--end-date",
        help="Optional inclusive end date for a multi-day historical download",
    )
    parser.add_argument("--output", type=Path, default=Path("kpx_output"))
    args = parser.parse_args()
    requested_date = datetime.strptime(args.date, "%Y-%m-%d").date().isoformat()
    end_date = (
        datetime.strptime(args.end_date, "%Y-%m-%d").date().isoformat()
        if args.end_date
        else requested_date
    )
    if end_date < requested_date:
        parser.error("--end-date must not be earlier than --date")
    args.output.mkdir(parents=True, exist_ok=True)

    cookies = CookieJar()
    opener = build_opener(HTTPCookieProcessor(cookies))

    current_html = fetch(opener, REAL_TIME_URL)
    current_load = extract_current_load(current_html)
    current_production = production_rows(extract_embedded_json(current_html))

    # KPX requires a session CSRF cookie for historical production requests.
    fetch(opener, HISTORICAL_URL)
    csrf_token = next(
        (cookie.value for cookie in cookies if cookie.name == "XSRF-TOKEN"), None
    )
    historical_html = fetch(
        opener,
        HISTORICAL_URL,
        {
            "mid": "a10606030000",
            "device": "chart",
            "view_sdate": requested_date,
            "view_edate": end_date,
            "_csrf": csrf_token,
        },
    )
    historical_production = production_rows(
        extract_embedded_json(historical_html)
    )

    outputs = {
        "current_load.csv": current_load,
        "current_production.csv": current_production,
        (
            f"production_{requested_date}.csv"
            if end_date == requested_date
            else f"production_{requested_date}_to_{end_date}.csv"
        ): historical_production,
    }
    for filename, rows in outputs.items():
        destination = args.output / filename
        write_csv(destination, rows)
        print(
            f"{destination}: {len(rows)} rows, "
            f"{rows[0]['datetime_kst']} to {rows[-1]['datetime_kst']}"
        )

    print("\nMost recent production row (MW):")
    print(json.dumps(current_production[-1], indent=2))
    print("\nMost recent load row (MW):")
    print(json.dumps(current_load[-1], indent=2))


if __name__ == "__main__":
    main()
