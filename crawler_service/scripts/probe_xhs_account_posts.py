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
    from crawler_service.schemas import AccountPostsRequest, SyncTarget

    settings = get_settings()
    provider = build_provider(settings)
    health = await provider.healthcheck()
    if settings.provider == 'playwright_xhs' and not health.get('storage_state_exists'):
        raise SystemExit(
            f"当前 provider=playwright_xhs，但未找到登录态文件：{health.get('storage_state_path') or '-'}\n"
            "请先执行 crawler_service/scripts/save_xhs_storage_state.py 保存登录态。"
        )

    profile_url = (os.environ.get('XHS_PROBE_PROFILE_URL') or '').strip()
    account_handle = (os.environ.get('XHS_PROBE_ACCOUNT_HANDLE') or '').strip()
    owner_name = (os.environ.get('XHS_PROBE_OWNER_NAME') or '测试账号').strip()
    owner_phone = (os.environ.get('XHS_PROBE_OWNER_PHONE') or '13800000000').strip()
    if not profile_url and not account_handle:
        raise SystemExit('请至少设置 XHS_PROBE_PROFILE_URL 或 XHS_PROBE_ACCOUNT_HANDLE')

    source_channel = (os.environ.get('XHS_PROBE_SOURCE_CHANNEL') or 'probe_script').strip() or 'probe_script'
    batch_name = (os.environ.get('XHS_PROBE_BATCH_NAME') or 'probe_account_posts').strip()
    current_month_only = str(os.environ.get('XHS_PROBE_CURRENT_MONTH_ONLY') or 'true').strip().lower() in {'1', 'true', 'yes', 'y', 'on'}
    date_from = (os.environ.get('XHS_PROBE_DATE_FROM') or '').strip()
    date_to = (os.environ.get('XHS_PROBE_DATE_TO') or '').strip()
    max_posts_per_account = int((os.environ.get('XHS_PROBE_MAX_POSTS_PER_ACCOUNT') or '10').strip() or '10')

    payload = AccountPostsRequest(
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

    result = await provider.fetch_account_posts(payload)
    output_dir = Path(settings.xhs_debug_output_dir or '/tmp/xhs_crawler_debug')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / 'xhs_account_probe.json'
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')

    print(json.dumps({
        'provider': settings.provider,
        'health': health,
        'target': {
            'profile_url': profile_url,
            'account_handle': account_handle,
        },
        'account_count': len(result.get('accounts') or []),
        'post_count': len(result.get('posts') or []),
        'snapshot_count': len(result.get('snapshots') or []),
        'output_path': str(output_path),
        'sample_account': (result.get('accounts') or [])[:1],
        'sample_posts': (result.get('posts') or [])[:5],
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
