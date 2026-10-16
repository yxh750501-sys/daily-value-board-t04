"""Record one real Open-Meteo reading for the current Asia/Seoul date."""
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
import json
import math
import time

SOURCE_URL = 'https://api.open-meteo.com/v1/forecast?latitude=37.5665&longitude=126.9780&current=temperature_2m&timezone=Asia%2FSeoul&forecast_days=1'
OUT = Path(__file__).resolve().parents[1] / 'docs/data/live-history.json'
KST = ZoneInfo('Asia/Seoul')

def normalize(raw, fetched_at):
    if raw.get('timezone') != 'Asia/Seoul' or not isinstance(raw.get('current'), dict) or not isinstance(raw.get('current_units'), dict):
        raise ValueError('Open-Meteo response shape changed')
    value = raw['current'].get('temperature_2m')
    source_time = raw['current'].get('time')
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ValueError('Temperature is not a finite number')
    if raw['current_units'].get('temperature_2m') != '°C' or not isinstance(source_time, str):
        raise ValueError('Source time or unit changed')
    observed = datetime.strptime(source_time, '%Y-%m-%dT%H:%M').replace(tzinfo=KST)
    fetched = datetime.fromisoformat(fetched_at.replace('Z', '+00:00'))
    return {
        'signal_id': 'seoul-temperature-2m',
        'normalized_value': value,
        'unit': '°C',
        'source_name': 'Open-Meteo · 서울 2m 기온',
        'source_url': SOURCE_URL,
        'source_time': observed.astimezone(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z'),
        'fetched_at': fetched.astimezone(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z'),
        'record_timezone': 'Asia/Seoul',
        'record_date': fetched.astimezone(KST).date().isoformat(),
    }

def upsert(history, raw, fetched_at):
    reading = normalize(raw, fetched_at)
    prior = {row['record_date']: row for row in history.get('readings', [])}
    prior[reading['record_date']] = reading
    raw_by_date = dict(history.get('raw_by_date', {}))
    raw_by_date[reading['record_date']] = {
        'timezone': raw['timezone'], 'current': raw['current'], 'current_units': raw['current_units']
    }
    dates = sorted(prior)[-2:]
    return {
        'schema_version': 't04-public-history-v1',
        'source': 'Open-Meteo',
        'readings': [prior[date] for date in dates],
        'raw_by_date': {date: raw_by_date[date] for date in dates},
    }

def main():
    request = Request(SOURCE_URL, headers={'User-Agent': 'daily-value-board-t04/1.0'})
    for attempt, delay in enumerate((0, 2, 5, 10)):
        if delay:
            time.sleep(delay)
        try:
            with urlopen(request, timeout=20) as response:
                if response.status != 200:
                    raise RuntimeError(f'Open-Meteo returned {response.status}')
                raw = json.load(response)
            break
        except HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 3:
                raise
            print(f'Open-Meteo HTTP {error.code}; retrying after a short wait', flush=True)
    fetched_at = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    existing = json.loads(OUT.read_text()) if OUT.exists() else {}
    updated = upsert(existing, raw, fetched_at)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + '\n')
    row = updated['readings'][-1]
    print(json.dumps({'record_date': row['record_date'], 'source_time': row['source_time'],
        'fetched_at': row['fetched_at'], 'normalized_value': row['normalized_value'],
        'unit': row['unit'], 'source_url': row['source_url'], 'row_count': len(updated['readings'])}, ensure_ascii=False))

if __name__ == '__main__':
    main()
