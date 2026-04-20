import asyncio
import json
import os
import sys
from pathlib import Path


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def _env_flag(name, default=False):
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {'1', 'true', 'yes', 'y', 'on'}


async def main():
    from crawler_service.config import get_settings
    from crawler_service.probe_diagnostics import build_bundle_diagnosis
    from crawler_service.providers import build_provider
    from crawler_service.schemas import AccountPostsRequest, SyncTarget, TrendQueryRequest

    settings = get_settings()
    provider = build_provider(settings)
    health = await provider.healthcheck()
    if settings.provider == 'playwright_xhs' and not health.get('storage_state_exists'):
        raise SystemExit(
            f"当前 provider=playwright_xhs，但未找到登录态文件：{health.get('storage_state_path') or '-'}\n"
            "请先执行 crawler_service/scripts/save_xhs_storage_state.py 保存登录态。"
        )

    output_dir = Path(settings.xhs_debug_output_dir or '/tmp/xhs_crawler_debug')
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        'provider': settings.provider,
        'health': health,
        'metric_support': {
            'account_views': health.get('supports_account_views'),
            'account_exposures': health.get('supports_account_exposures'),
            'trend_views': health.get('supports_trend_views'),
            'trend_hot_value': health.get('supports_trend_hot_value'),
        },
        'trends': {'enabled': False, 'skipped': True},
        'account_posts': {'enabled': False, 'skipped': True},
    }

    if _env_flag('XHS_PROBE_ENABLE_TRENDS', True):
        raw_keywords = (os.environ.get('XHS_PROBE_KEYWORDS') or os.environ.get('XHS_DEBUG_SEARCH_KEYWORD') or '脂肪肝').strip()
        keywords = [item.strip() for item in raw_keywords.replace('，', ',').split(',') if item.strip()]
        trend_type = (os.environ.get('XHS_PROBE_TREND_TYPE') or 'note_search').strip().lower() or 'note_search'
        page_size = int((os.environ.get('XHS_PROBE_PAGE_SIZE') or '10').strip() or '10')
        max_related_queries = int((os.environ.get('XHS_PROBE_MAX_RELATED_QUERIES') or '10').strip() or '10')
        source_channel = (os.environ.get('XHS_PROBE_SOURCE_CHANNEL') or 'probe_bundle').strip() or 'probe_bundle'
        batch_name = (os.environ.get('XHS_PROBE_BATCH_NAME') or f'probe_bundle_{trend_type}').strip()
        date_from = (os.environ.get('XHS_PROBE_DATE_FROM') or '').strip()
        date_to = (os.environ.get('XHS_PROBE_DATE_TO') or '').strip()

        trend_payload = TrendQueryRequest(
            keywords=keywords,
            trend_type=trend_type,
            page_size=page_size,
            max_related_queries=max_related_queries,
            source_channel=source_channel,
            batch_name=batch_name,
            date_from=date_from,
            date_to=date_to,
        )
        trend_result = await provider.fetch_trends(trend_payload)
        trend_output_path = output_dir / f'xhs_bundle_trends_{trend_type}.json'
        trend_output_path.write_text(json.dumps(trend_result, ensure_ascii=False, indent=2), encoding='utf-8')
        summary['trends'] = {
            'enabled': True,
            'skipped': False,
            'trend_type': trend_type,
            'keyword_count': len(keywords),
            'item_count': len(trend_result.get('items') or []),
            'output_path': str(trend_output_path),
            'sample_items': (trend_result.get('items') or [])[:5],
        }

    profile_url = (os.environ.get('XHS_PROBE_PROFILE_URL') or '').strip()
    account_handle = (os.environ.get('XHS_PROBE_ACCOUNT_HANDLE') or '').strip()
    if _env_flag('XHS_PROBE_ENABLE_ACCOUNT', True) and (profile_url or account_handle):
        owner_name = (os.environ.get('XHS_PROBE_OWNER_NAME') or '测试账号').strip()
        owner_phone = (os.environ.get('XHS_PROBE_OWNER_PHONE') or '13800000000').strip()
        source_channel = (os.environ.get('XHS_PROBE_SOURCE_CHANNEL') or 'probe_bundle').strip() or 'probe_bundle'
        batch_name = (os.environ.get('XHS_PROBE_BATCH_NAME') or 'probe_bundle_account_posts').strip()
        current_month_only = _env_flag('XHS_PROBE_CURRENT_MONTH_ONLY', True)
        date_from = (os.environ.get('XHS_PROBE_DATE_FROM') or '').strip()
        date_to = (os.environ.get('XHS_PROBE_DATE_TO') or '').strip()
        max_posts_per_account = int((os.environ.get('XHS_PROBE_MAX_POSTS_PER_ACCOUNT') or '10').strip() or '10')

        account_payload = AccountPostsRequest(
            targets=[
                SyncTarget(
                    profile_url=profile_url,
                    account_handle=account_handle,
                    owner_name=owner_name,
                    owner_phone=owner_phone,
                )
            ],
            batch_name=batch_name,
            source_channel=source_channel,
            current_month_only=current_month_only,
            date_from=date_from,
            date_to=date_to,
            max_posts_per_account=max_posts_per_account,
        )
        account_result = await provider.fetch_account_posts(account_payload)
        account_output_path = output_dir / 'xhs_bundle_account_posts.json'
        account_output_path.write_text(json.dumps(account_result, ensure_ascii=False, indent=2), encoding='utf-8')
        summary['account_posts'] = {
            'enabled': True,
            'skipped': False,
            'target': {
                'profile_url': profile_url,
                'account_handle': account_handle,
            },
            'account_count': len(account_result.get('accounts') or []),
            'post_count': len(account_result.get('posts') or []),
            'snapshot_count': len(account_result.get('snapshots') or []),
            'output_path': str(account_output_path),
            'sample_account': (account_result.get('accounts') or [])[:1],
            'sample_posts': (account_result.get('posts') or [])[:5],
        }

    bundle_output_path = output_dir / 'xhs_probe_bundle.json'
    summary['diagnosis'] = build_bundle_diagnosis(summary)
    bundle_output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    summary['output_path'] = str(bundle_output_path)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
