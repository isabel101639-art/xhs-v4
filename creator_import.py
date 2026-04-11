import json
from collections import Counter
from datetime import datetime

from creator_tracking import canonicalize_xhs_post_url, normalize_tracking_url, sync_tracking_for_creator_account
from models import (
    db,
    CreatorAccount,
    CreatorPost,
    CreatorAccountSnapshot,
    PLATFORM_DEFINITIONS,
)


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 'yes', 'y', 'on'}
    return False


def _parse_datetime(value):
    if not value:
        return None
    value = str(value).strip()
    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M', '%Y-%m-%d', '%Y/%m/%d %H:%M:%S', '%Y/%m/%d']:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value).strip(), '%Y-%m-%d').date()
    except ValueError:
        return None


def _infer_viral_post(views=0, likes=0, favorites=0, comments=0, exposures=0):
    interactions = (likes or 0) + (favorites or 0) + (comments or 0)
    return (views or 0) >= 10000 or (exposures or 0) >= 30000 or interactions >= 1000


def normalize_creator_platform(value=''):
    raw = (value or '').strip().lower()
    alias_map = {
        'xhs': 'xhs',
        'xiaohongshu': 'xhs',
        '小红书': 'xhs',
        'red': 'xhs',
        'douyin': 'douyin',
        '抖音': 'douyin',
        'dy': 'douyin',
        'video': 'video',
        'shipinhao': 'video',
        'wechat_video': 'video',
        '视频号': 'video',
        'weibo': 'weibo',
        '微博': 'weibo',
    }
    valid_keys = {key for key, _ in PLATFORM_DEFINITIONS}
    return alias_map.get(raw, raw if raw in valid_keys else 'xhs')


def parse_creator_import_bundle(raw_payload=''):
    payload = (raw_payload or '').strip()
    if not payload:
        return {
            'accounts': [],
            'posts': [],
            'snapshots': [],
        }

    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f'导入 JSON 格式不正确：{exc}')

    if isinstance(parsed, list):
        return {
            'accounts': parsed,
            'posts': [],
            'snapshots': [],
        }

    if not isinstance(parsed, dict):
        raise ValueError('导入内容必须是 JSON 对象或数组')

    def _ensure_list(value):
        return value if isinstance(value, list) else []

    return {
        'accounts': _ensure_list(parsed.get('accounts') or parsed.get('creator_accounts')),
        'posts': _ensure_list(parsed.get('posts') or parsed.get('creator_posts')),
        'snapshots': _ensure_list(parsed.get('snapshots') or parsed.get('creator_snapshots')),
    }


def _creator_account_identity_keys(platform='', account_handle='', display_name='', owner_phone='', profile_url=''):
    keys = []
    platform = normalize_creator_platform(platform)
    handle = (account_handle or '').strip().lower()
    name = (display_name or '').strip().lower()
    phone = (owner_phone or '').strip()
    normalized_profile = normalize_tracking_url(profile_url)
    if handle:
        keys.append(f'{platform}:handle:{handle}')
    if name:
        keys.append(f'{platform}:name:{name}')
    if phone:
        keys.append(f'phone:{phone}')
    if normalized_profile:
        keys.append(f'{platform}:profile:{normalized_profile}')
    return keys


def _build_creator_account_cache():
    cache = {}
    for account in CreatorAccount.query.all():
        keys = _creator_account_identity_keys(
            account.platform,
            account.account_handle,
            account.display_name,
            account.owner_phone,
            account.profile_url,
        )
        for key in keys:
            cache[key] = account
    return cache


def _cache_creator_account(account, cache):
    keys = _creator_account_identity_keys(
        account.platform,
        account.account_handle,
        account.display_name,
        account.owner_phone,
        account.profile_url,
    )
    for key in keys:
        cache[key] = account


def _find_creator_account_for_import(row, cache):
    if not isinstance(row, dict):
        return None
    account_id = _safe_int(row.get('id') or row.get('creator_account_id'), 0)
    if account_id > 0:
        account = CreatorAccount.query.get(account_id)
        if account:
            return account
    keys = _creator_account_identity_keys(
        row.get('platform'),
        row.get('account_handle') or row.get('creator_account_handle'),
        row.get('display_name') or row.get('creator_display_name'),
        row.get('owner_phone') or row.get('phone'),
        row.get('profile_url') or row.get('xhs_profile_link'),
    )
    for key in keys:
        if key in cache:
            return cache[key]
    return None


def _upsert_creator_account_row(row, cache):
    if not isinstance(row, dict):
        return None, 'skip'
    account = _find_creator_account_for_import(row, cache)
    action = 'update' if account else 'create'
    if not account:
        account = CreatorAccount()
        db.session.add(account)

    platform = normalize_creator_platform(row.get('platform'))
    account_handle = (row.get('account_handle') or row.get('creator_account_handle') or '').strip()
    display_name = (row.get('display_name') or row.get('creator_display_name') or '').strip()
    owner_name = (row.get('owner_name') or '').strip()
    owner_phone = (row.get('owner_phone') or row.get('phone') or '').strip()
    profile_url = normalize_tracking_url(row.get('profile_url') or row.get('xhs_profile_link') or '')
    if not account_handle and not display_name:
        return None, 'skip'

    account.platform = platform
    account.owner_name = owner_name
    account.owner_phone = owner_phone
    account.account_handle = account_handle or display_name
    account.display_name = display_name or account.account_handle
    if profile_url:
        account.profile_url = profile_url
    account.follower_count = _safe_int(row.get('follower_count'), account.follower_count or 0)
    account.source_channel = (row.get('source_channel') or account.source_channel or 'import').strip()
    account.status = (row.get('status') or account.status or 'active').strip()
    account.notes = (row.get('notes') or '').strip()
    account.last_synced_at = _parse_datetime(row.get('last_synced_at')) or datetime.now()
    db.session.flush()
    _cache_creator_account(account, cache)
    return account, action


def _resolve_or_create_import_account(row, cache, created_counter):
    account = _find_creator_account_for_import(row, cache)
    if account:
        return account

    fallback_row = {
        'platform': row.get('platform'),
        'account_handle': row.get('account_handle') or row.get('creator_account_handle'),
        'display_name': row.get('display_name') or row.get('creator_display_name') or row.get('account_handle') or row.get('creator_account_handle'),
        'owner_name': row.get('owner_name') or '',
        'owner_phone': row.get('owner_phone') or row.get('phone') or '',
        'source_channel': row.get('source_channel') or 'import_placeholder',
        'notes': '导入时自动创建的占位账号',
    }
    account, action = _upsert_creator_account_row(fallback_row, cache)
    if account and action == 'create':
        created_counter['placeholder_accounts'] += 1
    return account


def _match_creator_post(account, row):
    platform_post_id = (row.get('platform_post_id') or '').strip()
    if platform_post_id:
        post = CreatorPost.query.filter_by(creator_account_id=account.id, platform_post_id=platform_post_id).first()
        if post:
            return post
    post_url = (row.get('post_url') or '').strip()
    if post_url:
        post = CreatorPost.query.filter_by(creator_account_id=account.id, post_url=post_url).first()
        if post:
            return post
    title = (row.get('title') or '').strip()
    publish_time = _parse_datetime(row.get('publish_time'))
    if title and publish_time:
        return CreatorPost.query.filter_by(creator_account_id=account.id, title=title, publish_time=publish_time).first()
    return None


def preview_creator_import_bundle(bundle):
    account_cache = _build_creator_account_cache()
    summary = Counter()
    samples = {
        'accounts': [],
        'posts': [],
        'snapshots': [],
    }

    for row in bundle.get('accounts', []):
        if not isinstance(row, dict):
            summary['accounts_skipped'] += 1
            continue
        platform = normalize_creator_platform(row.get('platform'))
        account_handle = (row.get('account_handle') or row.get('creator_account_handle') or '').strip()
        display_name = (row.get('display_name') or row.get('creator_display_name') or '').strip()
        if not account_handle and not display_name:
            summary['accounts_skipped'] += 1
            continue
        existing = _find_creator_account_for_import(row, account_cache)
        action = 'update' if existing else 'create'
        summary[f'accounts_{action}'] += 1
        if len(samples['accounts']) < 3:
            samples['accounts'].append({
                'platform': platform,
                'account_handle': account_handle or display_name,
                'display_name': display_name or account_handle,
            })

    imported_account_keys = set()
    for row in bundle.get('accounts', []):
        keys = _creator_account_identity_keys(
            row.get('platform'),
            row.get('account_handle') or row.get('creator_account_handle'),
            row.get('display_name') or row.get('creator_display_name'),
            row.get('owner_phone') or row.get('phone'),
            row.get('profile_url') or row.get('xhs_profile_link'),
        )
        for key in keys:
            imported_account_keys.add(key)

    def preview_account_exists(row):
        return _find_creator_account_for_import(row, account_cache) is not None or bool(
            imported_account_keys.intersection(_creator_account_identity_keys(
                row.get('platform'),
                row.get('account_handle') or row.get('creator_account_handle'),
                row.get('display_name') or row.get('creator_display_name'),
                row.get('owner_phone') or row.get('phone'),
                row.get('profile_url') or row.get('xhs_profile_link'),
            ))
        )

    for row in bundle.get('posts', []):
        title = (row.get('title') or '').strip()
        if not title:
            summary['posts_skipped'] += 1
            continue
        if preview_account_exists(row):
            summary['posts_ready'] += 1
        else:
            summary['posts_need_placeholder'] += 1
        if len(samples['posts']) < 3:
            samples['posts'].append({
                'title': title,
                'platform': normalize_creator_platform(row.get('platform')),
                'account_handle': (row.get('account_handle') or row.get('creator_account_handle') or '').strip(),
            })

    for row in bundle.get('snapshots', []):
        snapshot_date = _parse_date(row.get('snapshot_date'))
        if not snapshot_date:
            summary['snapshots_skipped'] += 1
            continue
        if preview_account_exists(row):
            summary['snapshots_ready'] += 1
        else:
            summary['snapshots_need_placeholder'] += 1
        if len(samples['snapshots']) < 3:
            samples['snapshots'].append({
                'snapshot_date': snapshot_date.isoformat(),
                'platform': normalize_creator_platform(row.get('platform')),
                'account_handle': (row.get('account_handle') or row.get('creator_account_handle') or '').strip(),
            })

    return {
        'summary': {
            'accounts_total': len(bundle.get('accounts', [])),
            'posts_total': len(bundle.get('posts', [])),
            'snapshots_total': len(bundle.get('snapshots', [])),
            **dict(summary),
        },
        'samples': samples,
    }


def import_creator_bundle(bundle, log_operation):
    account_cache = _build_creator_account_cache()
    summary = Counter()
    touched_account_ids = set()

    for row in bundle.get('accounts', []):
        account, action = _upsert_creator_account_row(row, account_cache)
        if not account:
            summary['accounts_skipped'] += 1
            continue
        summary[f'accounts_{action}'] += 1
        touched_account_ids.add(account.id)

    for row in bundle.get('posts', []):
        title = (row.get('title') or '').strip()
        if not title:
            summary['posts_skipped'] += 1
            continue
        account = _resolve_or_create_import_account(row, account_cache, summary)
        if not account:
            summary['posts_skipped'] += 1
            continue
        post = _match_creator_post(account, row)
        action = 'update' if post else 'create'
        if not post:
            post = CreatorPost(creator_account_id=account.id)
            db.session.add(post)

        post.platform_post_id = (row.get('platform_post_id') or '').strip()
        post.registration_id = _safe_int(row.get('registration_id'), post.registration_id)
        post.topic_id = _safe_int(row.get('topic_id'), post.topic_id)
        post.submission_id = _safe_int(row.get('submission_id'), post.submission_id)
        post.title = title
        raw_post_url = (row.get('post_url') or '').strip()
        post.post_url = canonicalize_xhs_post_url(raw_post_url) if account.platform == 'xhs' else normalize_tracking_url(raw_post_url)
        if account.platform == 'xhs' and post.post_url and not post.platform_post_id:
            post.platform_post_id = post.post_url.rstrip('/').split('/')[-1]
        post.publish_time = _parse_datetime(row.get('publish_time'))
        post.topic_title = (row.get('topic_title') or '').strip()
        post.views = _safe_int(row.get('views'))
        post.exposures = _safe_int(row.get('exposures'))
        post.likes = _safe_int(row.get('likes'))
        post.favorites = _safe_int(row.get('favorites'))
        post.comments = _safe_int(row.get('comments'))
        post.shares = _safe_int(row.get('shares'))
        post.follower_delta = _safe_int(row.get('follower_delta'))
        raw_is_viral = row.get('is_viral')
        if raw_is_viral is None:
            post.is_viral = _infer_viral_post(
                views=post.views,
                likes=post.likes,
                favorites=post.favorites,
                comments=post.comments,
                exposures=post.exposures,
            )
        else:
            post.is_viral = _coerce_bool(raw_is_viral)
        post.source_channel = (row.get('source_channel') or post.source_channel or 'import').strip()
        post.raw_payload = json.dumps(row, ensure_ascii=False)
        account.last_synced_at = datetime.now()
        db.session.flush()
        summary[f'posts_{action}'] += 1
        touched_account_ids.add(account.id)

    for row in bundle.get('snapshots', []):
        snapshot_date = _parse_date(row.get('snapshot_date'))
        if not snapshot_date:
            summary['snapshots_skipped'] += 1
            continue
        account = _resolve_or_create_import_account(row, account_cache, summary)
        if not account:
            summary['snapshots_skipped'] += 1
            continue
        snapshot = CreatorAccountSnapshot.query.filter_by(
            creator_account_id=account.id,
            snapshot_date=snapshot_date,
        ).first()
        action = 'update' if snapshot else 'create'
        if not snapshot:
            snapshot = CreatorAccountSnapshot(
                creator_account_id=account.id,
                snapshot_date=snapshot_date,
            )
            db.session.add(snapshot)

        snapshot.follower_count = _safe_int(row.get('follower_count'), account.follower_count or 0)
        snapshot.post_count = _safe_int(row.get('post_count'))
        snapshot.total_views = _safe_int(row.get('total_views'))
        snapshot.total_interactions = _safe_int(row.get('total_interactions'))
        snapshot.source_channel = (row.get('source_channel') or snapshot.source_channel or 'import').strip()
        account.follower_count = snapshot.follower_count
        account.last_synced_at = datetime.now()
        db.session.flush()
        summary[f'snapshots_{action}'] += 1
        touched_account_ids.add(account.id)

    for account_id in touched_account_ids:
        account = CreatorAccount.query.get(account_id)
        if account:
            sync_tracking_for_creator_account(account)

    log_operation('import', 'creator_bundle', message='批量导入账号看板数据', detail=dict(summary))
    db.session.commit()
    return {
        'summary': dict(summary),
    }
