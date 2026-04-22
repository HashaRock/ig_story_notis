import re
import requests

resp = requests.get(
    'https://www.instagram.com/zero2sudo/',
    headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }
)

match = re.search(r'"userID":"(\d+)"', resp.text)
if not match:
    match = re.search(r'"owner":\{"id":"(\d+)"', resp.text)
if not match:
    match = re.search(r'profilePage_(\d+)', resp.text)

if match:
    print('userid:', match.group(1))
else:
    print('not found in page, status:', resp.status_code)

# --- debug: inspect raw stories API response ---
import json
import instaloader
from ig_client import IGClient, _MOBILE_UA, _APP_ID
from config import Config

ig = IGClient(Config.load())
ig.login()

resp = ig._loader.context._session.get(
    'https://i.instagram.com/api/v1/feed/reels_media/?reel_ids=50350974961',
    headers={'User-Agent': _MOBILE_UA, 'x-ig-app-id': _APP_ID}
)
print(resp.status_code)
print(json.dumps(resp.json(), indent=2))
