import json
import os
import shutil
import sys
import tempfile
from datetime import datetime
from unittest.mock import patch


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def _bootstrap_smoke_env():
    temp_dir = tempfile.mkdtemp(prefix='xhs_v4_smoke_')
    db_path = os.path.join(temp_dir, 'smoke_check.db')
    probe_dir = os.path.join(temp_dir, 'crawler_debug')
    os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
    os.environ.setdefault('SECRET_KEY', 'xhs_v4_smoke_secret')
    os.environ.setdefault('INLINE_AUTOMATION_JOBS', 'true')
    os.environ['XHS_DEBUG_OUTPUT_DIR'] = probe_dir
    return temp_dir


def _enable_admin_session(client):
    with client.session_transaction() as session_state:
        session_state['admin_logged_in'] = True
        session_state['admin_username'] = 'smoke_check'


def _print_check(label, detail):
    print(f'[OK] {label}: {detail}')


def _run_basic_endpoint_checks(client):
    endpoints = [
        ('healthz', '/healthz'),
        ('home', '/'),
        ('activity_list', '/activity'),
        ('data_analysis', '/data_analysis'),
        ('admin_login', '/admin/login'),
    ]
    for label, path in endpoints:
        res = client.get(path)
        _assert(res.status_code == 200, f'{label} expected 200, got {res.status_code}')
        _print_check(label, res.status_code)


def _save_automation_config(client, payload):
    response = client.post('/api/admin/automation-config', json=payload)
    data = response.get_json()
    _assert(response.status_code == 200, f'automation-config POST failed with {response.status_code}')
    _assert(data and data.get('success'), f'automation-config POST failed: {data}')
    return data


def _load_automation_config_preview(client):
    response = client.get('/api/admin/automation-config/preview')
    data = response.get_json()
    _assert(response.status_code == 200, f'automation-config preview failed with {response.status_code}')
    _assert(data and data.get('success'), f'automation-config preview failed: {data}')
    return data


def _run_runtime_diagnostics_checks(client):
    response = client.get('/api/admin/runtime-diagnostics')
    data = response.get_json()
    _assert(response.status_code == 200, f'runtime-diagnostics failed with {response.status_code}')
    _assert(data and data.get('success'), f'runtime-diagnostics failed: {data}')
    crawler_probe = data.get('crawler_probe') or {}
    _assert('items' in crawler_probe, 'runtime-diagnostics should include crawler_probe items')
    _assert(isinstance(crawler_probe.get('items'), list), 'crawler_probe items should be a list')
    _assert(len(crawler_probe.get('items') or []) >= 5, 'crawler_probe should expose default probe slots')
    _assert(isinstance(crawler_probe.get('summary') or {}, dict), 'crawler_probe summary should be a dict')
    existing_items = [item for item in (crawler_probe.get('items') or []) if item.get('exists')]
    for item in existing_items:
        _assert(isinstance(item.get('metric_sources') or {}, dict), 'crawler_probe metric_sources should be a dict when present')
    _print_check('runtime_diagnostics_crawler_probe', json.dumps(crawler_probe, ensure_ascii=False))


def _run_creator_sync_config_checks(client):
    base_payload = {
        'creator_sync_source_channel': 'SmokeCrawler',
        'creator_sync_fetch_mode': 'remote',
        'creator_sync_api_url': 'http://127.0.0.1:8081/xhs/account_posts',
        'creator_sync_api_method': 'POST',
        'creator_sync_api_headers_json': '',
        'creator_sync_api_query_json': '',
        'creator_sync_api_body_json': '',
        'creator_sync_result_path': '',
        'creator_sync_timeout_seconds': 30,
        'creator_sync_batch_limit': 5,
        'creator_sync_current_month_only': False,
        'creator_sync_date_from': '2026-04-01',
        'creator_sync_date_to': '2026-04-15',
        'creator_sync_max_posts_per_account': 7,
    }

    saved = _save_automation_config(client, base_payload)
    config = saved.get('config') or {}
    _assert(config.get('creator_sync_current_month_only') is False, 'creator_sync_current_month_only should persist as False')
    _assert(config.get('creator_sync_date_from') == '2026-04-01', 'creator_sync_date_from should persist custom value')
    _assert(config.get('creator_sync_date_to') == '2026-04-15', 'creator_sync_date_to should persist custom value')
    _assert(config.get('creator_sync_max_posts_per_account') == 7, 'creator_sync_max_posts_per_account should persist custom value')

    preview = _load_automation_config_preview(client)
    sync_preview = preview.get('creator_sync_preview') or {}
    request_preview = preview.get('creator_sync_request_preview') or {}
    _assert(sync_preview.get('current_month_only') is False, 'creator_sync preview current_month_only should be False')
    _assert(sync_preview.get('date_from') == '2026-04-01', 'creator_sync preview date_from should match saved config')
    _assert(sync_preview.get('date_to') == '2026-04-15', 'creator_sync preview date_to should match saved config')
    _assert(sync_preview.get('max_posts_per_account') == 7, 'creator_sync preview max_posts_per_account should match saved config')
    _assert((request_preview.get('body') or {}).get('date_from') == '2026-04-01', 'request preview body should include saved date_from')
    _assert((request_preview.get('body') or {}).get('max_posts_per_account') == 7, 'request preview body should include saved max_posts_per_account')
    _print_check('creator_sync_config_custom_range', json.dumps(sync_preview, ensure_ascii=False))

    cleared_payload = dict(base_payload)
    cleared_payload['creator_sync_date_from'] = ''
    cleared_payload['creator_sync_date_to'] = ''
    saved = _save_automation_config(client, cleared_payload)
    config = saved.get('config') or {}
    _assert(config.get('creator_sync_date_from') == '', 'creator_sync_date_from should allow clearing to blank')
    _assert(config.get('creator_sync_date_to') == '', 'creator_sync_date_to should allow clearing to blank')

    preview = _load_automation_config_preview(client)
    sync_preview = preview.get('creator_sync_preview') or {}
    _assert(sync_preview.get('date_from') == '', 'creator_sync preview date_from should stay blank when cleared')
    _assert(sync_preview.get('date_to') == '', 'creator_sync preview date_to should stay blank when cleared')
    _print_check('creator_sync_config_clear_range', json.dumps(sync_preview, ensure_ascii=False))

    current_month_payload = dict(base_payload)
    current_month_payload['creator_sync_current_month_only'] = True
    current_month_payload['creator_sync_date_from'] = ''
    current_month_payload['creator_sync_date_to'] = ''
    _save_automation_config(client, current_month_payload)
    preview = _load_automation_config_preview(client)
    sync_preview = preview.get('creator_sync_preview') or {}
    request_preview = preview.get('creator_sync_request_preview') or {}
    expected_month_start = datetime.now().replace(day=1).strftime('%Y-%m-%d')
    expected_today = datetime.now().strftime('%Y-%m-%d')
    _assert(sync_preview.get('current_month_only') is True, 'creator_sync preview current_month_only should be True')
    _assert(sync_preview.get('date_from') == expected_month_start, 'creator_sync preview should default date_from to current month start')
    _assert(sync_preview.get('date_to') == expected_today, 'creator_sync preview should default date_to to today')
    _assert((request_preview.get('body') or {}).get('date_from') == expected_month_start, 'request preview should use current month start')
    _assert((request_preview.get('body') or {}).get('date_to') == expected_today, 'request preview should use today as date_to')
    _print_check('creator_sync_config_current_month_default', json.dumps(sync_preview, ensure_ascii=False))


def _run_hotword_local_crawler_config_checks(client):
    payload = {
        'hotword_source_platform': '小红书',
        'hotword_source_template': 'xhs_note_search',
        'hotword_source_channel': 'Crawler热点',
        'hotword_keyword_limit': 5,
        'hotword_fetch_mode': 'remote',
        'hotword_api_url': 'http://127.0.0.1:8081/xhs/trends',
        'hotword_api_method': 'POST',
        'hotword_api_headers_json': '',
        'hotword_api_query_json': '',
        'hotword_api_body_json': '',
        'hotword_result_path': 'items',
        'hotword_keyword_param': 'keywords',
        'hotword_timeout_seconds': 30,
        'hotword_trend_type': 'note_search',
        'hotword_page_size': 12,
        'hotword_max_related_queries': 9,
    }
    saved = _save_automation_config(client, payload)
    config = saved.get('config') or {}
    _assert(config.get('hotword_api_url') == 'http://127.0.0.1:8081/xhs/trends', 'hotword_api_url should persist local crawler trends endpoint')
    _assert(config.get('hotword_source_template') == 'xhs_note_search', 'hotword_source_template should persist xhs_note_search')
    _assert(config.get('hotword_trend_type') == 'note_search', 'hotword_trend_type should persist note_search')
    _assert(config.get('hotword_page_size') == 12, 'hotword_page_size should persist custom page_size')
    _assert(config.get('hotword_max_related_queries') == 9, 'hotword_max_related_queries should persist custom max_related_queries')

    preview = _load_automation_config_preview(client)
    hotword_preview = preview.get('hotword_preview') or {}
    request_preview = preview.get('hotword_request_preview') or {}
    _assert(hotword_preview.get('fetch_mode') == 'remote', 'hotword preview should be remote')
    _assert(hotword_preview.get('api_url') == 'http://127.0.0.1:8081/xhs/trends', 'hotword preview should point to local crawler trends endpoint')
    _assert(hotword_preview.get('trend_type') == 'note_search', 'hotword preview should keep note_search trend type')
    _assert(hotword_preview.get('page_size') == 12, 'hotword preview should keep configured page_size')
    _assert(hotword_preview.get('max_related_queries') == 9, 'hotword preview should keep configured max_related_queries')
    body = request_preview.get('body') or {}
    _assert(body.get('trend_type') == 'note_search', 'hotword request preview should carry note_search trend_type')
    _assert(body.get('page_size') == 12, 'hotword request preview should carry configured page_size')
    _assert(body.get('max_related_queries') == 9, 'hotword request preview should carry configured max_related_queries')
    _assert(isinstance(body.get('keywords'), list) and len(body.get('keywords')) >= 2, 'hotword request preview should render keyword list')
    _assert((body.get('keywords') or [None])[0] == '脂肪肝', 'hotword request preview should start with default hotword seed')
    _print_check('hotword_local_crawler_config', json.dumps(request_preview, ensure_ascii=False))


def _run_creator_sync_worker_passthrough_check(app_module, db, data_source_task_model, sync_creator_accounts_job):
    with app_module.app.app_context():
        task = data_source_task_model(
            task_type='creator_account_sync',
            source_platform='小红书',
            source_channel='Crawler服务',
            mode='remote',
            status='queued',
            batch_name='smoke_creator_sync',
            params_payload=json.dumps({
                'targets': [{
                    'creator_account_id': 101,
                    'profile_url': 'https://www.xiaohongshu.com/user/profile/smoke',
                    'account_handle': 'smoke_account',
                    'owner_name': 'Smoke Tester',
                    'owner_phone': '13800000000',
                }],
                'creator_sync_api_url': 'http://127.0.0.1:8081/xhs/account_posts',
                'creator_sync_api_method': 'POST',
                'creator_sync_api_headers_json': '',
                'creator_sync_api_query_json': '',
                'creator_sync_api_body_json': '',
                'creator_sync_result_path': '',
                'creator_sync_timeout_seconds': 30,
                'current_month_only': False,
                'date_from': '2026-03-01',
                'date_to': '2026-03-10',
                'max_posts_per_account': 9,
            }, ensure_ascii=False),
        )
        db.session.add(task)
        db.session.commit()

        captured = {}

        def fake_fetch_remote_creator_bundle(config, targets, source_channel='', batch_name=''):
            captured['config'] = dict(config)
            captured['targets'] = list(targets)
            captured['source_channel'] = source_channel
            captured['batch_name'] = batch_name
            return {
                'bundle': {'accounts': [], 'posts': [], 'snapshots': []},
                'request_preview': {
                    'current_month_only': config.get('current_month_only'),
                    'date_from': config.get('date_from'),
                    'date_to': config.get('date_to'),
                    'max_posts_per_account': config.get('max_posts_per_account'),
                },
                'response_preview': {'success': True},
            }

        def fake_import_creator_bundle(bundle, log_operation=None):
            captured['bundle'] = bundle
            return {
                'summary': {
                    'accounts_create': 0,
                    'accounts_update': 0,
                    'posts_create': 0,
                    'posts_update': 0,
                }
            }

        with patch('app.fetch_remote_creator_bundle', side_effect=fake_fetch_remote_creator_bundle), patch(
            'creator_import.import_creator_bundle',
            side_effect=fake_import_creator_bundle,
        ):
            result = sync_creator_accounts_job(task.id)

        _assert(result.get('success') is True, f'creator sync worker should succeed, got: {result}')
        _assert(captured.get('config', {}).get('current_month_only') is False, 'worker should pass current_month_only to fetch_remote_creator_bundle')
        _assert(captured.get('config', {}).get('date_from') == '2026-03-01', 'worker should pass date_from to fetch_remote_creator_bundle')
        _assert(captured.get('config', {}).get('date_to') == '2026-03-10', 'worker should pass date_to to fetch_remote_creator_bundle')
        _assert(captured.get('config', {}).get('max_posts_per_account') == 9, 'worker should pass max_posts_per_account to fetch_remote_creator_bundle')
        _assert(len(captured.get('targets', [])) == 1, 'worker should pass targets to fetch_remote_creator_bundle')

        db.session.expire_all()
        refreshed_task = db.session.get(data_source_task_model, task.id)
        result_payload = json.loads(refreshed_task.result_payload or '{}')
        request_preview = result_payload.get('request_preview') or {}
        _assert(request_preview.get('date_from') == '2026-03-01', 'worker result payload should record date_from in request preview')
        _assert(request_preview.get('date_to') == '2026-03-10', 'worker result payload should record date_to in request preview')
        _assert(request_preview.get('max_posts_per_account') == 9, 'worker result payload should record max_posts_per_account in request preview')
        _print_check('creator_sync_worker_passthrough', json.dumps(request_preview, ensure_ascii=False))


def _run_hotword_worker_passthrough_check(app_module, db, data_source_task_model, trend_note_model, sync_hotwords_job):
    with app_module.app.app_context():
        task = data_source_task_model(
            task_type='hotword_sync',
            source_platform='小红书',
            source_channel='Crawler热点',
            mode='remote',
            status='queued',
            batch_name='smoke_hotword_sync',
            keyword_limit=2,
            params_payload=json.dumps({
                'keywords': ['肝纤维化', '脂肪肝'],
                'keyword_limit': 2,
                'source_platform': '小红书',
                'source_channel': 'Crawler热点',
                'mode': 'remote',
                'template_key': 'xhs_note_search',
                'batch_name': 'smoke_hotword_sync',
                'hotword_api_url': 'http://127.0.0.1:8081/xhs/trends',
                'hotword_api_method': 'POST',
                'hotword_api_headers_json': '',
                'hotword_api_query_json': '',
                'hotword_api_body_json': '{"keywords":"{{keywords_list}}","trend_type":"note_search"}',
                'hotword_result_path': 'items',
                'hotword_keyword_param': 'keywords',
                'hotword_timeout_seconds': 30,
                'hotword_auto_generate_topic_ideas': False,
            }, ensure_ascii=False),
        )
        db.session.add(task)
        db.session.commit()

        captured = {}

        def fake_fetch_remote_hotword_items(config, keywords, source_platform='', source_channel='', batch_name=''):
            captured['config'] = dict(config)
            captured['keywords'] = list(keywords)
            captured['source_platform'] = source_platform
            captured['source_channel'] = source_channel
            captured['batch_name'] = batch_name
            return {
                'items': [
                    {
                        'keyword': '肝纤维化',
                        'note_card': {
                            'title': '肝纤维化体检别只盯转氨酶',
                            'desc': '这是一条来自远端接口的爆款笔记样例',
                        },
                        'user': {'nickname': '热点样例账号'},
                        'interact_info': {
                            'liked_count': 123,
                            'collected_count': 45,
                            'comment_count': 12,
                        },
                        'share_url': 'https://www.xiaohongshu.com/explore/workerhot001',
                        'create_time': '2026-04-18 12:00:00',
                        'rank': 3,
                    }
                ],
                'request_preview': {
                    'api_url': config.get('api_url'),
                    'api_method': config.get('api_method'),
                    'result_path': config.get('result_path'),
                },
                'response_preview': {'items': ['trimmed']},
            }

        with patch('app.fetch_remote_hotword_items', side_effect=fake_fetch_remote_hotword_items):
            result = sync_hotwords_job(task.id)

        _assert(result.get('success') is True, f'hotword worker should succeed, got: {result}')
        _assert(captured.get('config', {}).get('api_url') == 'http://127.0.0.1:8081/xhs/trends', 'hotword worker should pass crawler trends endpoint')
        _assert(captured.get('keywords') == ['肝纤维化', '脂肪肝'], 'hotword worker should pass task keywords')

        db.session.expire_all()
        refreshed_task = db.session.get(data_source_task_model, task.id)
        _assert(refreshed_task.status == 'success', 'hotword task should finish as success')
        inserted_notes = trend_note_model.query.filter_by(import_batch='smoke_hotword_sync').all()
        _assert(len(inserted_notes) == 1, 'hotword worker should insert one trend note')
        inserted = inserted_notes[0]
        _assert(inserted.source_template_key == 'xhs_note_search', 'hotword worker should keep xhs_note_search template key')
        _assert(inserted.title == '肝纤维化体检别只盯转氨酶', 'hotword worker should normalize nested note title')
        _assert(inserted.author == '热点样例账号', 'hotword worker should normalize nested author')
        _assert(inserted.likes == 123, 'hotword worker should normalize nested likes')
        _assert(inserted.favorites == 45, 'hotword worker should normalize nested favorites')
        _assert(inserted.comments == 12, 'hotword worker should normalize nested comments')
        _print_check('hotword_worker_passthrough', json.dumps({
            'title': inserted.title,
            'author': inserted.author,
            'template_key': inserted.source_template_key,
            'likes': inserted.likes,
            'favorites': inserted.favorites,
            'comments': inserted.comments,
        }, ensure_ascii=False))


def _run_xhs_trend_template_checks(client):
    hot_query_payload = json.dumps([
        {
            'query': '脂肪肝体检',
            'hot_value': 9876,
            'rank': 2,
            'summary': '搜索热度持续上升',
        }
    ], ensure_ascii=False)
    response = client.post('/api/trends/import_preview', json={
        'template_key': 'xhs_hot_queries',
        'source_platform': '小红书',
        'source_channel': 'SmokeXHS',
        'batch_name': 'smoke_xhs_hot_queries',
        'payload': hot_query_payload,
    })
    data = response.get_json()
    _assert(response.status_code == 200, f'xhs_hot_queries preview failed with {response.status_code}')
    _assert(data and data.get('success'), f'xhs_hot_queries preview failed: {data}')
    item = (data.get('items') or [{}])[0]
    _assert(item.get('keyword') == '脂肪肝体检', 'xhs_hot_queries should map query to keyword')
    _assert(item.get('title') == '脂肪肝体检', 'xhs_hot_queries should map query to title when title missing')
    _assert(item.get('views') == 9876, 'xhs_hot_queries should map hot_value to views/hotness')
    _assert(item.get('normalized_rank') == 2, 'xhs_hot_queries should keep remote rank')
    _print_check('xhs_hot_queries_template', json.dumps(item, ensure_ascii=False))

    note_payload = json.dumps({
        'data': {
            'items': [
                {
                    'keyword': '肝纤维化',
                    'note_card': {
                        'title': '肝纤维化体检别只看转氨酶',
                        'desc': '这是一条爆款笔记摘要',
                    },
                    'user': {
                        'nickname': '护肝小助手',
                    },
                    'interact_info': {
                        'liked_count': 321,
                        'collected_count': 118,
                        'comment_count': 26,
                    },
                    'share_url': 'https://www.xiaohongshu.com/explore/smoke123',
                    'create_time': '2026-04-19 10:00:00',
                }
            ]
        }
    }, ensure_ascii=False)
    response = client.post('/api/trends/parse_remote_preview', json={
        'template_key': 'xhs_note_search',
        'source_platform': '小红书',
        'source_channel': 'SmokeXHS',
        'batch_name': 'smoke_xhs_notes',
        'result_path': 'data.items',
        'response_payload': note_payload,
    })
    data = response.get_json()
    _assert(response.status_code == 200, f'xhs_note_search parse failed with {response.status_code}')
    _assert(data and data.get('success'), f'xhs_note_search parse failed: {data}')
    item = (data.get('items') or [{}])[0]
    _assert(item.get('keyword') == '肝纤维化', 'xhs_note_search should keep keyword')
    _assert(item.get('title') == '肝纤维化体检别只看转氨酶', 'xhs_note_search should map nested note_card.title')
    _assert(item.get('author') == '护肝小助手', 'xhs_note_search should map nested user.nickname')
    _assert(item.get('likes') == 321, 'xhs_note_search should map nested liked_count')
    _assert(item.get('favorites') == 118, 'xhs_note_search should map nested collected_count')
    _assert(item.get('comments') == 26, 'xhs_note_search should map nested comment_count')
    _assert(item.get('link') == 'https://www.xiaohongshu.com/explore/smoke123', 'xhs_note_search should map share_url to link')
    _print_check('xhs_note_search_template', json.dumps(item, ensure_ascii=False))


def main():
    temp_dir = _bootstrap_smoke_env()
    try:
        from app import DataSourceTask, TrendNote, app, db, init_db
        from celery_app import sync_creator_accounts_job
        from celery_app import sync_hotwords_job
        import app as app_module

        init_db()
        client = app.test_client()
        _enable_admin_session(client)

        _run_basic_endpoint_checks(client)
        _run_runtime_diagnostics_checks(client)
        _run_creator_sync_config_checks(client)
        _run_hotword_local_crawler_config_checks(client)
        _run_xhs_trend_template_checks(client)
        _run_hotword_worker_passthrough_check(app_module, db, DataSourceTask, TrendNote, sync_hotwords_job)
        _run_creator_sync_worker_passthrough_check(app_module, db, DataSourceTask, sync_creator_accounts_job)
        print('Smoke check passed.')
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == '__main__':
    main()
