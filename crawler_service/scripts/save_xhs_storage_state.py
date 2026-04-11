import asyncio
import os
from pathlib import Path

from crawler_service.config import get_settings


async def main():
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise SystemExit('Playwright 未安装，请先执行 crawler_service/scripts/bootstrap_venv.sh') from exc

    settings = get_settings()
    default_output = Path(settings.playwright_storage_state_path or '.state/xhs_storage_state.json')
    output_path = Path(os.environ.get('PLAYWRIGHT_STORAGE_STATE_OUTPUT') or default_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    login_url = os.environ.get('XHS_LOGIN_URL') or 'https://www.xiaohongshu.com'
    print(f'即将打开浏览器，请在页面中完成登录：{login_url}')
    print(f'登录完成后，回到终端按回车，保存 storage state 到 {output_path}')

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=False,
            channel=settings.playwright_browser_channel or None,
        )
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(login_url, wait_until='domcontentloaded', timeout=settings.playwright_navigation_timeout_ms)
        await page.wait_for_load_state('networkidle', timeout=settings.playwright_navigation_timeout_ms)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, input, '')

        await context.storage_state(path=str(output_path))
        print(f'storage state 已保存：{output_path}')
        await context.close()
        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
