import asyncio
import json
import os
from pathlib import Path

from crawler_service.config import get_settings
from crawler_service.providers.playwright_xhs import PlaywrightXHSCrawlerProvider


async def main():
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise SystemExit('Playwright 未安装，请先执行 crawler_service/scripts/bootstrap_venv.sh') from exc

    keyword = (os.environ.get('XHS_DEBUG_SEARCH_KEYWORD') or '').strip()
    if not keyword:
        raise SystemExit('请先设置 XHS_DEBUG_SEARCH_KEYWORD')

    settings = get_settings()
    provider = PlaywrightXHSCrawlerProvider(settings)
    output_dir = Path(settings.xhs_debug_output_dir or '/tmp/xhs_crawler_debug')
    output_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = output_dir / 'xhs_search_debug.png'
    html_path = output_dir / 'xhs_search_debug.html'
    meta_path = output_dir / 'xhs_search_debug.json'

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=settings.playwright_headless,
            channel=settings.playwright_browser_channel or None,
        )
        context_kwargs = {}
        if settings.playwright_storage_state_path and os.path.exists(settings.playwright_storage_state_path):
            context_kwargs['storage_state'] = settings.playwright_storage_state_path
        context = await browser.new_context(**context_kwargs)
        page = await provider._open_search_page(context, keyword)

        try:
            state = await provider._read_page_state(page)
            state_note_items = await provider._extract_search_notes_from_state(
                page=page,
                keyword=keyword,
                source_channel='debug_search',
                page_size=10,
            )
            state_hot_queries = await provider._extract_hot_queries_from_state(
                page=page,
                keyword=keyword,
                source_channel='debug_search',
                max_related_queries=10,
            )

            await page.screenshot(path=str(screenshot_path), full_page=True)
            html_path.write_text(await page.content(), encoding='utf-8')

            meta = {
                'title': await page.title(),
                'url': page.url,
                'keyword': keyword,
                'state_available': bool(state),
                'state_top_keys': sorted(list(state.keys()))[:20] if isinstance(state, dict) else [],
                'state_note_items': state_note_items[:5],
                'state_hot_queries': state_hot_queries[:10],
                'screenshot_path': str(screenshot_path),
                'html_path': str(html_path),
            }
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps(meta, ensure_ascii=False, indent=2))
        finally:
            await page.close()
            await context.close()
            await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
