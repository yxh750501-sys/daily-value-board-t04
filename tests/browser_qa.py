"""Run with: python3 tests/browser_qa.py (requires Playwright and Chromium)."""
from datetime import datetime
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from threading import Thread
from zoneinfo import ZoneInfo
import json

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
CHROMIUM = '/usr/lib/chromium/chromium'

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / 'docs'), **kwargs)
    def log_message(self, *args):
        pass

server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
Thread(target=server.serve_forever, daemon=True).start()
url = f'http://127.0.0.1:{server.server_port}/'
source_time = datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%dT%H:%M')
temperatures = iter([17.4, 18.1, 18.2])
requests = []
live_mode = {'value': 'normal'}

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path=CHROMIUM, headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-crash-reporter', '--disable-breakpad'])
    context = browser.new_context(accept_downloads=True)
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.route('https://fonts.googleapis.com/**', lambda route: route.abort())
    page.route('https://fonts.gstatic.com/**', lambda route: route.abort())

    def mock_live(route):
        requests.append(route.request.url)
        if live_mode['value'] == 'offline':
            route.abort()
            return
        value = next(temperatures)
        route.fulfill(status=200, content_type='application/json', body=json.dumps({
            'timezone': 'Asia/Seoul', 'current': {'time': source_time, 'temperature_2m': value},
            'current_units': {'temperature_2m': '°C'}
        }))
    page.route('https://api.open-meteo.com/**', mock_live)
    page.goto(url, wait_until='domcontentloaded')
    expect(page.locator('#live-badge')).to_have_text('조회 전')
    live_mode['value'] = 'offline'
    page.locator('#live-refresh').click()
    expect(page.locator('#live-badge')).to_have_text('조회 실패')
    expect(page.locator('#live-value')).to_have_text('—')
    live_mode['value'] = 'normal'
    page.locator('#live-refresh').click()
    expect(page.locator('#live-value')).to_have_text('17.4')
    expect(page.locator('#live-unit')).to_have_text('°C')
    expect(page.locator('#live-badge')).to_have_text('최신 조회')
    expect(page.locator('#live-count')).to_have_text('1건')
    assert 'open-meteo.com' in page.locator('#live-source').get_attribute('href')
    assert 'KST' in page.locator('#live-source-time').inner_text()
    assert 'KST' in page.locator('#live-fetched-time').inner_text()
    assert 'Asia/Seoul' in page.locator('.facts').inner_text()
    page.locator('.data-details summary').click()
    expect(page.locator('#raw-data')).to_contain_text('17.4')
    expect(page.locator('#stored-data')).to_contain_text('17.4')
    expect(page.locator('#display-data')).to_contain_text('17.4 °C')
    print('PASS actual-source request path (mocked response) and raw/stored/display match')

    page.locator('#live-refresh').click()
    expect(page.locator('#live-value')).to_have_text('18.1')
    expect(page.locator('#live-count')).to_have_text('1건')
    page.reload(wait_until='domcontentloaded')
    expect(page.locator('#live-value')).to_have_text('18.1')
    expect(page.locator('#live-count')).to_have_text('1건')
    print('PASS same KST date upsert and IndexedDB reload')

    with page.expect_download() as download_info:
        page.locator('#live-export').click()
    export_path = Path('/tmp/t04-live-export-qa.json')
    download_info.value.save_as(str(export_path))
    exported = json.loads(export_path.read_text())
    assert len(exported['daily_readings']) == 1
    assert exported['daily_readings'][0]['normalized_value'] == 18.1
    assert exported['raw_by_date'][exported['daily_readings'][0]['record_date']]['current']['temperature_2m'] == 18.1
    print('PASS exported daily evidence includes matching source and stored value')

    live_mode['value'] = 'offline'
    page.locator('#live-refresh').click()
    expect(page.locator('#live-badge')).to_have_text('오래된 값')
    expect(page.locator('#live-note')).to_contain_text('네트워크 연결')
    expect(page.locator('#live-value')).to_have_text('18.1')
    expect(page.locator('#live-count')).to_have_text('1건')
    live_mode['value'] = 'normal'
    page.locator('#live-refresh').click()
    expect(page.locator('#live-badge')).to_have_text('최신 조회')
    expect(page.locator('#live-value')).to_have_text('18.2')
    expect(page.locator('#live-count')).to_have_text('1건')
    print('PASS live transport failure keeps stale value and retry recovers')

    page.locator('#demo-baseline').click()
    expect(page.locator('#demo-value')).to_have_text('105')
    expect(page.locator('#demo-count')).to_have_text('1건')
    for button, code in [('느린 응답','timeout'), ('원천 401','auth'), ('호출 제한','rate_limit'),
                         ('오프라인','offline'), ('형식 변경','schema_error')]:
        page.locator('#demo-baseline').click()
        expect(page.locator('#demo-status')).to_have_text('fresh / none')
        page.get_by_role('button', name=button).click()
        expect(page.locator('#demo-status')).to_have_text(f'stale / {code}')
        expect(page.locator('#demo-value')).to_have_text('105')
        expect(page.locator('#demo-count')).to_have_text('1건')
        expect(page.locator('#demo-message')).to_contain_text('오래된 값')
        expect(page.locator('#demo-retry')).to_be_visible()
        print(f'PASS {code} visible failure, stale value 105, retry')

    page.locator('#demo-baseline').click()
    page.get_by_role('button', name='느린 응답').click()
    expect(page.locator('#demo-status')).to_have_text('stale / timeout')
    page.locator('#demo-retry').click()
    expect(page.locator('#demo-status')).to_have_text('fresh / none')
    expect(page.locator('#demo-value')).to_have_text('120')
    expect(page.locator('#demo-count')).to_have_text('2건')
    expect(page.locator('#demo-message')).to_contain_text('+15 pt')
    page.reload(wait_until='domcontentloaded')
    expect(page.locator('#demo-count')).to_have_text('2건')
    expect(page.locator('#demo-status')).to_have_text('fresh / none')
    print('PASS public RECOVER-D2 and reload persistence')

    assert all('key=' not in request and 'token=' not in request for request in requests)
    assert not errors, errors
    page.screenshot(path='/tmp/t04-browser-qa.png', full_page=True)
    page.set_viewport_size({'width': 390, 'height': 844})
    page.screenshot(path='/tmp/t04-browser-qa-mobile.png', full_page=True)
    overflow = page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
    assert not overflow, 'mobile horizontal overflow'
    print('PASS 390px mobile layout without horizontal overflow')
    print('PASS no JavaScript errors and no secret in live request URL')
    browser.close()
server.shutdown()
