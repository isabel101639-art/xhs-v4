import hashlib
from datetime import datetime, timedelta

from crawler_service.providers.base import BaseCrawlerProvider


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _deterministic_seed(*parts):
    text = '|'.join(str(item or '') for item in parts)
    return int(hashlib.md5(text.encode('utf-8')).hexdigest()[:8], 16)


class MockCrawlerProvider(BaseCrawlerProvider):
    async def fetch_account_posts(self, payload):
        accounts = []
        posts = []
        snapshots = []
        now = datetime.now()
        max_posts = min(max(_safe_int(getattr(payload, 'max_posts_per_account', 60), 60), 1), self.settings.xhs_max_posts_per_account)
        date_from = self._parse_date_boundary(getattr(payload, 'date_from', ''), start=True)
        date_to = self._parse_date_boundary(getattr(payload, 'date_to', ''), start=False)
        if getattr(payload, 'current_month_only', False) and not date_from:
            date_from = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if getattr(payload, 'current_month_only', False) and not date_to:
            date_to = now

        for index, target in enumerate(payload.targets, start=1):
            profile_url = (target.profile_url or '').strip()
            account_handle = (target.account_handle or '').strip() or f'mock_handle_{index}'
            if not profile_url:
                profile_url = self.settings.xhs_profile_url_template.format(account_handle=account_handle)
            seed = _deterministic_seed(profile_url, account_handle, target.owner_phone)
            follower_count = 1000 + (seed % 5000)
            display_name = target.owner_name or f'模拟账号{account_handle[-4:]}'

            accounts.append({
                'platform': 'xhs',
                'owner_name': target.owner_name or '',
                'owner_phone': target.owner_phone or '',
                'account_handle': account_handle,
                'display_name': display_name,
                'profile_url': profile_url,
                'follower_count': follower_count,
                'source_channel': payload.source_channel or 'mock_provider',
                'notes': '模拟抓取返回，用于联调账号同步链路。',
            })

            total_views = 0
            total_interactions = 0
            for post_index in range(max_posts):
                post_seed = seed + post_index * 97
                post_id = f'mock{post_seed:08x}'
                views = 200 + (post_seed % 3000)
                likes = 20 + (post_seed % 200)
                favorites = 10 + (post_seed % 120)
                comments = 5 + (post_seed % 80)
                publish_time = now - timedelta(days=post_index * 2, hours=index)
                if date_from and publish_time < date_from:
                    continue
                if date_to and publish_time > date_to:
                    continue
                total_views += views
                total_interactions += likes + favorites + comments
                posts.append({
                    'platform': 'xhs',
                    'account_handle': account_handle,
                    'owner_phone': target.owner_phone or '',
                    'owner_name': target.owner_name or '',
                    'profile_url': profile_url,
                    'registration_id': _safe_int(target.registration_id),
                    'topic_id': _safe_int(target.topic_id),
                    'submission_id': _safe_int(target.submission_id),
                    'platform_post_id': post_id,
                    'title': f'模拟回流笔记 {post_index + 1}',
                    'post_url': f'https://www.xiaohongshu.com/explore/{post_id}',
                    'publish_time': publish_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'topic_title': '',
                    'views': views,
                    'exposures': views * 2,
                    'likes': likes,
                    'favorites': favorites,
                    'comments': comments,
                    'shares': 0,
                    'follower_delta': post_seed % 20,
                    'source_channel': payload.source_channel or 'mock_provider',
                })

            snapshots.append({
                'platform': 'xhs',
                'account_handle': account_handle,
                'owner_phone': target.owner_phone or '',
                'owner_name': target.owner_name or '',
                'profile_url': profile_url,
                'snapshot_date': now.strftime('%Y-%m-%d'),
                'follower_count': follower_count,
                'post_count': self.settings.mock_posts_per_account,
                'total_views': total_views,
                'total_interactions': total_interactions,
                'source_channel': payload.source_channel or 'mock_provider',
            })

        return {
            'success': True,
            'provider': 'mock',
            'batch_name': payload.batch_name,
            'source_channel': payload.source_channel,
            'accounts': accounts,
            'posts': posts,
            'snapshots': snapshots,
            'meta': {
                'target_count': len(payload.targets),
                'returned_account_count': len(accounts),
                'returned_post_count': len(posts),
                'current_month_only': bool(getattr(payload, 'current_month_only', False)),
                'date_from': getattr(payload, 'date_from', ''),
                'date_to': getattr(payload, 'date_to', ''),
            },
        }

    def _parse_date_boundary(self, raw, start=True):
        text = (raw or '').strip()
        if not text:
            return None
        formats = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d']
        for fmt in formats:
            try:
                parsed = datetime.strptime(text, fmt)
                if fmt == '%Y-%m-%d' and not start:
                    return parsed.replace(hour=23, minute=59, second=59, microsecond=999999)
                return parsed
            except ValueError:
                continue
        return None
