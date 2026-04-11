import os
import re
from datetime import datetime
from urllib.parse import urlparse

from crawler_service.providers.base import BaseCrawlerProvider


DEFAULT_PROFILE_NAME_SELECTORS = [
    'h1',
    '[class*="user-name"]',
    '[class*="nickname"]',
    '[data-testid*="user-name"]',
]

DEFAULT_FOLLOWER_COUNT_SELECTORS = [
    '[class*="follower"]',
    '[class*="fans"]',
    '[data-testid*="fans"]',
]

DEFAULT_POST_CARD_SELECTORS = [
    'section.note-item',
    'div.note-item',
    'div[data-testid*="note"]',
    'a[href*="/explore/"]',
    'a[href*="/discovery/item/"]',
]

DEFAULT_POST_LINK_SELECTORS = [
    'a[href*="/explore/"]',
    'a[href*="/discovery/item/"]',
]

DEFAULT_POST_TITLE_SELECTORS = [
    '[class*="title"]',
    '[data-testid*="title"]',
    'img[alt]',
]

DEFAULT_POST_LIKES_SELECTORS = [
    '[class*="like"]',
    '[data-testid*="like"]',
]

DEFAULT_POST_COMMENTS_SELECTORS = [
    '[class*="comment"]',
    '[data-testid*="comment"]',
]

DEFAULT_POST_FAVORITES_SELECTORS = [
    '[class*="collect"]',
    '[class*="favorite"]',
    '[data-testid*="collect"]',
]

DEFAULT_POST_VIEWS_SELECTORS = [
    '[class*="view"]',
    '[class*="read"]',
    '[data-testid*="view"]',
]

DEFAULT_POST_TIME_SELECTORS = [
    'time',
    '[class*="time"]',
    '[class*="date"]',
]


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_xhs_url(url):
    raw = (url or '').strip()
    if not raw:
        return ''
    if raw.startswith('/'):
        raw = f'https://www.xiaohongshu.com{raw}'
    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return raw
    path = parsed.path.rstrip('/')
    return f'{parsed.scheme}://{parsed.netloc.lower()}{path}'


def _extract_post_id(url):
    raw = _normalize_xhs_url(url)
    matched = re.search(r'/(?:explore|discovery/item)/([0-9a-zA-Z]+)', raw)
    return matched.group(1) if matched else ''


def _parse_count(text):
    raw = (text or '').strip().lower().replace(',', '')
    if not raw:
        return 0
    raw = (
        raw.replace('点赞', '')
        .replace('收藏', '')
        .replace('评论', '')
        .replace('浏览', '')
        .replace('阅读', '')
        .replace('粉丝', '')
        .strip()
    )
    multiplier = 1
    if raw.endswith('w'):
        multiplier = 10000
        raw = raw[:-1]
    elif raw.endswith('k'):
        multiplier = 1000
        raw = raw[:-1]
    try:
        return int(float(raw) * multiplier)
    except ValueError:
        matched = re.search(r'(\d+(?:\.\d+)?)', raw)
        if not matched:
            return 0
        return int(float(matched.group(1)) * multiplier)


def _selector_candidates(primary_value, defaults):
    items = []
    for row in [primary_value] + list(defaults or []):
        raw = (row or '').strip()
        if not raw:
            continue
        for token in re.split(r'\s*\|\|\s*|\n+', raw):
            current = token.strip()
            if current and current not in items:
                items.append(current)
    return items


class PlaywrightXHSCrawlerProvider(BaseCrawlerProvider):
    async def healthcheck(self):
        try:
            from playwright.async_api import async_playwright  # noqa: F401
            playwright_ready = True
        except ImportError:
            playwright_ready = False
        return {
            'provider': 'playwright_xhs',
            'ready': playwright_ready,
            'storage_state_path': self.settings.playwright_storage_state_path,
            'post_card_selectors': _selector_candidates(
                self.settings.xhs_post_card_selector,
                DEFAULT_POST_CARD_SELECTORS,
            )[:5],
        }

    async def fetch_account_posts(self, payload):
        try:
            from playwright.async_api import TimeoutError as PlaywrightTimeoutError, async_playwright
        except ImportError as exc:
            raise RuntimeError('未安装 Playwright，请先在 crawler_service 环境执行 playwright install') from exc

        accounts = []
        posts = []
        snapshots = []

        async with async_playwright() as playwright:
            launch_kwargs = {'headless': self.settings.playwright_headless}
            if self.settings.playwright_browser_channel:
                launch_kwargs['channel'] = self.settings.playwright_browser_channel
            browser = await playwright.chromium.launch(**launch_kwargs)
            context_kwargs = {}
            storage_path = self.settings.playwright_storage_state_path
            if storage_path and os.path.exists(storage_path):
                context_kwargs['storage_state'] = storage_path
            context = await browser.new_context(**context_kwargs)
            try:
                for target in payload.targets[: self.settings.xhs_max_posts_per_account]:
                    profile_url = (target.profile_url or '').strip()
                    account_handle = (target.account_handle or '').strip()
                    if not profile_url and account_handle:
                        profile_url = self.settings.xhs_profile_url_template.format(account_handle=account_handle)
                    if not profile_url:
                        continue

                    page = await context.new_page()
                    try:
                        await page.goto(
                            profile_url,
                            wait_until='domcontentloaded',
                            timeout=self.settings.playwright_navigation_timeout_ms,
                        )
                        await page.wait_for_load_state('networkidle', timeout=self.settings.playwright_navigation_timeout_ms)
                    except PlaywrightTimeoutError as exc:
                        await page.close()
                        raise RuntimeError(f'打开账号主页超时：{profile_url}') from exc

                    display_name = await self._extract_display_name(page, account_handle, target.owner_name)
                    follower_count = await self._extract_follower_count(page)
                    account_row = {
                        'platform': 'xhs',
                        'owner_name': target.owner_name or '',
                        'owner_phone': target.owner_phone or '',
                        'account_handle': account_handle or display_name,
                        'display_name': display_name or account_handle,
                        'profile_url': _normalize_xhs_url(profile_url),
                        'follower_count': follower_count,
                        'source_channel': payload.source_channel or 'playwright_xhs',
                        'notes': '由 Playwright 抓取账号主页返回',
                    }
                    accounts.append(account_row)

                    post_rows = await self._extract_posts(
                        page=page,
                        target=target,
                        profile_url=account_row['profile_url'],
                        account_handle=account_row['account_handle'],
                        source_channel=payload.source_channel or 'playwright_xhs',
                    )
                    posts.extend(post_rows)
                    snapshots.append({
                        'platform': 'xhs',
                        'account_handle': account_row['account_handle'],
                        'owner_phone': target.owner_phone or '',
                        'owner_name': target.owner_name or '',
                        'profile_url': account_row['profile_url'],
                        'snapshot_date': datetime.now().strftime('%Y-%m-%d'),
                        'follower_count': follower_count,
                        'post_count': len(post_rows),
                        'total_views': sum(item.get('views', 0) for item in post_rows),
                        'total_interactions': sum(
                            (item.get('likes', 0) or 0) +
                            (item.get('favorites', 0) or 0) +
                            (item.get('comments', 0) or 0)
                            for item in post_rows
                        ),
                        'source_channel': payload.source_channel or 'playwright_xhs',
                    })
                    await page.close()
            finally:
                await context.close()
                await browser.close()

        return {
            'success': True,
            'provider': 'playwright_xhs',
            'batch_name': payload.batch_name,
            'source_channel': payload.source_channel,
            'accounts': accounts,
            'posts': posts,
            'snapshots': snapshots,
            'meta': {
                'target_count': len(payload.targets),
                'returned_account_count': len(accounts),
                'returned_post_count': len(posts),
            },
        }

    async def _extract_display_name(self, page, account_handle, owner_name):
        for selector in _selector_candidates(self.settings.xhs_profile_name_selector, DEFAULT_PROFILE_NAME_SELECTORS):
            text = await self._read_text(page, selector)
            if text:
                return text
        title = (await page.title()).strip()
        if title:
            return title.split('-')[0].strip()
        return owner_name or account_handle or ''

    async def _extract_follower_count(self, page):
        for selector in _selector_candidates(self.settings.xhs_follower_count_selector, DEFAULT_FOLLOWER_COUNT_SELECTORS):
            text = await self._read_text(page, selector)
            count = _parse_count(text)
            if count:
                return count
        page_text = (await page.locator('body').text_content() or '').strip()
        matched = re.search(r'粉丝[^\d]*(\d+(?:\.\d+)?[wkW]?)', page_text)
        return _parse_count(matched.group(1)) if matched else 0

    async def _read_text(self, page_or_locator, selector):
        current_selector = (selector or '').strip()
        if not current_selector:
            return ''
        locator = page_or_locator.locator(current_selector)
        if await locator.count() == 0:
            return ''
        text = await locator.first.text_content()
        if text and text.strip():
            return text.strip()
        alt_text = await locator.first.get_attribute('alt')
        if alt_text and alt_text.strip():
            return alt_text.strip()
        title_text = await locator.first.get_attribute('title')
        return (title_text or '').strip()

    async def _read_attr(self, page_or_locator, selector, attr_name):
        current_selector = (selector or '').strip()
        if not current_selector:
            return ''
        locator = page_or_locator.locator(current_selector)
        if await locator.count() == 0:
            return ''
        value = await locator.first.get_attribute(attr_name)
        return (value or '').strip()

    async def _candidate_cards(self, page):
        candidates = []
        for selector in _selector_candidates(self.settings.xhs_post_card_selector, DEFAULT_POST_CARD_SELECTORS):
            locator = page.locator(selector)
            try:
                count = await locator.count()
            except Exception:
                continue
            if count <= 0:
                continue
            for index in range(min(count, self.settings.xhs_max_posts_per_account * 2)):
                card = locator.nth(index)
                href = await self._extract_post_url(card)
                if href:
                    candidates.append(card)
        if candidates:
            return candidates

        links = page.locator('a[href*="/explore/"], a[href*="/discovery/item/"]')
        count = await links.count()
        return [links.nth(index) for index in range(min(count, self.settings.xhs_max_posts_per_account * 2))]

    async def _extract_post_url(self, card):
        for selector in _selector_candidates(self.settings.xhs_post_link_selector, DEFAULT_POST_LINK_SELECTORS):
            href = await self._read_attr(card, selector, 'href')
            if href:
                return _normalize_xhs_url(href)
        href = await card.get_attribute('href')
        if href:
            return _normalize_xhs_url(href)
        return ''

    async def _extract_title(self, card):
        for selector in _selector_candidates(self.settings.xhs_post_title_selector, DEFAULT_POST_TITLE_SELECTORS):
            text = await self._read_text(card, selector)
            if text:
                return text
        fallback_text = (await card.text_content() or '').strip()
        return re.sub(r'\s+', ' ', fallback_text)[:60]

    async def _extract_metric(self, card, custom_selector, default_selectors, keyword):
        for selector in _selector_candidates(custom_selector, default_selectors):
            text = await self._read_text(card, selector)
            value = _parse_count(text)
            if value:
                return value
        block_text = (await card.text_content() or '').strip()
        matched = re.search(rf'{keyword}[^\d]*(\d+(?:\.\d+)?[wkW]?)', block_text)
        return _parse_count(matched.group(1)) if matched else 0

    async def _extract_publish_time(self, card):
        for selector in _selector_candidates(self.settings.xhs_post_time_selector, DEFAULT_POST_TIME_SELECTORS):
            text = await self._read_text(card, selector)
            if text:
                return text
        return ''

    async def _extract_posts(self, page, target, profile_url, account_handle, source_channel):
        cards = await self._candidate_cards(page)
        rows = []
        seen_urls = set()
        for card in cards:
            post_url = await self._extract_post_url(card)
            if not post_url or post_url in seen_urls:
                continue
            seen_urls.add(post_url)
            title = await self._extract_title(card)
            platform_post_id = _extract_post_id(post_url)
            if not (title or platform_post_id):
                continue
            rows.append({
                'platform': 'xhs',
                'account_handle': account_handle,
                'owner_phone': target.owner_phone or '',
                'owner_name': target.owner_name or '',
                'profile_url': profile_url,
                'registration_id': _safe_int(target.registration_id),
                'topic_id': _safe_int(target.topic_id),
                'submission_id': _safe_int(target.submission_id),
                'platform_post_id': platform_post_id,
                'title': title or f'未命名笔记 {len(rows) + 1}',
                'post_url': post_url,
                'publish_time': await self._extract_publish_time(card),
                'topic_title': '',
                'views': await self._extract_metric(card, self.settings.xhs_post_views_selector, DEFAULT_POST_VIEWS_SELECTORS, '浏览|阅读'),
                'exposures': 0,
                'likes': await self._extract_metric(card, self.settings.xhs_post_likes_selector, DEFAULT_POST_LIKES_SELECTORS, '点赞'),
                'favorites': await self._extract_metric(card, self.settings.xhs_post_favorites_selector, DEFAULT_POST_FAVORITES_SELECTORS, '收藏'),
                'comments': await self._extract_metric(card, self.settings.xhs_post_comments_selector, DEFAULT_POST_COMMENTS_SELECTORS, '评论'),
                'shares': 0,
                'follower_delta': 0,
                'source_channel': source_channel,
            })
            if len(rows) >= self.settings.xhs_max_posts_per_account:
                break
        return rows
