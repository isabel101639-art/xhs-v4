import asyncio
import json
import os
import sys
from pathlib import Path


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


async def main():
    from crawler_service.config import get_settings
    from crawler_service.providers import build_provider
    from crawler_service.schemas import TrendQueryRequest

    settings = get_settings()
    provider = build_provider(settings)
    health = await provider.healthcheck()
    if settings.provider == 'playwright_xhs' and not health.get('storage_state_exists'):
        raise SystemExit(
            f"当前 provider=playwright_xhs，但未找到登录态文件：{health.get('storage_state_path') or '-'}\n"
            "请先执行 crawler_service/scripts/save_xhs_storage_state.py 保存登录态。"
        )

    raw_keywords = (os.environ.get('XHS_PROBE_KEYWORDS') or os.environ.get('XHS_DEBUG_SEARCH_KEYWORD') or '脂肪肝').strip()
    keywords = [item.strip() for item in raw_keywords.replace('，', ',').split(',') if item.strip()]
    trend_type = (os.environ.get('XHS_PROBE_TREND_TYPE') or 'note_search').strip().lower() or 'note_search'
    page_size = int((os.environ.get('XHS_PROBE_PAGE_SIZE') or '10').strip() or '10')
    max_related_queries = int((os.environ.get('XHS_PROBE_MAX_RELATED_QUERIES') or '10').strip() or '10')
    source_channel = (os.environ.get('XHS_PROBE_SOURCE_CHANNEL') or 'probe_script').strip() or 'probe_script'
    batch_name = (os.environ.get('XHS_PROBE_BATCH_NAME') or f'probe_{trend_type}').strip()
    date_from = (os.environ.get('XHS_PROBE_DATE_FROM') or '').strip()
    date_to = (os.environ.get('XHS_PROBE_DATE_TO') or '').strip()

    payload = TrendQueryRequest(
        keywords=keywords,
        trend_type=trend_type,
        page_size=page_size,
        max_related_queries=max_related_queries,
        source_channel=source_channel,
        batch_name=batch_name,
        date_from=date_from,
        date_to=date_to,
    )

    result = await provider.fetch_trends(payload)
    output_dir = Path(settings.xhs_debug_output_dir or '/tmp/xhs_crawler_debug')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f'xhs_trends_probe_{trend_type}.json'
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')

    print(json.dumps({
        'provider': settings.provider,
        'health': health,
        'trend_type': trend_type,
        'keyword_count': len(keywords),
        'item_count': len(result.get('items') or []),
        'output_path': str(output_path),
        'sample_items': (result.get('items') or [])[:5],
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
