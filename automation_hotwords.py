import json
import re
from datetime import datetime

import requests


HOTWORD_SOURCE_TEMPLATE_OPTIONS = [
    {
        'key': 'generic_lines',
        'label': '通用行文本',
        'source_platform': '手工整理',
        'description': '每行一条，按“关键词|标题|链接|点赞|收藏|评论|曝光量|作者|摘要”粘贴',
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
        'key': 'xhs_hot_queries',
        'label': '小红书热搜词接口',
        'source_platform': '小红书',
        'description': '适配小红书热搜词/搜索词榜接口，常见字段为 query、keyword、hot_value、rank、summary',
    },
    {
        'key': 'xhs_note_search',
        'label': '小红书爆款笔记接口',
        'source_platform': '小红书',
        'description': '适配小红书搜索结果、爆款笔记接口或第三方导出，支持 note_card/user/interact_info 等嵌套字段',
    },
    {
        'key': 'qiangua_notes',
        'label': '千瓜笔记导出',
        'source_platform': '千瓜数据',
        'description': '适配千瓜笔记/爆文导出常见字段，如 title、like_count、collect_count、comment_count',
    },
]

HOTWORD_REMOTE_SOURCE_PRESETS = [
    {
        'key': 'generic_get_items',
        'label': '通用 GET JSON',
        'description': '适合 GET 接口，默认把关键词拼到 query，返回结构优先取 items/data/results/list。',
        'source_platform': '其他平台',
        'template_key': 'generic_json',
        'config': {
            'hotword_fetch_mode': 'remote',
            'hotword_api_method': 'GET',
            'hotword_api_query_json': '{"keyword":"{{keywords}}"}',
            'hotword_api_body_json': '',
            'hotword_result_path': '',
            'hotword_keyword_param': 'keyword',
        },
    },
    {
        'key': 'generic_post_items',
        'label': '通用 POST JSON',
        'description': '适合 POST 接口，请求体直接带 keywords 数组，返回结构优先取 items/data/results/list。',
        'source_platform': '其他平台',
        'template_key': 'generic_json',
        'config': {
            'hotword_fetch_mode': 'remote',
            'hotword_api_method': 'POST',
            'hotword_api_query_json': '',
            'hotword_api_body_json': '{"keywords":"{{keywords_list}}","batch_name":"{{batch_name}}"}',
            'hotword_result_path': '',
            'hotword_keyword_param': 'keywords',
        },
    },
    {
        'key': 'douyin_board_proxy',
        'label': '抖音热榜代理接口',
        'description': '适合热榜/热点词代理接口，默认按抖音热榜字段做归一化，常见结果路径是 data.word_list 或 data.items。',
        'source_platform': '抖音',
        'template_key': 'douyin_hotwords',
        'config': {
            'hotword_fetch_mode': 'remote',
            'hotword_api_method': 'GET',
            'hotword_api_query_json': '{"keyword":"{{first_keyword}}"}',
            'hotword_api_body_json': '',
            'hotword_result_path': 'data.word_list',
            'hotword_keyword_param': 'keyword',
        },
    },
    {
        'key': 'xhs_hot_queries_api',
        'label': '小红书热搜词接口',
        'description': '适合第三方小红书热搜/搜索词榜接口，默认按小红书热搜词字段做归一化，常见结果路径是 data.items。',
        'source_platform': '小红书',
        'template_key': 'xhs_hot_queries',
        'config': {
            'hotword_fetch_mode': 'remote',
            'hotword_api_method': 'GET',
            'hotword_api_query_json': '{"keyword":"{{first_keyword}}","page_size":20}',
            'hotword_api_body_json': '',
            'hotword_result_path': 'data.items',
            'hotword_keyword_param': 'keyword',
        },
    },
    {
        'key': 'xhs_note_search_api',
        'label': '小红书爆款笔记接口',
        'description': '适合第三方小红书搜索/爆款笔记接口，默认按笔记结果字段做归一化，常见结果路径是 data.items。',
        'source_platform': '小红书',
        'template_key': 'xhs_note_search',
        'config': {
            'hotword_fetch_mode': 'remote',
            'hotword_api_method': 'POST',
            'hotword_api_query_json': '',
            'hotword_api_body_json': '{"keyword":"{{first_keyword}}","page_size":20,"sort":"general"}',
            'hotword_result_path': 'data.items',
            'hotword_keyword_param': 'keyword',
        },
    },
    {
        'key': 'crawler_xhs_hot_queries_local',
        'label': '本地 crawler 小红书热搜词',
        'description': '直接调用本地 crawler_service 的 /xhs/trends 接口，适合 mock 或 Playwright 小红书相关搜索词抓取。',
        'source_platform': '小红书',
        'template_key': 'xhs_hot_queries',
        'config': {
            'hotword_fetch_mode': 'remote',
            'hotword_api_url': 'http://127.0.0.1:8081/xhs/trends',
            'hotword_api_method': 'POST',
            'hotword_api_query_json': '',
            'hotword_api_body_json': '',
            'hotword_result_path': 'items',
            'hotword_keyword_param': 'keywords',
            'hotword_trend_type': 'hot_queries',
            'hotword_page_size': 20,
            'hotword_max_related_queries': 20,
        },
    },
    {
        'key': 'crawler_xhs_note_search_local',
        'label': '本地 crawler 小红书爆款笔记',
        'description': '直接调用本地 crawler_service 的 /xhs/trends 接口，适合 mock 或 Playwright 搜索爆款笔记抓取。',
        'source_platform': '小红书',
        'template_key': 'xhs_note_search',
        'config': {
            'hotword_fetch_mode': 'remote',
            'hotword_api_url': 'http://127.0.0.1:8081/xhs/trends',
            'hotword_api_method': 'POST',
            'hotword_api_query_json': '',
            'hotword_api_body_json': '',
            'hotword_result_path': 'items',
            'hotword_keyword_param': 'keywords',
            'hotword_trend_type': 'note_search',
            'hotword_page_size': 20,
            'hotword_max_related_queries': 20,
        },
    },
    {
        'key': 'qiangua_notes_api',
        'label': '千瓜笔记接口',
        'description': '适合千瓜或第三方笔记接口，默认使用千瓜字段映射，常见结果路径是 data.items。',
        'source_platform': '千瓜数据',
        'template_key': 'qiangua_notes',
        'config': {
            'hotword_fetch_mode': 'remote',
            'hotword_api_method': 'POST',
            'hotword_api_query_json': '',
            'hotword_api_body_json': '{"keywords":"{{keywords_list}}","page_size":20}',
            'hotword_result_path': 'data.items',
            'hotword_keyword_param': 'keywords',
        },
    },
]


def hotword_source_template_options():
    return [dict(item) for item in HOTWORD_SOURCE_TEMPLATE_OPTIONS]


def hotword_remote_source_presets():
    return [dict(item) for item in HOTWORD_REMOTE_SOURCE_PRESETS]


def hotword_remote_source_preset_meta(preset_key=''):
    raw = (preset_key or '').strip()
    for item in HOTWORD_REMOTE_SOURCE_PRESETS:
        if raw == item['key']:
            return dict(item)
    return dict(HOTWORD_REMOTE_SOURCE_PRESETS[0])


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


def _extract_value_by_path(row, path):
    current = row
    for token in [item for item in str(path or '').split('.') if item]:
        if isinstance(current, dict):
            current = current.get(token)
        elif isinstance(current, list):
            try:
                current = current[int(token)]
            except (TypeError, ValueError, IndexError):
                return None
        else:
            return None
        if current is None:
            return None
    return current


def _extract_first_non_empty(row, keys, default=''):
    for key in keys:
        value = _extract_value_by_path(row, key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return default


def _extract_first_number(row, keys, default=0):
    for key in keys:
        value = _extract_value_by_path(row, key)
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
        elif template['key'] == 'xhs_hot_queries':
            keyword = _extract_first_non_empty(row, ['query', 'keyword', 'hot_word', 'word', 'search_word'])
            title = _extract_first_non_empty(row, ['title', 'query', 'keyword', 'word']) or keyword
            link = _extract_first_non_empty(row, ['link', 'url', 'share_url'])
            author = _extract_first_non_empty(row, ['board_name', 'source', 'author'])
            summary = _extract_first_non_empty(row, ['summary', 'desc', 'description', 'display_text', 'subtitle'])
            views = _extract_first_number(row, ['hot_value', 'search_volume', 'search_cnt', 'hot_score', 'trend_score'])
            likes = _extract_first_number(row, ['like_count', 'likes'])
            favorites = _extract_first_number(row, ['collect_count', 'favorites'])
            comments = _extract_first_number(row, ['comment_count', 'comments'])
            publish_time = _extract_first_non_empty(row, ['publish_time', 'event_time', 'create_time', 'updated_at'])
        elif template['key'] == 'xhs_note_search':
            keyword = _extract_first_non_empty(row, ['keyword', 'query', 'search_word', 'tag'])
            title = _extract_first_non_empty(row, ['display_title', 'title', 'note_card.display_title', 'note_card.title', 'note_card.note_title'])
            link = _extract_first_non_empty(row, ['link', 'note_url', 'share_url', 'url', 'note_card.share_url', 'note_card.url'])
            author = _extract_first_non_empty(row, [
                'author',
                'nickname',
                'user.nickname',
                'user.nick_name',
                'note_card.user.nickname',
                'account_name',
            ])
            summary = _extract_first_non_empty(row, [
                'summary',
                'desc',
                'description',
                'content',
                'note_card.desc',
                'note_card.display_desc',
            ])
            views = _extract_first_number(row, [
                'views',
                'view_count',
                'read_count',
                'impression_cnt',
                'exposure_count',
                'note_card.view_count',
            ])
            likes = _extract_first_number(row, [
                'likes',
                'like_count',
                'liked_count',
                'interact_info.liked_count',
                'note_card.interact_info.liked_count',
            ])
            favorites = _extract_first_number(row, [
                'favorites',
                'collect_count',
                'favorite_count',
                'collected_count',
                'interact_info.collected_count',
                'note_card.interact_info.collected_count',
            ])
            comments = _extract_first_number(row, [
                'comments',
                'comment_count',
                'interact_info.comment_count',
                'note_card.interact_info.comment_count',
            ])
            publish_time = _extract_first_non_empty(row, [
                'publish_time',
                'create_time',
                'time',
                'last_update_time',
                'note_card.time',
            ])
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
            'normalized_rank': _extract_first_number(row, ['rank', 'position', 'index', 'source_rank', 'note_rank'], index),
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
        '{{trend_type}}': context.get('trend_type', 'note_search'),
        '{{page_size}}': context.get('page_size', 20),
        '{{max_related_queries}}': context.get('max_related_queries', 20),
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
        '{{trend_type}}': str(context.get('trend_type', 'note_search')),
        '{{page_size}}': str(context.get('page_size', 20)),
        '{{max_related_queries}}': str(context.get('max_related_queries', 20)),
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
    trend_type = (config.get('trend_type') or 'note_search').strip().lower() or 'note_search'
    if trend_type not in {'note_search', 'hot_queries'}:
        trend_type = 'note_search'
    page_size = min(max(safe_int(config.get('page_size'), 20), 1), 50)
    max_related_queries = min(max(safe_int(config.get('max_related_queries'), 20), 1), 50)
    context = {
        'keywords_joined': ','.join(keywords),
        'keywords_list': list(keywords),
        'keyword_count': len(keywords),
        'first_keyword': keywords[0] if keywords else '',
        'source_platform': source_platform,
        'source_channel': source_channel,
        'batch_name': batch_name,
        'trend_type': trend_type,
        'page_size': page_size,
        'max_related_queries': max_related_queries,
    }
    rendered_headers = _render_template_value(headers_json, context) if isinstance(headers_json, dict) else {}
    rendered_query = _render_template_value(query_json, context) if isinstance(query_json, dict) else {}
    rendered_body = _render_template_value(body_json, context) if isinstance(body_json, dict) else {}

    if not rendered_query and api_method == 'GET' and keywords:
        rendered_query = {keyword_param: ','.join(keywords)}
    if not rendered_body and api_method != 'GET' and keywords:
        if api_url.rstrip('/').endswith('/xhs/trends'):
            rendered_body = {
                'keywords': list(keywords),
                'trend_type': trend_type,
                'page_size': page_size,
                'max_related_queries': max_related_queries,
                'source_channel': source_channel,
                'batch_name': batch_name,
            }
        else:
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
        'trend_type': trend_type,
        'page_size': page_size,
        'max_related_queries': max_related_queries,
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
