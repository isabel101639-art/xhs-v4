import json
import os
import sys
import asyncio


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def _print_check(label, detail):
    print(f'[OK] {label}: {detail}')


def main():
    os.environ['CRAWLER_PROVIDER'] = 'mock'

    from crawler_service.config import get_settings
    from crawler_service.providers import build_provider
    from crawler_service.providers.playwright_xhs import (
        _normalize_profile_feed_item,
        _normalize_related_query_item,
        _normalize_search_feed_item,
    )
    from crawler_service.schemas import TrendQueryRequest

    settings = get_settings()
    provider = build_provider(settings)

    data = asyncio.run(provider.healthcheck())
    _assert(data.get('ready') is True, f'healthcheck failed: {data}')
    _print_check('healthz', json.dumps(data, ensure_ascii=False))

    data = asyncio.run(provider.fetch_trends(TrendQueryRequest(
        keywords=['脂肪肝'],
        trend_type='note_search',
        page_size=5,
        source_channel='CrawlerSmoke',
        batch_name='crawler_smoke_note_search',
    )))
    _assert(data.get('success') is True, f'note_search failed: {data}')
    _assert(data.get('trend_type') == 'note_search', 'trend_type should be note_search')
    _assert(len(data.get('items') or []) > 0, 'note_search should return items')
    first_item = (data.get('items') or [{}])[0]
    _assert(first_item.get('title'), 'note_search item should have title')
    _assert(first_item.get('keyword') == '脂肪肝', 'note_search item should keep keyword')
    _print_check('xhs_trends_note_search', json.dumps(first_item, ensure_ascii=False))

    data = asyncio.run(provider.fetch_trends(TrendQueryRequest(
        keywords=['肝纤维化'],
        trend_type='hot_queries',
        max_related_queries=5,
        source_channel='CrawlerSmoke',
        batch_name='crawler_smoke_hot_queries',
    )))
    _assert(data.get('success') is True, f'hot_queries failed: {data}')
    _assert(data.get('trend_type') == 'hot_queries', 'trend_type should be hot_queries')
    _assert(len(data.get('items') or []) > 0, 'hot_queries should return items')
    first_item = (data.get('items') or [{}])[0]
    _assert(first_item.get('query'), 'hot_queries item should have query')
    _assert(first_item.get('title'), 'hot_queries item should have title')
    _print_check('xhs_trends_hot_queries', json.dumps(first_item, ensure_ascii=False))

    normalized_feed = _normalize_search_feed_item(
        {
            'id': 'state_note_001',
            'xsec_token': 'token_abc',
            'note_card': {
                'title': '状态树里的爆款笔记标题',
                'desc': '状态树里的爆款笔记摘要',
                'user': {'nickname': '状态树作者'},
                'interact_info': {
                    'liked_count': '321',
                    'collected_count': '88',
                    'comment_count': '16',
                },
                'time': 1713590400000,
            },
        },
        keyword='脂肪肝',
        source_channel='CrawlerSmoke',
        rank=1,
    )
    _assert(normalized_feed.get('title') == '状态树里的爆款笔记标题', 'state feed normalization should map nested title')
    _assert(normalized_feed.get('author') == '状态树作者', 'state feed normalization should map nested author')
    _assert(normalized_feed.get('likes') == 321, 'state feed normalization should map likes')
    _assert((normalized_feed.get('metric_sources') or {}).get('likes') == 'note_card.interact_info.liked_count', 'state feed normalization should expose likes source path')
    _print_check('state_feed_normalization', json.dumps(normalized_feed, ensure_ascii=False))

    normalized_profile_feed = _normalize_profile_feed_item(
        item={
            'id': 'profile_note_001',
            'xsec_token': 'token_profile',
            'note_card': {
                'title': '账号页状态树笔记标题',
                'desc': '账号页状态树摘要',
                'interact_info': {
                    'liked_count': 66,
                    'collected_count': 22,
                    'comment_count': 8,
                },
                'view_count': 4567,
                'impression_cnt': 12345,
                'time': 1713590400000,
            },
        },
        profile_url='https://www.xiaohongshu.com/user/profile/demo_account',
        account_handle='demo_account',
        target=type('Target', (), {
            'owner_phone': '13800000000',
            'owner_name': '测试账号',
            'registration_id': 0,
            'topic_id': 0,
            'submission_id': 0,
        })(),
        source_channel='CrawlerSmoke',
        rank=1,
    )
    _assert(normalized_profile_feed.get('views') == 4567, 'profile feed normalization should map view_count to views')
    _assert(normalized_profile_feed.get('exposures') == 12345, 'profile feed normalization should map impression_cnt to exposures')
    _assert((normalized_profile_feed.get('metric_sources') or {}).get('exposures') == 'note_card.impression_cnt', 'profile feed normalization should expose exposures source path')
    _print_check('profile_feed_normalization', json.dumps(normalized_profile_feed, ensure_ascii=False))

    normalized_query = _normalize_related_query_item(
        {'query': '脂肪肝体检', 'hot_value': 12345},
        keyword='脂肪肝',
        source_channel='CrawlerSmoke',
        rank=1,
    )
    _assert(normalized_query.get('query') == '脂肪肝体检', 'related query normalization should map query text')
    _assert(normalized_query.get('hot_value') == 12345, 'related query normalization should keep hot value')
    _assert((normalized_query.get('metric_sources') or {}).get('hot_value') == 'hot_value', 'related query normalization should expose hot value source path')
    _print_check('state_query_normalization', json.dumps(normalized_query, ensure_ascii=False))

    print('Crawler trend smoke check passed.')


if __name__ == '__main__':
    main()
