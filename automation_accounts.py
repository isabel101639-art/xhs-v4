import json

import requests


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _load_json_config(raw_text, default):
    text = (raw_text or '').strip()
    if not text:
        return default
    parsed = json.loads(text)
    return parsed if isinstance(parsed, type(default)) else default


def _extract_result_path(payload, result_path=''):
    path = (result_path or '').strip()
    if not path:
        return payload

    current = payload
    for token in [item for item in path.split('.') if item]:
        if isinstance(current, list):
            try:
                current = current[int(token)]
            except (ValueError, IndexError):
                return {}
        elif isinstance(current, dict):
            current = current.get(token)
        else:
            return {}
    return current


def _render_template_value(value, context):
    if isinstance(value, dict):
        return {key: _render_template_value(item, context) for key, item in value.items()}
    if isinstance(value, list):
        return [_render_template_value(item, context) for item in value]
    if not isinstance(value, str):
        return value

    exact_match_map = {
        '{{targets}}': context.get('targets', []),
        '{{target_count}}': context.get('target_count', 0),
        '{{first_profile_url}}': context.get('first_profile_url', ''),
        '{{first_account_handle}}': context.get('first_account_handle', ''),
        '{{creator_account_ids}}': context.get('creator_account_ids', []),
        '{{profile_urls}}': context.get('profile_urls', []),
        '{{account_handles}}': context.get('account_handles', []),
        '{{batch_name}}': context.get('batch_name', ''),
        '{{source_channel}}': context.get('source_channel', ''),
    }
    if value in exact_match_map:
        return exact_match_map[value]

    text = value
    replacements = {
        '{{target_count}}': str(context.get('target_count', 0)),
        '{{first_profile_url}}': context.get('first_profile_url', ''),
        '{{first_account_handle}}': context.get('first_account_handle', ''),
        '{{batch_name}}': context.get('batch_name', ''),
        '{{source_channel}}': context.get('source_channel', ''),
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _normalize_creator_bundle(payload):
    if isinstance(payload, list):
        return {
            'accounts': [],
            'posts': payload,
            'snapshots': [],
        }
    if not isinstance(payload, dict):
        raise ValueError('账号同步接口返回结构无法识别')

    accounts = payload.get('accounts') or payload.get('creator_accounts') or []
    posts = payload.get('posts') or payload.get('creator_posts') or payload.get('items') or []
    snapshots = payload.get('snapshots') or payload.get('creator_snapshots') or []

    return {
        'accounts': accounts if isinstance(accounts, list) else [],
        'posts': posts if isinstance(posts, list) else [],
        'snapshots': snapshots if isinstance(snapshots, list) else [],
    }


def build_creator_sync_request_preview(config, targets, source_channel='', batch_name=''):
    api_url = (config.get('api_url') or '').strip()
    api_method = (config.get('api_method') or 'POST').strip().upper() or 'POST'
    query_json = _load_json_config(config.get('query_json'), {})
    body_json = _load_json_config(config.get('body_json'), {})
    headers_json = _load_json_config(config.get('headers_json'), {})
    timeout_seconds = max(safe_int(config.get('timeout_seconds'), 60), 5)
    targets = targets or []
    context = {
        'targets': list(targets),
        'target_count': len(targets),
        'first_profile_url': str(targets[0].get('profile_url') or '').strip() if targets else '',
        'first_account_handle': str(targets[0].get('account_handle') or '').strip() if targets else '',
        'creator_account_ids': [item.get('creator_account_id') for item in targets if item.get('creator_account_id')],
        'profile_urls': [item.get('profile_url') for item in targets if item.get('profile_url')],
        'account_handles': [item.get('account_handle') for item in targets if item.get('account_handle')],
        'batch_name': batch_name,
        'source_channel': source_channel,
    }
    rendered_headers = _render_template_value(headers_json, context) if isinstance(headers_json, dict) else {}
    rendered_query = _render_template_value(query_json, context) if isinstance(query_json, dict) else {}
    rendered_body = _render_template_value(body_json, context) if isinstance(body_json, dict) else {}

    if not rendered_body and api_method != 'GET':
        rendered_body = {
            'targets': list(targets),
            'batch_name': batch_name,
            'source_channel': source_channel,
        }
    if not rendered_query and api_method == 'GET':
        rendered_query = {
            'target_count': len(targets),
            'batch_name': batch_name,
        }

    return {
        'api_url': api_url,
        'api_method': api_method,
        'headers': rendered_headers,
        'query': rendered_query,
        'body': rendered_body,
        'timeout_seconds': timeout_seconds,
        'result_path': (config.get('result_path') or '').strip(),
        'target_count': len(targets),
    }


def fetch_remote_creator_bundle(config, targets, source_channel='', batch_name=''):
    preview = build_creator_sync_request_preview(
        config,
        targets,
        source_channel=source_channel,
        batch_name=batch_name,
    )
    api_url = (preview.get('api_url') or '').strip()
    if not api_url:
        raise ValueError('未配置账号同步 API URL')

    method = preview.get('api_method') or 'POST'
    timeout_seconds = max(safe_int(preview.get('timeout_seconds'), 60), 5)
    request_kwargs = {
        'headers': preview.get('headers') or {},
        'timeout': timeout_seconds,
    }
    if method == 'GET':
        request_kwargs['params'] = preview.get('query') or {}
    else:
        request_kwargs['params'] = preview.get('query') or {}
        request_kwargs['json'] = preview.get('body') or {}

    response = requests.request(method, api_url, **request_kwargs)
    response.raise_for_status()

    try:
        payload = response.json()
    except ValueError as exc:
        raise ValueError(f'账号同步接口未返回 JSON：{exc}')

    extracted = _extract_result_path(payload, preview.get('result_path'))
    bundle = _normalize_creator_bundle(extracted)
    return {
        'bundle': bundle,
        'request_preview': preview,
        'response_preview': payload,
    }
