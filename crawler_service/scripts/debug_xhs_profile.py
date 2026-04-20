import asyncio
import json
import os
from pathlib import Path

from crawler_service.config import get_settings
from crawler_service.providers.playwright_xhs import (
    DEFAULT_FOLLOWER_COUNT_SELECTORS,
    DEFAULT_POST_CARD_SELECTORS,
    DEFAULT_POST_TITLE_SELECTORS,
    DEFAULT_PROFILE_NAME_SELECTORS,
    PlaywrightXHSCrawlerProvider,
    _collect_metric_candidates,
)


async def main():
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise SystemExit('Playwright 未安装，请先执行 crawler_service/scripts/bootstrap_venv.sh') from exc

    target_url = (os.environ.get('XHS_DEBUG_PROFILE_URL') or '').strip()
    if not target_url:
        raise SystemExit('请先设置 XHS_DEBUG_PROFILE_URL')

    settings = get_settings()
    provider = PlaywrightXHSCrawlerProvider(settings)
    output_dir = Path(settings.xhs_debug_output_dir or '/tmp/xhs_crawler_debug')
    output_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = output_dir / 'xhs_profile_debug.png'
    html_path = output_dir / 'xhs_profile_debug.html'
    meta_path = output_dir / 'xhs_profile_debug.json'

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=settings.playwright_headless,
            channel=settings.playwright_browser_channel or None,
        )
        context_kwargs = {}
        if settings.playwright_storage_state_path and os.path.exists(settings.playwright_storage_state_path):
            context_kwargs['storage_state'] = settings.playwright_storage_state_path
        context = await browser.new_context(**context_kwargs)
        page = await context.new_page()
        await page.goto(target_url, wait_until='domcontentloaded', timeout=settings.playwright_navigation_timeout_ms)
        await page.wait_for_load_state('networkidle', timeout=settings.playwright_navigation_timeout_ms)
        await page.screenshot(path=str(screenshot_path), full_page=True)
        html_path.write_text(await page.content(), encoding='utf-8')

        body_text = (await page.locator('body').text_content() or '').strip()
        state = await provider._read_page_state(page)
        state_posts = await provider._extract_profile_posts_from_state(
            page=page,
            target=type('Target', (), {
                'owner_phone': '',
                'owner_name': '',
                'registration_id': 0,
                'topic_id': 0,
                'submission_id': 0,
            })(),
            profile_url=target_url,
            account_handle='',
            source_channel='debug_profile',
            max_posts=5,
        )
        meta = {
            'title': await page.title(),
            'url': page.url,
            'display_name': await provider._extract_display_name(page, '', ''),
            'follower_count': await provider._extract_follower_count(page),
            'state_available': bool(state),
            'state_top_keys': sorted(list(state.keys()))[:20] if isinstance(state, dict) else [],
            'state_metric_candidates': _collect_metric_candidates(
                state,
                include_tokens=['view', 'read', 'impression', 'exposure', 'expo', 'reach'],
                exclude_tokens=['like', 'comment', 'collect', 'favor', 'share'],
                limit=30,
            ),
            'state_posts': state_posts[:5],
            'state_post_metric_sources': [item.get('metric_sources') or {} for item in state_posts[:5]],
            'profile_name_candidates': await _selector_counts(page, DEFAULT_PROFILE_NAME_SELECTORS),
            'follower_count_candidates': await _selector_counts(page, DEFAULT_FOLLOWER_COUNT_SELECTORS),
            'post_card_candidates': await _selector_counts(page, DEFAULT_POST_CARD_SELECTORS),
            'post_title_candidates': await _selector_counts(page, DEFAULT_POST_TITLE_SELECTORS),
            'body_preview': body_text[:2000],
            'screenshot_path': str(screenshot_path),
            'html_path': str(html_path),
        }
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(meta, ensure_ascii=False, indent=2))

        await context.close()
        await browser.close()


async def _selector_counts(page, selectors):
    results = []
    for selector in selectors:
        locator = page.locator(selector)
        try:
            count = await locator.count()
        except Exception as exc:
            count = f'error: {exc}'
        results.append({'selector': selector, 'count': count})
    return results


if __name__ == '__main__':
    asyncio.run(main())
