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

from release_manifest import build_release_manifest_payload


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
        ('liver_science', '/liver-science'),
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


def _run_release_manifest_check(client):
    local_manifest = build_release_manifest_payload(include_generated_at=False)
    response = client.get('/api/admin/release-manifest')
    data = response.get_json()
    _assert(response.status_code == 200, f'release-manifest failed with {response.status_code}')
    _assert(data and data.get('success'), f'release-manifest failed: {data}')
    features = data.get('release_features') or {}
    _assert(features.get('copy_quality_scoring') is True, 'release-manifest should expose copy_quality_scoring')
    _assert(features.get('image_workflow_decision') is True, 'release-manifest should expose image_workflow_decision')
    _assert(features.get('task_workspace') is True, 'release-manifest should expose task_workspace')
    _assert(data.get('release_version') == local_manifest.get('release_version'), 'release-manifest should match local release version')
    _assert(data.get('release_fingerprint') == local_manifest.get('release_fingerprint'), 'release-manifest should match local release fingerprint')
    _print_check('release_manifest', json.dumps({
        'release_version': data.get('release_version'),
        'release_fingerprint': data.get('release_fingerprint'),
    }, ensure_ascii=False))


def _run_release_marker_pages_check(client, db, activity_model, topic_model, registration_model):
    with client.application.app_context():
        activity = activity_model(
            name='Smoke Release Marker',
            title='Smoke Release Marker',
            status='published',
        )
        db.session.add(activity)
        db.session.flush()

        topic = topic_model(
            activity_id=activity.id,
            topic_name='版本标记检查话题',
            keywords='FibroScan, 版本, 标记',
            direction='用于检查关键页面是否带上 release manifest 标记。',
            quota=5,
            filled=0,
            group_num='第九组',
        )
        db.session.add(topic)
        db.session.flush()

        registration = registration_model(
            topic_id=topic.id,
            group_num='第九组',
            name='版本标记测试',
            phone='13600000000',
            xhs_account='release_marker_smoke',
        )
        db.session.add(registration)
        db.session.commit()
        registration_id = registration.id

    checks = [
        ('automation_center_page', 'GET', '/automation_center', None, ['data-release-manifest="release-manifest"', 'trendPayloadFile', 'xhs-release-version', 'releaseManifestWrap', 'releaseManifestPayload']),
        ('data_analysis_page', 'GET', '/data_analysis', None, ['data-release-manifest="release-manifest"', 'taskFunnelWrap', 'strategySummaryWrap', 'releaseSummaryBar', 'releaseManifestPayload']),
        ('my_registration_page', 'POST', '/my_registration', {'group_num': '第九组', 'name': '版本标记测试'}, ['data-release-manifest="release-manifest"', 'task-filter-chip', '建议优先处理', 'releasePublicSummary', 'releaseManifestPayload']),
        ('register_success_page', 'GET', f'/register_success/{registration_id}', None, ['data-release-manifest="release-manifest"', 'applyWorkflowDecision', 'copy-quality-chip', 'releaseStudioSummary', 'releaseManifestPayload']),
    ]
    results = {}
    for label, method, path, payload, tokens in checks:
        if method == 'POST':
            response = client.post(path, data=payload or {})
        else:
            response = client.get(path)
        html = response.get_data(as_text=True)
        _assert(response.status_code == 200, f'{label} failed with {response.status_code}')
        missing = [token for token in tokens if token not in html]
        _assert(not missing, f'{label} missing markers: {missing}')
        results[label] = 'ok'
    _print_check('release_marker_pages', json.dumps(results, ensure_ascii=False))


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
        'hotword_scope_preset': 'science_qna',
        'hotword_time_window': '30d',
        'hotword_date_from': '',
        'hotword_date_to': '',
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
        'hotword_auto_convert_corpus_templates': True,
        'hotword_auto_convert_corpus_limit': 8,
    }
    saved = _save_automation_config(client, payload)
    config = saved.get('config') or {}
    _assert(config.get('hotword_api_url') == 'http://127.0.0.1:8081/xhs/trends', 'hotword_api_url should persist local crawler trends endpoint')
    _assert(config.get('hotword_source_template') == 'xhs_note_search', 'hotword_source_template should persist xhs_note_search')
    _assert(config.get('hotword_trend_type') == 'note_search', 'hotword_trend_type should persist note_search')
    _assert(config.get('hotword_page_size') == 12, 'hotword_page_size should persist custom page_size')
    _assert(config.get('hotword_max_related_queries') == 9, 'hotword_max_related_queries should persist custom max_related_queries')
    _assert(config.get('hotword_scope_preset') == 'science_qna', 'hotword_scope_preset should persist science_qna')
    _assert(config.get('hotword_time_window') == '30d', 'hotword_time_window should persist 30d')
    _assert(config.get('hotword_auto_convert_corpus_templates') is True, 'hotword_auto_convert_corpus_templates should persist as True')
    _assert(config.get('hotword_auto_convert_corpus_limit') == 8, 'hotword_auto_convert_corpus_limit should persist custom limit')

    preview = _load_automation_config_preview(client)
    hotword_preview = preview.get('hotword_preview') or {}
    request_preview = preview.get('hotword_request_preview') or {}
    _assert(hotword_preview.get('fetch_mode') == 'remote', 'hotword preview should be remote')
    _assert(hotword_preview.get('api_url') == 'http://127.0.0.1:8081/xhs/trends', 'hotword preview should point to local crawler trends endpoint')
    _assert(hotword_preview.get('trend_type') == 'note_search', 'hotword preview should keep note_search trend type')
    _assert(hotword_preview.get('page_size') == 12, 'hotword preview should keep configured page_size')
    _assert(hotword_preview.get('max_related_queries') == 9, 'hotword preview should keep configured max_related_queries')
    _assert(hotword_preview.get('scope_preset') == 'science_qna', 'hotword preview should expose scope preset')
    _assert(hotword_preview.get('time_window') == '30d', 'hotword preview should expose time window')
    _assert(hotword_preview.get('auto_convert_corpus_templates') is True, 'hotword preview should expose auto-convert toggle')
    _assert(hotword_preview.get('auto_convert_corpus_limit') == 8, 'hotword preview should expose auto-convert limit')
    body = request_preview.get('body') or {}
    _assert(body.get('trend_type') == 'note_search', 'hotword request preview should carry note_search trend_type')
    _assert(body.get('page_size') == 12, 'hotword request preview should carry configured page_size')
    _assert(body.get('max_related_queries') == 9, 'hotword request preview should carry configured max_related_queries')
    _assert(isinstance(body.get('keywords'), list) and len(body.get('keywords')) >= 2, 'hotword request preview should render keyword list')
    _assert((body.get('keywords') or [None])[0] == '脂肪肝怎么吃', 'hotword request preview should start with scoped science_qna seed')
    _assert(body.get('date_from'), 'hotword request preview should include resolved date_from')
    _assert(body.get('date_to'), 'hotword request preview should include resolved date_to')
    _print_check('hotword_local_crawler_config', json.dumps(request_preview, ensure_ascii=False))


def _run_trend_csv_parse_check(parse_trend_payload):
    raw_payload = """关键词,标题,链接,点赞量,收藏量,评论量,阅读量,作者,摘要,发布时间
FibroScan,很多人把FibroScan看偏了,https://example.com/note1,321,118,26,8800,护肝小助手,这是一条爆款笔记摘要,2026-04-19 10:00:00
脂肪肝,脂肪肝体检后别只盯转氨酶,https://example.com/note2,220,95,18,6400,体检复盘号,先抛焦虑再拆重点,2026-04-18 09:20:00
"""
    items = parse_trend_payload(raw_payload)
    _assert(len(items) == 2, 'csv payload should parse two rows')
    _assert((items[0].get('keyword') or '') == 'FibroScan', 'csv payload should map keyword header')
    _assert((items[0].get('title') or '') == '很多人把FibroScan看偏了', 'csv payload should map title header')
    _assert((items[0].get('views') or '') == '8800', 'csv payload should map view header')
    _print_check('trend_csv_parse', json.dumps(items[:2], ensure_ascii=False))


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
                'hotword_auto_convert_corpus_templates': True,
                'hotword_auto_convert_corpus_limit': 5,
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
        result_payload = json.loads(refreshed_task.result_payload or '{}')
        corpus_conversion = result_payload.get('corpus_conversion') or {}
        _assert(corpus_conversion.get('selected_count') == 1, 'hotword worker should auto-convert inserted trend to corpus when enabled')
        _print_check('hotword_worker_passthrough', json.dumps({
            'title': inserted.title,
            'author': inserted.author,
            'template_key': inserted.source_template_key,
            'likes': inserted.likes,
            'favorites': inserted.favorites,
            'comments': inserted.comments,
            'corpus_conversion': corpus_conversion,
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


def _run_copy_skill_generation_check(client, db, activity_model, topic_model, registration_model, submission_model):
    with patch('app.DEEPSEEK_API_KEY', ''):
        with client.application.app_context():
            activity = activity_model(
                name='Smoke Activity',
                title='Smoke Growth Loop',
                description='用于验证标题池、封面池和策略复盘',
                status='published',
            )
            db.session.add(activity)
            db.session.commit()
            activity_id = activity.id

            topic = topic_model(
                activity_id=activity.id,
                topic_name='体检报告里的肝弹指标怎么看',
                keywords='体检, 报告, FibroScan, 指标',
                direction='把不会看报告的人最容易误判的点讲清楚。',
                quota=30,
                filled=0,
                group_num='A组',
            )
            db.session.add(topic)
            db.session.commit()

            registration = registration_model(
                topic_id=topic.id,
                group_num='A组',
                name='Smoke Tester',
                phone='13800000000',
                xhs_account='smoke_tester',
            )
            db.session.add(registration)
            db.session.commit()
            registration_id = registration.id

        response = client.post('/api/generate_copy', json={
            'registration_id': registration_id,
            'persona_key': 'patient_self',
            'scene_key': 'report_interpretation',
            'product_key': 'fibroscan',
            'copy_goal': 'save_value',
            'copy_skill': 'practical_checklist',
            'title_skill': 'checklist_collect',
            'user_prompt': '重点讲清楚先看什么再看什么',
            'fast_mode': True,
        })
        data = response.get_json()
        _assert(response.status_code == 200, f'generate_copy failed with {response.status_code}')
        _assert(data and data.get('success'), f'generate_copy failed: {data}')
        cards = data.get('cards') or []
        title_options = data.get('title_options') or []
        _assert(len(cards) == 3, 'generate_copy should return 3 cards')
        _assert(len(title_options) >= 4, 'generate_copy should return title option pool')
        generator_context = data.get('generator_context') or {}
        _assert(generator_context.get('skill') == '收藏清单型', 'generator_context should expose selected copy skill')
        _assert(generator_context.get('title_skill') == '收藏清单标题', 'generator_context should expose selected title skill')
        combined_text = '\n'.join(
            f"{card.get('title')}\n{card.get('body')}"
            for card in cards
        )
        _assert(
            any(token in combined_text for token in ['先确认这3件事', '这份清单先收好', '复查前后', '先看前后变化', '先把顺序理清', '先看这次检查到底想回答什么']),
            'copy skill should influence local fallback titles/body'
        )

        strategy_response = client.post('/api/strategy_selection', json={
            'registration_id': registration_id,
            'selected_title': title_options[0].get('title'),
            'selected_title_source': title_options[0].get('source'),
            'selected_title_index': 0,
            'selected_copy_version_index': 0,
            'selected_copy_goal': 'save_value',
            'selected_copy_skill': 'practical_checklist',
            'selected_title_skill': 'checklist_collect',
            'selected_image_skill': 'report_decode',
            'selected_cover_style_type': 'checklist_report',
            'selected_inner_style_type': 'checklist_report',
            'selected_generation_mode': 'smart_bundle',
            'selected_copy_text': cards[0].get('copy_text'),
            'title_options': title_options,
        })
        strategy_data = strategy_response.get_json()
        _assert(strategy_response.status_code == 200, f'strategy_selection failed with {strategy_response.status_code}')
        _assert(strategy_data and strategy_data.get('success'), f'strategy_selection failed: {strategy_data}')
        _assert(strategy_data.get('stored') is True, 'strategy_selection should create draft submission persistence before note submission exists')

        with client.application.app_context():
            draft_submission = submission_model.query.filter_by(registration_id=registration_id).first()
            _assert(draft_submission is not None, 'strategy_selection should create draft submission record')
            _assert(draft_submission.selected_title_skill == 'checklist_collect', 'draft submission should store title skill key')
            _assert(draft_submission.selected_image_skill == 'report_decode', 'draft submission should store image skill key')

        submit_response = client.post('/api/submit', json={
            'registration_id': registration_id,
            'xhs_link': 'https://www.xiaohongshu.com/explore/smoke-growth-001',
            'xhs_views': 3200,
            'xhs_likes': 180,
            'xhs_favorites': 66,
            'xhs_comments': 28,
            'selected_title': title_options[0].get('title'),
            'selected_title_source': title_options[0].get('source'),
            'selected_title_index': 0,
            'selected_copy_version_index': 0,
            'selected_copy_goal': 'save_value',
            'selected_copy_skill': 'practical_checklist',
            'selected_title_skill': 'checklist_collect',
            'selected_image_skill': 'report_decode',
            'selected_cover_style_type': 'checklist_report',
            'selected_inner_style_type': 'checklist_report',
            'selected_generation_mode': 'smart_bundle',
            'selected_copy_text': cards[0].get('copy_text'),
            'title_options': title_options,
        })
        submit_data = submit_response.get_json()
        _assert(submit_response.status_code == 200, f'submit failed with {submit_response.status_code}')
        _assert(submit_data and submit_data.get('success'), f'submit failed: {submit_data}')

        with client.application.app_context():
            saved_submission = submission_model.query.filter_by(registration_id=registration_id).first()
            _assert(saved_submission is not None, 'submit should create submission record')
            _assert(saved_submission.selected_title_skill == 'checklist_collect', 'submission should store title skill key')
            _assert(saved_submission.selected_image_skill == 'report_decode', 'submission should store image skill key')
            _assert((saved_submission.selected_title or '') == (title_options[0].get('title') or ''), 'submission should store selected title')

        recommendation_response = client.get(f'/api/strategy_recommendations/{registration_id}')
        recommendation_data = recommendation_response.get_json()
        _assert(recommendation_response.status_code == 200, f'strategy_recommendations failed with {recommendation_response.status_code}')
        _assert(recommendation_data and recommendation_data.get('success'), f'strategy_recommendations failed: {recommendation_data}')
        recommended = recommendation_data.get('recommended') or {}
        _assert(recommended.get('title_skill') == 'checklist_collect', 'strategy_recommendations should prefer historical title skill')
        _assert(recommended.get('image_skill') == 'report_decode', 'strategy_recommendations should prefer historical image skill')

        cover_response = client.post('/api/asset_style_recommendations', json={
            'registration_id': registration_id,
            'selected_content': cards[0].get('copy_text') or '',
            'title_hint': title_options[0].get('title') if title_options else cards[0].get('title'),
        })
        cover_data = cover_response.get_json()
        _assert(cover_response.status_code == 200, f'asset_style_recommendations failed with {cover_response.status_code}')
        _assert(cover_data and cover_data.get('success'), f'asset_style_recommendations failed: {cover_data}')
        _assert(len(cover_data.get('items') or []) >= 1, 'asset_style_recommendations should return at least one recommendation')

        stats_response = client.get(f'/api/stats/{activity_id}')
        stats_data = stats_response.get_json()
        _assert(stats_response.status_code == 200, f'stats failed with {stats_response.status_code}')
        _assert(stats_data and (stats_data.get('strategy_insights') or {}).get('captured_count', 0) >= 1, 'stats should include strategy insights')
        _assert((stats_data.get('task_funnel') or {}).get('strategy_selected_count', 0) >= 1, 'stats should include task funnel strategy selected count')
        _assert(len((stats_data.get('strategy_insights') or {}).get('summary_lines') or []) >= 1, 'stats should include strategy summary lines')

        weekly_report_response = client.get(f'/api/weekly_report/{activity_id}')
        weekly_report_text = weekly_report_response.get_data(as_text=True)
        _assert(weekly_report_response.status_code == 200, f'weekly report failed with {weekly_report_response.status_code}')
        _assert('## 三、任务漏斗' in weekly_report_text, 'weekly report should include task funnel section')
        _assert('## 四、策略结论' in weekly_report_text, 'weekly report should include strategy conclusion section')
        _print_check('copy_skill_generation', json.dumps({
            'skill': generator_context.get('skill'),
            'title_skill': generator_context.get('title_skill'),
            'title': cards[0].get('title'),
            'title_option_count': len(title_options),
            'cover_style': ((cover_data.get('items') or [{}])[0].get('style_key')),
            'strategy_capture_rate': ((stats_data.get('strategy_insights') or {}).get('capture_rate_display')),
            'task_funnel_strategy_count': ((stats_data.get('task_funnel') or {}).get('strategy_selected_count')),
            'recommendation_source': recommendation_data.get('source'),
            'weekly_report_has_task_funnel': '## 三、任务漏斗' in weekly_report_text,
        }, ensure_ascii=False))


def _run_image_decision_consistency_check(client, db, activity_model, topic_model, registration_model):
    with client.application.app_context():
        activity = activity_model(
            name='Smoke Image Decision',
            title='Smoke Image Decision',
            status='published',
        )
        db.session.add(activity)
        db.session.flush()

        topic = topic_model(
            activity_id=activity.id,
            topic_name='FibroScan 报告里的指标到底先看什么',
            keywords='FibroScan, 体检, 报告, 肝弹',
            direction='把不会看报告的人最容易误判的点讲清楚，重点做收藏型内容。',
            quota=30,
            filled=0,
            group_num='A组',
        )
        db.session.add(topic)
        db.session.flush()

        registration = registration_model(
            topic_id=topic.id,
            group_num='A组',
            name='Smoke Image Tester',
            phone='13900000000',
            xhs_account='smoke_image_tester',
        )
        db.session.add(registration)
        db.session.commit()
        registration_id = registration.id

    selected_content = (
        '标题：很多人把FibroScan看偏了\n'
        '开头钩子：拿到报告那一刻，我第一反应真是慌。\n'
        '正文：我后来才发现，很多人一看到报告里有这项检查，第一反应就已经跑偏了。'
        '先看前后变化，再问清检查目的，最后定复查时间。\n'
        '互动结尾：你们复查时最先看哪一项？'
    )

    recommendation_response = client.post('/api/asset_style_recommendations', json={
        'registration_id': registration_id,
        'selected_content': selected_content,
        'title_hint': '很多人把FibroScan看偏了',
    })
    recommendation_data = recommendation_response.get_json()
    _assert(recommendation_response.status_code == 200, f'asset_style_recommendations failed with {recommendation_response.status_code}')
    _assert(recommendation_data and recommendation_data.get('success'), f'asset_style_recommendations failed: {recommendation_data}')
    top_items = recommendation_data.get('items') or []
    _assert(top_items, 'asset_style_recommendations should return recommendation items')
    _assert((top_items[0].get('style_key') or '') == 'medical_science', 'report-like content should prefer medical_science cover route')
    _assert((top_items[0].get('cover_fit_label') or '') in {'强封面', '可直接试'}, 'top recommendation should expose cover fit label')

    creative_response = client.post('/api/generate_creative_pack', json={
        'registration_id': registration_id,
        'selected_content': selected_content,
        'style_type': 'checklist_report',
        'cover_style_type': 'poster_bold',
        'inner_style_type': 'checklist_report',
        'generation_mode': 'smart_bundle',
    })
    creative_data = creative_response.get_json()
    _assert(creative_response.status_code == 200, f'generate_creative_pack failed with {creative_response.status_code}')
    _assert(creative_data and creative_data.get('success'), f'generate_creative_pack failed: {creative_data}')
    creative_decision = creative_data.get('decision') or {}
    _assert(creative_decision.get('auto_adjusted_cover') is True, 'creative pack should auto-adjust weak poster cover for report-like content')
    _assert(creative_decision.get('cover_style_key') == 'medical_science', 'creative pack should switch report-like cover into medical_science')

    bundle_response = client.post('/api/generate_graphic_article_bundle', json={
        'registration_id': registration_id,
        'selected_content': selected_content,
        'style_type': 'checklist_report',
        'cover_style_type': 'poster_bold',
        'inner_style_type': 'checklist_report',
        'generation_mode': 'smart_bundle',
    })
    bundle_data = bundle_response.get_json()
    _assert(bundle_response.status_code == 200, f'generate_graphic_article_bundle failed with {bundle_response.status_code}')
    _assert(bundle_data and bundle_data.get('success'), f'generate_graphic_article_bundle failed: {bundle_data}')
    bundle_decision = bundle_data.get('decision') or {}
    _assert(bundle_decision.get('cover_style_key') == creative_decision.get('cover_style_key'), 'bundle decision should match creative pack effective cover style')
    _assert(bundle_decision.get('inner_style_key') == creative_decision.get('inner_style_key'), 'bundle decision should match creative pack inner style')
    _print_check('image_decision_consistency', json.dumps({
        'top_style': top_items[0].get('style_key'),
        'creative_cover': creative_decision.get('cover_style_key'),
        'bundle_cover': bundle_decision.get('cover_style_key'),
        'creative_adjusted': creative_decision.get('auto_adjusted_cover'),
    }, ensure_ascii=False))


def _run_reference_corpus_import_check(client):
    response = client.post('/api/corpus/import_reference_links', json={
        'title': '',
        'category': '爆款拆解',
        'source': '参考链接导入',
        'tags': '体检,报告,收藏型',
        'reference_links': 'https://www.xiaohongshu.com/explore/smoke-ref-001',
        'reference_note_text': '标题是提问式，开头先抛检查焦虑，再用3条清单讲清楚该先看什么，最后收口到互动提问。',
        'style_hint': '保留提问式标题和清单结构，但改写成围绕 FibroScan 福波看 的检查解读内容。',
        'product_anchor': 'FibroScan福波看',
    })
    data = response.get_json()
    _assert(response.status_code == 200, f'corpus import failed with {response.status_code}')
    _assert(data and data.get('success'), f'corpus import failed: {data}')
    items = data.get('items') or []
    _assert(len(items) == 1, 'corpus import should create one template entry')
    item = items[0]
    _assert(item.get('reference_url') == 'https://www.xiaohongshu.com/explore/smoke-ref-001', 'corpus import should keep reference url')
    _assert(bool((item.get('template_type_key') or '').strip()), 'corpus import should infer non-empty template type')
    _assert('FibroScan福波看' in (item.get('content') or ''), 'corpus import should include product anchor in corpus content')
    _print_check('reference_corpus_import', json.dumps({
        'reference_url': item.get('reference_url'),
        'template_type_key': item.get('template_type_key'),
        'title': item.get('title'),
    }, ensure_ascii=False))


def _run_topic_reference_import_check(client, db, activity_model, topic_model):
    with client.application.app_context():
        activity = activity_model(
            name='Reference Topic Activity',
            title='Reference Topic Import',
            status='published',
        )
        db.session.add(activity)
        db.session.commit()

        topic = topic_model(
            activity_id=activity.id,
            topic_name='体检报告里的肝弹指标怎么看',
            keywords='体检, 报告, FibroScan, 指标',
            direction='把不会看报告的人最容易误判的点讲清楚。',
            writing_example='提问式标题 + 三步清单结构',
            reference_link='https://www.xiaohongshu.com/explore/topic-ref-001 https://www.xiaohongshu.com/explore/topic-ref-002',
            quota=30,
            filled=0,
            group_num='A组',
        )
        db.session.add(topic)
        db.session.commit()
        topic_id = topic.id
        activity_id = activity.id

    topic_response = client.post(f'/api/topics/{topic_id}/import_reference_corpus', json={})
    topic_data = topic_response.get_json()
    _assert(topic_response.status_code == 200, f'topic reference import failed with {topic_response.status_code}')
    _assert(topic_data and topic_data.get('success'), f'topic reference import failed: {topic_data}')
    _assert(len(topic_data.get('items') or []) == 2, 'topic reference import should generate template corpus entries')

    activity_response = client.post(f'/api/activities/{activity_id}/import_reference_corpus', json={})
    activity_data = activity_response.get_json()
    _assert(activity_response.status_code == 200, f'activity reference import failed with {activity_response.status_code}')
    _assert(activity_data and activity_data.get('success'), f'activity reference import failed: {activity_data}')
    _assert(activity_data.get('processed_topics') == 1, 'activity reference import should process the topic with links')
    _print_check('topic_reference_import', json.dumps({
        'topic_items': len(topic_data.get('items') or []),
        'processed_topics': activity_data.get('processed_topics'),
    }, ensure_ascii=False))


def _run_trend_to_corpus_check(client, db, trend_note_model):
    with client.application.app_context():
        note = trend_note_model(
            source_platform='小红书',
            source_channel='Crawler热点',
            source_template_key='xhs_note_search',
            import_batch='smoke_trend_to_corpus',
            keyword='脂肪肝',
            title='脂肪肝体检后别只盯转氨酶',
            author='热点样例账号',
            link='https://www.xiaohongshu.com/explore/smoke-trend-corpus-001',
            views=8800,
            likes=320,
            favorites=118,
            comments=26,
            hot_score=860,
            summary='先抛体检焦虑，再拆3个判断点，最后引导收藏和提问。',
            pool_status='reserve',
        )
        db.session.add(note)
        db.session.commit()
        note_id = note.id

    single_response = client.post(f'/api/trends/{note_id}/to_corpus', json={'category': '爆款拆解'})
    single_data = single_response.get_json()
    _assert(single_response.status_code == 200, f'trend to corpus failed with {single_response.status_code}')
    _assert(single_data and single_data.get('success'), f'trend to corpus failed: {single_data}')
    _assert(len(single_data.get('items') or []) == 1, 'single trend to corpus should create one corpus template')
    trend_snapshot = single_data.get('trend') or {}
    _assert(trend_snapshot.get('has_corpus_template') is True, 'trend serialization should expose corpus linkage after conversion')

    batch_response = client.post('/api/trends/to_corpus_batch', json={
        'category': '爆款拆解',
        'keyword': '脂肪肝',
        'source_platform': '小红书',
        'limit': 20,
    })
    batch_data = batch_response.get_json()
    _assert(batch_response.status_code == 200, f'trend to corpus batch failed with {batch_response.status_code}')
    _assert(batch_data and batch_data.get('success'), f'trend to corpus batch failed: {batch_data}')
    _assert((batch_data.get('count') or 0) >= 1, 'batch trend to corpus should process at least one trend')
    _print_check('trend_to_corpus', json.dumps({
        'single_title': ((single_data.get('items') or [{}])[0].get('title')),
        'batch_count': batch_data.get('count'),
        'linked': trend_snapshot.get('has_corpus_template'),
    }, ensure_ascii=False))


def _run_trend_route_recommendation_check(client, db, activity_model, topic_model, topic_idea_model, trend_note_model, hot_topic_model):
    with client.application.app_context():
        activity = activity_model(name='Smoke 推荐分流活动', title='Smoke Route', status='published')
        db.session.add(activity)
        db.session.flush()

        current_topic_note = trend_note_model(
            source_platform='小红书',
            source_channel='SmokeHotword',
            source_template_key='xhs_note_search',
            keyword='脂肪肝',
            title='脂肪肝怎么吃才稳',
            author='SmokeUser',
            summary='高搜索问题，适合收藏型内容',
            hot_score=230,
            pool_status='reserve',
        )
        hot_topic_note = trend_note_model(
            source_platform='小红书',
            source_channel='SmokeHotword',
            source_template_key='xhs_hot_queries',
            keyword='减肥',
            title='减肥热搜问题',
            author='SmokeUser',
            summary='平台热搜，适合蹭热点',
            hot_score=120,
            pool_status='reserve',
        )
        db.session.add_all([current_topic_note, hot_topic_note])
        db.session.commit()
        activity_id = activity.id
        current_note_id = current_topic_note.id
        hot_note_id = hot_topic_note.id

    single_response = client.post(f'/api/trends/{current_note_id}/route_target', json={
        'target': 'recommended',
        'activity_id': activity_id,
    })
    single_data = single_response.get_json()
    _assert(single_response.status_code == 200, f'single recommended route failed with {single_response.status_code}')
    _assert(single_data and single_data.get('success'), f'single recommended route failed: {single_data}')
    _assert(single_data.get('target') == 'current_topic', 'high score fatty liver note should route to current_topic')

    batch_response = client.post('/api/trends/route_target_batch', json={
        'target': 'recommended',
        'note_ids': [hot_note_id],
        'activity_id': activity_id,
    })
    batch_data = batch_response.get_json()
    _assert(batch_response.status_code == 200, f'batch recommended route failed with {batch_response.status_code}')
    _assert(batch_data and batch_data.get('success'), f'batch recommended route failed: {batch_data}')
    _assert((batch_data.get('target_counts') or {}).get('hot_topic') == 1, 'hot query note should batch-route into hot_topic')

    with client.application.app_context():
        created_topic = topic_model.query.filter_by(source_type='trend_note', source_ref_id=current_note_id).first()
        created_hot = hot_topic_model.query.filter_by(reference_note_id=hot_note_id).first()
        _assert(created_topic is not None, 'recommended current_topic route should create a Topic')
        _assert(created_hot is not None, 'recommended batch route should create a HotTopicEntry')
        _assert(topic_idea_model.query.count() == 0, 'this recommendation smoke case should not create TopicIdea rows')

    _print_check('trend_route_recommendation', json.dumps({
        'single_target': single_data.get('target'),
        'batch_target_counts': batch_data.get('target_counts'),
        'topic_created': bool(created_topic),
        'hot_topic_created': bool(created_hot),
    }, ensure_ascii=False))


def _run_task_workspace_check(client, db, activity_model, topic_model, registration_model, submission_model):
    with client.application.app_context():
        activity = activity_model(
            name='Smoke Task Workspace',
            title='Smoke Task Workspace',
            status='published',
        )
        db.session.add(activity)
        db.session.flush()

        regs = []
        for idx, topic_name in enumerate(['未生成任务', '已选策略任务', '待发布任务', '已发布任务'], start=1):
            topic = topic_model(
                activity_id=activity.id,
                topic_name=topic_name,
                keywords='FibroScan, 体检, 报告',
                direction='围绕检查报告和复查顺序展开。',
                quota=30,
                filled=0,
                group_num='第九组',
            )
            db.session.add(topic)
            db.session.flush()
            reg = registration_model(
                topic_id=topic.id,
                group_num='第九组',
                name='任务流测试',
                phone='13700000000',
                xhs_account=f'smoke_task_{idx}',
            )
            db.session.add(reg)
            db.session.flush()
            regs.append(reg)

        db.session.add(submission_model(
            registration_id=regs[1].id,
            selected_copy_goal='viral_title',
            selected_copy_skill='story_empathy',
            selected_title_skill='result_first',
            selected_image_skill='high_click_cover',
            strategy_payload=json.dumps({
                'selected_persona_key': 'doctor_assistant',
                'selected_scene_key': 'daily_liver_care',
                'selected_direction_key': 'liver_care_habits',
                'selected_product_key': 'auto',
                'selected_agent_copy_route_id': 'story_first',
            }, ensure_ascii=False),
        ))
        db.session.add(submission_model(
            registration_id=regs[2].id,
            selected_title='看到FibroScan先别慌',
            selected_copy_text='正文：先看前后变化，再问清检查目的，最后定复查时间。',
            selected_copy_goal='save_value',
            selected_copy_skill='practical_checklist',
            selected_title_skill='checklist_collect',
            selected_image_skill='report_decode',
            strategy_payload=json.dumps({
                'selected_persona_key': 'patient_self',
                'selected_scene_key': 'report_interpretation',
            }, ensure_ascii=False),
        ))
        db.session.add(submission_model(
            registration_id=regs[3].id,
            xhs_link='https://www.xiaohongshu.com/explore/smoke-task-published',
            xhs_views=2600,
            xhs_likes=140,
            xhs_favorites=52,
            xhs_comments=16,
            xhs_tracking_status='tracking',
            selected_title='FibroScan这项检查先别自己吓自己',
            selected_copy_text='正文：先看前后变化，再问清检查目的，最后定复查时间。',
            selected_copy_goal='save_value',
            selected_copy_skill='report_interpretation',
            selected_title_skill='checklist_collect',
            selected_image_skill='report_decode',
        ))
        db.session.commit()

    response = client.post('/my_registration', data={
        'group_num': '第九组',
        'name': '任务流测试',
    })
    html = response.get_data(as_text=True)
    _assert(response.status_code == 200, f'my_registration failed with {response.status_code}')
    _assert('建议优先处理' in html, 'task workspace should render focus card')
    _assert('已选策略' in html, 'task workspace should render strategy-ready state')
    _assert('待发布' in html, 'task workspace should render pending-publish state')
    _assert('已发布' in html, 'task workspace should render published state')
    _assert('只看待处理' in html, 'task workspace should render filter chips')
    _print_check('task_workspace', json.dumps({
        'has_focus': '建议优先处理' in html,
        'has_strategy_ready': '已选策略' in html,
        'has_pending_publish': '待发布' in html,
        'has_published': '已发布' in html,
    }, ensure_ascii=False))


def main():
    temp_dir = _bootstrap_smoke_env()
    try:
        from app import Activity, DataSourceTask, HotTopicEntry, Registration, Submission, Topic, TopicIdea, TrendNote, app, db, init_db, _parse_trend_payload
        from celery_app import sync_creator_accounts_job
        from celery_app import sync_hotwords_job
        import app as app_module

        init_db()
        client = app.test_client()
        _enable_admin_session(client)

        _run_basic_endpoint_checks(client)
        _run_release_manifest_check(client)
        _run_release_marker_pages_check(client, db, Activity, Topic, Registration)
        _run_runtime_diagnostics_checks(client)
        _run_creator_sync_config_checks(client)
        _run_hotword_local_crawler_config_checks(client)
        _run_trend_csv_parse_check(_parse_trend_payload)
        _run_xhs_trend_template_checks(client)
        _run_reference_corpus_import_check(client)
        _run_trend_to_corpus_check(client, db, TrendNote)
        _run_trend_route_recommendation_check(client, db, Activity, Topic, TopicIdea, TrendNote, HotTopicEntry)
        _run_task_workspace_check(client, db, Activity, Topic, Registration, Submission)
        _run_topic_reference_import_check(client, db, Activity, Topic)
        _run_copy_skill_generation_check(client, db, Activity, Topic, Registration, Submission)
        _run_image_decision_consistency_check(client, db, Activity, Topic, Registration)
        _run_hotword_worker_passthrough_check(app_module, db, DataSourceTask, TrendNote, sync_hotwords_job)
        _run_creator_sync_worker_passthrough_check(app_module, db, DataSourceTask, sync_creator_accounts_job)
        print('Smoke check passed.')
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == '__main__':
    main()
