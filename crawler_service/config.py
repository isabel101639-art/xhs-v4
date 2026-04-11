import os
from dataclasses import dataclass


def _env_flag(name, default=False):
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {'1', 'true', 'yes', 'y', 'on'}


def _env_int(name, default=0, min_value=None, max_value=None):
    raw = (os.environ.get(name) or '').strip()
    value = default
    if raw:
        try:
            value = int(raw)
        except ValueError:
            value = default
    if min_value is not None:
        value = max(value, min_value)
    if max_value is not None:
        value = min(value, max_value)
    return value


@dataclass(frozen=True)
class CrawlerSettings:
    service_name: str
    provider: str
    port: int
    request_timeout_seconds: int
    xhs_profile_url_template: str
    playwright_headless: bool
    playwright_navigation_timeout_ms: int
    playwright_storage_state_path: str
    playwright_browser_channel: str
    xhs_profile_name_selector: str
    xhs_follower_count_selector: str
    xhs_post_card_selector: str
    xhs_post_link_selector: str
    xhs_post_title_selector: str
    xhs_post_likes_selector: str
    xhs_post_comments_selector: str
    xhs_post_favorites_selector: str
    xhs_post_views_selector: str
    xhs_post_time_selector: str
    xhs_wait_after_login_seconds: int
    xhs_debug_output_dir: str
    xhs_max_posts_per_account: int
    mock_posts_per_account: int


def get_settings():
    return CrawlerSettings(
        service_name=(os.environ.get('CRAWLER_SERVICE_NAME') or 'xhs-v4-crawler').strip() or 'xhs-v4-crawler',
        provider=(os.environ.get('CRAWLER_PROVIDER') or 'mock').strip().lower() or 'mock',
        port=_env_int('CRAWLER_PORT', 8081, 1, 65535),
        request_timeout_seconds=_env_int('CRAWLER_REQUEST_TIMEOUT_SECONDS', 60, 5, 300),
        xhs_profile_url_template=(
            os.environ.get('XHS_PROFILE_URL_TEMPLATE')
            or 'https://www.xiaohongshu.com/user/profile/{account_handle}'
        ).strip(),
        playwright_headless=_env_flag('PLAYWRIGHT_HEADLESS', True),
        playwright_navigation_timeout_ms=_env_int('PLAYWRIGHT_NAVIGATION_TIMEOUT_MS', 30000, 1000, 180000),
        playwright_storage_state_path=(os.environ.get('PLAYWRIGHT_STORAGE_STATE_PATH') or '').strip(),
        playwright_browser_channel=(os.environ.get('PLAYWRIGHT_BROWSER_CHANNEL') or '').strip(),
        xhs_profile_name_selector=(os.environ.get('XHS_PROFILE_NAME_SELECTOR') or '').strip(),
        xhs_follower_count_selector=(os.environ.get('XHS_FOLLOWER_COUNT_SELECTOR') or '').strip(),
        xhs_post_card_selector=(os.environ.get('XHS_POST_CARD_SELECTOR') or '').strip(),
        xhs_post_link_selector=(os.environ.get('XHS_POST_LINK_SELECTOR') or '').strip(),
        xhs_post_title_selector=(os.environ.get('XHS_POST_TITLE_SELECTOR') or '').strip(),
        xhs_post_likes_selector=(os.environ.get('XHS_POST_LIKES_SELECTOR') or '').strip(),
        xhs_post_comments_selector=(os.environ.get('XHS_POST_COMMENTS_SELECTOR') or '').strip(),
        xhs_post_favorites_selector=(os.environ.get('XHS_POST_FAVORITES_SELECTOR') or '').strip(),
        xhs_post_views_selector=(os.environ.get('XHS_POST_VIEWS_SELECTOR') or '').strip(),
        xhs_post_time_selector=(os.environ.get('XHS_POST_TIME_SELECTOR') or '').strip(),
        xhs_wait_after_login_seconds=_env_int('XHS_WAIT_AFTER_LOGIN_SECONDS', 90, 5, 600),
        xhs_debug_output_dir=(os.environ.get('XHS_DEBUG_OUTPUT_DIR') or '/tmp/xhs_crawler_debug').strip(),
        xhs_max_posts_per_account=_env_int('XHS_MAX_POSTS_PER_ACCOUNT', 20, 1, 100),
        mock_posts_per_account=_env_int('MOCK_POSTS_PER_ACCOUNT', 2, 1, 20),
    )
