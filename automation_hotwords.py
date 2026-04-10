import json
import re
from datetime import datetime

import requests


HOTWORD_SOURCE_TEMPLATE_OPTIONS = [
    {
        'key': 'generic_lines',
        'label': '通用行文本',
        'source_platform': '手工整理',
        'description': '每行一条，按“关键词|标题|链接|点赞|收藏|评论|传播量|作者|摘要”粘贴',
    },
    {
        'key': 'generic_json',
        'label': '通用 JSON',
        'source_platform': '手工整理',
        'description': 'JSON 数组或 {items: []} 结构，字段包含 keyword、title、views 等',
    },
    {
        'key': 'douyin_hotwords',
        'label': '抖音热点词接口',
        'source_platform': '抖音',
        'description': '适配抖音热点词/热榜类接口的 words、sentence_id、hot_value 结构',
    },
    {
        'key': 'qiangua_notes',
        'label': '千瓜笔记导出',
        'source_platform': '千瓜数据',
        'description': '适配千瓜笔记/爆文导出常见字段，如 title、like_count、collect_count、comment_count',
    },
]


def hotword_source_template_options():
    return [dict(item) for item in HOTWORD_SOURCE_TEMPLATE_OPTIONS]


def hotword_source_template_meta(template_key=''):
    raw = (template_key or '').strip()
    for item in HOTWORD_SOURCE_TEMPLATE_OPTIONS:
        if raw == item['key']:
            return dict(item)
    return dict(HOTWORD_SOURCE_TEMPLATE_OPTIONS[0])


def split_keywords(text):
    return [item.strip() for item in re.split(r'[\n,，;；\s]+', text or '') if item.strip()]


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_trend_payload(raw_payload):
    payload = (raw_payload or '').strip()
    if not payload:
        return []

    items = []
    if payload.startswith('[') or payload.startswith('{'):
        parsed = json.loads(payload)
        if isinstance(parsed, dict):
            parsed = parsed.get('items', [])
        if isinstance(parsed, list):
            for row in parsed:
                if isinstance(row, dict):
                    items.append(row)
        return items

    for line in payload.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [part.strip() for part in re.split(r'[\t|]', line)]
        if len(parts) < 2:
            continue
        items.append({
            'keyword': parts[0],
            'title': parts[1],
            'link': parts[2] if len(parts) > 2 else '',
            'likes': parts[3] if len(parts) > 3 else 0,
            'favorites': parts[4] if len(parts) > 4 else 0,
            'comments': parts[5] if len(parts) > 5 else 0,
            'views': parts[6] if len(parts) > 6 else 0,
            'author': parts[7] if len(parts) > 7 else '',
            'summary': parts[8] if len(parts) > 8 else '',
        })
    return items


def _extract_first_non_empty(row, keys, default=''):
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return default


def _extract_first_number(row, keys, default=0):
    for key in keys:
        value = row.get(key)
        if value in [None, '']:
            continue
        number = safe_int(value, None)
        if number is not None:
            return number
    return default


def normalize_trend_items(items, template_key='generic_lines', source_platform='', source_channel='', batch_name=''):
    template = hotword_source_template_meta(template_key)
    normalized = []
    for index, row in enumerate(items or [], start=1):
        if not isinstance(row, dict):
            continue

        if template['key'] in {'generic_lines', 'generic_json'}:
            keyword = _extract_first_non_empty(row, ['keyword', 'hot_word', 'query'])
            title = _extract_first_non_empty(row, ['title', 'sentence', 'name'])
            link = _extract_first_non_empty(row, ['link', 'url', 'share_url'])
            author = _extract_first_non_empty(row, ['author', 'nickname', 'user_name'])
            summary = _extract_first_non_empty(row, ['summary', 'desc', 'description'])
            views = _extract_first_number(row, ['views', 'view_count', 'play_count', 'read_count'])
            likes = _extract_first_number(row, ['likes', 'like_count', 'digg_count'])
            favorites = _extract_first_number(row, ['favorites', 'collect_count', 'favorite_count'])
            comments = _extract_first_number(row, ['comments', 'comment_count'])
            publish_time = _extract_first_non_empty(row, ['publish_time', 'create_time'])
        elif template['key'] == 'douyin_hotwords':
            keyword = _extract_first_non_empty(row, ['word', 'hot_word', 'keyword', 'sentence'])
            title = _extract_first_non_empty(row, ['sentence', 'title', 'word']) or keyword
            link = _extract_first_non_empty(row, ['url', 'link'])
            author = _extract_first_non_empty(row, ['source', 'board_name'])
            summary = _extract_first_non_empty(row, ['sentence_tag', 'summary', 'description'])
            views = _extract_first_number(row, ['hot_value', 'hot_score', 'search_cnt'])
            likes = _extract_first_number(row, ['like_count', 'digg_count'])
            favorites = _extract_first_number(row, ['collect_count', 'favorite_count'])
            comments = _extract_first_number(row, ['comment_count'])
            publish_time = _extract_first_non_empty(row, ['event_time', 'create_time'])
        elif template['key'] == 'qiangua_notes':
            keyword = _extract_first_non_empty(row, ['keyword', 'search_word', 'topic'])
            title = _extract_first_non_empty(row, ['title', 'note_title'])
            link = _extract_first_non_empty(row, ['link', 'note_url', 'url'])
            author = _extract_first_non_empty(row, ['author', 'nickname', 'account_name'])
            summary = _extract_first_non_empty(row, ['summary', 'content_summary', 'desc'])
            views = _extract_first_number(row, ['views', 'view_count', 'read_num'])
            likes = _extract_first_number(row, ['likes', 'like_count'])
            favorites = _extract_first_number(row, ['favorites', 'collect_count', 'favorite_count'])
            comments = _extract_first_number(row, ['comments', 'comment_count'])
            publish_time = _extract_first_non_empty(row, ['publish_time', 'create_time'])
        else:
            continue

        if not title:
            continue

        normalized_row = {
            'keyword': keyword,
            'title': title,
            'link': link,
            'author': author,
            'summary': summary,
            'views': views,
            'likes': likes,
            'favorites': favorites,
            'comments': comments,
            'publish_time': publish_time,
            'source_platform': source_platform or template.get('source_platform') or '手工整理',
            'source_channel': source_channel or template['label'],
            'import_batch': batch_name,
            'topic_category': template['label'],
            'raw_payload': row,
            'normalized_rank': index,
        }
        normalized_row['interactions'] = likes + favorites + comments
        score_seed = (
            normalized_row['views']
            + normalized_row['likes'] * 3
            + normalized_row['favorites'] * 4
            + normalized_row['comments'] * 5
            + max(0, 100 - index * 3)
        )
        normalized_row['hot_score'] = score_seed
        normalized.append(normalized_row)
    return normalized


def build_hotword_skeleton_rows(keywords, source_platform='小红书', source_channel='Worker骨架', batch_name=''):
    rows = []
    templates = [
        '体检后最容易忽视的3个点',
        '门诊咨询量上升的真实问题',
        '最近一周讨论度明显提升',
        '用户最常追问的复查场景',
        '适合继续延展的内容方向',
    ]
    for idx, keyword in enumerate(keywords, start=1):
        title = f'{keyword}{templates[(idx - 1) % len(templates)]}'
        rows.append({
            'keyword': keyword,
            'title': title,
            'link': '',
            'views': 4200 + idx * 830,
            'likes': 160 + idx * 25,
            'favorites': 72 + idx * 12,
            'comments': 18 + idx * 5,
            'author': f'热点样例账号{idx}',
            'summary': f'Worker 骨架模式生成，供热点池、候选话题生成和后续真实数据源接入联调使用。关键词：{keyword}',
            'source_platform': source_platform,
            'source_channel': source_channel,
            'import_batch': batch_name,
            'topic_category': '热点骨架',
            'publish_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'raw_payload': {
                'mode': 'skeleton',
                'keyword_rank': idx,
                'batch_name': batch_name,
            }
        })
    return rows


def _render_template_value(value, context):
    if isinstance(value, dict):
        return {key: _render_template_value(item, context) for key, item in value.items()}
    if isinstance(value, list):
        return [_render_template_value(item, context) for item in value]
    if not isinstance(value, str):
        return value

    exact_match_map = {
        '{{keywords_list}}': context.get('keywords_list', []),
        '{{keyword_count}}': context.get('keyword_count', 0),
        '{{first_keyword}}': context.get('first_keyword', ''),
        '{{keywords}}': context.get('keywords_joined', ''),
        '{{source_platform}}': context.get('source_platform', ''),
        '{{source_channel}}': context.get('source_channel', ''),
        '{{batch_name}}': context.get('batch_name', ''),
    }
    if value in exact_match_map:
        return exact_match_map[value]

    text = value
    replacements = {
        '{{keywords}}': context.get('keywords_joined', ''),
        '{{keyword_count}}': str(context.get('keyword_count', 0)),
        '{{first_keyword}}': context.get('first_keyword', ''),
        '{{source_platform}}': context.get('source_platform', ''),
        '{{source_channel}}': context.get('source_channel', ''),
        '{{batch_name}}': context.get('batch_name', ''),
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _load_json_config(raw_text, default):
    text = (raw_text or '').strip()
    if not text:
        return default
    parsed = json.loads(text)
    return parsed if isinstance(parsed, type(default)) else default


def _extract_result_path(payload, result_path=''):
    path = (result_path or '').strip()
    if not path:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ['items', 'data', 'results', 'list']:
                value = payload.get(key)
                if isinstance(value, list):
                    return value
        return payload

    current = payload
    for token in [item for item in path.split('.') if item]:
        if isinstance(current, list):
            try:
                current = current[int(token)]
            except (ValueError, IndexError):
                return []
        elif isinstance(current, dict):
            current = current.get(token)
        else:
            return []
    return current


def build_remote_hotword_request_preview(config, keywords, source_platform='', source_channel='', batch_name=''):
    api_url = (config.get('api_url') or '').strip()
    api_method = (config.get('api_method') or 'GET').strip().upper() or 'GET'
    keyword_param = (config.get('keyword_param') or 'keyword').strip() or 'keyword'
    query_json = _load_json_config(config.get('query_json'), {})
    body_json = _load_json_config(config.get('body_json'), {})
    headers_json = _load_json_config(config.get('headers_json'), {})
    timeout_seconds = max(safe_int(config.get('timeout_seconds'), 30), 5)
    context = {
        'keywords_joined': ','.join(keywords),
        'keywords_list': list(keywords),
        'keyword_count': len(keywords),
        'first_keyword': keywords[0] if keywords else '',
        'source_platform': source_platform,
        'source_channel': source_channel,
        'batch_name': batch_name,
    }
    rendered_headers = _render_template_value(headers_json, context) if isinstance(headers_json, dict) else {}
    rendered_query = _render_template_value(query_json, context) if isinstance(query_json, dict) else {}
    rendered_body = _render_template_value(body_json, context) if isinstance(body_json, dict) else {}

    if not rendered_query and api_method == 'GET' and keywords:
        rendered_query = {keyword_param: ','.join(keywords)}
    if not rendered_body and api_method != 'GET' and keywords:
        rendered_body = {keyword_param: list(keywords)}

    return {
        'api_url': api_url,
        'api_method': api_method,
        'keyword_param': keyword_param,
        'headers': rendered_headers,
        'query': rendered_query,
        'body': rendered_body,
        'timeout_seconds': timeout_seconds,
        'result_path': (config.get('result_path') or '').strip(),
    }


def fetch_remote_hotword_items(config, keywords, source_platform='', source_channel='', batch_name=''):
    preview = build_remote_hotword_request_preview(
        config,
        keywords,
        source_platform=source_platform,
        source_channel=source_channel,
        batch_name=batch_name,
    )
    api_url = (preview.get('api_url') or '').strip()
    if not api_url:
        raise ValueError('未配置热点 API URL')

    method = preview.get('api_method') or 'GET'
    timeout_seconds = max(safe_int(preview.get('timeout_seconds'), 30), 5)
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
        raise ValueError(f'热点接口未返回 JSON：{exc}')

    extracted = _extract_result_path(payload, preview.get('result_path'))
    if isinstance(extracted, dict):
        extracted = extracted.get('items') if isinstance(extracted.get('items'), list) else [extracted]
    if not isinstance(extracted, list):
        raise ValueError('热点接口返回结构无法识别，请检查结果路径')

    return {
        'items': extracted,
        'request_preview': preview,
        'response_preview': payload,
    }
