import json
import re
from datetime import datetime
from urllib.parse import unquote, urlparse, urlunparse

from models import db, CreatorAccount, CreatorPost, CreatorAccountSnapshot, Submission


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coalesce_text(*values):
    for value in values:
        if isinstance(value, str):
            text = value.strip()
            if text:
                return text
    return ''


def _normalize_url(url, keep_query=False):
    raw = (url or '').strip()
    if not raw:
        return ''
    try:
        parsed = urlparse(raw)
    except ValueError:
        return raw
    if not parsed.scheme or not parsed.netloc:
        return raw
    path = parsed.path.rstrip('/')
    query = parsed.query if keep_query else ''
    fragment = parsed.fragment if keep_query else ''
    return urlunparse((parsed.scheme, parsed.netloc.lower(), path, '', query, fragment))


def normalize_tracking_url(url):
    return _normalize_url(url, keep_query=False)


def extract_xhs_post_id(url):
    raw = (url or '').strip()
    if not raw:
        return ''
    decoded = unquote(raw)
    patterns = [
        r'/explore/([0-9a-zA-Z]+)',
        r'/discovery/item/([0-9a-zA-Z]+)',
        r'item/([0-9a-zA-Z]+)',
    ]
    for pattern in patterns:
        matched = re.search(pattern, decoded, flags=re.IGNORECASE)
        if matched:
            return matched.group(1)
    return ''


def canonicalize_xhs_post_url(url):
    normalized = normalize_tracking_url(url)
    post_id = extract_xhs_post_id(normalized or url)
    if post_id:
        return f'https://www.xiaohongshu.com/explore/{post_id}'
    return normalized


def _creator_post_interactions(post):
    return (post.likes or 0) + (post.favorites or 0) + (post.comments or 0)


def _infer_viral_post(views=0, likes=0, favorites=0, comments=0, exposures=0):
    interactions = (likes or 0) + (favorites or 0) + (comments or 0)
    return (views or 0) >= 10000 or (exposures or 0) >= 30000 or interactions >= 1000


def _serialize_post_brief(post):
    if not post:
        return None
    return {
        'id': post.id,
        'title': post.title or '',
        'post_url': post.post_url or '',
        'views': post.views or 0,
        'likes': post.likes or 0,
        'favorites': post.favorites or 0,
        'comments': post.comments or 0,
        'interactions': _creator_post_interactions(post),
        'publish_time': post.publish_time.strftime('%Y-%m-%d %H:%M:%S') if post.publish_time else '',
    }


def _current_month_range(now=None):
    current = now or datetime.now()
    month_start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return month_start, current


def _filter_posts_in_range(posts, start_dt=None, end_dt=None):
    if not posts:
        return []
    start_dt = start_dt or datetime.min
    end_dt = end_dt or datetime.max
    rows = []
    for post in posts:
        active_time = post.publish_time or post.created_at or datetime.min
        if start_dt <= active_time <= end_dt:
            rows.append(post)
    return rows


def _tracking_status_label(status):
    return {
        'empty': '未开启',
        'pending': '待绑定',
        'account_bound': '已绑定账号',
        'tracking': '跟踪中',
    }.get(status or '', '跟踪中')


def _find_tracking_account(registration, submission, profile_url=''):
    account_id = _safe_int(getattr(submission, 'xhs_creator_account_id', 0), 0)
    if account_id > 0:
        account = CreatorAccount.query.get(account_id)
        if account:
            return account

    profile_url = normalize_tracking_url(profile_url or getattr(submission, 'xhs_profile_link', '') or '')
    platform = 'xhs'
    if profile_url:
        account = CreatorAccount.query.filter_by(platform=platform, profile_url=profile_url).order_by(
            CreatorAccount.updated_at.desc(),
            CreatorAccount.id.desc(),
        ).first()
        if account:
            return account

    handle = (getattr(registration, 'xhs_account', '') or '').strip()
    phone = (getattr(registration, 'phone', '') or '').strip()
    if phone and handle:
        account = CreatorAccount.query.filter_by(
            platform=platform,
            owner_phone=phone,
            account_handle=handle,
        ).order_by(CreatorAccount.updated_at.desc(), CreatorAccount.id.desc()).first()
        if account:
            return account

    if phone:
        account = CreatorAccount.query.filter_by(platform=platform, owner_phone=phone).order_by(
            CreatorAccount.updated_at.desc(),
            CreatorAccount.id.desc(),
        ).first()
        if account:
            return account

    if handle:
        account = CreatorAccount.query.filter_by(platform=platform, account_handle=handle).order_by(
            CreatorAccount.updated_at.desc(),
            CreatorAccount.id.desc(),
        ).first()
        if account:
            return account

    return None


def _ensure_tracking_account(registration, submission, profile_url=''):
    normalized_profile = normalize_tracking_url(profile_url or getattr(submission, 'xhs_profile_link', '') or '')
    account = _find_tracking_account(registration, submission, normalized_profile)
    if not account:
        account = CreatorAccount(platform='xhs')
        db.session.add(account)

    handle = _coalesce_text(getattr(registration, 'xhs_account', ''), account.account_handle, account.display_name)
    display_name = _coalesce_text(account.display_name, getattr(registration, 'xhs_account', ''), handle)
    account.platform = 'xhs'
    if getattr(registration, 'name', ''):
        account.owner_name = registration.name
    if getattr(registration, 'phone', ''):
        account.owner_phone = registration.phone
    account.account_handle = handle or f'registration_{registration.id}'
    account.display_name = display_name or account.account_handle
    if normalized_profile:
        account.profile_url = normalized_profile
        submission.xhs_profile_link = normalized_profile
    if not account.source_channel:
        account.source_channel = 'registration_tracking'
    if not account.status:
        account.status = 'active'
    account.last_synced_at = datetime.now()
    db.session.flush()
    submission.xhs_creator_account_id = account.id
    return account


def _match_primary_post(submission, account, note_url=''):
    primary_post_id = _safe_int(getattr(submission, 'xhs_primary_post_id', 0), 0)
    if primary_post_id > 0:
        post = CreatorPost.query.filter_by(id=primary_post_id, creator_account_id=account.id).first()
        if post:
            return post

    current_url = canonicalize_xhs_post_url(note_url or getattr(submission, 'xhs_link', '') or '')
    current_post_id = extract_xhs_post_id(current_url)
    if current_post_id:
        post = CreatorPost.query.filter_by(creator_account_id=account.id, platform_post_id=current_post_id).first()
        if post:
            return post
    if current_url:
        post = CreatorPost.query.filter_by(creator_account_id=account.id, post_url=current_url).first()
        if post:
            return post
    return None


def _upsert_primary_post(registration, submission, account, payload=None):
    payload = payload or {}
    note_url = canonicalize_xhs_post_url(payload.get('xhs_link') or getattr(submission, 'xhs_link', '') or '')
    if not note_url:
        return None

    topic_name = getattr(registration.topic, 'topic_name', '') if getattr(registration, 'topic', None) else ''
    post = _match_primary_post(submission, account, note_url)
    if not post:
        post = CreatorPost(creator_account_id=account.id)
        db.session.add(post)

    title = _coalesce_text(
        payload.get('note_title'),
        getattr(submission, 'note_title', ''),
        post.title,
        topic_name,
        '小红书提报笔记',
    )
    post.platform_post_id = extract_xhs_post_id(note_url) or post.platform_post_id
    post.title = title
    post.post_url = note_url
    post.topic_title = _coalesce_text(
        topic_name,
        post.topic_title,
    )
    post.views = _safe_int(payload.get('xhs_views'), getattr(submission, 'xhs_views', 0) or post.views or 0)
    post.likes = _safe_int(payload.get('xhs_likes'), getattr(submission, 'xhs_likes', 0) or post.likes or 0)
    post.favorites = _safe_int(payload.get('xhs_favorites'), getattr(submission, 'xhs_favorites', 0) or post.favorites or 0)
    post.comments = _safe_int(payload.get('xhs_comments'), getattr(submission, 'xhs_comments', 0) or post.comments or 0)
    post.registration_id = registration.id
    post.topic_id = registration.topic_id
    post.submission_id = submission.id
    if not post.publish_time:
        post.publish_time = getattr(submission, 'created_at', None) or getattr(registration, 'created_at', None) or datetime.now()
    if not post.source_channel:
        post.source_channel = 'registration_submission'
    post.raw_payload = json.dumps({
        'registration_id': registration.id,
        'submission_id': submission.id,
        'xhs_profile_link': getattr(submission, 'xhs_profile_link', '') or '',
        'xhs_link': note_url,
        'note_title': getattr(submission, 'note_title', '') or '',
        'note_content': getattr(submission, 'note_content', '') or '',
    }, ensure_ascii=False)
    post.is_viral = _infer_viral_post(
        views=post.views,
        likes=post.likes,
        favorites=post.favorites,
        comments=post.comments,
        exposures=post.exposures,
    )
    db.session.flush()
    submission.xhs_link = note_url
    submission.xhs_primary_post_id = post.id
    return post


def refresh_creator_account_snapshot(account, snapshot_date=None):
    if not account:
        return None

    posts = CreatorPost.query.filter_by(creator_account_id=account.id).all()
    total_views = sum(post.views or 0 for post in posts)
    total_interactions = sum(_creator_post_interactions(post) for post in posts)
    snapshot_date = snapshot_date or datetime.now().date()
    snapshot = CreatorAccountSnapshot.query.filter_by(
        creator_account_id=account.id,
        snapshot_date=snapshot_date,
    ).order_by(CreatorAccountSnapshot.created_at.desc(), CreatorAccountSnapshot.id.desc()).first()
    if not snapshot:
        snapshot = CreatorAccountSnapshot(
            creator_account_id=account.id,
            snapshot_date=snapshot_date,
        )
        db.session.add(snapshot)

    snapshot.follower_count = account.follower_count or 0
    snapshot.post_count = len(posts)
    snapshot.total_views = total_views
    snapshot.total_interactions = total_interactions
    if not snapshot.source_channel:
        snapshot.source_channel = 'registration_tracking'
    account.last_synced_at = datetime.now()
    db.session.flush()
    return snapshot


def refresh_submission_tracking_state(submission):
    if not submission:
        return None

    account = None
    account_id = _safe_int(getattr(submission, 'xhs_creator_account_id', 0), 0)
    if account_id > 0:
        account = CreatorAccount.query.get(account_id)

    if not account:
        submission.xhs_tracking_enabled = False
        submission.xhs_tracking_status = 'pending' if (submission.xhs_profile_link or submission.xhs_link) else 'empty'
        submission.xhs_tracking_message = '待绑定账号跟踪对象' if (submission.xhs_profile_link or submission.xhs_link) else '待填写账号主页链接和笔记链接'
        return None

    posts = CreatorPost.query.filter_by(creator_account_id=account.id).order_by(
        CreatorPost.publish_time.desc(),
        CreatorPost.updated_at.desc(),
        CreatorPost.id.desc(),
    ).all()
    month_start, now = _current_month_range()
    month_posts = _filter_posts_in_range(posts, month_start, now)

    submission.xhs_tracking_enabled = True
    submission.xhs_tracking_status = 'tracking' if posts else 'account_bound'
    submission.xhs_tracking_message = (
        (
            f'已绑定账号，本月同步 {len(month_posts)} 条小红书笔记，账号累计 {len(posts)} 条'
            if month_posts else
            f'已绑定账号，本月暂未同步到新笔记，账号累计 {len(posts)} 条'
        )
        if posts else
        '已绑定账号，等待同步该账号下的笔记'
    )
    submission.xhs_last_synced_at = account.last_synced_at or datetime.now()
    return month_posts[0] if month_posts else (posts[0] if posts else None)


def sync_tracking_from_submission(registration, submission, payload=None):
    payload = payload or {}
    profile_url = normalize_tracking_url(payload.get('xhs_profile_link') or getattr(submission, 'xhs_profile_link', '') or '')
    note_url = canonicalize_xhs_post_url(payload.get('xhs_link') or getattr(submission, 'xhs_link', '') or '')

    if profile_url:
        submission.xhs_profile_link = profile_url
    if note_url:
        submission.xhs_link = note_url

    if not (submission.xhs_profile_link or submission.xhs_link):
        refresh_submission_tracking_state(submission)
        return build_registration_tracking_summary(registration, submission=submission)

    account = _ensure_tracking_account(registration, submission, submission.xhs_profile_link)
    _upsert_primary_post(registration, submission, account, payload=payload)
    refresh_creator_account_snapshot(account)
    refresh_submission_tracking_state(submission)
    return build_registration_tracking_summary(registration, submission=submission)


def sync_tracking_for_creator_account(account, refresh_snapshot=True):
    if not account:
        return []

    if refresh_snapshot:
        refresh_creator_account_snapshot(account)
    else:
        account.last_synced_at = datetime.now()

    refreshed_submission_ids = []
    for submission in Submission.query.filter_by(xhs_creator_account_id=account.id).all():
        refresh_submission_tracking_state(submission)
        refreshed_submission_ids.append(submission.id)
    return refreshed_submission_ids


def build_registration_tracking_summary(registration, submission=None):
    submission = submission or getattr(registration, 'submission', None)
    if not submission:
        return {
            'enabled': False,
            'status': 'empty',
            'status_label': _tracking_status_label('empty'),
            'message': '尚未提交账号主页链接和笔记链接',
            'profile_url': '',
            'account_handle': getattr(registration, 'xhs_account', '') or '',
            'creator_account_id': 0,
            'total_post_count': 0,
            'total_views': 0,
            'total_interactions': 0,
            'follower_count': 0,
            'last_synced_at': '',
            'current_month_label': datetime.now().strftime('%Y-%m'),
            'current_month_post_count': 0,
            'current_month_views': 0,
            'current_month_interactions': 0,
            'tracked_posts': [],
            'latest_post': None,
            'best_post': None,
        }

    refresh_submission_tracking_state(submission)
    account = None
    account_id = _safe_int(getattr(submission, 'xhs_creator_account_id', 0), 0)
    if account_id > 0:
        account = CreatorAccount.query.get(account_id)

    if not account:
        status = getattr(submission, 'xhs_tracking_status', '') or ('pending' if (submission.xhs_profile_link or submission.xhs_link) else 'empty')
        return {
            'enabled': bool(getattr(submission, 'xhs_tracking_enabled', False)),
            'status': status,
            'status_label': _tracking_status_label(status),
            'message': getattr(submission, 'xhs_tracking_message', '') or '待绑定账号跟踪对象',
            'profile_url': getattr(submission, 'xhs_profile_link', '') or '',
            'account_handle': getattr(registration, 'xhs_account', '') or '',
            'creator_account_id': 0,
            'total_post_count': 0,
            'total_views': 0,
            'total_interactions': 0,
            'follower_count': 0,
            'last_synced_at': getattr(submission, 'xhs_last_synced_at', None).strftime('%Y-%m-%d %H:%M:%S') if getattr(submission, 'xhs_last_synced_at', None) else '',
            'current_month_label': datetime.now().strftime('%Y-%m'),
            'current_month_post_count': 0,
            'current_month_views': 0,
            'current_month_interactions': 0,
            'tracked_posts': [],
            'latest_post': None,
            'best_post': None,
        }

    posts = CreatorPost.query.filter_by(creator_account_id=account.id).order_by(
        CreatorPost.publish_time.desc(),
        CreatorPost.updated_at.desc(),
        CreatorPost.id.desc(),
    ).all()
    month_start, now = _current_month_range()
    month_posts = _filter_posts_in_range(posts, month_start, now)
    scoped_posts = month_posts or posts
    best_post = sorted(
        scoped_posts,
        key=lambda item: ((item.views or 0), _creator_post_interactions(item), (item.follower_delta or 0), (item.exposures or 0)),
        reverse=True,
    )[0] if scoped_posts else None
    latest_post = scoped_posts[0] if scoped_posts else None
    total_views = sum(post.views or 0 for post in posts)
    total_interactions = sum(_creator_post_interactions(post) for post in posts)
    current_month_views = sum(post.views or 0 for post in month_posts)
    current_month_interactions = sum(_creator_post_interactions(post) for post in month_posts)
    status = getattr(submission, 'xhs_tracking_status', '') or ('tracking' if posts else 'account_bound')
    return {
        'enabled': bool(getattr(submission, 'xhs_tracking_enabled', False) or account or submission.xhs_profile_link or submission.xhs_link),
        'status': status,
        'status_label': _tracking_status_label(status),
        'message': getattr(submission, 'xhs_tracking_message', '') or (
            (
                f'已绑定账号，本月同步 {len(month_posts)} 条小红书笔记，账号累计 {len(posts)} 条'
                if month_posts else
                f'已绑定账号，本月暂未同步到新笔记，账号累计 {len(posts)} 条'
            )
            if posts else
            '已绑定账号，等待同步该账号下的笔记'
        ),
        'profile_url': account.profile_url or getattr(submission, 'xhs_profile_link', '') or '',
        'account_handle': account.account_handle or getattr(registration, 'xhs_account', '') or '',
        'creator_account_id': account.id,
        'total_post_count': len(posts),
        'total_views': total_views,
        'total_interactions': total_interactions,
        'follower_count': account.follower_count or 0,
        'last_synced_at': (getattr(submission, 'xhs_last_synced_at', None) or account.last_synced_at).strftime('%Y-%m-%d %H:%M:%S') if ((getattr(submission, 'xhs_last_synced_at', None) or account.last_synced_at)) else '',
        'current_month_label': now.strftime('%Y-%m'),
        'current_month_post_count': len(month_posts),
        'current_month_views': current_month_views,
        'current_month_interactions': current_month_interactions,
        'tracked_posts': [_serialize_post_brief(post) for post in month_posts[:10]],
        'latest_post': _serialize_post_brief(latest_post),
        'best_post': _serialize_post_brief(best_post),
    }


def backfill_submission_tracking():
    synced = 0
    for submission in Submission.query.order_by(Submission.id.asc()).all():
        if not ((submission.xhs_link or '').strip() or (getattr(submission, 'xhs_profile_link', '') or '').strip()):
            continue
        registration = getattr(submission, 'registration', None)
        if not registration:
            continue
        sync_tracking_from_submission(registration, submission)
        synced += 1
    return synced
