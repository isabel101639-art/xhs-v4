from datetime import datetime

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='draft')
    source_type = db.Column(db.String(30), default='manual')
    source_activity_id = db.Column(db.Integer)
    source_snapshot_id = db.Column(db.Integer)
    archived_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)

    topics = db.relationship('Topic', backref='activity', lazy=True)
    snapshots = db.relationship('ActivitySnapshot', backref='activity', lazy=True)


class ActivitySnapshot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('activity.id'))
    snapshot_name = db.Column(db.String(200))
    source_status = db.Column(db.String(20))
    payload = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)


class BackupRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    backup_type = db.Column(db.String(50), nullable=False)
    target_type = db.Column(db.String(50), default='activity')
    target_id = db.Column(db.Integer)
    activity_id = db.Column(db.Integer)
    snapshot_id = db.Column(db.Integer)
    status = db.Column(db.String(20), default='success')
    trigger_mode = db.Column(db.String(20), default='manual')
    backup_name = db.Column(db.String(200))
    storage_path = db.Column(db.String(500))
    payload = db.Column(db.Text)
    summary = db.Column(db.Text)
    restored_activity_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.now)


class AdminUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    display_name = db.Column(db.String(100))
    role_key = db.Column(db.String(50), default='super_admin')
    status = db.Column(db.String(20), default='active')
    last_login_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)


class RolePermission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role_key = db.Column(db.String(50), unique=True, nullable=False)
    role_name = db.Column(db.String(100), nullable=False)
    permissions = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)


class OperationLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actor = db.Column(db.String(100), default='system')
    action = db.Column(db.String(100), nullable=False)
    target_type = db.Column(db.String(50), nullable=False)
    target_id = db.Column(db.Integer)
    message = db.Column(db.String(300))
    detail = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)


class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('activity.id'))
    topic_name = db.Column(db.String(200))
    keywords = db.Column(db.String(500))
    direction = db.Column(db.Text)
    reference_content = db.Column(db.Text)
    reference_link = db.Column(db.String(500))
    writing_example = db.Column(db.Text)
    quota = db.Column(db.Integer, default=30)
    group_num = db.Column(db.String(50))
    filled = db.Column(db.Integer, default=0)
    pool_status = db.Column(db.String(20), default='formal')
    source_type = db.Column(db.String(30), default='manual')
    source_ref_id = db.Column(db.Integer)
    source_snapshot_id = db.Column(db.Integer)
    published_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)

    registrations = db.relationship('Registration', backref='topic', lazy=True)


class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'))
    group_num = db.Column(db.String(50))
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    xhs_account = db.Column(db.String(100))
    status = db.Column(db.String(20), default='registered')
    created_at = db.Column(db.DateTime, default=datetime.now)

    submission = db.relationship('Submission', backref='registration', uselist=False)


class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(db.Integer, db.ForeignKey('registration.id'))
    xhs_link = db.Column(db.String(500))
    xhs_profile_link = db.Column(db.String(500))
    xhs_views = db.Column(db.Integer, default=0)
    xhs_likes = db.Column(db.Integer, default=0)
    xhs_favorites = db.Column(db.Integer, default=0)
    xhs_comments = db.Column(db.Integer, default=0)
    xhs_creator_account_id = db.Column(db.Integer)
    xhs_primary_post_id = db.Column(db.Integer)
    xhs_tracking_enabled = db.Column(db.Boolean, default=False)
    xhs_tracking_status = db.Column(db.String(30), default='empty')
    xhs_tracking_message = db.Column(db.String(300))
    xhs_last_synced_at = db.Column(db.DateTime)
    douyin_link = db.Column(db.String(500))
    douyin_views = db.Column(db.Integer, default=0)
    douyin_likes = db.Column(db.Integer, default=0)
    douyin_favorites = db.Column(db.Integer, default=0)
    douyin_comments = db.Column(db.Integer, default=0)
    video_link = db.Column(db.String(500))
    video_views = db.Column(db.Integer, default=0)
    video_likes = db.Column(db.Integer, default=0)
    video_favorites = db.Column(db.Integer, default=0)
    video_comments = db.Column(db.Integer, default=0)
    weibo_link = db.Column(db.String(500))
    weibo_views = db.Column(db.Integer, default=0)
    weibo_likes = db.Column(db.Integer, default=0)
    weibo_favorites = db.Column(db.Integer, default=0)
    weibo_comments = db.Column(db.Integer, default=0)
    content_screenshot = db.Column(db.Text)
    note_title = db.Column(db.String(300))
    note_content = db.Column(db.Text)
    content_type = db.Column(db.String(30), default='未识别')
    status = db.Column(db.String(20), default='pending')
    keyword_check = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)


class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True)
    value = db.Column(db.Text)


class SiteTheme(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    theme_key = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    primary_color = db.Column(db.String(20), default='#ff2442')
    primary_soft_color = db.Column(db.String(20), default='#ffe5e8')
    secondary_color = db.Column(db.String(20), default='#ff7a59')
    secondary_soft_color = db.Column(db.String(20), default='#fff3e8')
    nav_gradient_start = db.Column(db.String(20), default='#ff2442')
    nav_gradient_end = db.Column(db.String(20), default='#ff6b6b')
    hero_gradient_start = db.Column(db.String(20), default='#ff2442')
    hero_gradient_end = db.Column(db.String(20), default='#ff7a59')
    background_gradient_start = db.Column(db.String(20), default='#fff7f5')
    background_gradient_end = db.Column(db.String(20), default='#ffffff')
    surface_color = db.Column(db.String(20), default='#ffffff')
    text_color = db.Column(db.String(20), default='#1f2937')
    muted_text_color = db.Column(db.String(20), default='#6b7280')
    footer_text = db.Column(db.String(200), default='福瑞医科小红书任务管理系统')
    font_family = db.Column(db.String(200), default='-apple-system, BlinkMacSystemFont, PingFang SC, sans-serif')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)


class SitePageConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    page_key = db.Column(db.String(50), unique=True, nullable=False)
    site_name = db.Column(db.String(100), default='福瑞医科')
    page_title = db.Column(db.String(200), default='福瑞医科内容运营平台')
    hero_badge = db.Column(db.String(100), default='当前活动期')
    hero_title = db.Column(db.String(200))
    hero_subtitle = db.Column(db.Text)
    announcement_title = db.Column(db.String(100), default='最新公告')
    trend_title = db.Column(db.String(100), default='最新热点')
    primary_section_title = db.Column(db.String(100), default='复方鳖甲软肝片话题')
    primary_section_icon = db.Column(db.String(50), default='bi-capsule')
    secondary_section_title = db.Column(db.String(100), default='FibroScan体检话题')
    secondary_section_icon = db.Column(db.String(50), default='bi-heart-pulse')
    primary_topic_limit = db.Column(db.Integer, default=18)
    footer_text = db.Column(db.String(200), default='福瑞医科小红书任务管理系统')
    nav_items = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)


class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)
    link_url = db.Column(db.String(500))
    button_text = db.Column(db.String(50))
    priority = db.Column(db.Integer, default=100)
    status = db.Column(db.String(20), default='draft')
    starts_at = db.Column(db.DateTime)
    ends_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)


class DataSourceTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_type = db.Column(db.String(50), nullable=False)
    source_platform = db.Column(db.String(50), default='小红书')
    source_channel = db.Column(db.String(50), default='worker_skeleton')
    mode = db.Column(db.String(30), default='skeleton')
    status = db.Column(db.String(20), default='queued')
    celery_task_id = db.Column(db.String(100))
    batch_name = db.Column(db.String(120))
    keyword_limit = db.Column(db.Integer, default=10)
    activity_id = db.Column(db.Integer)
    item_count = db.Column(db.Integer, default=0)
    message = db.Column(db.String(300))
    params_payload = db.Column(db.Text)
    result_payload = db.Column(db.Text)
    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)


class DataSourceLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('data_source_task.id'), nullable=False)
    level = db.Column(db.String(20), default='info')
    message = db.Column(db.String(300), nullable=False)
    detail = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)


class AssetGenerationTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(db.Integer)
    topic_id = db.Column(db.Integer)
    source_provider = db.Column(db.String(50), default='svg_fallback')
    model_name = db.Column(db.String(100))
    style_preset = db.Column(db.String(50), default='小红书图文')
    product_profile = db.Column(db.String(80))
    product_category = db.Column(db.String(30))
    product_name = db.Column(db.String(200))
    product_indication = db.Column(db.String(200))
    product_asset_ids = db.Column(db.String(500))
    reference_asset_ids = db.Column(db.String(500))
    image_count = db.Column(db.Integer, default=3)
    status = db.Column(db.String(20), default='queued')
    celery_task_id = db.Column(db.String(100))
    title_hint = db.Column(db.String(200))
    prompt_text = db.Column(db.Text)
    selected_content = db.Column(db.Text)
    message = db.Column(db.String(300))
    result_payload = db.Column(db.Text)
    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)


class AssetLibrary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_generation_task_id = db.Column(db.Integer)
    registration_id = db.Column(db.Integer)
    topic_id = db.Column(db.Integer)
    library_type = db.Column(db.String(30), default='generated')
    asset_type = db.Column(db.String(50), default='知识卡片')
    title = db.Column(db.String(200))
    subtitle = db.Column(db.String(300))
    source_provider = db.Column(db.String(50), default='svg_fallback')
    model_name = db.Column(db.String(100))
    pool_status = db.Column(db.String(20), default='reserve')
    status = db.Column(db.String(20), default='active')
    product_category = db.Column(db.String(30))
    product_name = db.Column(db.String(200))
    product_indication = db.Column(db.String(200))
    visual_role = db.Column(db.String(50))
    tags = db.Column(db.String(300))
    prompt_text = db.Column(db.Text)
    preview_url = db.Column(db.Text)
    download_name = db.Column(db.String(200))
    raw_payload = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)


class AutomationSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_key = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    task_type = db.Column(db.String(50), nullable=False)
    enabled = db.Column(db.Boolean, default=False)
    interval_minutes = db.Column(db.Integer, default=60)
    params_payload = db.Column(db.Text)
    next_run_at = db.Column(db.DateTime)
    last_run_at = db.Column(db.DateTime)
    last_status = db.Column(db.String(20), default='idle')
    last_message = db.Column(db.String(300))
    last_celery_task_id = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)


class CorpusEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), default='爆款拆解')
    source = db.Column(db.String(100), default='手动录入')
    tags = db.Column(db.String(300))
    content = db.Column(db.Text, nullable=False)
    usage_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='active')
    pool_status = db.Column(db.String(20), default='reserve')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)


class TrendNote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source_platform = db.Column(db.String(50), default='小红书')
    source_channel = db.Column(db.String(50), default='手动导入')
    source_template_key = db.Column(db.String(50), default='generic_lines')
    import_batch = db.Column(db.String(100))
    keyword = db.Column(db.String(200))
    topic_category = db.Column(db.String(100))
    title = db.Column(db.String(300), nullable=False)
    author = db.Column(db.String(100))
    link = db.Column(db.String(500))
    views = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)
    favorites = db.Column(db.Integer, default=0)
    comments = db.Column(db.Integer, default=0)
    hot_score = db.Column(db.Integer, default=0)
    source_rank = db.Column(db.Integer, default=0)
    publish_time = db.Column(db.DateTime)
    summary = db.Column(db.Text)
    raw_payload = db.Column(db.Text)
    pool_status = db.Column(db.String(20), default='reserve')
    created_at = db.Column(db.DateTime, default=datetime.now)


class TopicIdea(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('activity.id'))
    topic_title = db.Column(db.String(200), nullable=False)
    keywords = db.Column(db.String(500))
    angle = db.Column(db.Text)
    content_type = db.Column(db.String(50))
    persona = db.Column(db.String(50))
    soft_insertion = db.Column(db.String(100))
    hot_value = db.Column(db.Integer, default=0)
    source_note_ids = db.Column(db.String(200))
    source_links = db.Column(db.Text)
    copy_prompt = db.Column(db.Text)
    cover_title = db.Column(db.String(120))
    asset_brief = db.Column(db.Text)
    compliance_note = db.Column(db.Text)
    quota = db.Column(db.Integer, default=30)
    status = db.Column(db.String(20), default='pending_review')
    review_note = db.Column(db.Text)
    reviewed_at = db.Column(db.DateTime)
    published_at = db.Column(db.DateTime)
    published_topic_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.now)


class CreatorAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(20), default='xhs')
    owner_name = db.Column(db.String(100))
    owner_phone = db.Column(db.String(20))
    account_handle = db.Column(db.String(100), nullable=False)
    display_name = db.Column(db.String(100))
    profile_url = db.Column(db.String(500))
    follower_count = db.Column(db.Integer, default=0)
    source_channel = db.Column(db.String(50), default='manual')
    status = db.Column(db.String(20), default='active')
    notes = db.Column(db.Text)
    last_synced_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    posts = db.relationship('CreatorPost', backref='creator_account', lazy=True)
    snapshots = db.relationship('CreatorAccountSnapshot', backref='creator_account', lazy=True)


class CreatorPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    creator_account_id = db.Column(db.Integer, db.ForeignKey('creator_account.id'))
    platform_post_id = db.Column(db.String(100))
    registration_id = db.Column(db.Integer)
    topic_id = db.Column(db.Integer)
    submission_id = db.Column(db.Integer)
    title = db.Column(db.String(300), nullable=False)
    post_url = db.Column(db.String(500))
    publish_time = db.Column(db.DateTime)
    topic_title = db.Column(db.String(200))
    views = db.Column(db.Integer, default=0)
    exposures = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)
    favorites = db.Column(db.Integer, default=0)
    comments = db.Column(db.Integer, default=0)
    shares = db.Column(db.Integer, default=0)
    follower_delta = db.Column(db.Integer, default=0)
    is_viral = db.Column(db.Boolean, default=False)
    source_channel = db.Column(db.String(50), default='manual')
    raw_payload = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)


class CreatorAccountSnapshot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    creator_account_id = db.Column(db.Integer, db.ForeignKey('creator_account.id'))
    snapshot_date = db.Column(db.Date)
    follower_count = db.Column(db.Integer, default=0)
    post_count = db.Column(db.Integer, default=0)
    total_views = db.Column(db.Integer, default=0)
    total_interactions = db.Column(db.Integer, default=0)
    source_channel = db.Column(db.String(50), default='manual')
    created_at = db.Column(db.DateTime, default=datetime.now)


PLATFORM_DEFINITIONS = [
    ('xhs', '小红书'),
    ('douyin', '抖音'),
    ('video', '视频号'),
    ('weibo', '微博'),
]

TOPIC_IDEA_STATUS_LABELS = {
    'draft': '草稿',
    'pending_review': '待审核',
    'approved': '已通过',
    'rejected': '已驳回',
    'published': '已发布',
    'archived': '已归档',
}

ACTIVITY_STATUS_LABELS = {
    'draft': '草稿',
    'published': '已发布',
    'closed': '已关闭',
    'archived': '已归档',
}

POOL_STATUS_LABELS = {
    'reserve': '储备池',
    'candidate': '候选池',
    'formal': '正式池',
    'archived': '归档池',
}

PRIMARY_PERSONAL_PLATFORMS = ['xhs', 'douyin', 'video']
