# South Korea KPX power-data downloader

A small, dependency-free Python downloader for public electricity data from the
Korea Power Exchange (KPX). It follows the endpoints and parsing approach used
by the Electricity Maps South Korea parser and does not require an API key.

## Data available

- Current system load
- Current generation by source
- Historical generation by source for a requested date range

Generation fields include coal, domestic coal, gas, oil, nuclear, hydro, pumped
storage, wind, solar, new renewables, and battery storage. Timestamps are Korea
Standard Time and power values are MW.

KPX controls the historical availability of the underlying endpoint. A request
can therefore return no data even when the date syntax is valid.

## Requirements

- Python 3.10 or newer
- Internet access

The downloader uses only the Python standard library.

## Usage

Download current data and yesterday's historical generation:

```bash
python3 kpx_download_example.py
```

Download a particular date:

```bash
python3 kpx_download_example.py --date 2024-01-01
```

Download an inclusive date range:

```bash
python3 kpx_download_example.py \
  --date 2024-01-01 \
  --end-date 2024-01-07 \
  --output kpx_output/week
```

The script writes CSV files beneath `kpx_output/`. Downloaded outputs are
excluded from Git because they are reproducible and may grow substantially.

## Data source and caveats

The source is the public [KPX power-information website](https://new.kpx.or.kr/powerinfoSubmain.es?mid=a10606030000).

- This project is unofficial and is not affiliated with KPX or Electricity Maps.
- The page format and endpoints can change without notice.
- Review KPX's applicable terms before redistributing or commercially using the data.
- The script reports data as published by KPX; it does not correct or reconcile values.
