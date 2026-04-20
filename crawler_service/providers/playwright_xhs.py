import os
import re
import tempfile
from datetime import datetime, timedelta
from urllib.parse import quote, urlparse

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

DEFAULT_POST_AUTHOR_SELECTORS = [
    '[class*="author"]',
    '[class*="user"]',
    '[class*="nickname"]',
    '[data-testid*="author"]',
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

DEFAULT_SEARCH_RELATED_QUERY_SELECTORS = [
    '[class*="related"] a',
    '[class*="recommend"] a',
    '[class*="suggest"] a',
    '[class*="hot"] a',
]

SEARCH_STATE_CANDIDATE_PATHS = [
    ('search', 'feeds', 'value'),
    ('search', 'feedList', 'value'),
    ('search', 'noteList', 'items'),
    ('search', 'items'),
]

RELATED_QUERY_STATE_CANDIDATE_PATHS = [
    ('search', 'relatedQueries'),
    ('search', 'related_queries'),
    ('search', 'hotQuery'),
    ('search', 'hot_query'),
    ('search', 'queryList'),
    ('search', 'query_list'),
    ('search', 'suggestQueries'),
    ('search', 'suggest_queries'),
    ('search', 'recQuery'),
    ('search', 'rec_query'),
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
    if isinstance(text, (int, float)):
        return int(text)
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


def _parse_date_boundary(raw, *, start=True):
    text = (raw or '').strip()
    if not text:
        return None
    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
        try:
            parsed = datetime.strptime(text, fmt)
            if fmt == '%Y-%m-%d' and not start:
                return parsed.replace(hour=23, minute=59, second=59, microsecond=999999)
            return parsed
        except ValueError:
            continue
    return None


def _resolve_post_date_window(payload):
    now = datetime.now()
    date_from = _parse_date_boundary(getattr(payload, 'date_from', ''), start=True)
    date_to = _parse_date_boundary(getattr(payload, 'date_to', ''), start=False)
    if getattr(payload, 'current_month_only', False) and not date_from:
        date_from = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if getattr(payload, 'current_month_only', False) and not date_to:
        date_to = now
    return date_from, date_to


def _state_get(value, path, default=None):
    current = value
    for token in [item for item in str(path or '').split('.') if item]:
        if isinstance(current, dict):
            current = current.get(token)
        elif isinstance(current, list):
            try:
                current = current[int(token)]
            except (TypeError, ValueError, IndexError):
                return default
        else:
            return default
        if current is None:
            return default
    return current


def _state_text(value, paths, default=''):
    for path in paths:
        current = _state_get(value, path)
        if current in [None, '']:
            continue
        text = str(current).strip()
        if text:
            return text
    return default


def _state_count(value, paths, default=0):
    for path in paths:
        current = _state_get(value, path)
        if current in [None, '']:
            continue
        count = _parse_count(current)
        if count:
            return count
    return default


def _looks_like_search_feed_item(value):
    if not isinstance(value, dict):
        return False
    if any(key in value for key in ['note_card', 'noteCard']):
        return True
    return bool(_state_get(value, 'id') and (
        _state_get(value, 'title') or
        _state_get(value, 'display_title') or
        _state_get(value, 'note_card.title') or
        _state_get(value, 'noteCard.title')
    ))


def _walk_dicts(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_dicts(child)


def _find_state_list(value, candidate_paths, predicate):
    for path_tokens in candidate_paths:
        current = value
        for token in path_tokens:
            if isinstance(current, dict):
                current = current.get(token)
            else:
                current = None
                break
        if isinstance(current, list) and current:
            if predicate(current):
                return current
    return []


def _parse_state_publish_time(raw_value):
    if raw_value in [None, '']:
        return None
    if isinstance(raw_value, (int, float)):
        timestamp = float(raw_value)
        if timestamp > 10**12:
            timestamp = timestamp / 1000.0
        if timestamp > 10**9:
            return datetime.fromtimestamp(timestamp)
    text = str(raw_value).strip()
    if text.isdigit():
        return _parse_state_publish_time(int(text))
    return _parse_publish_time_value(text)


def _build_search_result_url(item):
    direct_url = _state_text(item, [
        'link',
        'url',
        'note_card.share_url',
        'note_card.url',
        'noteCard.share_url',
        'noteCard.url',
    ])
    if direct_url:
        return _normalize_xhs_url(direct_url)
    note_id = _state_text(item, [
        'id',
        'note_id',
        'noteCard.note_id',
        'note_card.note_id',
    ])
    if not note_id:
        return ''
    xsec_token = _state_text(item, ['xsec_token', 'xsecToken'])
    if xsec_token:
        return _normalize_xhs_url(
            f'https://www.xiaohongshu.com/explore/{note_id}?xsec_token={quote(xsec_token)}&xsec_source=pc_search'
        )
    return _normalize_xhs_url(f'https://www.xiaohongshu.com/explore/{note_id}')


def _normalize_search_feed_item(item, keyword, source_channel, rank):
    title = _state_text(item, [
        'note_card.display_title',
        'note_card.title',
        'noteCard.display_title',
        'noteCard.title',
        'display_title',
        'title',
    ])
    post_url = _build_search_result_url(item)
    if not (title or post_url):
        return {}
    publish_time_dt = _parse_state_publish_time(_state_get(item, 'note_card.time'))
    if not publish_time_dt:
        publish_time_dt = _parse_state_publish_time(_state_get(item, 'noteCard.time'))
    if not publish_time_dt:
        publish_time_dt = _parse_state_publish_time(_state_get(item, 'publish_time'))
    views = _state_count(item, [
        'view_count',
        'note_card.view_count',
        'noteCard.view_count',
        'impression_cnt',
        'exposure_count',
    ])
    likes = _state_count(item, [
        'interact_info.liked_count',
        'note_card.interact_info.liked_count',
        'noteCard.interact_info.liked_count',
        'likes',
        'like_count',
    ])
    favorites = _state_count(item, [
        'interact_info.collected_count',
        'note_card.interact_info.collected_count',
        'noteCard.interact_info.collected_count',
        'favorites',
        'collect_count',
    ])
    comments = _state_count(item, [
        'interact_info.comment_count',
        'note_card.interact_info.comment_count',
        'noteCard.interact_info.comment_count',
        'comments',
        'comment_count',
    ])
    return {
        'keyword': keyword,
        'query': keyword,
        'title': title or f'{keyword} 搜索结果 {rank}',
        'link': post_url,
        'author': _state_text(item, [
            'note_card.user.nickname',
            'noteCard.user.nickname',
            'user.nickname',
            'author.nickname',
            'author',
        ]),
        'summary': _state_text(item, [
            'note_card.desc',
            'noteCard.desc',
            'desc',
            'description',
        ]),
        'hot_value': views + likes * 3 + favorites * 4 + comments * 5 + max(0, 100 - rank * 3),
        'rank': rank,
        'views': views,
        'likes': likes,
        'favorites': favorites,
        'comments': comments,
        'publish_time': publish_time_dt.strftime('%Y-%m-%d %H:%M:%S') if publish_time_dt else _state_text(item, ['publish_time', 'note_card.time', 'noteCard.time']),
        'source_channel': source_channel,
    }


def _normalize_related_query_item(item, keyword, source_channel, rank):
    if isinstance(item, str):
        query = re.sub(r'\s+', ' ', item).strip()
    else:
        query = _state_text(item, ['query', 'keyword', 'text', 'display_text', 'search_word', 'word', 'title'])
    if not query or len(query) > 24:
        return {}
    hot_value = _state_count(item, ['hot_value', 'hotScore', 'score', 'search_cnt'], max(0, 10000 - rank * 131))
    return {
        'keyword': keyword,
        'query': query,
        'title': query,
        'summary': f'由小红书搜索页状态数据提取，原始关键词：{keyword}',
        'hot_value': hot_value,
        'rank': rank,
        'source_channel': source_channel,
    }


def _parse_publish_time_value(raw_text, now=None):
    current = now or datetime.now()
    text = (raw_text or '').strip()
    if not text:
        return None
    compact = re.sub(r'\s+', ' ', text)
    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M', '%Y/%m/%d', '%Y-%m-%d']:
        try:
            return datetime.strptime(compact, fmt)
        except ValueError:
            continue
    matched = re.match(r'(\d{1,2})-(\d{1,2})(?:\s+(\d{1,2}):(\d{2}))?', compact)
    if matched:
        month = int(matched.group(1))
        day = int(matched.group(2))
        hour = int(matched.group(3) or 0)
        minute = int(matched.group(4) or 0)
        year = current.year
        candidate = datetime(year, month, day, hour, minute)
        if candidate > current + timedelta(days=1):
            candidate = datetime(year - 1, month, day, hour, minute)
        return candidate
    matched = re.match(r'(\d+)\s*分钟前', compact)
    if matched:
        return current - timedelta(minutes=int(matched.group(1)))
    matched = re.match(r'(\d+)\s*小时前', compact)
    if matched:
        return current - timedelta(hours=int(matched.group(1)))
    matched = re.match(r'(\d+)\s*天前', compact)
    if matched:
        return current - timedelta(days=int(matched.group(1)))
    matched = re.match(r'昨天(?:\s+(\d{1,2}):(\d{2}))?', compact)
    if matched:
        hour = int(matched.group(1) or 12)
        minute = int(matched.group(2) or 0)
        return (current - timedelta(days=1)).replace(hour=hour, minute=minute, second=0, microsecond=0)
    matched = re.match(r'前天(?:\s+(\d{1,2}):(\d{2}))?', compact)
    if matched:
        hour = int(matched.group(1) or 12)
        minute = int(matched.group(2) or 0)
        return (current - timedelta(days=2)).replace(hour=hour, minute=minute, second=0, microsecond=0)
    if compact in {'刚刚', '刚刚发布'}:
        return current
    return None


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
            'search_url_template': self.settings.xhs_search_url_template,
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
        max_posts = min(max(_safe_int(getattr(payload, 'max_posts_per_account', 60), 60), 1), self.settings.xhs_max_posts_per_account)
        date_from, date_to = _resolve_post_date_window(payload)

        async with async_playwright() as playwright:
            launch_kwargs = {'headless': self.settings.playwright_headless}
            if self.settings.playwright_headless:
                launch_kwargs['headless'] = True
                launch_kwargs['args'] = ['--headless=new', '--disable-crashpad', '--disable-crash-reporter', '--disable-breakpad']
            temp_home = tempfile.mkdtemp(prefix='xhs-pw-home-')
            launch_kwargs['env'] = {
                **os.environ,
                'HOME': temp_home,
                'TMPDIR': temp_home,
                'XDG_CONFIG_HOME': temp_home,
                'XDG_CACHE_HOME': temp_home,
            }
            if self.settings.playwright_browser_channel:
                launch_kwargs['channel'] = self.settings.playwright_browser_channel
            browser = await playwright.chromium.launch(**launch_kwargs)
            context_kwargs = {}
            storage_path = self.settings.playwright_storage_state_path
            if storage_path and os.path.exists(storage_path):
                context_kwargs['storage_state'] = storage_path
            context = await browser.new_context(**context_kwargs)
            try:
                for target in payload.targets:
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
                        max_posts=max_posts,
                        date_from=date_from,
                        date_to=date_to,
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
                'current_month_only': bool(getattr(payload, 'current_month_only', False)),
                'date_from': getattr(payload, 'date_from', ''),
                'date_to': getattr(payload, 'date_to', ''),
            },
        }

    async def fetch_trends(self, payload):
        try:
            from playwright.async_api import TimeoutError as PlaywrightTimeoutError, async_playwright
        except ImportError as exc:
            raise RuntimeError('未安装 Playwright，请先在 crawler_service 环境执行 playwright install') from exc

        keywords = [str(item or '').strip() for item in getattr(payload, 'keywords', []) if str(item or '').strip()]
        if not keywords:
            keywords = ['脂肪肝']
        trend_type = (getattr(payload, 'trend_type', 'note_search') or 'note_search').strip().lower() or 'note_search'
        page_size = min(max(_safe_int(getattr(payload, 'page_size', 20), 20), 1), 50)
        max_related_queries = min(max(_safe_int(getattr(payload, 'max_related_queries', 20), 20), 1), 50)
        source_channel = getattr(payload, 'source_channel', '') or 'playwright_xhs'
        date_from = _parse_date_boundary(getattr(payload, 'date_from', ''), start=True)
        date_to = _parse_date_boundary(getattr(payload, 'date_to', ''), start=False)

        async with async_playwright() as playwright:
            launch_kwargs = {'headless': self.settings.playwright_headless}
            if self.settings.playwright_headless:
                launch_kwargs['headless'] = True
                launch_kwargs['args'] = ['--headless=new', '--disable-crashpad', '--disable-crash-reporter', '--disable-breakpad']
            temp_home = tempfile.mkdtemp(prefix='xhs-pw-home-')
            launch_kwargs['env'] = {
                **os.environ,
                'HOME': temp_home,
                'TMPDIR': temp_home,
                'XDG_CONFIG_HOME': temp_home,
                'XDG_CACHE_HOME': temp_home,
            }
            if self.settings.playwright_browser_channel:
                launch_kwargs['channel'] = self.settings.playwright_browser_channel
            browser = await playwright.chromium.launch(**launch_kwargs)
            context_kwargs = {}
            storage_path = self.settings.playwright_storage_state_path
            if storage_path and os.path.exists(storage_path):
                context_kwargs['storage_state'] = storage_path
            context = await browser.new_context(**context_kwargs)
            try:
                if trend_type == 'hot_queries':
                    items = await self._extract_hot_queries(
                        context=context,
                        keywords=keywords,
                        source_channel=source_channel,
                        max_related_queries=max_related_queries,
                    )
                else:
                    items = await self._extract_search_notes(
                        context=context,
                        keywords=keywords,
                        source_channel=source_channel,
                        page_size=page_size,
                        date_from=date_from,
                        date_to=date_to,
                    )
            except PlaywrightTimeoutError as exc:
                raise RuntimeError(f'打开小红书搜索页超时：{exc}') from exc
            finally:
                await context.close()
                await browser.close()

        return {
            'success': True,
            'provider': 'playwright_xhs',
            'batch_name': getattr(payload, 'batch_name', ''),
            'source_channel': source_channel,
            'trend_type': trend_type,
            'items': items,
            'meta': {
                'keyword_count': len(keywords),
                'item_count': len(items),
                'trend_type': trend_type,
                'date_from': getattr(payload, 'date_from', ''),
                'date_to': getattr(payload, 'date_to', ''),
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

    async def _read_page_state(self, page):
        candidate_expressions = [
            'window.__INITIAL_STATE__',
            'window.__INITIAL_SSR_STATE__',
            'window.__INITIAL_DATA__',
            'window.__REDUX_STATE__',
        ]
        for expression in candidate_expressions:
            try:
                value = await page.evaluate(f'() => {expression} || null')
            except Exception:
                value = None
            if isinstance(value, (dict, list)) and value:
                return value
        return {}

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

    async def _extract_author(self, card):
        for selector in _selector_candidates(self.settings.xhs_post_author_selector, DEFAULT_POST_AUTHOR_SELECTORS):
            text = await self._read_text(card, selector)
            if text:
                return text
        return ''

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

    async def _extract_posts(self, page, target, profile_url, account_handle, source_channel, max_posts=20, date_from=None, date_to=None):
        rows = []
        seen_urls = set()
        reached_older_posts = False
        previous_seen_count = -1
        for _ in range(8):
            cards = await self._candidate_cards(page)
            for card in cards:
                post_url = await self._extract_post_url(card)
                if not post_url or post_url in seen_urls:
                    continue
                seen_urls.add(post_url)
                publish_time_text = await self._extract_publish_time(card)
                publish_time_dt = _parse_publish_time_value(publish_time_text)
                if date_from and publish_time_dt and publish_time_dt < date_from:
                    reached_older_posts = True
                    continue
                if date_to and publish_time_dt and publish_time_dt > date_to:
                    continue
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
                    'publish_time': publish_time_dt.strftime('%Y-%m-%d %H:%M:%S') if publish_time_dt else publish_time_text,
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
                if len(rows) >= max_posts:
                    return rows
            current_seen_count = len(seen_urls)
            if reached_older_posts or current_seen_count == previous_seen_count:
                break
            previous_seen_count = current_seen_count
            await page.mouse.wheel(0, 2400)
            await page.wait_for_timeout(1200)
        return rows

    def _build_search_url(self, keyword):
        safe_keyword = quote((keyword or '').strip())
        template = self.settings.xhs_search_url_template or 'https://www.xiaohongshu.com/search_result?keyword={keyword}&source=web_explore_feed'
        return template.format(keyword=safe_keyword)

    async def _open_search_page(self, context, keyword):
        page = await context.new_page()
        await page.goto(
            self._build_search_url(keyword),
            wait_until='domcontentloaded',
            timeout=self.settings.playwright_navigation_timeout_ms,
        )
        await page.wait_for_load_state('networkidle', timeout=self.settings.playwright_navigation_timeout_ms)
        return page

    async def _extract_search_notes(self, context, keywords, source_channel, page_size=20, date_from=None, date_to=None):
        items = []
        seen_urls = set()
        for keyword in keywords:
            page = await self._open_search_page(context, keyword)
            try:
                state_items = await self._extract_search_notes_from_state(
                    page=page,
                    keyword=keyword,
                    source_channel=source_channel,
                    page_size=page_size,
                    date_from=date_from,
                    date_to=date_to,
                )
                for item in state_items:
                    item_url = item.get('link') or ''
                    if item_url and item_url in seen_urls:
                        continue
                    if item_url:
                        seen_urls.add(item_url)
                    items.append(item)
                    if len(items) >= page_size:
                        return items[:page_size]

                previous_seen_count = -1
                reached_limit = False
                reached_older_posts = False
                for _ in range(8):
                    cards = await self._candidate_cards(page)
                    for card in cards:
                        post_url = await self._extract_post_url(card)
                        if not post_url or post_url in seen_urls:
                            continue
                        seen_urls.add(post_url)
                        publish_time_text = await self._extract_publish_time(card)
                        publish_time_dt = _parse_publish_time_value(publish_time_text)
                        if date_from and publish_time_dt and publish_time_dt < date_from:
                            reached_older_posts = True
                            continue
                        if date_to and publish_time_dt and publish_time_dt > date_to:
                            continue
                        title = await self._extract_title(card)
                        if not title:
                            continue
                        rank = len(items) + 1
                        likes = await self._extract_metric(card, self.settings.xhs_post_likes_selector, DEFAULT_POST_LIKES_SELECTORS, '点赞')
                        favorites = await self._extract_metric(card, self.settings.xhs_post_favorites_selector, DEFAULT_POST_FAVORITES_SELECTORS, '收藏')
                        comments = await self._extract_metric(card, self.settings.xhs_post_comments_selector, DEFAULT_POST_COMMENTS_SELECTORS, '评论')
                        views = await self._extract_metric(card, self.settings.xhs_post_views_selector, DEFAULT_POST_VIEWS_SELECTORS, '浏览|阅读')
                        items.append({
                            'keyword': keyword,
                            'query': keyword,
                            'title': title,
                            'link': post_url,
                            'author': await self._extract_author(card),
                            'summary': re.sub(r'\s+', ' ', (await card.text_content() or '').strip())[:120],
                            'hot_value': views + likes * 3 + favorites * 4 + comments * 5 + max(0, 100 - rank * 3),
                            'rank': rank,
                            'views': views,
                            'likes': likes,
                            'favorites': favorites,
                            'comments': comments,
                            'publish_time': publish_time_dt.strftime('%Y-%m-%d %H:%M:%S') if publish_time_dt else publish_time_text,
                            'source_channel': source_channel,
                        })
                        if len(items) >= page_size:
                            reached_limit = True
                            break
                    if reached_limit or reached_older_posts:
                        break
                    current_seen_count = len(seen_urls)
                    if current_seen_count == previous_seen_count:
                        break
                    previous_seen_count = current_seen_count
                    await page.mouse.wheel(0, 2400)
                    await page.wait_for_timeout(1200)
                if len(items) >= page_size:
                    break
            finally:
                await page.close()
        return items[:page_size]

    async def _extract_hot_queries(self, context, keywords, source_channel, max_related_queries=20):
        items = []
        seen_queries = set()
        for keyword in keywords:
            page = await self._open_search_page(context, keyword)
            try:
                state_items = await self._extract_hot_queries_from_state(
                    page=page,
                    keyword=keyword,
                    source_channel=source_channel,
                    max_related_queries=max_related_queries,
                )
                for item in state_items:
                    query = item.get('query') or ''
                    if query and query in seen_queries:
                        continue
                    if query:
                        seen_queries.add(query)
                    items.append(item)
                    if len(items) >= max_related_queries:
                        return items[:max_related_queries]

                found_any = False
                selectors = _selector_candidates(
                    self.settings.xhs_search_related_query_selector,
                    DEFAULT_SEARCH_RELATED_QUERY_SELECTORS,
                )
                for selector in selectors:
                    locator = page.locator(selector)
                    try:
                        count = await locator.count()
                    except Exception:
                        continue
                    for index in range(min(count, max_related_queries * 2)):
                        text = (await locator.nth(index).text_content() or '').strip()
                        text = re.sub(r'\s+', ' ', text)
                        if not text or len(text) > 24 or text in seen_queries:
                            continue
                        seen_queries.add(text)
                        found_any = True
                        rank = len(items) + 1
                        items.append({
                            'keyword': keyword,
                            'query': text,
                            'title': text,
                            'summary': f'由小红书搜索页相关搜索词提取，原始关键词：{keyword}',
                            'hot_value': max(0, 10000 - rank * 131),
                            'rank': rank,
                            'source_channel': source_channel,
                        })
                        if len(items) >= max_related_queries:
                            return items
                if not found_any and keyword not in seen_queries:
                    seen_queries.add(keyword)
                    rank = len(items) + 1
                    items.append({
                        'keyword': keyword,
                        'query': keyword,
                        'title': keyword,
                        'summary': '未解析到相关热搜词，先回退为输入关键词，便于联调热点链路。',
                        'hot_value': max(0, 10000 - rank * 131),
                        'rank': rank,
                        'source_channel': source_channel,
                    })
                    if len(items) >= max_related_queries:
                        return items
            finally:
                await page.close()
        return items[:max_related_queries]

    async def _extract_search_notes_from_state(self, page, keyword, source_channel, page_size=20, date_from=None, date_to=None):
        state = await self._read_page_state(page)
        if not state:
            return []
        feed_list = _find_state_list(
            state,
            SEARCH_STATE_CANDIDATE_PATHS,
            lambda rows: any(_looks_like_search_feed_item(item) for item in rows),
        )
        if not feed_list:
            feed_list = [item for item in _walk_dicts(state) if _looks_like_search_feed_item(item)]
        items = []
        seen_urls = set()
        for feed in feed_list:
            normalized = _normalize_search_feed_item(feed, keyword, source_channel, len(items) + 1)
            if not normalized:
                continue
            publish_time_dt = _parse_publish_time_value(normalized.get('publish_time') or '')
            if date_from and publish_time_dt and publish_time_dt < date_from:
                continue
            if date_to and publish_time_dt and publish_time_dt > date_to:
                continue
            post_url = normalized.get('link') or ''
            if post_url and post_url in seen_urls:
                continue
            if post_url:
                seen_urls.add(post_url)
            items.append(normalized)
            if len(items) >= page_size:
                break
        return items

    async def _extract_hot_queries_from_state(self, page, keyword, source_channel, max_related_queries=20):
        state = await self._read_page_state(page)
        if not state:
            return []
        related_list = _find_state_list(
            state,
            RELATED_QUERY_STATE_CANDIDATE_PATHS,
            lambda rows: bool(rows),
        )
        if not related_list:
            return []
        items = []
        seen_queries = set()
        for raw_item in related_list:
            normalized = _normalize_related_query_item(raw_item, keyword, source_channel, len(items) + 1)
            query = normalized.get('query') if normalized else ''
            if not query or query in seen_queries:
                continue
            seen_queries.add(query)
            items.append(normalized)
            if len(items) >= max_related_queries:
                break
        return items
