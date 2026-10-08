"""Wikimedia Commons image search with explicit reusable-license metadata."""
from __future__ import annotations

import re
from html import unescape
from urllib.parse import urlparse

import httpx

API = 'https://commons.wikimedia.org/w/api.php'
HEADERS = {'User-Agent': 'MoCoCo/0.1 (https://github.com/Baixue-Wu/MoCoCo)'}
IMAGE_HOSTS = {'upload.wikimedia.org', 'thumb.wikimedia.org'}


def plain(value: str) -> str:
    return re.sub(r'\s+', ' ', unescape(re.sub(r'<[^>]+>', ' ', str(value)))).strip()


def allowed_license(name: str, url: str) -> bool:
    name = name.lower().strip()
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname != 'creativecommons.org':
        return False
    path = parsed.path.rstrip('/')
    if re.fullmatch(r'cc by (1\.0|2\.0|2\.5|3\.0|4\.0)', name):
        return path == '/licenses/by/' + name.split()[-1]
    if name in {'cc0', 'cc0 1.0', 'public domain'}:
        return path in {'/publicdomain/zero/1.0', '/publicdomain/mark/1.0'}
    return False


def parse_page(page: dict) -> dict | None:
    info = (page.get('imageinfo') or [{}])[0]
    meta = info.get('extmetadata', {})
    field = lambda k: plain(meta.get(k, {}).get('value', ''))
    license_name, license_url = field('LicenseShortName'), field('LicenseUrl')
    if license_url.startswith('//'):
        license_url = 'https:' + license_url
    artist = field('Artist')
    image_url = info.get('thumburl') or info.get('url', '')
    source_url = info.get('descriptionurl', '')
    if (not artist or not allowed_license(license_name, license_url)
            or info.get('mime') not in {'image/jpeg', 'image/png', 'image/webp'}
            or urlparse(image_url).hostname not in IMAGE_HOSTS
            or urlparse(image_url).scheme != 'https'
            or urlparse(source_url).hostname != 'commons.wikimedia.org'
            or urlparse(source_url).scheme != 'https'):
        return None
    return {'id': str(page['pageid']), 'title': page['title'], 'image_url': image_url,
            'source_url': source_url, 'artist': artist, 'license': license_name,
            'license_url': license_url, 'caption': field('ImageDescription') or page['title'],
            'credit': field('Credit'), 'restrictions': field('Restrictions')}


def query(*, search: str | None = None, page_id: str | None = None, limit: int = 8) -> list[dict]:
    if not 1 <= limit <= 20:
        raise ValueError('Image result limit must be 1-20')
    params = {'action': 'query', 'format': 'json', 'prop': 'imageinfo',
              'iiprop': 'url|extmetadata|mime|size', 'iiurlwidth': 960}
    if search is not None:
        if not search.strip() or len(search) > 300:
            raise ValueError('Image query must contain 1-300 characters')
        params.update(generator='search', gsrsearch=search, gsrnamespace=6, gsrlimit=limit)
    elif page_id and page_id.isdigit():
        params['pageids'] = page_id
    else:
        raise ValueError('Provide a search question or numeric Commons page ID')
    try:
        response = httpx.get(API, params=params, headers=HEADERS, timeout=30)
        response.raise_for_status()
        result = response.json()
        if 'error' in result:
            raise ValueError(str(result['error']))
    except (httpx.HTTPError, ValueError) as exc:
        raise RuntimeError(f'Commons image lookup failed: {exc}. Check the connection and retry image search.') from exc
    pages = sorted(result.get('query', {}).get('pages', {}).values(), key=lambda p: p.get('index', 0))
    return [record for page in pages if (record := parse_page(page)) is not None]


def download(url: str, max_bytes: int = 10_000_000) -> bytes:
    """Download only Commons image hosts, checking every redirect and the size."""
    for _ in range(4):
        parsed = urlparse(url)
        if parsed.scheme != 'https' or parsed.hostname not in IMAGE_HOSTS or parsed.username:
            raise ValueError('Image download must remain on Wikimedia image hosts; repeat image search')
        with httpx.stream('GET', url, headers=HEADERS, timeout=45, follow_redirects=False) as response:
            if response.is_redirect:
                url = str(response.url.join(response.headers['location']))
                continue
            response.raise_for_status()
            data = bytearray()
            for block in response.iter_bytes(65536):
                data.extend(block)
                if len(data) > max_bytes:
                    raise ValueError('Image exceeds 10 MB; choose a smaller image')
            return bytes(data)
    raise ValueError('Too many image redirects; repeat image search')
