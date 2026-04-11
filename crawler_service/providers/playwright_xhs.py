import os
import re
from datetime import datetime

from crawler_service.providers.base import BaseCrawlerProvider


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_count(text):
    raw = (text or '').strip().lower().replace(',', '')
    if not raw:
        return 0
    raw = raw.replace('点赞', '').replace('收藏', '').replace('评论', '').replace('浏览', '').strip()
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
            'post_card_selector_configured': bool(self.settings.xhs_post_card_selector),
        }

    async def fetch_account_posts(self, payload):
        try:
            from playwright.async_api import TimeoutError as PlaywrightTimeoutError, async_playwright
        except ImportError as exc:
            raise RuntimeError('未安装 Playwright，请先在 crawler_service 环境执行 playwright install') from exc

        if not self.settings.xhs_post_card_selector:
            raise RuntimeError('请先配置 XHS_POST_CARD_SELECTOR 等抓取选择器，再启用 playwright_xhs provider')

        accounts = []
        posts = []
        snapshots = []

        async with async_playwright() as playwright:
            launch_kwargs = {
                'headless': self.settings.playwright_headless,
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

                    display_name = await self._read_text(page, self.settings.xhs_profile_name_selector) or target.owner_name or account_handle
                    follower_count = _parse_count(await self._read_text(page, self.settings.xhs_follower_count_selector))
                    account_row = {
                        'platform': 'xhs',
                        'owner_name': target.owner_name or '',
                        'owner_phone': target.owner_phone or '',
                        'account_handle': account_handle or display_name,
                        'display_name': display_name or account_handle,
                        'profile_url': profile_url,
                        'follower_count': follower_count,
                        'source_channel': payload.source_channel or 'playwright_xhs',
                        'notes': '由 Playwright 抓取账号主页返回',
                    }
                    accounts.append(account_row)

                    post_rows = await self._extract_posts(page, target, profile_url, account_row['account_handle'], payload.source_channel or 'playwright_xhs')
                    posts.extend(post_rows)
                    snapshots.append({
                        'platform': 'xhs',
                        'account_handle': account_row['account_handle'],
                        'owner_phone': target.owner_phone or '',
                        'owner_name': target.owner_name or '',
                        'profile_url': profile_url,
                        'snapshot_date': datetime.now().strftime('%Y-%m-%d'),
                        'follower_count': follower_count,
                        'post_count': len(post_rows),
                        'total_views': sum(item.get('views', 0) for item in post_rows),
                        'total_interactions': sum(
                            (item.get('likes', 0) or 0) + (item.get('favorites', 0) or 0) + (item.get('comments', 0) or 0)
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

    async def _read_text(self, page_or_locator, selector):
        current_selector = (selector or '').strip()
        if not current_selector:
            return ''
        locator = page_or_locator.locator(current_selector)
        if await locator.count() == 0:
            return ''
        text = await locator.first.text_content()
        return (text or '').strip()

    async def _read_attr(self, page_or_locator, selector, attr_name):
        current_selector = (selector or '').strip()
        if not current_selector:
            return ''
        locator = page_or_locator.locator(current_selector)
        if await locator.count() == 0:
            return ''
        value = await locator.first.get_attribute(attr_name)
        return (value or '').strip()

    async def _extract_posts(self, page, target, profile_url, account_handle, source_channel):
        cards = page.locator(self.settings.xhs_post_card_selector)
        post_count = min(await cards.count(), self.settings.xhs_max_posts_per_account)
        rows = []
        for index in range(post_count):
            card = cards.nth(index)
            post_url = await self._read_attr(card, self.settings.xhs_post_link_selector, 'href')
            if post_url and post_url.startswith('/'):
                post_url = f'https://www.xiaohongshu.com{post_url}'
            title = await self._read_text(card, self.settings.xhs_post_title_selector)
            if not title and not post_url:
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
                'platform_post_id': (post_url.rstrip('/').split('/')[-1] if post_url else ''),
                'title': title or f'未命名笔记 {index + 1}',
                'post_url': post_url,
                'publish_time': await self._read_text(card, self.settings.xhs_post_time_selector),
                'topic_title': '',
                'views': _parse_count(await self._read_text(card, self.settings.xhs_post_views_selector)),
                'exposures': 0,
                'likes': _parse_count(await self._read_text(card, self.settings.xhs_post_likes_selector)),
                'favorites': _parse_count(await self._read_text(card, self.settings.xhs_post_favorites_selector)),
                'comments': _parse_count(await self._read_text(card, self.settings.xhs_post_comments_selector)),
                'shares': 0,
                'follower_delta': 0,
                'source_channel': source_channel,
            })
        return rows
