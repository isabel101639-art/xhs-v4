import asyncio
import json
import os
import sys
from pathlib import Path


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def _has_login_prompt(text):
    compact = (text or '').strip()
    prompts = ['登录', '注册', '立即登录', '验证码登录', '手机号登录']
    return any(token in compact for token in prompts)


async def main():
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise SystemExit('Playwright 未安装，请先执行 crawler_service/scripts/bootstrap_venv.sh') from exc

    from crawler_service.config import get_settings
    from crawler_service.providers.playwright_xhs import PlaywrightXHSCrawlerProvider

    settings = get_settings()
    storage_state_path = Path(settings.playwright_storage_state_path)
    if not storage_state_path.exists():
        raise SystemExit(
            f'未找到登录态文件：{storage_state_path}\n'
            '请先执行 crawler_service/scripts/save_xhs_storage_state.py 保存登录态。'
        )

    verify_keyword = (os.environ.get('XHS_VERIFY_KEYWORD') or '脂肪肝').strip() or '脂肪肝'
    provider = PlaywrightXHSCrawlerProvider(settings)
    output_dir = Path(settings.xhs_debug_output_dir or '/tmp/xhs_crawler_debug')
    output_dir.mkdir(parents=True, exist_ok=True)

    home_screenshot_path = output_dir / 'xhs_login_verify_home.png'
    search_screenshot_path = output_dir / 'xhs_login_verify_search.png'
    output_path = output_dir / 'xhs_login_verify.json'

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=settings.playwright_headless,
            channel=settings.playwright_browser_channel or None,
        )
        context = await browser.new_context(storage_state=str(storage_state_path))
        try:
            home_page = await context.new_page()
            await home_page.goto('https://www.xiaohongshu.com', wait_until='domcontentloaded', timeout=settings.playwright_navigation_timeout_ms)
            await home_page.wait_for_load_state('networkidle', timeout=settings.playwright_navigation_timeout_ms)
            home_body = (await home_page.locator('body').text_content() or '').strip()
            await home_page.screenshot(path=str(home_screenshot_path), full_page=True)

            search_page = await provider._open_search_page(context, verify_keyword)
            search_body = (await search_page.locator('body').text_content() or '').strip()
            await search_page.screenshot(path=str(search_screenshot_path), full_page=True)
            search_state = await provider._read_page_state(search_page)
            search_notes = await provider._extract_search_notes_from_state(
                page=search_page,
                keyword=verify_keyword,
                source_channel='verify_login_state',
                page_size=5,
            )
            related_queries = await provider._extract_hot_queries_from_state(
                page=search_page,
                keyword=verify_keyword,
                source_channel='verify_login_state',
                max_related_queries=5,
            )

            cookies = await context.cookies()
            xhs_cookies = [item for item in cookies if 'xiaohongshu.com' in (item.get('domain') or '')]
            result = {
                'storage_state_path': str(storage_state_path),
                'storage_state_exists': True,
                'provider': settings.provider,
                'verify_keyword': verify_keyword,
                'cookie_count': len(cookies),
                'xhs_cookie_count': len(xhs_cookies),
                'home': {
                    'url': home_page.url,
                    'title': await home_page.title(),
                    'login_prompt_detected': _has_login_prompt(home_body[:5000]),
                    'body_preview': home_body[:1200],
                    'screenshot_path': str(home_screenshot_path),
                },
                'search': {
                    'url': search_page.url,
                    'title': await search_page.title(),
                    'login_prompt_detected': _has_login_prompt(search_body[:5000]),
                    'state_available': bool(search_state),
                    'state_top_keys': sorted(list(search_state.keys()))[:20] if isinstance(search_state, dict) else [],
                    'state_note_count': len(search_notes),
                    'state_related_query_count': len(related_queries),
                    'sample_notes': search_notes[:3],
                    'sample_related_queries': related_queries[:3],
                    'screenshot_path': str(search_screenshot_path),
                },
            }
            result['login_state_likely_valid'] = bool(
                result['xhs_cookie_count'] > 0 and
                not result['home']['login_prompt_detected'] and
                not result['search']['login_prompt_detected']
            )
            output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps(result, ensure_ascii=False, indent=2))

            await search_page.close()
            await home_page.close()
        finally:
            await context.close()
            await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
