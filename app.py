#!/usr/bin/env python3
from dotenv import load_dotenv
load_dotenv()
# -*- coding: utf-8 -*-
"""
小红书任务管理系统 v4.0 - 福瑞医科
完全基于需求定制开发
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from sqlalchemy import or_, text
from werkzeug.middleware.proxy_fix import ProxyFix
import os
import json
import base64
import html
from datetime import datetime, timedelta
import random
import re
from collections import Counter, defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _env_flag(name, default=False):
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {'1', 'true', 'yes', 'y', 'on'}


def _resolve_database_url():
    database_url = (os.environ.get('DATABASE_URL') or '').strip()
    if not database_url:
        return f'sqlite:///{os.path.join(BASE_DIR, "xhs_system.db")}'
    if database_url.startswith('postgres://'):
        return database_url.replace('postgres://', 'postgresql+psycopg2://', 1)
    if database_url.startswith('postgresql://') and '+psycopg2' not in database_url:
        return database_url.replace('postgresql://', 'postgresql+psycopg2://', 1)
    return database_url


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'xhs_furui_2026_secret_key')
app.secret_key = app.config['SECRET_KEY']
app.config['SQLALCHEMY_DATABASE_URI'] = _resolve_database_url()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_AS_ASCII'] = False
try:
    max_content_length_mb = int(os.environ.get('MAX_CONTENT_LENGTH_MB', '16'))
except ValueError:
    max_content_length_mb = 16
app.config['MAX_CONTENT_LENGTH'] = max_content_length_mb * 1024 * 1024
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
app.config['SESSION_COOKIE_SECURE'] = _env_flag('SESSION_COOKIE_SECURE', False)
app.config['PREFERRED_URL_SCHEME'] = os.environ.get('PREFERRED_URL_SCHEME', 'https')

if app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite'):
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': {'check_same_thread': False}
    }
else:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 1800,
    }

db = SQLAlchemy(app)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

cors_origins = [item.strip() for item in (os.environ.get('CORS_ORIGINS') or '').split(',') if item.strip()]
if cors_origins:
    CORS(app, resources={r"/api/*": {"origins": cors_origins}})
else:
    CORS(app)

# ==================== 数据库模型 ====================

# 活动期数
class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))  # 第1期、第2期等
    title = db.Column(db.String(200))  # 活动标题
    description = db.Column(db.Text)  # 活动描述
    status = db.Column(db.String(20), default='draft')  # draft, published, closed, archived
    source_type = db.Column(db.String(30), default='manual')  # manual, clone, snapshot_restore
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


class OperationLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actor = db.Column(db.String(100), default='system')
    action = db.Column(db.String(100), nullable=False)
    target_type = db.Column(db.String(50), nullable=False)
    target_id = db.Column(db.Integer)
    message = db.Column(db.String(300))
    detail = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)

# 话题
class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('activity.id'))
    topic_name = db.Column(db.String(200))  # 话题名称
    keywords = db.Column(db.String(500))  # 关键词
    direction = db.Column(db.Text)  # 撰写方向
    reference_content = db.Column(db.Text)  # 参考内容
    reference_link = db.Column(db.String(500))  # 爆款参考链接
    writing_example = db.Column(db.Text)  # 撰写示例
    quota = db.Column(db.Integer, default=30)  # 名额上限（兜底默认值，实际可按每期/每话题调整）
    group_num = db.Column(db.String(50))  # 组号
    filled = db.Column(db.Integer, default=0)  # 已报名人数
    pool_status = db.Column(db.String(20), default='formal')  # formal, archived
    source_type = db.Column(db.String(30), default='manual')  # manual, topic_idea, snapshot_restore
    source_ref_id = db.Column(db.Integer)
    source_snapshot_id = db.Column(db.Integer)
    published_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)

    registrations = db.relationship('Registration', backref='topic', lazy=True)

# 报名
class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'))
    group_num = db.Column(db.String(50))  # 组号
    name = db.Column(db.String(100))  # 姓名
    phone = db.Column(db.String(20))  # 联系方式
    xhs_account = db.Column(db.String(100))  # 小红书账号
    status = db.Column(db.String(20), default='registered')  # registered, published, submitted
    created_at = db.Column(db.DateTime, default=datetime.now)

    submission = db.relationship('Submission', backref='registration', uselist=False)

# 提交数据
class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(db.Integer, db.ForeignKey('registration.id'))

    # 小红书
    xhs_link = db.Column(db.String(500))
    xhs_views = db.Column(db.Integer, default=0)  # 传播量
    xhs_likes = db.Column(db.Integer, default=0)
    xhs_favorites = db.Column(db.Integer, default=0)
    xhs_comments = db.Column(db.Integer, default=0)

    # 抖音
    douyin_link = db.Column(db.String(500))
    douyin_views = db.Column(db.Integer, default=0)
    douyin_likes = db.Column(db.Integer, default=0)
    douyin_favorites = db.Column(db.Integer, default=0)
    douyin_comments = db.Column(db.Integer, default=0)

    # 视频号
    video_link = db.Column(db.String(500))
    video_views = db.Column(db.Integer, default=0)
    video_likes = db.Column(db.Integer, default=0)
    video_favorites = db.Column(db.Integer, default=0)
    video_comments = db.Column(db.Integer, default=0)

    # 微博
    weibo_link = db.Column(db.String(500))
    weibo_views = db.Column(db.Integer, default=0)
    weibo_likes = db.Column(db.Integer, default=0)
    weibo_favorites = db.Column(db.Integer, default=0)
    weibo_comments = db.Column(db.Integer, default=0)

    content_screenshot = db.Column(db.Text)  # 正文截图
    note_title = db.Column(db.String(300))  # 笔记标题（可选）
    note_content = db.Column(db.Text)  # 笔记正文（可选）
    content_type = db.Column(db.String(30), default='未识别')  # 自动识别类型
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    keyword_check = db.Column(db.Boolean, default=False)  # 关键词检查
    created_at = db.Column(db.DateTime, default=datetime.now)

# 系统设置
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
    quota = db.Column(db.Integer, default=30)  # 候选话题名额（生成时可覆盖）
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

LIVER_KEYWORD_SEEDS = [
    '脂肪肝', '肝纤维化', '肝硬化', '肝癌预防', '复方鳖甲软肝片', 'FibroScan福波看',
    '肝弹', '肝硬度', '转氨酶', '乙肝', '丙肝', '酒精肝', '肝功能异常', '健康体检',
    '体检', '肝病筛查', '肝脏B超', '肝结节', '肝区不适', '熬夜护肝',
]

TOPIC_CONTENT_TYPES = [
    '真实经历型', '轻科普问答型', '检查解读型', '避坑清单型',
    '知识卡片型', '门诊答疑型', '复查管理型', '场景种草型',
]

TOPIC_PERSONAS = [
    '患者本人', '家属视角', '职场应酬族', '体检人群', '门诊答疑视角',
    '病友经验', '健康管理视角', '医学助理视角',
]

TOPIC_VISUAL_TYPES = ['医学科普图', '知识卡片', '检查流程图', '误区对照图', '复查清单卡']

COMPLIANCE_BASELINE = (
    '避免绝对化表述、避免功效承诺、避免购买引导；涉及药品时使用“在医生指导下”'
    '“管理方案”“复查评估”这类表达，不写根治、治愈、最有效。'
)

CORPUS_SEED_ENTRIES = [
    {
        'title': '医疗健康内容合规底线',
        'category': '合规表达',
        'source': '系统初始化',
        'tags': '合规,医疗,广告法',
        'content': '涉及药品和治疗方案时，统一使用“在医生指导下”“管理方案”“复查评估”表达，避免根治、治愈、最有效、保证改善、私信购买等话术。'
    },
    {
        'title': '检查解读类爆款结构',
        'category': '爆款拆解',
        'source': '系统初始化',
        'tags': '检查解读,FibroScan,体检',
        'content': '标题先给结果冲突，首屏抛出检查数值焦虑，中段解释指标含义，尾部给下一步动作，如复查、问诊、生活方式管理。'
    },
    {
        'title': '脂肪肝知识卡常用表达',
        'category': '医学科普',
        'source': '系统初始化',
        'tags': '脂肪肝,知识卡片,科普',
        'content': '适合拆成“什么情况要重视”“体检最常见误区”“日常管理三步走”三段结构，画面要清爽、信息块短、标题用问题句。'
    },
    {
        'title': '软植入表达模板',
        'category': '产品卖点',
        'source': '系统初始化',
        'tags': '复方鳖甲软肝片,FibroScan福波看,壳脂胶囊',
        'content': '复方鳖甲软肝片适合放在抗纤维化管理语境，FibroScan福波看适合放在检查评估和复查跟踪语境，壳脂胶囊适合放在脂肪肝管理场景。'
    },
    {
        'title': '封面图常用版式',
        'category': '封面模板',
        'source': '系统初始化',
        'tags': '爆款封面,医学科普图,知识卡片',
        'content': '优先做大标题+一行结论+3个短信息点，颜色用医疗感红橙蓝，减少长段落，突出数字、问句和清单感。'
    },
]

DEFAULT_SITE_NAV_ITEMS = [
    {'label': '话题广场', 'url': '/', 'icon': 'bi-collection', 'target': '_self'},
    {'label': '我的报名', 'url': '/my_registration', 'icon': 'bi-person-check', 'target': '_self'},
    {'label': '数据分析', 'url': '/data_analysis', 'icon': 'bi-bar-chart', 'target': '_self'},
    {'label': '自动化中心', 'url': '/automation_center', 'icon': 'bi-lightning-charge', 'target': '_self'},
    {'label': '活动管理', 'url': '/activity', 'icon': 'bi-calendar-event', 'target': '_self'},
    {'label': '后台', 'url': '/admin', 'icon': 'bi-gear', 'target': '_self'},
]

DEFAULT_SITE_THEME = {
    'theme_key': 'default',
    'name': '福瑞红橙',
    'primary_color': '#ff2442',
    'primary_soft_color': '#ffe5e8',
    'secondary_color': '#ff7a59',
    'secondary_soft_color': '#fff3e8',
    'nav_gradient_start': '#ff2442',
    'nav_gradient_end': '#ff6b6b',
    'hero_gradient_start': '#ff2442',
    'hero_gradient_end': '#ff7a59',
    'background_gradient_start': '#fff7f5',
    'background_gradient_end': '#ffffff',
    'surface_color': '#ffffff',
    'text_color': '#1f2937',
    'muted_text_color': '#6b7280',
    'footer_text': '福瑞医科小红书任务管理系统',
    'font_family': '-apple-system, BlinkMacSystemFont, PingFang SC, sans-serif',
}

DEFAULT_HOME_PAGE_CONFIG = {
    'page_key': 'home',
    'site_name': '福瑞医科',
    'page_title': '福瑞医科内容运营平台',
    'hero_badge': '当前活动期',
    'hero_title': '',
    'hero_subtitle': '',
    'announcement_title': '最新公告',
    'trend_title': '最新热点',
    'primary_section_title': '复方鳖甲软肝片话题',
    'primary_section_icon': 'bi-capsule',
    'secondary_section_title': 'FibroScan体检话题',
    'secondary_section_icon': 'bi-heart-pulse',
    'primary_topic_limit': 18,
    'footer_text': '福瑞医科小红书任务管理系统',
}


def _admin_json_guard():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': '未登录'}), 401
    return None


def _default_topic_quota():
    env_value = (os.environ.get('DEFAULT_TOPIC_QUOTA') or '').strip()
    if env_value:
        try:
            value = int(env_value)
            if value > 0:
                return value
        except ValueError:
            pass
    try:
        setting = Settings.query.filter_by(key='default_topic_quota').first()
        if setting and str(setting.value).strip():
            value = int(str(setting.value).strip())
            if value > 0:
                return value
    except Exception:
        pass
    return 30


def _automation_keyword_seeds():
    try:
        setting = Settings.query.filter_by(key='automation_keyword_seeds').first()
        parsed = _load_json_value(setting.value if setting else '', [])
        if parsed:
            return [str(item).strip() for item in parsed if str(item).strip()]
    except Exception:
        pass
    return list(LIVER_KEYWORD_SEEDS)


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_hex_color(value, default):
    value = (value or '').strip()
    if re.fullmatch(r'#[0-9a-fA-F]{6}', value):
        return value.lower()
    return default


def _split_keywords(text):
    raw = (text or '').replace('，', ',').replace('、', ',').replace('#', ',')
    return [item.strip() for item in raw.split(',') if item and item.strip()]


def _truncate_text(text, limit=80):
    text = (text or '').strip()
    return text if len(text) <= limit else text[:limit] + '...'


def _coerce_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 'yes', 'y', 'on'}
    return False


def _normalize_quota(value, default=None, min_value=1, max_value=500):
    fallback = _default_topic_quota() if default is None else default
    quota = _safe_int(value, fallback)
    if quota < min_value:
        quota = min_value
    if quota > max_value:
        quota = max_value
    return quota


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


def _format_datetime(value):
    return value.strftime('%Y-%m-%d %H:%M:%S') if value else ''


def _format_datetime_local(value):
    return value.strftime('%Y-%m-%dT%H:%M') if value else ''


def _topic_idea_status_label(status):
    return TOPIC_IDEA_STATUS_LABELS.get(status or '', status or '未知')


def _activity_status_label(status):
    return ACTIVITY_STATUS_LABELS.get(status or '', status or '未知')


def _pool_status_label(status):
    return POOL_STATUS_LABELS.get(status or '', status or '未知')


def _current_actor():
    return session.get('admin_username') or 'system'


def _admin_username():
    return os.environ.get('ADMIN_USERNAME', 'furui')


def _admin_password():
    return os.environ.get('ADMIN_PASSWORD', 'wangdandan39')


def _log_operation(action, target_type, target_id=None, message='', detail=None):
    detail_text = ''
    if detail is not None:
        if isinstance(detail, str):
            detail_text = detail
        else:
            try:
                detail_text = json.dumps(detail, ensure_ascii=False)
            except TypeError:
                detail_text = str(detail)

    db.session.add(OperationLog(
        actor=_current_actor(),
        action=action,
        target_type=target_type,
        target_id=target_id,
        message=(message or '')[:300],
        detail=detail_text,
    ))


def _serialize_activity(activity):
    return {
        'id': activity.id,
        'name': activity.name,
        'title': activity.title,
        'description': activity.description or '',
        'status': activity.status,
        'status_label': _activity_status_label(activity.status),
        'source_type': activity.source_type or 'manual',
        'source_activity_id': activity.source_activity_id,
        'source_snapshot_id': activity.source_snapshot_id,
        'topic_count': len(activity.topics or []),
        'snapshot_count': len(activity.snapshots or []),
        'archived_at': activity.archived_at.strftime('%Y-%m-%d %H:%M:%S') if getattr(activity, 'archived_at', None) else '',
        'created_at': activity.created_at.strftime('%Y-%m-%d %H:%M:%S') if activity.created_at else '',
    }


def _load_json_value(raw_value, default):
    if not raw_value:
        return default
    try:
        parsed = json.loads(raw_value)
    except Exception:
        return default
    return parsed if isinstance(parsed, type(default)) else default


def _normalize_nav_items(items):
    normalized = []
    if not isinstance(items, list):
        items = []
    for raw_item in items[:8]:
        if not isinstance(raw_item, dict):
            continue
        label = (raw_item.get('label') or '').strip()
        url = (raw_item.get('url') or '').strip()
        if not label or not url:
            continue
        normalized.append({
            'label': label[:20],
            'url': url[:300],
            'icon': (raw_item.get('icon') or '').strip()[:50],
            'target': '_blank' if (raw_item.get('target') or '').strip() == '_blank' else '_self',
        })
    return normalized or [dict(item) for item in DEFAULT_SITE_NAV_ITEMS]


def _serialize_site_theme(theme):
    return {
        'id': theme.id,
        'theme_key': theme.theme_key,
        'name': theme.name,
        'is_active': bool(theme.is_active),
        'primary_color': theme.primary_color,
        'primary_soft_color': theme.primary_soft_color,
        'secondary_color': theme.secondary_color,
        'secondary_soft_color': theme.secondary_soft_color,
        'nav_gradient_start': theme.nav_gradient_start,
        'nav_gradient_end': theme.nav_gradient_end,
        'hero_gradient_start': theme.hero_gradient_start,
        'hero_gradient_end': theme.hero_gradient_end,
        'background_gradient_start': theme.background_gradient_start,
        'background_gradient_end': theme.background_gradient_end,
        'surface_color': theme.surface_color,
        'text_color': theme.text_color,
        'muted_text_color': theme.muted_text_color,
        'footer_text': theme.footer_text or '',
        'font_family': theme.font_family or DEFAULT_SITE_THEME['font_family'],
        'created_at': _format_datetime(theme.created_at),
        'updated_at': _format_datetime(theme.updated_at),
    }


def _serialize_site_page_config(config):
    return {
        'id': config.id,
        'page_key': config.page_key,
        'site_name': config.site_name or '',
        'page_title': config.page_title or '',
        'hero_badge': config.hero_badge or '',
        'hero_title': config.hero_title or '',
        'hero_subtitle': config.hero_subtitle or '',
        'announcement_title': config.announcement_title or '',
        'trend_title': config.trend_title or '',
        'primary_section_title': config.primary_section_title or '',
        'primary_section_icon': config.primary_section_icon or '',
        'secondary_section_title': config.secondary_section_title or '',
        'secondary_section_icon': config.secondary_section_icon or '',
        'primary_topic_limit': config.primary_topic_limit or DEFAULT_HOME_PAGE_CONFIG['primary_topic_limit'],
        'footer_text': config.footer_text or '',
        'nav_items': _normalize_nav_items(_load_json_value(config.nav_items, [])),
        'created_at': _format_datetime(config.created_at),
        'updated_at': _format_datetime(config.updated_at),
    }


def _serialize_announcement(item):
    return {
        'id': item.id,
        'title': item.title or '',
        'content': item.content or '',
        'link_url': item.link_url or '',
        'button_text': item.button_text or '',
        'priority': item.priority or 0,
        'status': item.status or 'draft',
        'starts_at': _format_datetime(item.starts_at),
        'ends_at': _format_datetime(item.ends_at),
        'starts_at_input': _format_datetime_local(item.starts_at),
        'ends_at_input': _format_datetime_local(item.ends_at),
        'created_at': _format_datetime(item.created_at),
        'updated_at': _format_datetime(item.updated_at),
    }


def _serialize_data_source_log(item):
    return {
        'id': item.id,
        'task_id': item.task_id,
        'level': item.level or 'info',
        'message': item.message or '',
        'detail': item.detail or '',
        'created_at': _format_datetime(item.created_at),
    }


def _serialize_data_source_task(task):
    logs = DataSourceLog.query.filter_by(task_id=task.id).order_by(DataSourceLog.created_at.desc(), DataSourceLog.id.desc()).limit(5).all()
    return {
        'id': task.id,
        'task_type': task.task_type,
        'source_platform': task.source_platform or '',
        'source_channel': task.source_channel or '',
        'mode': task.mode or 'skeleton',
        'status': task.status or 'queued',
        'celery_task_id': task.celery_task_id or '',
        'batch_name': task.batch_name or '',
        'keyword_limit': task.keyword_limit or 0,
        'activity_id': task.activity_id,
        'item_count': task.item_count or 0,
        'message': task.message or '',
        'params_payload': task.params_payload or '',
        'result_payload': task.result_payload or '',
        'started_at': _format_datetime(task.started_at),
        'finished_at': _format_datetime(task.finished_at),
        'created_at': _format_datetime(task.created_at),
        'updated_at': _format_datetime(task.updated_at),
        'recent_logs': [_serialize_data_source_log(item) for item in logs],
    }


def _serialize_asset_generation_task(task):
    return {
        'id': task.id,
        'registration_id': task.registration_id,
        'topic_id': task.topic_id,
        'source_provider': task.source_provider or 'svg_fallback',
        'model_name': task.model_name or '',
        'style_preset': task.style_preset or '小红书图文',
        'image_count': task.image_count or 0,
        'status': task.status or 'queued',
        'celery_task_id': task.celery_task_id or '',
        'title_hint': task.title_hint or '',
        'prompt_text': task.prompt_text or '',
        'selected_content': task.selected_content or '',
        'message': task.message or '',
        'result_payload': _load_json_value(task.result_payload, []),
        'started_at': _format_datetime(task.started_at),
        'finished_at': _format_datetime(task.finished_at),
        'created_at': _format_datetime(task.created_at),
        'updated_at': _format_datetime(task.updated_at),
    }


def _serialize_operation_log(log):
    return {
        'id': log.id,
        'actor': log.actor or 'system',
        'action': log.action,
        'target_type': log.target_type,
        'target_id': log.target_id,
        'message': log.message or '',
        'detail': log.detail or '',
        'created_at': log.created_at.strftime('%Y-%m-%d %H:%M:%S') if log.created_at else '',
    }


def _deserialize_operation_detail(detail):
    if not detail:
        return {}
    try:
        parsed = json.loads(detail)
        return parsed if isinstance(parsed, dict) else {'raw': parsed}
    except Exception:
        return {'raw': detail}


def _serialize_topic(topic):
    return {
        'id': topic.id,
        'activity_id': topic.activity_id,
        'topic_name': topic.topic_name,
        'keywords': topic.keywords or '',
        'direction': topic.direction or '',
        'reference_content': topic.reference_content or '',
        'reference_link': topic.reference_link or '',
        'writing_example': topic.writing_example or '',
        'quota': topic.quota or 0,
        'filled': topic.filled or 0,
        'available': max((topic.quota or 0) - (topic.filled or 0), 0),
        'group_num': topic.group_num or '',
        'pool_status': topic.pool_status or 'formal',
        'pool_status_label': _pool_status_label(topic.pool_status or 'formal'),
        'source_type': topic.source_type or 'manual',
        'source_ref_id': topic.source_ref_id,
        'source_snapshot_id': topic.source_snapshot_id,
        'published_at': topic.published_at.strftime('%Y-%m-%d %H:%M:%S') if topic.published_at else '',
        'created_at': topic.created_at.strftime('%Y-%m-%d %H:%M:%S') if topic.created_at else '',
    }


def _serialize_corpus_entry(entry):
    return {
        'id': entry.id,
        'title': entry.title,
        'category': entry.category,
        'source': entry.source,
        'tags': entry.tags or '',
        'content': entry.content,
        'usage_count': entry.usage_count or 0,
        'status': entry.status,
        'pool_status': entry.pool_status or 'reserve',
        'pool_status_label': _pool_status_label(entry.pool_status or 'reserve'),
        'created_at': entry.created_at.strftime('%Y-%m-%d %H:%M:%S') if entry.created_at else '',
        'updated_at': entry.updated_at.strftime('%Y-%m-%d %H:%M:%S') if entry.updated_at else '',
    }


def _serialize_trend_note(note):
    return {
        'id': note.id,
        'source_platform': note.source_platform,
        'source_channel': note.source_channel,
        'import_batch': note.import_batch or '',
        'keyword': note.keyword or '',
        'title': note.title,
        'author': note.author or '',
        'link': note.link or '',
        'views': note.views or 0,
        'likes': note.likes or 0,
        'favorites': note.favorites or 0,
        'comments': note.comments or 0,
        'interactions': (note.likes or 0) + (note.favorites or 0) + (note.comments or 0),
        'score': _trend_score(note),
        'summary': note.summary or '',
        'pool_status': note.pool_status or 'reserve',
        'pool_status_label': _pool_status_label(note.pool_status or 'reserve'),
        'created_at': note.created_at.strftime('%Y-%m-%d %H:%M:%S') if note.created_at else '',
    }


def _build_activity_snapshot_payload(activity):
    topics = Topic.query.filter_by(activity_id=activity.id).order_by(Topic.id.asc()).all()
    topic_ids = [topic.id for topic in topics]
    registrations = Registration.query.filter(Registration.topic_id.in_(topic_ids)).order_by(Registration.id.asc()).all() if topic_ids else []
    submissions = Submission.query.join(Registration).filter(Registration.topic_id.in_(topic_ids)).order_by(Submission.id.asc()).all() if topic_ids else []

    registrations_by_topic = defaultdict(list)
    submissions_by_registration = {}
    for reg in registrations:
        registrations_by_topic[reg.topic_id].append(reg)
    for sub in submissions:
        submissions_by_registration[sub.registration_id] = sub

    return {
        'activity': _serialize_activity(activity),
        'topics': [{
            **_serialize_topic(topic),
            'registrations': [{
                'id': reg.id,
                'group_num': reg.group_num or '',
                'name': reg.name or '',
                'phone': reg.phone or '',
                'xhs_account': reg.xhs_account or '',
                'status': reg.status or '',
                'created_at': reg.created_at.strftime('%Y-%m-%d %H:%M:%S') if reg.created_at else '',
                'submission': None if reg.id not in submissions_by_registration else {
                    'id': submissions_by_registration[reg.id].id,
                    'xhs_link': submissions_by_registration[reg.id].xhs_link or '',
                    'xhs_views': submissions_by_registration[reg.id].xhs_views or 0,
                    'xhs_likes': submissions_by_registration[reg.id].xhs_likes or 0,
                    'xhs_favorites': submissions_by_registration[reg.id].xhs_favorites or 0,
                    'xhs_comments': submissions_by_registration[reg.id].xhs_comments or 0,
                    'douyin_link': submissions_by_registration[reg.id].douyin_link or '',
                    'douyin_views': submissions_by_registration[reg.id].douyin_views or 0,
                    'douyin_likes': submissions_by_registration[reg.id].douyin_likes or 0,
                    'douyin_favorites': submissions_by_registration[reg.id].douyin_favorites or 0,
                    'douyin_comments': submissions_by_registration[reg.id].douyin_comments or 0,
                    'video_link': submissions_by_registration[reg.id].video_link or '',
                    'video_views': submissions_by_registration[reg.id].video_views or 0,
                    'video_likes': submissions_by_registration[reg.id].video_likes or 0,
                    'video_favorites': submissions_by_registration[reg.id].video_favorites or 0,
                    'video_comments': submissions_by_registration[reg.id].video_comments or 0,
                    'weibo_link': submissions_by_registration[reg.id].weibo_link or '',
                    'weibo_views': submissions_by_registration[reg.id].weibo_views or 0,
                    'weibo_likes': submissions_by_registration[reg.id].weibo_likes or 0,
                    'weibo_favorites': submissions_by_registration[reg.id].weibo_favorites or 0,
                    'weibo_comments': submissions_by_registration[reg.id].weibo_comments or 0,
                    'note_title': submissions_by_registration[reg.id].note_title or '',
                    'note_content': submissions_by_registration[reg.id].note_content or '',
                    'content_type': submissions_by_registration[reg.id].content_type or '',
                    'keyword_check': bool(submissions_by_registration[reg.id].keyword_check),
                    'created_at': submissions_by_registration[reg.id].created_at.strftime('%Y-%m-%d %H:%M:%S') if submissions_by_registration[reg.id].created_at else '',
                }
            } for reg in registrations_by_topic.get(topic.id, [])]
        } for topic in topics],
        'summary': {
            'topic_count': len(topics),
            'registration_count': len(registrations),
            'submission_count': len(submissions),
        }
    }


def _create_activity_snapshot(activity, snapshot_name=''):
    payload = _build_activity_snapshot_payload(activity)
    snapshot = ActivitySnapshot(
        activity_id=activity.id,
        snapshot_name=snapshot_name or f'{activity.name} 归档快照',
        source_status=activity.status,
        payload=json.dumps(payload, ensure_ascii=False)
    )
    db.session.add(snapshot)
    return snapshot


def _clone_activity(activity, *, name=None, title=None, description=None):
    cloned = Activity(
        name=name or f'{activity.name}-复制',
        title=title or activity.title,
        description=description if description is not None else activity.description,
        status='draft',
        source_type='clone',
        source_activity_id=activity.id,
    )
    db.session.add(cloned)
    db.session.flush()

    topics = Topic.query.filter_by(activity_id=activity.id).order_by(Topic.id.asc()).all()
    for topic in topics:
        db.session.add(Topic(
            activity_id=cloned.id,
            topic_name=topic.topic_name,
            keywords=topic.keywords,
            direction=topic.direction,
            reference_content=topic.reference_content,
            reference_link=topic.reference_link,
            writing_example=topic.writing_example,
            quota=topic.quota,
            group_num=topic.group_num,
            pool_status='formal',
            source_type=topic.source_type or 'manual',
            source_ref_id=topic.source_ref_id,
            source_snapshot_id=topic.source_snapshot_id,
            published_at=topic.published_at,
            filled=0
        ))
    return cloned


def _restore_activity_from_snapshot(snapshot, *, name=None, title=None, description=None):
    payload, _ = _snapshot_payload_and_summary(snapshot)
    if not isinstance(payload, dict):
        payload = {}
    activity_data = payload.get('activity') or {}
    topics_data = payload.get('topics') or []

    restored = Activity(
        name=name or f"{activity_data.get('name') or '历史活动'}-恢复",
        title=title or activity_data.get('title') or '恢复活动',
        description=description if description is not None else activity_data.get('description', ''),
        status='draft',
        source_type='snapshot_restore',
        source_activity_id=snapshot.activity_id,
        source_snapshot_id=snapshot.id,
    )
    db.session.add(restored)
    db.session.flush()

    for topic_data in topics_data:
        db.session.add(Topic(
            activity_id=restored.id,
            topic_name=topic_data.get('topic_name'),
            keywords=topic_data.get('keywords'),
            direction=topic_data.get('direction'),
            reference_content=topic_data.get('reference_content'),
            reference_link=topic_data.get('reference_link'),
            writing_example=topic_data.get('writing_example'),
            quota=_normalize_quota(topic_data.get('quota'), default=_default_topic_quota()),
            group_num=topic_data.get('group_num'),
            filled=0,
            pool_status='formal',
            source_type='snapshot_restore',
            source_ref_id=topic_data.get('id'),
            source_snapshot_id=snapshot.id,
            published_at=datetime.now(),
        ))
    return restored


def _snapshot_payload_and_summary(snapshot):
    payload = {}
    if snapshot.payload:
        try:
            payload = json.loads(snapshot.payload)
        except json.JSONDecodeError:
            payload = {'raw_payload': snapshot.payload}
    summary = payload.get('summary') if isinstance(payload, dict) else {}
    return payload, (summary if isinstance(summary, dict) else {})


def _is_sqlite_backend():
    try:
        return db.engine.url.get_backend_name() == 'sqlite'
    except Exception:
        return app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite')


def _serialize_topic_idea(idea):
    return {
        'id': idea.id,
        'activity_id': idea.activity_id,
        'topic_title': idea.topic_title,
        'keywords': idea.keywords or '',
        'angle': idea.angle or '',
        'content_type': idea.content_type or '',
        'persona': idea.persona or '',
        'soft_insertion': idea.soft_insertion or '',
        'hot_value': idea.hot_value or 0,
        'source_note_ids': idea.source_note_ids or '',
        'source_links': idea.source_links or '',
        'copy_prompt': idea.copy_prompt or '',
        'cover_title': idea.cover_title or '',
        'asset_brief': idea.asset_brief or '',
        'compliance_note': idea.compliance_note or '',
        'quota': idea.quota or _default_topic_quota(),
        'status': idea.status,
        'status_label': _topic_idea_status_label(idea.status),
        'review_note': idea.review_note or '',
        'reviewed_at': idea.reviewed_at.strftime('%Y-%m-%d %H:%M:%S') if idea.reviewed_at else '',
        'published_at': idea.published_at.strftime('%Y-%m-%d %H:%M:%S') if idea.published_at else '',
        'published_topic_id': idea.published_topic_id,
        'created_at': idea.created_at.strftime('%Y-%m-%d %H:%M:%S') if idea.created_at else '',
    }


def _creator_post_interactions(post):
    return (post.likes or 0) + (post.favorites or 0) + (post.comments or 0)


def _creator_post_score(post):
    return (
        post.views or 0,
        _creator_post_interactions(post),
        post.follower_delta or 0,
        post.exposures or 0,
    )


def _infer_viral_post(views=0, likes=0, favorites=0, comments=0, exposures=0):
    interactions = (likes or 0) + (favorites or 0) + (comments or 0)
    return (views or 0) >= 10000 or (exposures or 0) >= 30000 or interactions >= 1000


def _serialize_creator_post(post):
    interactions = _creator_post_interactions(post)
    return {
        'id': post.id,
        'creator_account_id': post.creator_account_id,
        'platform_post_id': post.platform_post_id or '',
        'title': post.title,
        'post_url': post.post_url or '',
        'publish_time': post.publish_time.strftime('%Y-%m-%d %H:%M:%S') if post.publish_time else '',
        'topic_title': post.topic_title or '',
        'views': post.views or 0,
        'exposures': post.exposures or 0,
        'likes': post.likes or 0,
        'favorites': post.favorites or 0,
        'comments': post.comments or 0,
        'shares': post.shares or 0,
        'follower_delta': post.follower_delta or 0,
        'interactions': interactions,
        'is_viral': bool(post.is_viral),
        'source_channel': post.source_channel or '',
        'created_at': post.created_at.strftime('%Y-%m-%d %H:%M:%S') if post.created_at else '',
    }


def _serialize_creator_account(account):
    posts = CreatorPost.query.filter_by(creator_account_id=account.id).order_by(
        CreatorPost.publish_time.desc(), CreatorPost.created_at.desc()
    ).all()
    snapshots = CreatorAccountSnapshot.query.filter_by(creator_account_id=account.id).order_by(
        CreatorAccountSnapshot.snapshot_date.desc(), CreatorAccountSnapshot.created_at.desc()
    ).all()
    best_post = sorted(posts, key=_creator_post_score, reverse=True)[0] if posts else None
    latest_snapshot = snapshots[0] if snapshots else None
    total_views = sum(post.views or 0 for post in posts)
    total_exposures = sum(post.exposures or 0 for post in posts)
    total_interactions = sum(_creator_post_interactions(post) for post in posts)
    follower_count = account.follower_count or 0
    if latest_snapshot and latest_snapshot.follower_count is not None:
        follower_count = latest_snapshot.follower_count

    return {
        'id': account.id,
        'platform': account.platform,
        'owner_name': account.owner_name or '',
        'owner_phone': account.owner_phone or '',
        'account_handle': account.account_handle,
        'display_name': account.display_name or account.account_handle,
        'profile_url': account.profile_url or '',
        'follower_count': follower_count,
        'source_channel': account.source_channel or '',
        'status': account.status or 'active',
        'notes': account.notes or '',
        'post_count': len(posts),
        'viral_post_count': len([post for post in posts if post.is_viral]),
        'total_views': total_views,
        'total_exposures': total_exposures,
        'total_interactions': total_interactions,
        'last_synced_at': account.last_synced_at.strftime('%Y-%m-%d %H:%M:%S') if account.last_synced_at else '',
        'latest_snapshot_date': latest_snapshot.snapshot_date.isoformat() if latest_snapshot and latest_snapshot.snapshot_date else '',
        'best_post': _serialize_creator_post(best_post) if best_post else None,
        'created_at': account.created_at.strftime('%Y-%m-%d %H:%M:%S') if account.created_at else '',
        'updated_at': account.updated_at.strftime('%Y-%m-%d %H:%M:%S') if account.updated_at else '',
    }


def _get_active_site_theme():
    theme = SiteTheme.query.filter_by(is_active=True).order_by(SiteTheme.updated_at.desc(), SiteTheme.id.desc()).first()
    if theme:
        return theme
    return SiteTheme.query.order_by(SiteTheme.id.asc()).first()


def _get_site_page_config(page_key='home'):
    return SitePageConfig.query.filter_by(page_key=page_key).first()


def _list_announcements(include_inactive=False, limit=None):
    query = Announcement.query
    if not include_inactive:
        now = datetime.now()
        query = query.filter_by(status='active')
        query = query.filter(or_(Announcement.starts_at.is_(None), Announcement.starts_at <= now))
        query = query.filter(or_(Announcement.ends_at.is_(None), Announcement.ends_at >= now))
    query = query.order_by(Announcement.priority.asc(), Announcement.updated_at.desc(), Announcement.id.desc())
    if limit:
        query = query.limit(limit)
    return query.all()


def _append_data_source_log(task_id, message, level='info', detail=None):
    detail_text = ''
    if detail is not None:
        if isinstance(detail, str):
            detail_text = detail
        else:
            try:
                detail_text = json.dumps(detail, ensure_ascii=False)
            except TypeError:
                detail_text = str(detail)
    db.session.add(DataSourceLog(
        task_id=task_id,
        level=level,
        message=(message or '')[:300],
        detail=detail_text,
    ))


def _apply_creator_post_range(query, args):
    date_from = _parse_date(args.get('date_from')) if hasattr(args, 'get') else None
    date_to = _parse_date(args.get('date_to')) if hasattr(args, 'get') else None
    if date_from:
        start_dt = datetime.combine(date_from, datetime.min.time())
        query = query.filter(or_(CreatorPost.publish_time.is_(None), CreatorPost.publish_time >= start_dt))
    if date_to:
        end_dt = datetime.combine(date_to, datetime.max.time())
        query = query.filter(or_(CreatorPost.publish_time.is_(None), CreatorPost.publish_time <= end_dt))
    return query, date_from, date_to


def _build_creator_account_query(args):
    phone = (args.get('phone') or '').strip()
    platform = (args.get('platform') or '').strip()
    keyword = (args.get('keyword') or '').strip()
    viral_only = _coerce_bool(args.get('viral_only'))

    query = CreatorAccount.query
    if phone:
        query = query.filter(CreatorAccount.owner_phone.contains(phone))
    if platform:
        query = query.filter_by(platform=platform)
    if keyword:
        query = query.filter(or_(
            CreatorAccount.owner_name.contains(keyword),
            CreatorAccount.owner_phone.contains(keyword),
            CreatorAccount.account_handle.contains(keyword),
            CreatorAccount.display_name.contains(keyword),
        ))
    if viral_only:
        query = query.join(CreatorPost, CreatorPost.creator_account_id == CreatorAccount.id).filter(CreatorPost.is_viral.is_(True)).distinct()
    return query


def _build_creator_analytics_payload(posts, snapshots, date_from=None, date_to=None):
    daily_map = defaultdict(lambda: {
        'post_count': 0,
        'viral_posts': 0,
        'views': 0,
        'exposures': 0,
        'interactions': 0,
        'follower_delta': 0,
    })
    topic_map = defaultdict(lambda: {'post_count': 0, 'views': 0, 'interactions': 0})

    for post in posts:
        base_dt = post.publish_time or post.created_at or datetime.now()
        day_key = base_dt.strftime('%Y-%m-%d')
        interactions = (post.likes or 0) + (post.favorites or 0) + (post.comments or 0)
        row = daily_map[day_key]
        row['post_count'] += 1
        row['viral_posts'] += 1 if post.is_viral else 0
        row['views'] += post.views or 0
        row['exposures'] += post.exposures or 0
        row['interactions'] += interactions
        row['follower_delta'] += post.follower_delta or 0

        topic_key = (post.topic_title or '未关联话题').strip()
        topic_row = topic_map[topic_key]
        topic_row['post_count'] += 1
        topic_row['views'] += post.views or 0
        topic_row['interactions'] += interactions

    daily_rows = [{'date': day_key, **daily_map[day_key]} for day_key in sorted(daily_map.keys())]
    snapshot_rows = [{
        'date': snapshot.snapshot_date.isoformat() if snapshot.snapshot_date else '',
        'follower_count': snapshot.follower_count or 0,
        'post_count': snapshot.post_count or 0,
        'total_views': snapshot.total_views or 0,
        'total_interactions': snapshot.total_interactions or 0,
    } for snapshot in snapshots]

    top_topics = []
    for topic_name, item in topic_map.items():
        top_topics.append({'topic_title': topic_name, **item})
    top_topics.sort(key=lambda row: (row['interactions'], row['views'], row['post_count']), reverse=True)

    total_views = sum(post.views or 0 for post in posts)
    total_exposures = sum(post.exposures or 0 for post in posts)
    total_interactions = sum((post.likes or 0) + (post.favorites or 0) + (post.comments or 0) for post in posts)
    total_follower_delta = sum(post.follower_delta or 0 for post in posts)
    viral_posts = len([post for post in posts if post.is_viral])
    best_post = sorted(
        posts,
        key=lambda item: ((item.views or 0), ((item.likes or 0) + (item.favorites or 0) + (item.comments or 0)), (item.follower_delta or 0)),
        reverse=True
    )[0] if posts else None

    overview = {
        'post_count': len(posts),
        'viral_posts': viral_posts,
        'total_views': total_views,
        'total_exposures': total_exposures,
        'total_interactions': total_interactions,
        'total_follower_delta': total_follower_delta,
        'avg_views': round(total_views / len(posts), 2) if posts else 0,
        'avg_interactions': round(total_interactions / len(posts), 2) if posts else 0,
        'best_post': _serialize_creator_post(best_post) if best_post else None,
        'date_from': date_from.isoformat() if date_from else '',
        'date_to': date_to.isoformat() if date_to else '',
    }

    return {
        'overview': overview,
        'daily_posts': daily_rows,
        'daily_snapshots': snapshot_rows,
        'top_topics': top_topics[:10],
    }


@app.route('/healthz')
def healthz():
    try:
        db.session.execute(text('SELECT 1'))
        return jsonify({
            'success': True,
            'status': 'ok',
            'service': 'xhs_v4',
            'database': 'ok',
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        })
    except Exception as exc:
        return jsonify({
            'success': False,
            'status': 'degraded',
            'service': 'xhs_v4',
            'database': 'error',
            'message': str(exc),
        }), 503


def _resolve_analysis_range(args):
    today = datetime.now().date()
    range_key = (args.get('range') or 'all').strip()
    start_date = _parse_date(args.get('start_date'))
    end_date = _parse_date(args.get('end_date'))

    if range_key == 'this_week':
        start_date = today - timedelta(days=today.weekday())
        end_date = today
        label = '本周'
    elif range_key == 'last_week':
        this_week_start = today - timedelta(days=today.weekday())
        end_date = this_week_start - timedelta(days=1)
        start_date = end_date - timedelta(days=6)
        label = '上周'
    elif range_key == '7d':
        start_date = today - timedelta(days=6)
        end_date = today
        label = '近7天'
    elif range_key == '30d':
        start_date = today - timedelta(days=29)
        end_date = today
        label = '近30天'
    elif range_key == 'custom' and start_date and end_date:
        label = '自定义'
    else:
        range_key = 'all'
        start_date = None
        end_date = None
        label = '全部时间'

    start_dt = datetime.combine(start_date, datetime.min.time()) if start_date else None
    end_dt = datetime.combine(end_date, datetime.max.time()) if end_date else None
    return {
        'key': range_key,
        'label': label,
        'start_date': start_date.isoformat() if start_date else '',
        'end_date': end_date.isoformat() if end_date else '',
        'start_dt': start_dt,
        'end_dt': end_dt,
    }


def _is_in_range(value, start_dt=None, end_dt=None):
    if not start_dt and not end_dt:
        return True
    if not value:
        return False
    if start_dt and value < start_dt:
        return False
    if end_dt and value > end_dt:
        return False
    return True


def _submission_has_platform_link(submission, platform_key):
    return bool((getattr(submission, f'{platform_key}_link', '') or '').strip())


def _submission_has_any_link(submission):
    return any(_submission_has_platform_link(submission, key) for key, _ in PLATFORM_DEFINITIONS)


def _collect_platform_metrics(submission, platform_key):
    keys = [platform_key] if platform_key != 'all' else [key for key, _ in PLATFORM_DEFINITIONS]
    views = likes = favorites = comments = 0
    has_link = False
    for key in keys:
        if _submission_has_platform_link(submission, key):
            has_link = True
        views += getattr(submission, f'{key}_views', 0) or 0
        likes += getattr(submission, f'{key}_likes', 0) or 0
        favorites += getattr(submission, f'{key}_favorites', 0) or 0
        comments += getattr(submission, f'{key}_comments', 0) or 0
    return {
        'has_link': has_link,
        'views': views,
        'likes': likes,
        'favorites': favorites,
        'comments': comments,
        'interactions': likes + favorites + comments,
    }


def _calculate_rate(numerator, denominator):
    if not denominator:
        return None
    return round((numerator / denominator) * 100, 2)


def _format_rate(rate):
    return '-' if rate is None else f'{rate}%'


def _load_activity_scope(activity_id, range_info):
    topics = Topic.query.filter_by(activity_id=activity_id).all()
    topic_ids = [t.id for t in topics]
    if not topic_ids:
        return topics, [], []

    registrations_all = Registration.query.filter(Registration.topic_id.in_(topic_ids)).all()
    submissions_all = Submission.query.join(Registration).filter(
        Registration.topic_id.in_(topic_ids)
    ).all()

    if range_info['key'] == 'all':
        return topics, registrations_all, submissions_all

    participant_ids = set()
    for reg in registrations_all:
        if _is_in_range(reg.created_at, range_info['start_dt'], range_info['end_dt']):
            participant_ids.add(reg.id)

    for sub in submissions_all:
        active_time = sub.created_at or (sub.registration.created_at if sub.registration else None)
        if _is_in_range(active_time, range_info['start_dt'], range_info['end_dt']):
            participant_ids.add(sub.registration_id)

    registrations = [reg for reg in registrations_all if reg.id in participant_ids]
    submissions = []
    for sub in submissions_all:
        active_time = sub.created_at or (sub.registration.created_at if sub.registration else None)
        if sub.registration_id in participant_ids and _is_in_range(active_time, range_info['start_dt'], range_info['end_dt']):
            submissions.append(sub)

    return topics, registrations, submissions


def _build_group_rankings(registrations, submissions, platform_key='all'):
    reg_by_id = {reg.id: reg for reg in registrations}
    participant_counts = Counter((reg.group_num or '未分组') for reg in registrations)
    ranking = {}

    for group, count in participant_counts.items():
        ranking[group] = {
            'group': group,
            'participants': count,
            'published_count': 0,
            'views': 0,
            'likes': 0,
            'favorites': 0,
            'comments': 0,
            'interactions': 0,
        }

    for sub in submissions:
        metrics = _collect_platform_metrics(sub, platform_key)
        if not metrics['has_link']:
            continue
        reg = reg_by_id.get(sub.registration_id) or sub.registration
        group = (reg.group_num if reg else '') or '未分组'
        current = ranking.setdefault(group, {
            'group': group,
            'participants': participant_counts.get(group, 0),
            'published_count': 0,
            'views': 0,
            'likes': 0,
            'favorites': 0,
            'comments': 0,
            'interactions': 0,
        })
        current['published_count'] += 1
        current['views'] += metrics['views']
        current['likes'] += metrics['likes']
        current['favorites'] += metrics['favorites']
        current['comments'] += metrics['comments']
        current['interactions'] += metrics['interactions']

    rows = []
    for row in ranking.values():
        participants = row['participants']
        row['views_per_capita'] = round(row['views'] / participants, 2) if participants else 0
        row['interactions_per_capita'] = round(row['interactions'] / participants, 2) if participants else 0
        row['interaction_rate'] = _calculate_rate(row['interactions'], row['views'])
        row['interaction_rate_display'] = _format_rate(row['interaction_rate'])
        rows.append(row)

    rows.sort(key=lambda item: (item['interactions'], item['views'], item['published_count']), reverse=True)
    return rows


def _build_personal_rankings(registrations, submissions):
    reg_by_id = {reg.id: reg for reg in registrations}
    topic_map = {reg.id: (reg.topic.topic_name if reg.topic else '') for reg in registrations}

    def collect(keys, limit=20):
        rows = []
        for sub in submissions:
            metrics = {
                'has_link': any(_submission_has_platform_link(sub, key) for key in keys),
                'views': 0,
                'likes': 0,
                'favorites': 0,
                'comments': 0,
            }
            for key in keys:
                metrics['views'] += getattr(sub, f'{key}_views', 0) or 0
                metrics['likes'] += getattr(sub, f'{key}_likes', 0) or 0
                metrics['favorites'] += getattr(sub, f'{key}_favorites', 0) or 0
                metrics['comments'] += getattr(sub, f'{key}_comments', 0) or 0

            if not metrics['has_link']:
                continue

            reg = reg_by_id.get(sub.registration_id) or sub.registration
            rows.append({
                'registration_id': sub.registration_id,
                'name': reg.name if reg else '未命名',
                'group': (reg.group_num if reg else '') or '未分组',
                'topic': topic_map.get(sub.registration_id, ''),
                'views': metrics['views'],
                'likes': metrics['likes'],
                'favorites': metrics['favorites'],
                'comments': metrics['comments'],
                'interactions': metrics['likes'] + metrics['favorites'] + metrics['comments'],
            })

        rows.sort(key=lambda item: (item['interactions'], item['views']), reverse=True)
        return rows[:limit]

    return {
        'all_platform': collect(PRIMARY_PERSONAL_PLATFORMS),
        'xhs': collect(['xhs']),
        'douyin': collect(['douyin']),
        'video': collect(['video']),
    }


def _trend_score(note):
    return (
        (note.likes or 0) +
        (note.favorites or 0) * 2 +
        (note.comments or 0) * 3 +
        min((note.views or 0) // 100, 200)
    )


def _extract_keywords_from_note(note):
    keywords = _split_keywords(note.keyword)
    search_text = f"{note.title or ''} {note.summary or ''}"
    for seed in LIVER_KEYWORD_SEEDS:
        if seed in search_text and seed not in keywords:
            keywords.append(seed)
    return keywords[:6]


def _detect_soft_insertion(text):
    text = text or ''
    if any(token in text for token in ['FibroScan', '福波看', '肝弹', '肝硬度', '体检', '检查', '转氨酶']):
        return 'FibroScan福波看'
    if any(token in text for token in ['脂肪肝', '减脂', '肥胖', '代谢']):
        return '壳脂胶囊治疗脂肪肝'
    return '复方鳖甲软肝片'


def _pick_asset_types(keyword):
    text = keyword or ''
    if any(token in text for token in ['FibroScan', '福波看', '肝弹', '体检', '转氨酶']):
        return ['医学科普图', '检查流程图', '知识卡片']
    if '脂肪肝' in text:
        return ['知识卡片', '误区对照图', '复查清单卡']
    return ['医学科普图', '知识卡片', '复查清单卡']


def _matching_corpus_snippets(keyword, limit=3):
    entries = CorpusEntry.query.filter_by(status='active').filter(CorpusEntry.pool_status != 'archived').order_by(CorpusEntry.updated_at.desc()).all()
    if not entries:
        return []

    hits = []
    for entry in entries:
        haystack = f"{entry.title or ''} {entry.tags or ''} {entry.content or ''}"
        score = 0
        for token in _split_keywords(keyword):
            if token and token in haystack:
                score += 2
        if entry.category in ['合规表达', '爆款拆解', '封面模板']:
            score += 1
        if score > 0:
            hits.append((score, entry))

    hits.sort(key=lambda item: (item[0], item[1].updated_at or datetime.min), reverse=True)
    return [entry for _, entry in hits[:limit]]


def _build_topic_prompt(title, keyword, persona, content_type, insertion, corpus_entries):
    corpus_text = '\n'.join([f"- {entry.title}：{_truncate_text(entry.content, 80)}" for entry in corpus_entries]) or '- 暂无附加语料'
    return (
        f"请围绕《{title}》写一篇小红书文案。\n"
        f"人设：{persona}\n"
        f"内容类型：{content_type}\n"
        f"重点关键词：{keyword}\n"
        f"软植入方向：{insertion}\n"
        f"语料参考：\n{corpus_text}\n"
        f"合规要求：{COMPLIANCE_BASELINE}\n"
        "风格要求：真实口语化、去AI腔、首屏有钩子、正文200-350字、结尾自然提问。"
    )


def _generate_topic_ideas(count=80, activity_id=None, quota=None):
    recent_notes = TrendNote.query.filter(TrendNote.pool_status != 'archived').order_by(TrendNote.created_at.desc()).limit(300).all()
    topic_quota = _normalize_quota(quota)
    keyword_scores = defaultdict(int)
    keyword_notes = defaultdict(list)

    for note in recent_notes:
        extracted = _extract_keywords_from_note(note)
        if not extracted:
            continue
        score = max(_trend_score(note), 1)
        for keyword in extracted:
            keyword_scores[keyword] += score
            if len(keyword_notes[keyword]) < 5:
                keyword_notes[keyword].append(note)

    for idx, seed in enumerate(LIVER_KEYWORD_SEEDS, start=1):
        keyword_scores[seed] += max(10 - idx // 3, 1)

    sorted_keywords = sorted(keyword_scores.items(), key=lambda item: item[1], reverse=True)
    if not sorted_keywords:
        sorted_keywords = [(seed, len(LIVER_KEYWORD_SEEDS) - idx) for idx, seed in enumerate(LIVER_KEYWORD_SEEDS)]

    angle_templates = [
        '体检发现{keyword}异常，下一步到底先做什么？',
        '{keyword}拖着不管的人，后来最容易后悔哪一步？',
        '关于{keyword}，门诊里最常被问到的3个问题',
        '{keyword}到底要不要复查？什么时间点更关键？',
        '{keyword}相关内容怎么写，既有信任感又不吓人？',
        '{keyword}最容易被误解的地方，很多人第一步就走偏了',
        '{keyword}人群日常管理，哪些动作是高频踩坑点？',
        '{keyword}做成知识卡片时，哪3个信息点最容易被收藏？',
        '{keyword}这类爆款笔记，为什么大家愿意看完并互动？',
        '{keyword}相关复查和管理，真实用户最关心什么？',
    ]

    created = []
    seen_titles = {idea.topic_title for idea in TopicIdea.query.all()}
    max_attempts = max(count * 6, 200)
    attempt = 0

    while len(created) < count and attempt < max_attempts:
        keyword, score = sorted_keywords[attempt % len(sorted_keywords)]
        persona = TOPIC_PERSONAS[attempt % len(TOPIC_PERSONAS)]
        content_type = TOPIC_CONTENT_TYPES[(attempt + len(keyword)) % len(TOPIC_CONTENT_TYPES)]
        angle_template = angle_templates[(attempt + score) % len(angle_templates)]
        title = angle_template.format(keyword=keyword)
        insertion = _detect_soft_insertion(keyword + title)
        asset_types = _pick_asset_types(keyword)
        note_refs = keyword_notes.get(keyword, [])[:3]
        ref_links = [note.link for note in note_refs if note.link]
        ref_ids = [str(note.id) for note in note_refs]
        corpus_entries = _matching_corpus_snippets(keyword)
        source_keywords = [keyword]
        if note_refs:
            source_keywords.extend(_extract_keywords_from_note(note_refs[0]))
        cover_title = _truncate_text(f'{keyword}高频问题', 18)
        angle = (
            f"以{persona}切入，用{content_type}方式拆解“{keyword}”热点话题，"
            f"结合近期热门内容常见的焦虑点、误区和下一步动作，"
            f"自然带出{insertion}，但表达必须符合医疗广告合规。"
        )
        asset_brief = (
            f"建议做{asset_types[0]}、{asset_types[1]}、{asset_types[2]}三套素材；"
            f"主封面标题用“{cover_title}”，画面突出问题句、数字和复查提醒。"
        )

        if title in seen_titles:
            attempt += 1
            continue

        idea = TopicIdea(
            activity_id=activity_id,
            topic_title=title,
            keywords=','.join(dict.fromkeys(source_keywords))[:500],
            angle=angle,
            content_type=content_type,
            persona=persona,
            soft_insertion=insertion,
            hot_value=min(score, 9999),
            source_note_ids=','.join(ref_ids),
            source_links='\n'.join(ref_links),
            copy_prompt=_build_topic_prompt(title, keyword, persona, content_type, insertion, corpus_entries),
            cover_title=cover_title,
            asset_brief=asset_brief,
            compliance_note=COMPLIANCE_BASELINE,
            quota=topic_quota,
            status='pending_review'
        )
        for note in note_refs:
            if note.pool_status != 'archived':
                note.pool_status = 'candidate'
        created.append(idea)
        seen_titles.add(title)
        attempt += 1

    return created


def _wrap_svg_text(text, line_length=11, max_lines=3):
    text = re.sub(r'\s+', '', (text or '').strip())
    if not text:
        return []
    lines = [text[i:i + line_length] for i in range(0, len(text), line_length)]
    return lines[:max_lines]


def _svg_data_uri(svg_text):
    encoded = base64.b64encode(svg_text.encode('utf-8')).decode('ascii')
    return f'data:image/svg+xml;base64,{encoded}'


def _render_svg_card(card_type, title, subtitle, bullets, accent='#ff6b57', bg='#fff7f3'):
    title_lines = _wrap_svg_text(title, line_length=10, max_lines=3)
    subtitle_lines = _wrap_svg_text(subtitle, line_length=16, max_lines=2)
    safe_bullets = bullets[:3]

    title_svg = ''.join(
        f'<text x="48" y="{118 + idx * 44}" font-size="34" font-weight="700" fill="#242424">{html.escape(line)}</text>'
        for idx, line in enumerate(title_lines)
    )
    subtitle_svg = ''.join(
        f'<text x="48" y="{255 + idx * 26}" font-size="20" fill="#4c4c4c">{html.escape(line)}</text>'
        for idx, line in enumerate(subtitle_lines)
    )

    bullet_svg = ''
    base_y = 355
    for idx, bullet in enumerate(safe_bullets):
        y = base_y + idx * 82
        bullet_lines = _wrap_svg_text(bullet, line_length=18, max_lines=2)
        bullet_svg += f'<rect x="44" y="{y - 24}" rx="24" ry="24" width="392" height="58" fill="white" opacity="0.95" />'
        bullet_svg += f'<circle cx="74" cy="{y + 5}" r="14" fill="{accent}" />'
        bullet_svg += f'<text x="69" y="{y + 11}" font-size="16" font-weight="700" fill="white">{idx + 1}</text>'
        for line_idx, line in enumerate(bullet_lines):
            bullet_svg += (
                f'<text x="98" y="{y + line_idx * 22}" font-size="19" fill="#2c2c2c">'
                f'{html.escape(line)}</text>'
            )

    badge_map = {
        '医学科普图': '#FFE4DA',
        '知识卡片': '#E8F4FF',
        '检查流程图': '#FFF1CC',
        '误区对照图': '#FDE7EC',
        '复查清单卡': '#EAF7E7',
    }
    badge_bg = badge_map.get(card_type, '#FFE4DA')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1440" viewBox="0 0 480 640">
<defs>
<linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
<stop offset="0%" stop-color="{bg}" />
<stop offset="100%" stop-color="#ffffff" />
</linearGradient>
</defs>
<rect width="480" height="640" rx="36" fill="url(#g)" />
<circle cx="400" cy="70" r="88" fill="{accent}" opacity="0.15" />
<circle cx="100" cy="600" r="72" fill="{accent}" opacity="0.10" />
<rect x="42" y="42" width="138" height="42" rx="21" fill="{badge_bg}" />
<text x="62" y="69" font-size="19" font-weight="700" fill="{accent}">{html.escape(card_type)}</text>
{title_svg}
{subtitle_svg}
<rect x="42" y="302" rx="28" ry="28" width="396" height="286" fill="{accent}" opacity="0.12" />
{bullet_svg}
</svg>'''


def _extract_content_points(content):
    text = re.sub(r'(标题|钩子|正文|内文|结尾互动)\s*[：:]', ' ', content or '')
    parts = [part.strip() for part in re.split(r'[。！？\n]+', text) if part and part.strip()]
    points = []
    for part in parts:
        if 6 <= len(part) <= 32:
            points.append(part)
        if len(points) >= 3:
            break
    return points


def _build_creative_pack(topic, selected_content=''):
    topic_name = topic.topic_name or '肝病热点'
    keywords = _split_keywords(topic.keywords or topic_name)
    primary_keyword = keywords[0] if keywords else topic_name
    insertion = _detect_soft_insertion(f'{topic_name} {" ".join(keywords)}')
    content_points = _extract_content_points(selected_content)

    if any(token in topic_name for token in ['体检', 'FibroScan', '福波看', '肝弹', '转氨酶', '肝硬度']):
        configs = [
            ('医学科普图', f'{primary_keyword}怎么判断', '体检后先看这3件事', content_points or ['先看指标变化，不只盯单次结果', '把复查时间和检查方式说明白', f'自然带出{insertion}的检查评估场景'], '#FF7A59', '#FFF4EE'),
            ('检查流程图', f'{primary_keyword}复查流程', '适合做流程型配图', content_points or ['异常发现', '进一步评估', '复查跟踪'], '#F2A43C', '#FFF8EA'),
            ('知识卡片', f'{primary_keyword}高频问题', '评论区最容易被问到的点', content_points or ['为什么会异常', '什么人更要重视', '下一步怎么安排'], '#4C91FF', '#EEF5FF'),
        ]
    elif '脂肪肝' in topic_name:
        configs = [
            ('知识卡片', f'{primary_keyword}别忽视', '适合收藏型封面', content_points or ['先拆误区，再给动作建议', '重点讲体检和复查节奏', f'软植入{insertion}要自然'], '#FF6B6B', '#FFF2F2'),
            ('误区对照图', f'{primary_keyword}常见误区', '左右对照最容易看懂', content_points or ['误区1：没症状就不用管', '误区2：只看一次报告', '误区3：只靠短期节食'], '#D96570', '#FFF2F5'),
            ('复查清单卡', f'{primary_keyword}复查清单', '截图保存型内容', content_points or ['检查项目别漏掉', '饮食运动要记录', '复查前后做对比'], '#61A36B', '#F0F8F1'),
        ]
    else:
        configs = [
            ('医学科普图', f'{primary_keyword}重点提醒', '适合做专业感封面', content_points or ['标题先问问题', '正文给真实场景', f'植入{insertion}时别写成硬广'], '#FF7A59', '#FFF4EE'),
            ('知识卡片', f'{primary_keyword}三件事', '收藏感最强的一种版式', content_points or ['适合拆成三格信息块', '首屏保留数字和问句', '结尾引导经验交流'], '#4C91FF', '#EEF5FF'),
            ('复查清单卡', f'{primary_keyword}管理清单', '适合带复查节奏', content_points or ['什么时候复查', '哪些指标要看', '如何记录趋势'], '#61A36B', '#F0F8F1'),
        ]

    pack = []
    for idx, (card_type, title, subtitle, bullets, accent, bg) in enumerate(configs, start=1):
        svg = _render_svg_card(card_type, title, subtitle, bullets, accent=accent, bg=bg)
        pack.append({
            'type': card_type,
            'title': title,
            'subtitle': subtitle,
            'bullets': bullets,
            'image_prompt': (
                f'小红书风格{card_type}，主题“{title}”，医疗健康视觉，信息块清晰，'
                f'突出{primary_keyword}，色彩克制，含{len(bullets)}个短信息点，软植入{insertion}。'
            ),
            'download_name': f'creative_{topic.id}_{idx}.svg',
            'svg_data_uri': _svg_data_uri(svg),
        })
    return pack


def _build_graphic_article_bundle(topic, selected_content=''):
    creative_pack = _build_creative_pack(topic, selected_content)
    topic_name = topic.topic_name or '肝病管理'
    keywords = _split_keywords(topic.keywords or topic_name)
    content_title = _extract_title_from_version(selected_content) if selected_content else topic_name
    raw_body = _extract_body_from_version(selected_content) if selected_content else ''
    raw_body = re.sub(r'^(正文|内文)\s*[：:]\s*', '', (raw_body or '').strip())
    if not raw_body:
        raw_body = f'这篇内容围绕“{topic_name}”展开，先讲真实场景，再拆重点，最后给出复查或管理建议。'

    body_sentences = [item.strip() for item in re.split(r'[。！？\n]+', raw_body) if item and item.strip()]
    body_excerpt = '。'.join(body_sentences[:3]).strip()
    if body_excerpt and not body_excerpt.endswith(('。', '！', '？')):
        body_excerpt += '。'

    tag_text = ' '.join([f'#{item}' for item in keywords[:4]])
    bundles = []
    for index, asset in enumerate(creative_pack, start=1):
        bullet_lines = [item.strip() for item in (asset.get('bullets') or []) if item and item.strip()]
        support_text = '；'.join(bullet_lines[:3])
        publish_title = (asset.get('title') or content_title or topic_name).strip()[:18]
        publish_body = body_excerpt
        if support_text:
            publish_body = f'{publish_body}\n\n这版我想重点放在：{support_text}。'
        publish_body = f"{publish_body}\n\n封面我会用“{asset.get('type') or '知识卡片'}”这个版式，方便一眼看懂重点。"
        publish_body = f"{publish_body}\n\n你们更想看哪一类延展内容？"

        full_copy = f"标题：{publish_title}\n内文：{publish_body}\n\n推荐标签：{tag_text or '#肝病管理'}"
        bundles.append({
            'id': index,
            'asset': asset,
            'publish_title': publish_title,
            'publish_body': publish_body,
            'full_copy': full_copy,
            'tag_text': tag_text or '#肝病管理',
            'cover_title': asset.get('title') or publish_title,
            'card_type': asset.get('type') or '知识卡片',
            'summary': support_text or asset.get('subtitle') or '',
        })
    return bundles


def _build_asset_generation_prompt(topic, selected_content='', style_preset='小红书图文', title_hint=''):
    topic_name = topic.topic_name or '肝病管理'
    keywords = _split_keywords(topic.keywords or topic_name)
    primary_keyword = keywords[0] if keywords else topic_name
    clean_title = (title_hint or '').strip() or _extract_title_from_version(selected_content) or topic_name
    body = _extract_body_from_version(selected_content) if selected_content else ''
    body = re.sub(r'^(正文|内文)\s*[：:]\s*', '', (body or '').strip())
    support_points = _extract_content_points(body) if body else []
    point_text = '；'.join(support_points[:3]) if support_points else f'围绕{primary_keyword}做清晰信息表达'
    return (
        f'{style_preset}，适合小红书封面与配图，主题“{clean_title}”，'
        f'核心关键词：{primary_keyword}，风格要求：干净、真实、医疗信息清楚、不过度营销。'
        f'画面重点：{point_text}。配色建议与当前话题一致，保留收藏感和截图传播感。'
    )


def _build_asset_generation_fallback_results(topic, selected_content='', image_count=3):
    creative_pack = _build_creative_pack(topic, selected_content)
    results = []
    for idx, asset in enumerate(creative_pack[:max(image_count, 1)], start=1):
        results.append({
            'index': idx,
            'type': asset.get('type') or '知识卡片',
            'title': asset.get('title') or '',
            'subtitle': asset.get('subtitle') or '',
            'image_prompt': asset.get('image_prompt') or '',
            'preview_url': asset.get('svg_data_uri') or '',
            'download_name': asset.get('download_name') or f'asset_{idx}.svg',
            'provider': 'svg_fallback',
            'format': 'svg',
            'bullets': asset.get('bullets') or [],
        })
    return results


def _build_dashboard_stats(activity_id, args):
    range_info = _resolve_analysis_range(args)
    topics, registrations, submissions = _load_activity_scope(activity_id, range_info)
    topic_map = {topic.id: topic.topic_name for topic in topics}
    reg_by_id = {reg.id: reg for reg in registrations}

    total_participants = len(registrations)
    total_published_ids = {sub.registration_id for sub in submissions if _submission_has_any_link(sub)}
    total_published = len(total_published_ids)

    total_likes = total_favorites = total_comments = total_views = 0
    platform_published = {}
    platform_stats = {}

    for platform_key, label in PLATFORM_DEFINITIONS:
        platform_submissions = [sub for sub in submissions if _submission_has_platform_link(sub, platform_key)]
        participant_ids = {sub.registration_id for sub in platform_submissions}
        views = sum(getattr(sub, f'{platform_key}_views', 0) or 0 for sub in platform_submissions)
        likes = sum(getattr(sub, f'{platform_key}_likes', 0) or 0 for sub in platform_submissions)
        favorites = sum(getattr(sub, f'{platform_key}_favorites', 0) or 0 for sub in platform_submissions)
        comments = sum(getattr(sub, f'{platform_key}_comments', 0) or 0 for sub in platform_submissions)
        interactions = likes + favorites + comments
        platform_published[platform_key] = len(platform_submissions)
        platform_stats[platform_key] = {
            'label': label,
            'participants': len(participant_ids),
            'published_count': len(platform_submissions),
            'views': views,
            'likes': likes,
            'favorites': favorites,
            'comments': comments,
            'interactions': interactions,
            'interaction_rate': _calculate_rate(interactions, views),
            'interaction_rate_display': _format_rate(_calculate_rate(interactions, views)),
            'penetration_rate': _calculate_rate(len(platform_submissions), total_participants),
            'penetration_rate_display': _format_rate(_calculate_rate(len(platform_submissions), total_participants)),
        }
        total_views += views
        total_likes += likes
        total_favorites += favorites
        total_comments += comments

    total_interactions = total_likes + total_favorites + total_comments
    publish_rate = _calculate_rate(total_published, total_participants)

    group_stats = {}
    for reg in registrations:
        group = reg.group_num or '未分组'
        if group not in group_stats:
            group_stats[group] = {'count': 0, 'published': 0}
        group_stats[group]['count'] += 1
        if reg.id in total_published_ids:
            group_stats[group]['published'] += 1

    group_participants = [
        {'group': group, 'participants': data['count']}
        for group, data in sorted(group_stats.items(), key=lambda item: (-item[1]['count'], item[0]))
    ]

    topic_stats = []
    for topic in topics:
        count = len([reg for reg in registrations if reg.topic_id == topic.id])
        topic_stats.append({'name': topic.topic_name, 'count': count})
    topic_stats.sort(key=lambda item: item['count'], reverse=True)

    content_type_stats = {}
    content_type_perf = {}
    for sub in submissions:
        content_type = (sub.content_type or '').strip() or '未识别'
        metrics = _collect_platform_metrics(sub, 'all')
        content_type_stats[content_type] = content_type_stats.get(content_type, 0) + 1
        current = content_type_perf.setdefault(content_type, {'count': 0, 'views': 0, 'interactions': 0})
        current['count'] += 1
        current['views'] += metrics['views']
        current['interactions'] += metrics['interactions']

    best_content_type = None
    for row in content_type_perf.values():
        row['avg_interactions'] = round(row['interactions'] / row['count'], 2) if row['count'] else 0
        row['interaction_rate'] = _calculate_rate(row['interactions'], row['views'])
        row['interaction_rate_display'] = _format_rate(row['interaction_rate'])

    if content_type_perf:
        best_content_type = sorted(
            content_type_perf.items(),
            key=lambda item: ((item[1]['interaction_rate'] or 0), item[1]['avg_interactions']),
            reverse=True
        )[0][0]

    personal_rankings = _build_personal_rankings(registrations, submissions)
    group_rankings = {
        'all_platform': _build_group_rankings(registrations, submissions, 'all'),
        'xhs': _build_group_rankings(registrations, submissions, 'xhs'),
        'douyin': _build_group_rankings(registrations, submissions, 'douyin'),
        'video': _build_group_rankings(registrations, submissions, 'video'),
        'weibo': _build_group_rankings(registrations, submissions, 'weibo'),
    }

    group_completion = []
    for group, data in group_stats.items():
        completion_rate = _calculate_rate(data['published'], data['count'])
        group_completion.append({
            'group': group,
            'count': data['count'],
            'published': data['published'],
            'completion_rate': completion_rate or 0,
        })
    group_completion.sort(key=lambda item: item['completion_rate'], reverse=True)

    viral_notes = []
    for sub in submissions:
        if not _submission_has_platform_link(sub, 'xhs'):
            continue
        reg = reg_by_id.get(sub.registration_id) or sub.registration
        xhs_interactions = (sub.xhs_likes or 0) + (sub.xhs_favorites or 0) + (sub.xhs_comments or 0)
        viral_notes.append({
            'name': reg.name if reg else '未命名',
            'group': (reg.group_num if reg else '') or '未分组',
            'topic': reg.topic.topic_name if reg and reg.topic else '',
            'content_type': (sub.content_type or '未识别'),
            'xhs_link': sub.xhs_link,
            'xhs_views': sub.xhs_views or 0,
            'xhs_likes': sub.xhs_likes or 0,
            'xhs_favorites': sub.xhs_favorites or 0,
            'xhs_comments': sub.xhs_comments or 0,
            'xhs_interactions': xhs_interactions,
        })
    viral_notes.sort(key=lambda item: (item['xhs_interactions'], item['xhs_views']), reverse=True)

    type_note_recommendations = {}
    for note in viral_notes:
        content_type = note['content_type'] or '未识别'
        type_note_recommendations.setdefault(content_type, [])
        if len(type_note_recommendations[content_type]) < 3:
            type_note_recommendations[content_type].append(note)

    top_keyword_trends = []
    recent_trends = TrendNote.query.order_by(TrendNote.created_at.desc()).limit(200).all()
    trend_keyword_scores = defaultdict(int)
    for note in recent_trends:
        for keyword in _extract_keywords_from_note(note):
            trend_keyword_scores[keyword] += _trend_score(note)
    for keyword, score in sorted(trend_keyword_scores.items(), key=lambda item: item[1], reverse=True)[:5]:
        top_keyword_trends.append({'keyword': keyword, 'score': score})

    note_improvement_suggestions = []
    if publish_rate is not None and publish_rate < 60:
        note_improvement_suggestions.append('先补齐提交率，建议增加组长催更、截止提醒和二次提交入口。')
    if best_content_type:
        note_improvement_suggestions.append(f'当前最佳内容类型是“{best_content_type}”，建议沉淀成固定模板。')
    low_groups = [row['group'] for row in group_completion if row['completion_rate'] < 50]
    if low_groups:
        note_improvement_suggestions.append('低完成率小组：' + '、'.join(low_groups) + '，建议安排小组共创和复盘。')
    if not note_improvement_suggestions:
        note_improvement_suggestions.append('整体运行平稳，可以继续做标题钩子和封面形式的A/B测试。')

    next_topic_suggestions = []
    if top_keyword_trends:
        next_topic_suggestions.extend([f"围绕“{row['keyword']}”做多角度选题和素材分发" for row in top_keyword_trends[:3]])
    if best_content_type in ['检查解读型', '复查管理型', '轻科普问答型']:
        next_topic_suggestions.append('继续加大检查解读和复查管理类话题占比。')
    if best_content_type in ['真实经历型', '场景种草型']:
        next_topic_suggestions.append('增加患者/家属/体检人群多角色叙事，提高互动回复率。')
    next_topic_suggestions = next_topic_suggestions[:5]

    definitions = [
        '总参与人数 = 报名人数',
        '总发布条数 = 任一平台有链接算1条',
        '平台发布条数 = 该平台有链接',
        '总互动 = 点赞 + 收藏 + 评论',
        '互动率分母为传播量，传播量=0时显示“-”',
        '时间筛选按参与活跃时间统计：报名时间或提交更新时间命中筛选区间即纳入统计',
    ]

    return {
        'activity_id': activity_id,
        'range': {
            'key': range_info['key'],
            'label': range_info['label'],
            'start_date': range_info['start_date'],
            'end_date': range_info['end_date'],
        },
        'definitions': definitions,
        'overview': {
            'total_participants': total_participants,
            'group_participants': group_participants,
            'total_published': total_published,
            'publish_rate': publish_rate,
            'publish_rate_display': _format_rate(publish_rate),
            'platform_publish_counts': platform_published,
            'platform_penetration': {
                key: {
                    'rate': platform_stats[key]['penetration_rate'],
                    'display': platform_stats[key]['penetration_rate_display'],
                } for key, _ in PLATFORM_DEFINITIONS
            },
        },
        'platforms': platform_stats,
        'group_rankings': group_rankings,
        'personal_rankings': personal_rankings,
        'top_keyword_trends': top_keyword_trends,
        'total_registrations': total_participants,
        'total_published': total_published,
        'total_likes': total_likes,
        'total_favorites': total_favorites,
        'total_comments': total_comments,
        'total_views': total_views,
        'total_interactions': total_interactions,
        'group_stats': group_stats,
        'topic_stats': topic_stats,
        'content_type_stats': content_type_stats,
        'content_type_performance': content_type_perf,
        'best_content_type': best_content_type,
        'group_completion': group_completion,
        'viral_notes': viral_notes[:20],
        'type_note_recommendations': type_note_recommendations,
        'note_improvement_suggestions': note_improvement_suggestions,
        'next_topic_suggestions': next_topic_suggestions,
        'top_30': personal_rankings['all_platform'][:30],
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }

# ==================== 路由 ====================

@app.route('/')
def index():
    activity = Activity.query.filter_by(status='published').order_by(Activity.created_at.desc()).first()
    if not activity:
        activities = Activity.query.order_by(Activity.created_at.desc()).all()
        if activities:
            activity = activities[0]

    page_config = _get_site_page_config('home')
    theme = _get_active_site_theme()
    site_config = _serialize_site_page_config(page_config) if page_config else {
        **DEFAULT_HOME_PAGE_CONFIG,
        'nav_items': [dict(item) for item in DEFAULT_SITE_NAV_ITEMS],
    }
    site_theme = _serialize_site_theme(theme) if theme else dict(DEFAULT_SITE_THEME)

    split_index = _normalize_quota(site_config.get('primary_topic_limit'), default=DEFAULT_HOME_PAGE_CONFIG['primary_topic_limit'], min_value=1, max_value=120)
    all_topics = list(activity.topics) if activity else []
    primary_topics = all_topics[:split_index]
    secondary_topics = all_topics[split_index:]
    first_available_topic = next((topic for topic in all_topics if (topic.filled or 0) < (topic.quota or 0)), None)
    announcements = [_serialize_announcement(item) for item in _list_announcements(limit=4)]
    trend_notes = [{
        'id': note.id,
        'title': note.title or '',
        'keyword': note.keyword or '',
        'source_platform': note.source_platform or '',
        'likes': note.likes or 0,
        'favorites': note.favorites or 0,
        'comments': note.comments or 0,
        'views': note.views or 0,
        'link': note.link or '',
    } for note in TrendNote.query.order_by(TrendNote.created_at.desc()).limit(6).all()]

    hero_title = (site_config.get('hero_title') or '').strip() or (activity.title if activity else '')
    hero_subtitle = (site_config.get('hero_subtitle') or '').strip() or (activity.description if activity else '')
    hero_badge = (site_config.get('hero_badge') or '').strip() or (activity.name if activity else '内容运营平台')

    return render_template(
        'index.html',
        activity=activity,
        primary_topics=primary_topics,
        secondary_topics=secondary_topics,
        first_available_topic=first_available_topic,
        announcements=announcements,
        trend_notes=trend_notes,
        site_config={
            **site_config,
            'hero_title': hero_title,
            'hero_subtitle': hero_subtitle,
            'hero_badge': hero_badge,
        },
        site_theme=site_theme,
    )

@app.route('/topic/<int:topic_id>')
def topic_detail(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    return render_template('topic_detail.html', topic=topic)

# 报名成功页面（带一键生成文案）
@app.route('/register_success/<int:reg_id>')
def register_success(reg_id):
    reg = Registration.query.get_or_404(reg_id)
    return render_template('register_success.html', registration=reg)

@app.route('/my_registration', methods=['GET', 'POST'])
def my_registration():
    # 如果有reg_id参数，仍按"列表卡片"统一展示（避免不同人展示样式不一致）
    reg_id = request.args.get('reg_id')
    if reg_id:
        reg = Registration.query.get(int(reg_id))
        if reg:
            return render_template('my_registration.html', registrations=[reg])

    if request.method == 'POST':
        group_num = request.form.get('group_num')
        name = request.form.get('name')

        # 查询该姓名下的所有报名记录
        regs = Registration.query.filter_by(group_num=group_num, name=name).all()
        if regs:
            # 统一走同一展示模板：无论几条都用列表卡片
            return render_template('my_registration.html', registrations=regs)
        else:
            return render_template('my_registration.html', error='未找到报名信息')

    return render_template('my_registration.html')

@app.route('/api/topics/<int:activity_id>')
def get_topics(activity_id):
    topics = Topic.query.filter_by(activity_id=activity_id).all()
    return jsonify([_serialize_topic(topic) for topic in topics])


@app.route('/api/profile_by_phone')
def profile_by_phone():
    phone = (request.args.get('phone') or '').strip()
    if not phone:
        return jsonify({'success': False, 'message': '手机号不能为空'})

    reg = Registration.query.filter_by(phone=phone).order_by(Registration.created_at.desc()).first()
    if not reg:
        return jsonify({'success': True, 'found': False})

    return jsonify({
        'success': True,
        'found': True,
        'profile': {
            'name': reg.name or '',
            'xhs_account': reg.xhs_account or '',
            'group_num': reg.group_num or ''
        }
    })


@app.route('/api/admin/site-config', methods=['GET', 'POST'])
def admin_site_config():
    guard = _admin_json_guard()
    if guard:
        return guard

    created_defaults = False
    page_config = _get_site_page_config('home')
    if not page_config:
        page_config = SitePageConfig(
            page_key=DEFAULT_HOME_PAGE_CONFIG['page_key'],
            site_name=DEFAULT_HOME_PAGE_CONFIG['site_name'],
            page_title=DEFAULT_HOME_PAGE_CONFIG['page_title'],
            hero_badge=DEFAULT_HOME_PAGE_CONFIG['hero_badge'],
            hero_title=DEFAULT_HOME_PAGE_CONFIG['hero_title'],
            hero_subtitle=DEFAULT_HOME_PAGE_CONFIG['hero_subtitle'],
            announcement_title=DEFAULT_HOME_PAGE_CONFIG['announcement_title'],
            trend_title=DEFAULT_HOME_PAGE_CONFIG['trend_title'],
            primary_section_title=DEFAULT_HOME_PAGE_CONFIG['primary_section_title'],
            primary_section_icon=DEFAULT_HOME_PAGE_CONFIG['primary_section_icon'],
            secondary_section_title=DEFAULT_HOME_PAGE_CONFIG['secondary_section_title'],
            secondary_section_icon=DEFAULT_HOME_PAGE_CONFIG['secondary_section_icon'],
            primary_topic_limit=DEFAULT_HOME_PAGE_CONFIG['primary_topic_limit'],
            footer_text=DEFAULT_HOME_PAGE_CONFIG['footer_text'],
            nav_items=json.dumps(DEFAULT_SITE_NAV_ITEMS, ensure_ascii=False),
        )
        db.session.add(page_config)
        created_defaults = True

    theme = _get_active_site_theme()
    if not theme:
        theme = SiteTheme(theme_key=DEFAULT_SITE_THEME['theme_key'], name=DEFAULT_SITE_THEME['name'], is_active=True)
        for field, default_value in DEFAULT_SITE_THEME.items():
            if field in {'theme_key', 'name'}:
                continue
            setattr(theme, field, default_value)
        db.session.add(theme)
        created_defaults = True
    if created_defaults:
        db.session.commit()
    elif page_config.id is None or theme.id is None:
        db.session.flush()

    if request.method == 'POST':
        payload = request.json or {}
        config_data = payload.get('page_config') if isinstance(payload.get('page_config'), dict) else payload
        theme_data = payload.get('theme') if isinstance(payload.get('theme'), dict) else {}

        page_config.site_name = (config_data.get('site_name') or DEFAULT_HOME_PAGE_CONFIG['site_name']).strip()[:100]
        page_config.page_title = (config_data.get('page_title') or DEFAULT_HOME_PAGE_CONFIG['page_title']).strip()[:200]
        page_config.hero_badge = (config_data.get('hero_badge') or '').strip()[:100]
        page_config.hero_title = (config_data.get('hero_title') or '').strip()[:200]
        page_config.hero_subtitle = (config_data.get('hero_subtitle') or '').strip()
        page_config.announcement_title = (config_data.get('announcement_title') or DEFAULT_HOME_PAGE_CONFIG['announcement_title']).strip()[:100]
        page_config.trend_title = (config_data.get('trend_title') or DEFAULT_HOME_PAGE_CONFIG['trend_title']).strip()[:100]
        page_config.primary_section_title = (config_data.get('primary_section_title') or DEFAULT_HOME_PAGE_CONFIG['primary_section_title']).strip()[:100]
        page_config.primary_section_icon = (config_data.get('primary_section_icon') or DEFAULT_HOME_PAGE_CONFIG['primary_section_icon']).strip()[:50]
        page_config.secondary_section_title = (config_data.get('secondary_section_title') or DEFAULT_HOME_PAGE_CONFIG['secondary_section_title']).strip()[:100]
        page_config.secondary_section_icon = (config_data.get('secondary_section_icon') or DEFAULT_HOME_PAGE_CONFIG['secondary_section_icon']).strip()[:50]
        page_config.primary_topic_limit = _normalize_quota(
            config_data.get('primary_topic_limit'),
            default=DEFAULT_HOME_PAGE_CONFIG['primary_topic_limit'],
            min_value=1,
            max_value=120,
        )
        page_config.footer_text = (config_data.get('footer_text') or DEFAULT_HOME_PAGE_CONFIG['footer_text']).strip()[:200]
        page_config.nav_items = json.dumps(_normalize_nav_items(config_data.get('nav_items')), ensure_ascii=False)

        theme.name = (theme_data.get('name') or theme.name or DEFAULT_SITE_THEME['name']).strip()[:100]
        for field, default_value in DEFAULT_SITE_THEME.items():
            if field in {'theme_key', 'name'}:
                continue
            if field == 'font_family':
                setattr(theme, field, (theme_data.get(field) or theme.font_family or default_value).strip()[:200])
                continue
            if field == 'footer_text':
                setattr(theme, field, (theme_data.get(field) or page_config.footer_text or default_value).strip()[:200])
                continue
            setattr(theme, field, _normalize_hex_color(theme_data.get(field), getattr(theme, field) or default_value))
        theme.is_active = True
        SiteTheme.query.filter(SiteTheme.id != theme.id).update({'is_active': False}, synchronize_session=False)

        db.session.flush()
        _log_operation('save_site_config', 'site_page_config', target_id=page_config.id, message='更新网站门户配置', detail={
            'page_key': page_config.page_key,
            'theme_id': theme.id,
            'site_name': page_config.site_name,
            'nav_count': len(_normalize_nav_items(config_data.get('nav_items'))),
        })
        db.session.commit()

    return jsonify({
        'success': True,
        'page_config': _serialize_site_page_config(page_config),
        'theme': _serialize_site_theme(theme),
    })


@app.route('/api/admin/announcements', methods=['GET', 'POST'])
def admin_announcements():
    guard = _admin_json_guard()
    if guard:
        return guard

    if request.method == 'POST':
        payload = request.json or {}
        announcement_id = _safe_int(payload.get('id'), 0)
        if announcement_id > 0:
            announcement = Announcement.query.get_or_404(announcement_id)
        else:
            announcement = Announcement()
            db.session.add(announcement)

        title = (payload.get('title') or '').strip()
        content = (payload.get('content') or '').strip()
        if not title:
            return jsonify({'success': False, 'message': '公告标题不能为空'})
        if not content:
            return jsonify({'success': False, 'message': '公告内容不能为空'})

        status = (payload.get('status') or 'draft').strip()
        if status not in {'draft', 'active', 'archived'}:
            return jsonify({'success': False, 'message': '不支持的公告状态'})

        announcement.title = title[:200]
        announcement.content = content
        announcement.link_url = (payload.get('link_url') or '').strip()[:500]
        announcement.button_text = (payload.get('button_text') or '').strip()[:50]
        announcement.priority = max(_safe_int(payload.get('priority'), 100), 0)
        announcement.status = status
        announcement.starts_at = _parse_datetime(payload.get('starts_at'))
        announcement.ends_at = _parse_datetime(payload.get('ends_at'))

        db.session.flush()
        _log_operation('save_announcement', 'announcement', target_id=announcement.id, message='保存网站公告', detail={
            'title': announcement.title,
            'status': announcement.status,
            'priority': announcement.priority,
        })
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '公告已保存',
            'item': _serialize_announcement(announcement),
        })

    status = (request.args.get('status') or '').strip()
    query = Announcement.query
    if status:
        query = query.filter_by(status=status)
    items = query.order_by(Announcement.priority.asc(), Announcement.updated_at.desc(), Announcement.id.desc()).all()
    return jsonify({
        'success': True,
        'items': [_serialize_announcement(item) for item in items]
    })


@app.route('/api/admin/announcements/<int:announcement_id>/status', methods=['POST'])
def update_announcement_status(announcement_id):
    guard = _admin_json_guard()
    if guard:
        return guard

    payload = request.json or {}
    status = (payload.get('status') or '').strip()
    if status not in {'draft', 'active', 'archived'}:
        return jsonify({'success': False, 'message': '不支持的公告状态'})

    announcement = Announcement.query.get_or_404(announcement_id)
    announcement.status = status
    _log_operation('update_status', 'announcement', target_id=announcement.id, message='更新公告状态', detail={
        'title': announcement.title,
        'status': status,
    })
    db.session.commit()
    return jsonify({
        'success': True,
        'message': '公告状态已更新',
        'item': _serialize_announcement(announcement),
    })


@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    topic = Topic.query.get(data.get('topic_id'))

    if not topic:
        return jsonify({'success': False, 'message': '话题不存在'})

    if topic.filled >= topic.quota:
        return jsonify({'success': False, 'message': '名额已满'})

    # 检查是否已报名
    existing = Registration.query.filter_by(
        topic_id=data.get('topic_id'),
        xhs_account=data.get('xhs_account')
    ).first()
    if existing:
        return jsonify({'success': False, 'message': '您已报名此话题'})

    reg = Registration(
        topic_id=data.get('topic_id'),
        group_num=data.get('group_num'),
        name=data.get('name'),
        phone=data.get('phone'),
        xhs_account=data.get('xhs_account')
    )
    db.session.add(reg)
    topic.filled += 1
    db.session.commit()

    return jsonify({'success': True, 'message': '报名成功', 'registration_id': reg.id})

# AI生成文案API - 接入DeepSeek
import requests

DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_API_URL = os.environ.get('DEEPSEEK_API_URL', 'https://api.deepseek.com/v1/chat/completions')

def auto_humanize_text(content):
    """自动去AI化重写（保留原意）"""
    if not content or not DEEPSEEK_API_KEY:
        return content
    try:
        prompt = f"""请把下面这段小红书文案做"真人化重写"，并保持原意：

要求：
1) 去AI腔，像真实用户随手发的分享
2) 保留原有结构（标题+钩子+内文）
3) 增加生活细节和情绪波动，但不要夸张
4) 内文保持200-300字
5) 结尾自然提问，不要出现"评论区"
6) 合规：不要绝对化词，不引导购买

原文：
{content}

只输出重写后的内容。"""
        headers = {'Authorization': f'Bearer {DEEPSEEK_API_KEY}', 'Content-Type': 'application/json'}
        payload = {
            'model': 'deepseek-chat',
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 1.15,
            'top_p': 0.9
        }
        resp = requests.post(DEEPSEEK_API_URL, json=payload, headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"auto_humanize error: {e}")
    return content

# 小红书API配置
XHS_PROXY = os.environ.get('XHS_PROXY', None)  # 如需代理设置
XHS_WEB_SESSION = os.environ.get('XHS_WEB_SESSION', None)  # 如需登录态

def fetch_xhs_trending(keywords):
    """从获取小红书热门笔记"""
    try:
        import asyncio
        import sys
        sys.path.insert(0, '/home/node/.openclaw/workspace/xiaohongshu/scripts')

        from request.web.xhs_session import create_xhs_session

        async def search():
            xhs = await create_xhs_session(proxy=XHS_PROXY, web_session=XHS_WEB_SESSION)
            # 提取第一个关键词搜索
            kw = keywords.split('#')[0].split(' ')[0].strip() if keywords else '体检'
            res = await xhs.apis.note.search_notes(kw)
            data = await res.json()
            await xhs.close_session()
            return data

        # 同步调用
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(search())
            if result.get('code') == -104:
                # 未登录无权限，返回空
                return []
            notes = result.get('data', {}).get('items', [])[:3]
            return notes
        finally:
            loop.close()
    except Exception as e:
        print(f"XHS API error: {e}")
        return []

@app.route('/api/generate_copy', methods=['POST'])
def generate_copy():
    data = request.json
    registration_id = data.get('registration_id')
    user_prompt = data.get('user_prompt', '').strip()  # 用户自定义提示词
    fast_mode = bool(data.get('fast_mode', True))

    reg = Registration.query.get(registration_id)
    if not reg:
        return jsonify({'success': False, 'message': '报名信息不存在'})

    topic = reg.topic

    # 获取话题信息
    keywords = topic.keywords or ""
    direction = topic.direction or ""
    direction_clean = direction.strip()
    if (not direction_clean) or direction_clean in ['同上', '同上。', '同上 ', '同上（同前）']:
        direction_clean = ''

    # 获取小红书热门参考（按话题，不按关键词）
    xhs_notes = [] # disabled for stability
    xhs_ref = ""
    if xhs_notes:
        for i, note in enumerate(xhs_notes):
            title = note.get('note_card', {}).get('title', '')[:50]
            user = note.get('note_card', {}).get('user', {}).get('nickname', '')
            if title:
                xhs_ref += f"\n参考{i+1}: {title} (作者:{user})"

    # 话题意图识别（按话题决定软植入主线）
    topic_text = (topic.topic_name or '').strip()
    if any(k in topic_text for k in ['肝弹', 'FibroScan', '福波看', '做检查', '检查']):
        product_hint = '主线：FibroScan福波看（检查评估）；可辅带1次复方鳖甲软肝片'
        topic_goal = '围绕检查评估与复查管理，软植入FibroScan福波看'
    elif any(k in topic_text for k in ['肝硬化吃什么药', '肝纤维化吃什么药', '吃什么药', '乙肝肝纤维化', '乙肝肝硬化']):
        product_hint = '主线：恩替卡韦（抗病毒）+复方鳖甲软肝片（抗纤维化）联合管理；可辅带1次FibroScan复查'
        topic_goal = '围绕"抗病毒+抗纤维化联合管理"主线作答，禁止泛泛保肝药表达'
    elif any(k in topic_text for k in ['解酒', '护肝']) and not any(k in topic_text for k in ['纤维化', '肝硬化']):
        product_hint = '主线：复方鳖甲软肝片（软肝片）解酒护肝场景；可用卖点：12片小包装（带着方便）、单盒不到50、喝前4粒/酒局后4粒/次晨4粒（共12粒）'
        topic_goal = '严格围绕"解酒护肝"话题，主推复方鳖甲软肝片，不跑题不换品'
    else:
        product_hint = '按话题自动匹配，不强行套用固定病种话术'
        topic_goal = '先对齐话题，再做自然软植入'

    import random, time
    generation_id = f"G{int(time.time()*1000)}-{random.randint(1000,9999)}"

    # 读取最近文案片段，避免重复
    recent_snippets = []
    try:
        s = Settings.query.filter_by(key='recent_copy_snippets').first()
        if s and s.value:
            recent_snippets = json.loads(s.value)
            if not isinstance(recent_snippets, list):
                recent_snippets = []
    except Exception:
        recent_snippets = []

    identities = [
        '患者本人', '子女视角', '家属视角', '朋友视角', '医疗从业者', '学习笔记型', '病友群见闻',
        '逆转型患者', '稳定型患者', '初诊患者', '职场应酬族', '曾经酗酒现在养生'
    ]
    hooks = ['后悔没早点知道', '我以为没事结果被医生提醒', '踩坑后才懂', '真的被吓到了', '这次复查让我松口气']
    endings = ['你们遇到过这种情况吗？', '我这样做对吗？', '有同样经历的可以说说吗？', '你们一般怎么处理？', '我还漏了什么要注意的？']

    output_count = 3
    selected_identities = random.sample(identities, 3)
    selected_hook = random.choice(hooks)
    selected_ending = random.choice(endings)
    # 固定"拉互动+冲爆款"双目标输出
    selected_types = ['故事痛点型', '轻科普问答型', '情绪求助型']

    role_type_block = "\n".join([f"- 版本{i+1}：{selected_identities[i % len(selected_identities)]} / {selected_types[i]}" for i in range(output_count)])
    output_format_block = "\n\n".join([
        f"===版本{i+1}===\n角色：...\n类型：{selected_types[i]}\n标题：...\n爆款逻辑：...\n钩子：...\n内文：...\n互动结尾：..." for i in range(output_count)
    ])

    # 读取本地爆款语料库（节选）用于生成参考
    knowledge_hint = ''
    try:
        with open('/home/node/.openclaw/workspace/knowledge/xhs_viral_templates.md', 'r', encoding='utf-8') as f:
            knowledge_hint = f.read()[-2500:] if fast_mode else f.read()[-5000:]
    except Exception:
        knowledge_hint = ''

    priority_rules = "优先级：1) 话题 2) 用户提示词（逐条落实） 3) 爆款文案植入产品词 4) 产品语料库。若冲突，严格按优先级执行。"

    prompt = f"""你是小红书真实用户，分享亲身经历和真实感受。

【话题】
{topic.topic_name}

【用户提示词】（尽量体现，至少70%）
{user_prompt if user_prompt else '无，按话题自动生成'}

【关键词】（参考补充）
{keywords}

【产品提示】
{product_hint}

【参考笔记】（可学习结构和语气，不得照抄）
{knowledge_hint}

【生成要求 - 共7条】
1. 严格依据话题+用户提示词生成，不跑题
2. 用户写了提示词时，至少体现70%的关键要求
3. 内容真实、口语化、像人话，禁止"首先/其次/综上/总之/建议大家"等模板腔
4. 合规：不说绝对化词（最好/第一/最有效/根治/100%等），不引导购买，不提"评论区"，处方药需符合广告法
5. 标题：小红书爆款风格（8-14字）；开篇有钩子；正文有真实细节（时间/人物/情绪/经历）和科普内容；结尾有互动提问
6. 每篇内容不重复，句式、结构、案例要有差异，实现千人千面
7. 字数：正文不超过350字（标题单独计算）

【输出格式 - 一次生成3篇，用===分隔】
===版本1===
标题：
钩子：
正文：
结尾互动：
===版本2===
标题：
钩子：
正文：
结尾互动：
===版本3===
标题：
钩子：
正文：
结尾互动：
"""

    # 兜底兼容变量名
    product = product_hint

    # 调用DeepSeek API
    titles = []
    versions = []
    try:
        if DEEPSEEK_API_KEY:
            headers = {'Authorization': f'Bearer {DEEPSEEK_API_KEY}', 'Content-Type': 'application/json'}
            payload = {
                'model': 'deepseek-chat',
                'messages': [
                    {'role': 'system', 'content': '先保证贴题和真实口语化，再考虑花哨表达。严禁跑题。'},
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 1.15,
                'top_p': 0.9,
                'presence_penalty': 0.8,
                'frequency_penalty': 0.3
            }
            resp = requests.post(DEEPSEEK_API_URL, json=payload, headers=headers, timeout=30)
            if resp.status_code == 200:
                result = resp.json()
                content = result['choices'][0]['message']['content']

                # 解析标题和3个版本（鲁棒解析，避免模板字段泄漏）
                titles = []
                versions = []

                import re
                parts = re.split(r'===版本\s*\d+\s*===', content)
                for p in parts:
                    version_text = (p or '').strip()
                    if not version_text:
                        continue

                    title_part, body_part = _parse_model_output(version_text)
                    if not body_part:
                        continue

                    cleaned = _clean_generated_version(title_part, body_part)
                    versions.append(cleaned)
                    titles.append(_extract_title_from_version(cleaned))

                # 确保有足够版本
                if len(versions) < output_count:
                    for i in range(output_count - len(versions)):
                        versions.append(f"版本{i+1}内容待生成")
                versions = versions[:output_count]
                titles = titles[:output_count]
        else:
            raise Exception('No API key')
    except Exception as e:
        print(f"DeepSeek API error: {e}")
        # 如果API调用失败，使用本地生成
        result = generate_local_copy(topic, keywords, product)
        titles = result['titles']
        versions = result['versions']

    if not versions:
        result = generate_local_copy(topic, keywords, product)
        titles = result['titles']
        versions = result['versions']

    # 自动去AI化（默认关闭，避免二次改写把"人话感"磨平）
    ENABLE_AUTO_HUMANIZE = False
    if ENABLE_AUTO_HUMANIZE:
        try:
            versions = [auto_humanize_text(v) for v in versions]
        except Exception as e:
            print(f"auto humanize batch error: {e}")

    # 话题主线兜底校验（避免跑题）
    try:
        t = (topic.topic_name or '')
        if any(k in t for k in ['肝硬化吃什么药', '肝纤维化吃什么药', '乙肝肝硬化怎么治疗', '乙肝肝纤维化', '怎么调理']):
            fixed = []
            for v in versions:
                if ('复方鳖甲软肝片' not in v) and ('软肝片' not in v):
                    v += '\n\n补充：我这边在医生指导下是按复方鳖甲软肝片（软肝片）做抗纤维化管理的。'
                if ('恩替卡韦' not in v):
                    v += ' 同时配合恩替卡韦做抗病毒联合管理。'
                if ('抗纤维化' not in v):
                    v += ' 核心是抗病毒+抗纤维化一起做，配合复查争取改善甚至逆转趋势。'
                fixed.append(v)
            versions = fixed
        if any(k in t for k in ['体检', '检查', '肝弹', 'FibroScan', '福波看']):
            versions = [v if ('FibroScan' in v or '福波看' in v) else v + '\n\n补充：复查我会做FibroScan福波看，方便看趋势变化。' for v in versions]

        if any(k in t for k in ['解酒', '护肝']) and not any(k in t for k in ['纤维化', '肝硬化']):
            banned_tokens = ['水飞蓟', '奶蓟草', '葛根', '解酒糖']
            fixed = []
            for v in versions:
                vv = v
                if ('复方鳖甲软肝片' not in vv) and ('软肝片' not in vv):
                    vv += '\n\n补充：我自己在解酒护肝上用的是复方鳖甲软肝片（软肝片）。'
                if ('12片' not in vv) and ('喝前4粒' not in vv):
                    vv += ' 现在有12片小包装，一盒不到50；我一般喝前4粒、酒局后4粒，第二天早上再4粒。'
                for bt in banned_tokens:
                    vv = vv.replace(bt, '复方鳖甲软肝片')
                fixed.append(vv)
            versions = fixed
    except Exception as e:
        print(f"topic guard error: {e}")

    # 提示词强对齐兜底（用户填写提示词时强制命中）
    versions = _enforce_prompt_alignment(versions, user_prompt)

    # 去同质化兜底（避免和历史内容/同批次过于相似）
    versions = _dehomogenize_versions(versions, recent_snippets)

    # 最终校验：不再模板化强制重写，避免“驴唇不对马嘴”
    # 仅保留提示词对齐与去同质化两层兜底

    # 输出数量控制（固定3篇）
    versions = versions[:output_count]
    titles = titles[:output_count]

    # 写入最近文案片段（用于下次反重复）
    try:
        new_snips = []
        for v in versions:
            line = (v or '').replace('\n', ' ').strip()
            if line:
                new_snips.append(line[:500])
        merged = (new_snips + recent_snippets)[:3000]
        s = Settings.query.filter_by(key='recent_copy_snippets').first()
        if not s:
            s = Settings(key='recent_copy_snippets', value='[]')
            db.session.add(s)
        s.value = json.dumps(merged, ensure_ascii=False)
        db.session.commit()
    except Exception as e:
        print(f"save snippet error: {e}")

    return jsonify({
        'success': True,
        'titles': titles,
        'versions': versions,
        'reg_id': registration_id
    })

def generate_local_copy(topic, keywords, product):
    """本地生成文案（无API时使用）- 自然生活化风格，多样化"""
    import random

    # 多样化身份
    identities = [
        ("职场应酬族", "每周都有饭局，靠这个方法缓酒"),
        ("曾经酗酒现在养生", "喝伤了，现在开始养肝"),
        ("家属视角", "看老公喝酒，帮他护肝"),
        ("病友群老手", "喝酒多年，有自己的护肝心得"),
        ("初诊患者", "刚查出，正在选药"),
        ("逆转型患者", "治疗后指标明显下降")
    ]

    # 不同角度的正文（120-180字，有故事感，结尾自然互动）
    versions = []

    if '体检' in topic.topic_name or 'FibroScan' in topic.topic_name:
        versions = [
            """标题：闺蜜体检发现肝纤维化早期，我惊了！
正文：昨天陪闺蜜去体检，查出早期纤维化...好在发现得早！医生说这个FibroScan检测很准，无痛的还好。你们带爸妈去记得加上这个，真的能救命！""",

            """标题：医生一句建议，让我后怕到现在
正文：今天体检医生让我加做一个FibroScan，查完真的后怕！好在是早期...你们体检千万别忽略这个！""",

            """标题：肝指标异常的姐妹们，这篇必看！
正文：刚查出肝指标异常给我慌的...好在及时做了检查配合调理，慢慢稳定了。有问题一定要早查早干预！""",
            """标题：我来讲讲肝弹怎么读
正文：很多人拿到FibroScan报告就懵，我之前也是。后来医生教我先看CAP再看E值，前后对比才有意义。你们复查时会记录每次数值吗？""",
        ]
    else:
        # 软肝片类 - 用模糊指代，合规，250-300字
        id1, id2 = random.sample(identities, 2)

        versions = [
            f"""标题：{id1[0]}的真实分享！这个真的帮我改善了
正文：姐妹们真不是智商税！之前熬夜太厉害，肝指标一直不好，吓得我...后来开始配合调理一段时间，再去检查居然好多了！真的惊喜到了！

跟你们说说我怎么做的：先是调整作息，然后配合医生开的药，再就是注意饮食...坚持了几个月真的有变化！

你们要是也有类似情况，可以试试，但一定要配合检查啊！""",

            f"""标题：{id2[0]}：医生推荐的方法
正文：绝了！闺蜜推荐的，说她爸用了之后复查结果好很多...当时我还不信，结果昨天去查真香了！医生都问我吃了啥哈哈

我是属于那种经常应酬的，之前肝指标一直临界值，焦虑死了...后来开始调理+配合用药，现在终于降下来了！

你们懂的，理性种草！具体情况还是要问医生！""",

            """标题：肝指标异常的，这个方法真的救了我
正文：家人们谁懂啊！之前肝指标临界值焦虑死...开始调理一段时间今天去查居然降了！医生都问我吃了啥哈哈

说一下我的情况：经常熬夜喝酒是有的...后来被医生说了才开始重视，一边配合用药一边调整作息

不保证每个人都有用，但可以试试！具体情况问医生最靠谱！""",
            """标题：肝硬化吃药我踩过的坑
正文：以前我只会到处搜"吃什么药"，结果越看越乱。后来按医生方案走，主线是复方鳖甲软肝片联合管理，再配合定期FibroScan复查，心里才踏实。你们是怎么坚持复查节奏的？"""
        ]

    titles = [v.split('\n正文：')[0].replace('标题：', '').strip() for v in versions]

    return {'titles': titles, 'versions': versions}

# 合规检查API
@app.route('/api/humanize_copy', methods=['POST'])
def humanize_copy():
    data = request.json
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'success': False, 'message': '内容为空'})

    prompt = f"""请把下面这段小红书文案做"真人化重写"：

要求：
1) 保留原意，不改核心信息
2) 去AI腔，像真实用户随手发的分享
3) 增加生活细节和情绪波动，但不要夸张
4) 保持200-300字
5) 结尾自然提问，不要出现"评论区"
6) 合规：不要绝对化词，不引导购买

原文：
{content}

只输出重写后的正文。"""

    try:
        if DEEPSEEK_API_KEY:
            headers = {'Authorization': f'Bearer {DEEPSEEK_API_KEY}', 'Content-Type': 'application/json'}
            payload = {
                'model': 'deepseek-chat',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 1.15,
                'top_p': 0.9
            }
            resp = requests.post(DEEPSEEK_API_URL, json=payload, headers=headers, timeout=30)
            if resp.status_code == 200:
                result = resp.json()
                rewritten = result['choices'][0]['message']['content'].strip()
                return jsonify({'success': True, 'content': rewritten})
        return jsonify({'success': False, 'message': '重写失败，请重试'})
    except Exception as e:
        print(f"Humanize error: {e}")
        return jsonify({'success': False, 'message': '重写失败，请重试'})

@app.route('/api/check_compliance', methods=['POST'])
def check_compliance():
    data = request.json
    content = data.get('content', '')

    # 合规关键词检查
    forbidden_words = ['最好', '第一', '最有效', '根治', '治愈', '特效', '保证', '绝对', '100%', '最靠谱', '就吃这个', '别的药都没用', '药盒', '私信我', '天猫', '京东', '胃疼', '堵得慌', '副作用', '吃完难受']
    warnings = []

    for word in forbidden_words:
        if word in content:
            warnings.append(f'包含违规词：{word}')

    return jsonify({
        'success': True,
        'passed': len(warnings) == 0,
        'warnings': warnings
    })


@app.route('/api/generate_creative_pack', methods=['POST'])
def generate_creative_pack():
    data = request.json or {}
    registration_id = data.get('registration_id')
    selected_content = (data.get('selected_content') or '').strip()

    reg = Registration.query.get(registration_id)
    if not reg:
        return jsonify({'success': False, 'message': '报名信息不存在'})

    creative_pack = _build_creative_pack(reg.topic, selected_content)
    return jsonify({
        'success': True,
        'topic': reg.topic.topic_name,
        'assets': creative_pack
    })


@app.route('/api/generate_graphic_article_bundle', methods=['POST'])
def generate_graphic_article_bundle():
    data = request.json or {}
    registration_id = data.get('registration_id')
    selected_content = (data.get('selected_content') or '').strip()

    reg = Registration.query.get(registration_id)
    if not reg:
        return jsonify({'success': False, 'message': '报名信息不存在'})

    bundles = _build_graphic_article_bundle(reg.topic, selected_content)
    return jsonify({
        'success': True,
        'topic': reg.topic.topic_name,
        'items': bundles,
    })

def _to_non_negative_int(value, field_name):
    try:
        v = int(value)
    except (TypeError, ValueError):
        raise ValueError(f'{field_name}必须为非负整数')
    if v < 0:
        raise ValueError(f'{field_name}必须为非负整数')
    return v


def _validate_required_platform_data(data):
    # 兼容历史命名：保留函数名，但逻辑改为"可按平台分步提交"
    return _validate_partial_platform_data(data, require_at_least_one_link=True)


def _validate_partial_platform_data(data, require_at_least_one_link=False):
    platform_defs = [
        ('xhs', '小红书'),
        ('douyin', '抖音'),
        ('video', '视频号'),
        ('weibo', '微博'),
    ]

    normalized = {}
    link_count = 0
    for key, label in platform_defs:
        raw_link = data.get(f'{key}_link')
        link = (raw_link or '').strip() if isinstance(raw_link, str) else ''
        has_link = bool(link)
        if has_link:
            if not (link.startswith('http://') or link.startswith('https://')):
                raise ValueError(f'{label}链接格式不正确')
            normalized[f'{key}_link'] = link
            link_count += 1

        # 允许分平台提交：只要该平台给了链接或任何一个指标，就更新该平台指标
        metric_keys = [f'{key}_views', f'{key}_likes', f'{key}_favorites', f'{key}_comments']
        has_any_metric = any((mk in data and str(data.get(mk)).strip() != '') for mk in metric_keys)
        if has_link or has_any_metric:
            normalized[f'{key}_views'] = _to_non_negative_int(data.get(f'{key}_views', 0), f'{label}传播量')
            normalized[f'{key}_likes'] = _to_non_negative_int(data.get(f'{key}_likes', 0), f'{label}点赞量')
            normalized[f'{key}_favorites'] = _to_non_negative_int(data.get(f'{key}_favorites', 0), f'{label}收藏量')
            normalized[f'{key}_comments'] = _to_non_negative_int(data.get(f'{key}_comments', 0), f'{label}评论量')

    if require_at_least_one_link and link_count == 0:
        raise ValueError('至少提交一个平台链接和数据')

    return normalized


def _auto_detect_content_type(note_text: str, topic_text: str = '') -> str:
    text = f"{note_text or ''} {topic_text or ''}".strip()
    if not text:
        return '未识别'

    if any(k in text for k in ['FibroScan', '福波看', '肝弹', 'CAP', 'LSM', 'SSM', '检查结果', '指标']):
        return '检查解读型'
    if any(k in text for k in ['清单', '总结', '避坑', '步骤', '建议', '第1', '第2', '注意事项']):
        return '经验清单型'
    if any(k in text for k in ['我妈', '我爸', '我老公', '我老婆', '我自己', '那天', '后来', '当时']):
        return '真实经历型'
    if any(k in text for k in ['求助', '怎么办', '有人知道', '我该怎么', '能不能']):
        return '求助型'
    if any(k in text for k in ['复盘', '踩坑', '避雷', '失败', '教训']):
        return '复盘避坑型'
    if any(k in text for k in ['为什么', '是什么', '科普', '原理', '问答']):
        return '轻科普问答型'
    return '其他型'


def _extract_prompt_terms(user_prompt: str):
    import re
    text = (user_prompt or '').strip()
    if not text:
        return []

    # 优先抽取中文短语，过滤无意义碎片词
    parts = re.split(r'[，,。；;、\n\t ]+', text)
    stop = {'然后', '这个', '那个', '我们', '你们', '他们', '以及', '还有', '进行', '相关', '内容', '文案'}
    terms = []
    for p in parts:
        p = p.strip('"“”()（）[]【】:：')
        if not p:
            continue
        if p.lower() in {'journal', 'of', 'hepatology'}:
            continue
        if p in stop:
            continue
        # 保留较像“约束词”的短语
        if 2 <= len(p) <= 16:
            terms.append(p)

    # 关键实体优先前置
    priority = []
    for k in ['医学助理', '复方鳖甲软肝片', '软肝片', '恩替卡韦', '肝纤维化', '肝硬化']:
        if k in text and k not in priority:
            priority.append(k)

    merged = priority + [t for t in terms if t not in priority]
    uniq = []
    for t in merged:
        if t not in uniq:
            uniq.append(t)
    return uniq[:8]


def _parse_model_output(version_text: str):
    import re
    text = (version_text or '').strip()
    if not text:
        return '', ''

    # 去除内部模板标签行
    text = re.sub(r'(?m)^\s*(角色|类型|爆款逻辑|钩子|互动结尾)\s*[：:].*$', '', text)
    text = re.sub(r'===+', '', text)

    title = ''
    body = ''
    m = re.search(r'标题\s*[：:]\s*(.+)', text)
    if m:
        title = m.group(1).strip()

    if '内文：' in text:
        body = text.split('内文：', 1)[1].strip()
    elif '正文：' in text:
        body = text.split('正文：', 1)[1].strip()
    elif '【正文】' in text:
        body = text.split('【正文】', 1)[1].strip()
    else:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if lines:
            if not title:
                title = lines[0][:18]
            body = '\n'.join(lines[1:]) if len(lines) > 1 else lines[0]

    title = re.sub(r'^(标题\s*[：:]\s*)+', '', title).strip('：: =-')
    body = body.strip()
    return title, body


def _extract_title_from_version(v: str):
    import re
    vv = (v or '').strip()
    m = re.search(r'标题\s*[：:]\s*(.+)', vv)
    if m:
        t = m.group(1).splitlines()[0].strip()
        t = re.sub(r'^=+|=+$', '', t).strip()
        return t or '分享笔记'
    line = vv.splitlines()[0].strip() if vv else '分享笔记'
    return line[:18] if line else '分享笔记'


def _extract_body_from_version(v: str):
    vv = (v or '').strip()
    if '内文：' in vv:
        return vv.split('内文：', 1)[1].strip()
    if '正文：' in vv:
        return vv.split('正文：', 1)[1].strip()
    return vv


def _clean_generated_version(title: str, body: str):
    import re
    t = (title or '').strip()
    b = (body or '').strip()

    # 清理模板字段/占位符泄漏
    b = re.sub(r'(?m)^\s*(角色|类型|爆款逻辑|钩子|互动结尾)\s*[：:].*$', '', b)
    b = re.sub(r'===+', '', b)
    b = re.sub(r'\n{3,}', '\n\n', b).strip()

    t = re.sub(r'^(标题\s*[：:]\s*)+', '', t)
    t = re.sub(r'[=\-]{2,}', '', t).strip(' ：:')
    if (not t) or t in {'...', '版本', '分享笔记'}:
        first = b.split('\n')[0].strip() if b else '分享笔记'
        t = first[:16] if first else '分享笔记'

    if '药盒' in b:
        b = b.replace('药盒', '用药记录')

    return f"标题：{t}\n内文：{b}"


def _enforce_prompt_alignment(versions, user_prompt):
    # 用户填写提示词时：做“语义约束”而不是生硬拼接，确保贴题且读起来通顺
    terms = _extract_prompt_terms(user_prompt)
    if not terms:
        return versions

    import re
    up = (user_prompt or '').strip()
    fixed = []

    for i, v in enumerate(versions or []):
        vv = v or ''
        title = _extract_title_from_version(vv)
        body = _extract_body_from_version(vv)

        must_lines = []

        # 角色约束
        if '医学助理' in up and '医学助理' not in body:
            must_lines.append('作为医学助理，我先按门诊沟通思路把重点讲清楚。')

        # 药物约束
        if ('软肝片' in up or '复方鳖甲软肝片' in up) and ('软肝片' not in body and '复方鳖甲软肝片' not in body):
            must_lines.append('在抗纤维化管理里，复方鳖甲软肝片（软肝片）是常被讨论的方案之一。')

        if '恩替卡韦' in up and '恩替卡韦' not in body:
            must_lines.append('如果是乙肝相关人群，医生常会考虑恩替卡韦与抗纤维化管理联合评估。')

        # 证据/发表约束
        if re.search(r'Journal\s*of\s*hepatology|J\s*Hepatology|顶刊|发表', up, re.I):
            if ('Journal of Hepatology' not in body and '发表' not in body and '研究' not in body):
                must_lines.append('相关方向已有公开研究讨论，临床上更强调个体化评估后再定方案。')

        # 至少命中一个提示词核心词
        if not any(t in body for t in terms):
            core = terms[i % len(terms)]
            must_lines.insert(0, f'先围绕“{core}”这个核心点来讲，避免跑题。')

        if must_lines:
            body = '\n'.join(must_lines) + '\n' + body

        # 轻度通顺化：去重复句、去生硬补丁词
        body = body.replace('提示词对齐补充：', '')
        body = body.replace('这篇按“', '围绕“').replace('”这个重点来写。', '”展开。')

        vv = _clean_generated_version(title, body)
        fixed.append(vv)

    return fixed


def _text_similarity(a: str, b: str) -> float:
    import difflib
    a = (a or '').replace('\n', ' ').strip()
    b = (b or '').replace('\n', ' ').strip()
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def _dehomogenize_versions(versions, recent_snippets):
    """去同质化兜底：若与最近片段或批次内高度相似，强制改写开头/结尾句式"""
    if not versions:
        return versions

    openers = ['先说结论：', '说实话，', '我以前也不信，', '这事我踩过坑，', '今天只讲干货：']
    endings = [
        '你们会怎么做？',
        '有没有人和我一样？',
        '你们更认可哪种做法？',
        '这一步你们会坚持吗？',
        '我这个做法你们觉得可行吗？'
    ]

    fixed = []
    for i, v in enumerate(versions):
        vv = v or ''
        too_close_recent = any(_text_similarity(vv, r) > 0.62 for r in (recent_snippets or [])[:1000])
        too_close_batch = any(_text_similarity(vv, p) > 0.78 for p in fixed)
        exact_seen = vv in (recent_snippets or [])
        if too_close_recent or too_close_batch or exact_seen:
            parts = vv.split('内文：', 1)
            if len(parts) == 2:
                head, body = parts[0], parts[1].strip()
                body_lines = [x for x in body.split('\n') if x.strip()]
                if body_lines:
                    body_lines[0] = f"{openers[i % len(openers)]}{body_lines[0].lstrip('，,。 ')}"
                    if len(body_lines) >= 2:
                        body_lines[-1] = endings[i % len(endings)]
                    else:
                        body_lines.append(endings[i % len(endings)])
                vv = head + '内文：' + '\n'.join(body_lines)
            else:
                vv = f"{openers[i % len(openers)]}{vv}\n\n{endings[i % len(endings)]}"
        fixed.append(vv)
    return fixed


def _hard_rewrite_by_prompt(topic_name: str, user_prompt: str, idx: int = 0) -> str:
    terms = _extract_prompt_terms(user_prompt)
    t1 = terms[idx % len(terms)] if terms else '核心要点'
    t2 = terms[(idx + 1) % len(terms)] if len(terms) > 1 else t1
    openers = ['标题：先把重点说清楚', '标题：这次我按提示词来写', '标题：只围绕这个点展开']
    logic = ['问题导向', '反常识切入', '实操清单']
    endings = ['你们会怎么做？', '你们更认同哪种做法？', '这个点你们会坚持吗？']
    title = openers[idx % len(openers)]
    body = (
        f"内文：围绕话题“{topic_name}”，这篇只讲{t1}和{t2}。"
        f"我不展开无关内容，直接给可执行动作：先做{t1}，再落实{t2}。"
        "场景放在日常真实沟通里，避免模板话术。"
        f"最后复盘一次执行结果，再决定下一步。{endings[idx % len(endings)]}"
    )
    return f"{title}\n爆款逻辑：{logic[idx % len(logic)]}\n{body}\n提示词对齐：{t1}"


def _final_guard_rewrite(versions, recent_snippets, user_prompt, topic_name):
    terms = _extract_prompt_terms(user_prompt)
    fixed = []
    for i, v in enumerate(versions or []):
        vv = v or ''
        similar = any(_text_similarity(vv, r) > 0.60 for r in (recent_snippets or [])[:1200])
        hit = True if not terms else any(t in vv for t in terms)
        if similar or not hit:
            vv = _hard_rewrite_by_prompt(topic_name, user_prompt, i)
        fixed.append(vv)
    return fixed


def _validate_platform_metrics_only(data):
    platform_defs = [
        ('xhs', '小红书'),
        ('douyin', '抖音'),
        ('video', '视频号'),
        ('weibo', '微博'),
    ]

    normalized = {}
    for key, label in platform_defs:
        normalized[f'{key}_views'] = _to_non_negative_int(data.get(f'{key}_views', 0), f'{label}传播量')
        normalized[f'{key}_likes'] = _to_non_negative_int(data.get(f'{key}_likes', 0), f'{label}点赞量')
        normalized[f'{key}_favorites'] = _to_non_negative_int(data.get(f'{key}_favorites', 0), f'{label}收藏量')
        normalized[f'{key}_comments'] = _to_non_negative_int(data.get(f'{key}_comments', 0), f'{label}评论量')

    return normalized


@app.route('/api/submit', methods=['POST'])
def submit_data():
    data = request.json or {}
    reg = Registration.query.get(data.get('registration_id'))

    if not reg:
        return jsonify({'success': False, 'message': '报名信息不存在'})

    try:
        normalized = _validate_required_platform_data(data)
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)})

    note_title = (data.get('note_title') or '').strip()
    note_content = (data.get('note_content') or '').strip()
    auto_type = _auto_detect_content_type(f"{note_title} {note_content}", reg.topic.topic_name if reg and reg.topic else '')
    if note_title:
        normalized['note_title'] = note_title
    if note_content:
        normalized['note_content'] = note_content
    normalized['content_type'] = auto_type

    # 检查关键词（以小红书链接为主；分平台提交时允许为空）
    topic = reg.topic
    keywords = topic.keywords.split(',') if topic.keywords else []

    existing_submission = Submission.query.filter_by(registration_id=reg.id).first()
    xhs_for_check = normalized.get('xhs_link')
    if not xhs_for_check and existing_submission:
        xhs_for_check = existing_submission.xhs_link or ''
    keyword_check = any(k.strip() in (xhs_for_check or '') for k in keywords if k.strip())

    if existing_submission:
        for k, v in normalized.items():
            setattr(existing_submission, k, v)
        existing_submission.keyword_check = keyword_check
        existing_submission.created_at = datetime.now()
    else:
        submission = Submission(
            registration_id=reg.id,
            keyword_check=keyword_check,
            **normalized
        )
        db.session.add(submission)

    reg.status = 'submitted'
    db.session.commit()

    return jsonify({'success': True, 'message': '提交成功'})

# 数据更新API - 仅更新多平台互动数据（不要求重新提交链接）
@app.route('/api/update_data', methods=['POST'])
def update_data():
    data = request.json or {}
    reg = Registration.query.get(data.get('registration_id'))

    if not reg:
        return jsonify({'success': False, 'message': '报名信息不存在'})

    submission = Submission.query.filter_by(registration_id=reg.id).first()

    if not submission:
        submission = Submission(registration_id=reg.id)
        db.session.add(submission)

    try:
        partial = _validate_partial_platform_data(data, require_at_least_one_link=False)
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)})

    for k, v in partial.items():
        setattr(submission, k, v)

    # 可选：根据补充的标题/正文重新识别类型
    note_title = (data.get('note_title') or '').strip()
    note_content = (data.get('note_content') or '').strip()
    if note_title:
        submission.note_title = note_title
    if note_content:
        submission.note_content = note_content
    if note_title or note_content or (submission.note_title or submission.note_content):
        submission.content_type = _auto_detect_content_type(f"{submission.note_title or ''} {submission.note_content or ''}", reg.topic.topic_name if reg and reg.topic else '')

    db.session.commit()
    return jsonify({'success': True, 'message': '数据更新成功'})

@app.route('/data_analysis')
def data_analysis():
    activities = Activity.query.order_by(Activity.created_at.desc()).all()
    return render_template('data_analysis.html', activities=activities)


@app.route('/automation_center')
def automation_center():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    activities = Activity.query.order_by(Activity.created_at.desc()).all()
    return render_template('automation_center.html', activities=activities, default_topic_quota=_default_topic_quota())


@app.route('/api/automation/overview')
def automation_overview():
    guard = _admin_json_guard()
    if guard:
        return guard

    return jsonify({
        'success': True,
        'counts': {
            'corpus_entries': CorpusEntry.query.count(),
            'trend_notes': TrendNote.query.count(),
            'topic_ideas': TopicIdea.query.count(),
            'published_ideas': TopicIdea.query.filter_by(status='published').count(),
            'data_source_tasks': DataSourceTask.query.count(),
            'running_data_source_tasks': DataSourceTask.query.filter(DataSourceTask.status.in_(['queued', 'running'])).count(),
            'asset_generation_tasks': AssetGenerationTask.query.count(),
        },
        'default_keywords': _automation_keyword_seeds(),
        'capabilities': {
            'image_provider_configured': bool((os.environ.get('ASSET_IMAGE_API_URL') or '').strip() and (os.environ.get('ASSET_IMAGE_API_KEY') or '').strip()),
            'image_provider_name': (os.environ.get('ASSET_IMAGE_PROVIDER') or 'svg_fallback').strip() or 'svg_fallback',
        },
        'latest_batches': [
            row.import_batch for row in TrendNote.query
            .filter(TrendNote.import_batch.isnot(None))
            .order_by(TrendNote.created_at.desc())
            .limit(10)
            .all()
        ]
    })


@app.route('/api/admin/data-source-tasks')
def list_data_source_tasks():
    guard = _admin_json_guard()
    if guard:
        return guard

    task_type = (request.args.get('task_type') or '').strip()
    status = (request.args.get('status') or '').strip()
    limit = min(max(_safe_int(request.args.get('limit'), 20), 1), 100)

    query = DataSourceTask.query
    if task_type:
        query = query.filter_by(task_type=task_type)
    if status:
        query = query.filter_by(status=status)

    items = query.order_by(DataSourceTask.created_at.desc(), DataSourceTask.id.desc()).limit(limit).all()
    return jsonify({
        'success': True,
        'items': [_serialize_data_source_task(item) for item in items]
    })


@app.route('/api/admin/assets/tasks')
def list_asset_generation_tasks():
    guard = _admin_json_guard()
    if guard:
        return guard

    status = (request.args.get('status') or '').strip()
    limit = min(max(_safe_int(request.args.get('limit'), 20), 1), 100)
    query = AssetGenerationTask.query
    if status:
        query = query.filter_by(status=status)

    items = query.order_by(AssetGenerationTask.created_at.desc(), AssetGenerationTask.id.desc()).limit(limit).all()
    return jsonify({
        'success': True,
        'items': [_serialize_asset_generation_task(item) for item in items]
    })


@app.route('/api/asset_tasks/<int:task_id>')
def asset_generation_task_detail(task_id):
    task = AssetGenerationTask.query.get_or_404(task_id)
    registration_id = _safe_int(request.args.get('registration_id'), 0)
    if task.registration_id:
        if not registration_id or task.registration_id != registration_id:
            return jsonify({'success': False, 'message': '任务归属不匹配'}), 403
    return jsonify({
        'success': True,
        'item': _serialize_asset_generation_task(task)
    })


@app.route('/api/corpus', methods=['GET', 'POST'])
def corpus_entries():
    guard = _admin_json_guard()
    if guard:
        return guard

    if request.method == 'POST':
        data = request.json or {}
        title = (data.get('title') or '').strip()
        content = (data.get('content') or '').strip()
        if not title or not content:
            return jsonify({'success': False, 'message': '标题和内容不能为空'})

        entry = CorpusEntry(
            title=title,
            category=(data.get('category') or '爆款拆解').strip(),
            source=(data.get('source') or '手动录入').strip(),
            tags=(data.get('tags') or '').strip(),
            content=content,
            status='active'
        )
        db.session.add(entry)
        db.session.flush()
        _log_operation('create', 'corpus_entry', message='新增语料', detail={
            'entry_id': entry.id,
            'title': entry.title,
            'category': entry.category,
            'source': entry.source,
        })
        db.session.commit()
        return jsonify({'success': True, 'message': '语料已入库'})

    pool_status = (request.args.get('pool_status') or '').strip()
    query = CorpusEntry.query
    if pool_status:
        query = query.filter_by(pool_status=pool_status)
    entries = query.order_by(CorpusEntry.updated_at.desc()).limit(80).all()
    return jsonify({
        'success': True,
        'items': [_serialize_corpus_entry(entry) for entry in entries]
    })


@app.route('/api/corpus/<int:entry_id>/pool_status', methods=['POST'])
def update_corpus_pool_status(entry_id):
    guard = _admin_json_guard()
    if guard:
        return guard

    data = request.json or {}
    pool_status = (data.get('pool_status') or '').strip()
    if pool_status not in {'reserve', 'candidate', 'archived'}:
        return jsonify({'success': False, 'message': '不支持的语料池状态'})

    entry = CorpusEntry.query.get_or_404(entry_id)
    entry.pool_status = pool_status
    _log_operation('move_pool', 'corpus_entry', target_id=entry.id, message='更新语料池状态', detail={
        'title': entry.title,
        'pool_status': pool_status,
    })
    db.session.commit()
    return jsonify({
        'success': True,
        'message': f'语料已移动到{_pool_status_label(pool_status)}',
        'item': _serialize_corpus_entry(entry)
    })


@app.route('/api/corpus/promote_reserve', methods=['POST'])
def promote_corpus_reserve():
    guard = _admin_json_guard()
    if guard:
        return guard

    entries = CorpusEntry.query.filter_by(pool_status='reserve').all()
    for entry in entries:
        entry.pool_status = 'candidate'
    _log_operation('promote_reserve', 'corpus_entry', message='批量推送语料到候选池', detail={
        'count': len(entries),
    })
    db.session.commit()
    return jsonify({
        'success': True,
        'message': f'已将 {len(entries)} 条储备语料推入候选池',
        'count': len(entries),
    })


def _parse_trend_payload(raw_payload):
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


def _build_hotword_skeleton_rows(keywords, source_platform='小红书', source_channel='Worker骨架', batch_name=''):
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


@app.route('/api/trends/import', methods=['POST'])
def import_trends():
    guard = _admin_json_guard()
    if guard:
        return guard

    data = request.json or {}
    items = _parse_trend_payload(data.get('payload'))
    if not items:
        return jsonify({'success': False, 'message': '没有识别到可导入的热点数据'})

    batch_name = (data.get('batch_name') or datetime.now().strftime('batch_%Y%m%d_%H%M%S')).strip()
    source_platform = (data.get('source_platform') or '小红书').strip()
    source_channel = (data.get('source_channel') or '手动导入').strip()

    inserted = 0
    skipped = 0
    for item in items:
        title = (item.get('title') or '').strip()
        link = (item.get('link') or '').strip()
        if not title:
            skipped += 1
            continue

        duplicate = None
        if link:
            duplicate = TrendNote.query.filter_by(link=link).first()
        if not duplicate:
            duplicate = TrendNote.query.filter_by(title=title, keyword=(item.get('keyword') or '').strip()).first()
        if duplicate:
            skipped += 1
            continue

        note = TrendNote(
            source_platform=(item.get('source_platform') or source_platform).strip(),
            source_channel=(item.get('source_channel') or source_channel).strip(),
            import_batch=batch_name,
            keyword=(item.get('keyword') or '').strip(),
            topic_category=(item.get('topic_category') or '').strip(),
            title=title,
            author=(item.get('author') or '').strip(),
            link=link,
            views=_safe_int(item.get('views')),
            likes=_safe_int(item.get('likes')),
            favorites=_safe_int(item.get('favorites')),
            comments=_safe_int(item.get('comments')),
            publish_time=_parse_datetime(item.get('publish_time')),
            summary=(item.get('summary') or '').strip(),
            raw_payload=json.dumps(item, ensure_ascii=False)
        )
        db.session.add(note)
        inserted += 1

    _log_operation('import', 'trend_note', message='导入热点数据', detail={
        'source_platform': source_platform,
        'source_channel': source_channel,
        'batch_name': batch_name,
        'inserted': inserted,
        'skipped': skipped,
    })
    db.session.commit()
    return jsonify({
        'success': True,
        'message': f'导入完成：新增{inserted}条，跳过{skipped}条',
        'inserted': inserted,
        'skipped': skipped
    })


@app.route('/api/trends')
def list_trends():
    guard = _admin_json_guard()
    if guard:
        return guard

    keyword = (request.args.get('keyword') or '').strip()
    source_platform = (request.args.get('source_platform') or '').strip()
    pool_status = (request.args.get('pool_status') or '').strip()
    query = TrendNote.query
    if keyword:
        query = query.filter(or_(
            TrendNote.keyword.contains(keyword),
            TrendNote.title.contains(keyword),
            TrendNote.summary.contains(keyword),
        ))
    if source_platform:
        query = query.filter_by(source_platform=source_platform)
    if pool_status:
        query = query.filter_by(pool_status=pool_status)

    notes = query.order_by(TrendNote.created_at.desc()).limit(120).all()
    return jsonify({
        'success': True,
        'items': [_serialize_trend_note(note) for note in notes]
    })


@app.route('/api/trends/<int:note_id>/pool_status', methods=['POST'])
def update_trend_pool_status(note_id):
    guard = _admin_json_guard()
    if guard:
        return guard

    data = request.json or {}
    pool_status = (data.get('pool_status') or '').strip()
    if pool_status not in {'reserve', 'candidate', 'archived'}:
        return jsonify({'success': False, 'message': '不支持的热点池状态'})

    note = TrendNote.query.get_or_404(note_id)
    note.pool_status = pool_status
    _log_operation('move_pool', 'trend_note', target_id=note.id, message='更新热点池状态', detail={
        'title': note.title,
        'pool_status': pool_status,
    })
    db.session.commit()
    return jsonify({
        'success': True,
        'message': f'热点已移动到{_pool_status_label(pool_status)}',
        'item': _serialize_trend_note(note)
    })


@app.route('/api/trends/promote_reserve', methods=['POST'])
def promote_trends_reserve():
    guard = _admin_json_guard()
    if guard:
        return guard

    data = request.json or {}
    source_platform = (data.get('source_platform') or '').strip()
    query = TrendNote.query.filter_by(pool_status='reserve')
    if source_platform:
        query = query.filter_by(source_platform=source_platform)

    notes = query.all()
    for note in notes:
        note.pool_status = 'candidate'
    _log_operation('promote_reserve', 'trend_note', message='批量推送热点到候选池', detail={
        'source_platform': source_platform,
        'count': len(notes),
    })
    db.session.commit()
    return jsonify({
        'success': True,
        'message': f'已将 {len(notes)} 条储备热点推入候选池',
        'count': len(notes),
    })


@app.route('/api/topic_ideas', methods=['GET'])
def list_topic_ideas():
    guard = _admin_json_guard()
    if guard:
        return guard

    activity_id = request.args.get('activity_id', type=int)
    status = (request.args.get('status') or '').strip()
    query = TopicIdea.query
    if activity_id:
        query = query.filter_by(activity_id=activity_id)
    if status:
        query = query.filter_by(status=status)

    ideas = query.order_by(TopicIdea.created_at.desc()).limit(200).all()
    return jsonify({
        'success': True,
        'items': [_serialize_topic_idea(idea) for idea in ideas]
    })


@app.route('/api/topic_ideas/generate', methods=['POST'])
def generate_topic_ideas():
    guard = _admin_json_guard()
    if guard:
        return guard

    data = request.json or {}
    count = min(max(_safe_int(data.get('count'), 80), 1), 120)
    activity_id = data.get('activity_id')
    quota = _normalize_quota(data.get('quota'))

    ideas = _generate_topic_ideas(count=count, activity_id=activity_id, quota=quota)
    for idea in ideas:
        db.session.add(idea)

    if ideas:
        matching_ids = {entry.id for entry in _matching_corpus_snippets(','.join(LIVER_KEYWORD_SEEDS[:5]), limit=5)}
        matched_entries = CorpusEntry.query.filter(CorpusEntry.id.in_(matching_ids)).all() if matching_ids else []
        for entry in matched_entries:
            entry.usage_count = (entry.usage_count or 0) + 1

    db.session.commit()
    return jsonify({
        'success': True,
        'message': f'已生成{len(ideas)}个候选话题，默认名额为{quota}，并进入待审核状态',
        'count': len(ideas)
    })


@app.route('/api/topic_ideas/<int:idea_id>/review', methods=['POST'])
def review_topic_idea(idea_id):
    guard = _admin_json_guard()
    if guard:
        return guard

    data = request.json or {}
    action = (data.get('action') or '').strip()
    note = (data.get('note') or '').strip()
    idea = TopicIdea.query.get_or_404(idea_id)

    if idea.status == 'published' and action != 'archive':
        return jsonify({'success': False, 'message': '已发布的话题请先归档后再调整'})

    if action == 'approve':
        idea.status = 'approved'
        message = '候选话题已审核通过'
    elif action == 'reject':
        idea.status = 'rejected'
        message = '候选话题已驳回'
    elif action == 'reset':
        idea.status = 'pending_review'
        message = '候选话题已退回待审核'
    elif action == 'archive':
        idea.status = 'archived'
        message = '候选话题已归档'
    else:
        return jsonify({'success': False, 'message': '不支持的审核动作'})

    idea.review_note = note
    idea.reviewed_at = datetime.now()
    _log_operation('review', 'topic_idea', target_id=idea.id, message='审核候选话题', detail={
        'action': action,
        'topic_title': idea.topic_title,
        'status': idea.status,
        'note': note,
    })
    db.session.commit()
    return jsonify({
        'success': True,
        'message': message,
        'item': _serialize_topic_idea(idea)
    })


@app.route('/api/topic_ideas/review_batch', methods=['POST'])
def review_topic_ideas_batch():
    guard = _admin_json_guard()
    if guard:
        return guard

    data = request.json or {}
    action = (data.get('action') or '').strip()
    note = (data.get('note') or '').strip()
    raw_ids = data.get('idea_ids') or []
    idea_ids = []
    for item in raw_ids:
        value = _safe_int(item, 0)
        if value > 0:
            idea_ids.append(value)
    idea_ids = list(dict.fromkeys(idea_ids))
    if not idea_ids:
        return jsonify({'success': False, 'message': '请先选择要批量处理的话题'})
    if action not in {'approve', 'reject', 'reset', 'archive'}:
        return jsonify({'success': False, 'message': '不支持的批量审核动作'})

    ideas = TopicIdea.query.filter(TopicIdea.id.in_(idea_ids)).all()
    if not ideas:
        return jsonify({'success': False, 'message': '未找到可处理的话题'})

    status_map = {
        'approve': ('approved', '已审核通过'),
        'reject': ('rejected', '已驳回'),
        'reset': ('pending_review', '已退回待审核'),
        'archive': ('archived', '已归档'),
    }
    target_status, message = status_map[action]
    updated = []
    skipped = []
    for idea in ideas:
        if idea.status == 'published' and action != 'archive':
            skipped.append({'id': idea.id, 'title': idea.topic_title, 'reason': '已发布的话题仅支持归档'})
            continue
        idea.status = target_status
        idea.review_note = note
        idea.reviewed_at = datetime.now()
        updated.append({'id': idea.id, 'title': idea.topic_title, 'status': idea.status})

    _log_operation('review_batch', 'topic_idea', message='批量审核候选话题', detail={
        'action': action,
        'note': note,
        'selected_count': len(idea_ids),
        'updated_count': len(updated),
        'skipped_count': len(skipped),
        'updated': updated,
        'skipped': skipped,
    })
    db.session.commit()
    return jsonify({
        'success': True,
        'message': f'批量处理完成：{message} {len(updated)} 条，跳过 {len(skipped)} 条',
        'updated': updated,
        'skipped': skipped,
    })


@app.route('/api/topic_ideas/<int:idea_id>/publish', methods=['POST'])
def publish_topic_idea(idea_id):
    guard = _admin_json_guard()
    if guard:
        return guard

    data = request.json or {}
    idea = TopicIdea.query.get_or_404(idea_id)
    if idea.status == 'published' and idea.published_topic_id:
        return jsonify({'success': False, 'message': '该候选话题已发布过'})
    if idea.status not in {'approved', 'published'}:
        return jsonify({'success': False, 'message': '请先审核通过再发布到活动'})

    activity_id = _safe_int(data.get('activity_id') or idea.activity_id)
    if not activity_id:
        current_activity = Activity.query.filter_by(status='published').order_by(Activity.created_at.desc()).first()
        activity_id = current_activity.id if current_activity else None
    if not activity_id:
        return jsonify({'success': False, 'message': '请先选择目标活动期数'})
    quota = _normalize_quota(data.get('quota'), default=idea.quota or _default_topic_quota())

    topic = Topic(
        activity_id=activity_id,
        topic_name=idea.topic_title,
        keywords=idea.keywords,
        direction='\n'.join(filter(None, [
            idea.angle,
            f'推荐内容形式：{idea.content_type}',
            f'推荐人设：{idea.persona}',
            f'软植入建议：{idea.soft_insertion}',
            f'合规提醒：{idea.compliance_note}',
        ])),
        reference_content=idea.asset_brief,
        reference_link=idea.source_links,
        writing_example=idea.copy_prompt,
        quota=quota,
        group_num=(data.get('group_num') or '自动化选题').strip(),
        pool_status='formal',
        source_type='topic_idea',
        source_ref_id=idea.id,
        published_at=datetime.now()
    )
    db.session.add(topic)
    db.session.flush()
    idea.quota = quota
    idea.status = 'published'
    idea.published_topic_id = topic.id
    idea.published_at = datetime.now()
    _log_operation('publish', 'topic_idea', target_id=idea.id, message='候选话题发布到正式活动', detail={
        'topic_title': idea.topic_title,
        'activity_id': activity_id,
        'published_topic_id': topic.id,
        'quota': quota,
    })
    db.session.commit()
    return jsonify({'success': True, 'message': '已发布到活动题库'})


@app.route('/api/topic_ideas/publish_batch', methods=['POST'])
def publish_topic_ideas_batch():
    guard = _admin_json_guard()
    if guard:
        return guard

    data = request.json or {}
    raw_ids = data.get('idea_ids') or []
    idea_ids = []
    for item in raw_ids:
        value = _safe_int(item, 0)
        if value > 0:
            idea_ids.append(value)
    idea_ids = list(dict.fromkeys(idea_ids))
    if not idea_ids:
        return jsonify({'success': False, 'message': '请先选择要批量发布的话题'})

    activity_id = _safe_int(data.get('activity_id'))
    if not activity_id:
        return jsonify({'success': False, 'message': '请先选择目标活动期数'})

    ideas = TopicIdea.query.filter(TopicIdea.id.in_(idea_ids)).all()
    if not ideas:
        return jsonify({'success': False, 'message': '未找到可发布的话题'})

    published = []
    skipped = []
    for idea in ideas:
        if idea.status != 'approved':
            skipped.append({'id': idea.id, 'title': idea.topic_title, 'reason': '未审核通过'})
            continue
        if idea.published_topic_id:
            skipped.append({'id': idea.id, 'title': idea.topic_title, 'reason': '已发布过'})
            continue

        topic = Topic(
            activity_id=activity_id,
            topic_name=idea.topic_title,
            keywords=idea.keywords,
            direction='\n'.join(filter(None, [
                idea.angle,
                f'推荐内容形式：{idea.content_type}',
                f'推荐人设：{idea.persona}',
                f'软植入建议：{idea.soft_insertion}',
                f'合规提醒：{idea.compliance_note}',
            ])),
            reference_content=idea.asset_brief,
            reference_link=idea.source_links,
            writing_example=idea.copy_prompt,
            quota=_normalize_quota(idea.quota, default=_default_topic_quota()),
            group_num='自动化选题',
            pool_status='formal',
            source_type='topic_idea',
            source_ref_id=idea.id,
            published_at=datetime.now()
        )
        db.session.add(topic)
        db.session.flush()
        idea.status = 'published'
        idea.published_topic_id = topic.id
        idea.published_at = datetime.now()
        published.append({'id': idea.id, 'title': idea.topic_title, 'topic_id': topic.id})

    _log_operation('publish_batch', 'topic_idea', message='批量发布候选话题', detail={
        'activity_id': activity_id,
        'selected_count': len(idea_ids),
        'published_count': len(published),
        'skipped_count': len(skipped),
        'published': published,
        'skipped': skipped,
    })
    db.session.commit()
    return jsonify({
        'success': True,
        'message': f'批量发布完成：成功 {len(published)} 条，跳过 {len(skipped)} 条',
        'published': published,
        'skipped': skipped,
    })


@app.route('/api/topic_ideas/<int:idea_id>/quota', methods=['POST'])
def update_topic_idea_quota(idea_id):
    guard = _admin_json_guard()
    if guard:
        return guard

    data = request.json or {}
    idea = TopicIdea.query.get_or_404(idea_id)
    idea.quota = _normalize_quota(data.get('quota'), default=idea.quota or _default_topic_quota())
    _log_operation('update_quota', 'topic_idea', target_id=idea.id, message='调整候选话题名额', detail={
        'topic_title': idea.topic_title,
        'quota': idea.quota,
    })
    db.session.commit()
    return jsonify({
        'success': True,
        'message': f'候选话题名额已调整为 {idea.quota}',
        'item': _serialize_topic_idea(idea)
    })


@app.route('/api/creator_accounts', methods=['GET', 'POST'])
def creator_accounts():
    guard = _admin_json_guard()
    if guard:
        return guard

    if request.method == 'POST':
        data = request.json or {}
        account_id = data.get('id')
        if account_id:
            account = CreatorAccount.query.get_or_404(account_id)
        else:
            account = CreatorAccount()
            db.session.add(account)

        platform = (data.get('platform') or 'xhs').strip()
        account_handle = (data.get('account_handle') or '').strip()
        display_name = (data.get('display_name') or '').strip()
        if not account_handle and not display_name:
            return jsonify({'success': False, 'message': '账号标识或昵称至少填写一个'})

        account.platform = platform
        account.owner_name = (data.get('owner_name') or '').strip()
        account.owner_phone = (data.get('owner_phone') or '').strip()
        account.account_handle = account_handle or display_name
        account.display_name = display_name or account.account_handle
        account.profile_url = (data.get('profile_url') or '').strip()
        account.follower_count = _safe_int(data.get('follower_count'), account.follower_count or 0)
        account.source_channel = (data.get('source_channel') or account.source_channel or 'manual').strip()
        account.status = (data.get('status') or account.status or 'active').strip()
        account.notes = (data.get('notes') or '').strip()
        account.last_synced_at = datetime.now()
        db.session.flush()
        _log_operation('save', 'creator_account', target_id=account.id, message='保存账号信息', detail={
            'platform': account.platform,
            'owner_name': account.owner_name,
            'account_handle': account.account_handle,
        })
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '账号已保存',
            'item': _serialize_creator_account(account)
        })

    query = _build_creator_account_query(request.args)
    accounts = query.order_by(CreatorAccount.updated_at.desc(), CreatorAccount.created_at.desc()).limit(200).all()
    return jsonify({
        'success': True,
        'items': [_serialize_creator_account(account) for account in accounts]
    })


@app.route('/api/creator_accounts/analytics')
def creator_accounts_analytics():
    guard = _admin_json_guard()
    if guard:
        return guard

    accounts = _build_creator_account_query(request.args).all()
    account_ids = [account.id for account in accounts]
    date_from = _parse_date(request.args.get('date_from'))
    date_to = _parse_date(request.args.get('date_to'))

    posts = []
    snapshots = []
    if account_ids:
        post_query = CreatorPost.query.filter(CreatorPost.creator_account_id.in_(account_ids))
        post_query, _, _ = _apply_creator_post_range(post_query, request.args)
        posts = post_query.order_by(CreatorPost.publish_time.asc(), CreatorPost.created_at.asc()).all()

        snapshot_query = CreatorAccountSnapshot.query.filter(CreatorAccountSnapshot.creator_account_id.in_(account_ids))
        if date_from:
            snapshot_query = snapshot_query.filter(CreatorAccountSnapshot.snapshot_date >= date_from)
        if date_to:
            snapshot_query = snapshot_query.filter(CreatorAccountSnapshot.snapshot_date <= date_to)
        snapshots = snapshot_query.order_by(CreatorAccountSnapshot.snapshot_date.asc(), CreatorAccountSnapshot.created_at.asc()).all()

    analytics = _build_creator_analytics_payload(posts, snapshots, date_from=date_from, date_to=date_to)

    platform_map = defaultdict(lambda: {
        'account_count': 0,
        'post_count': 0,
        'viral_posts': 0,
        'total_views': 0,
        'total_interactions': 0,
        'follower_count': 0,
    })
    account_rows = []
    posts_by_account = defaultdict(list)
    for post in posts:
        posts_by_account[post.creator_account_id].append(post)

    for account in accounts:
        platform_key = account.platform or 'unknown'
        account_posts = posts_by_account.get(account.id, [])
        post_count = len(account_posts)
        viral_posts = len([post for post in account_posts if post.is_viral])
        total_views = sum(post.views or 0 for post in account_posts)
        total_interactions = sum((post.likes or 0) + (post.favorites or 0) + (post.comments or 0) for post in account_posts)
        platform_row = platform_map[platform_key]
        platform_row['account_count'] += 1
        platform_row['post_count'] += post_count
        platform_row['viral_posts'] += viral_posts
        platform_row['total_views'] += total_views
        platform_row['total_interactions'] += total_interactions
        platform_row['follower_count'] += account.follower_count or 0

        account_rows.append({
            'id': account.id,
            'owner_name': account.owner_name or '',
            'display_name': account.display_name or account.account_handle or '',
            'platform': platform_key,
            'post_count': post_count,
            'viral_posts': viral_posts,
            'total_views': total_views,
            'total_interactions': total_interactions,
        })

    platform_rows = [{'platform': platform, **stats} for platform, stats in platform_map.items()]
    platform_rows.sort(key=lambda item: (item['total_interactions'], item['total_views'], item['account_count']), reverse=True)
    account_rows.sort(key=lambda item: (item['total_interactions'], item['total_views'], item['post_count']), reverse=True)

    analytics['overview']['account_count'] = len(accounts)
    analytics['platforms'] = platform_rows
    analytics['top_accounts'] = account_rows[:10]
    return jsonify({
        'success': True,
        **analytics,
    })


@app.route('/api/creator_accounts/export')
def export_creator_accounts():
    guard = _admin_json_guard()
    if guard:
        return guard

    accounts = _build_creator_account_query(request.args).order_by(
        CreatorAccount.updated_at.desc(),
        CreatorAccount.created_at.desc()
    ).all()
    rows = ['平台,姓名,手机号,账号标识,显示昵称,当前粉丝,发文数,爆款数,总阅读,总互动,最佳笔记,最佳笔记阅读,上次同步']
    for account in accounts:
        item = _serialize_creator_account(account)
        best_post = item.get('best_post') or {}
        row = [
            item.get('platform', ''),
            (item.get('owner_name') or '').replace(',', ' '),
            (item.get('owner_phone') or '').replace(',', ' '),
            (item.get('account_handle') or '').replace(',', ' '),
            (item.get('display_name') or '').replace(',', ' '),
            str(item.get('follower_count') or 0),
            str(item.get('post_count') or 0),
            str(item.get('viral_post_count') or 0),
            str(item.get('total_views') or 0),
            str(item.get('total_interactions') or 0),
            (best_post.get('title') or '').replace(',', ' '),
            str(best_post.get('views') or 0),
            (item.get('last_synced_at') or '').replace(',', ' '),
        ]
        rows.append(','.join(row))

    _log_operation('export', 'creator_account_list', message='导出账号列表', detail={
        'platform': request.args.get('platform', ''),
        'phone': request.args.get('phone', ''),
        'keyword': request.args.get('keyword', ''),
        'viral_only': request.args.get('viral_only', ''),
        'count': len(accounts),
    })
    db.session.commit()
    content = '\n'.join(rows)
    return content, 200, {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': 'attachment; filename=creator_accounts.csv'
    }


@app.route('/api/creator_accounts/<int:account_id>/export')
def export_creator_account_detail(account_id):
    guard = _admin_json_guard()
    if guard:
        return guard

    account = CreatorAccount.query.get_or_404(account_id)
    post_query = CreatorPost.query.filter_by(creator_account_id=account.id)
    post_query, date_from, date_to = _apply_creator_post_range(post_query, request.args)
    posts = post_query.order_by(CreatorPost.publish_time.desc(), CreatorPost.created_at.desc()).all()

    rows = [
        '账号维度',
        '平台,姓名,手机号,账号标识,显示昵称,当前粉丝,发文数,爆款数,总阅读,总互动,统计起始,统计截止',
        ','.join([
            account.platform or '',
            (account.owner_name or '').replace(',', ' '),
            (account.owner_phone or '').replace(',', ' '),
            (account.account_handle or '').replace(',', ' '),
            (account.display_name or '').replace(',', ' '),
            str(account.follower_count or 0),
            str(len(posts)),
            str(len([post for post in posts if post.is_viral])),
            str(sum(post.views or 0 for post in posts)),
            str(sum((post.likes or 0) + (post.favorites or 0) + (post.comments or 0) for post in posts)),
            date_from.isoformat() if date_from else '',
            date_to.isoformat() if date_to else '',
        ]),
        '',
        '笔记维度',
        '标题,话题,发布时间,阅读,曝光,点赞,收藏,评论,涨粉,是否爆款,链接',
    ]
    for post in posts:
        rows.append(','.join([
            (post.title or '').replace(',', ' '),
            (post.topic_title or '').replace(',', ' '),
            post.publish_time.strftime('%Y-%m-%d %H:%M:%S') if post.publish_time else '',
            str(post.views or 0),
            str(post.exposures or 0),
            str(post.likes or 0),
            str(post.favorites or 0),
            str(post.comments or 0),
            str(post.follower_delta or 0),
            '是' if post.is_viral else '否',
            (post.post_url or '').replace(',', ' '),
        ]))

    _log_operation('export', 'creator_account', target_id=account.id, message='导出单账号数据', detail={
        'date_from': date_from.isoformat() if date_from else '',
        'date_to': date_to.isoformat() if date_to else '',
        'post_count': len(posts),
    })
    db.session.commit()
    content = '\n'.join(rows)
    return content, 200, {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': f'attachment; filename=creator_account_{account.id}.csv'
    }


@app.route('/api/creator_accounts/<int:account_id>/posts', methods=['GET', 'POST'])
def creator_account_posts(account_id):
    guard = _admin_json_guard()
    if guard:
        return guard

    account = CreatorAccount.query.get_or_404(account_id)
    if request.method == 'POST':
        data = request.json or {}
        post_id = data.get('id')
        if post_id:
            post = CreatorPost.query.filter_by(id=post_id, creator_account_id=account.id).first()
            if not post:
                return jsonify({'success': False, 'message': '笔记不存在'})
        else:
            post = CreatorPost(creator_account_id=account.id)
            db.session.add(post)

        title = (data.get('title') or '').strip()
        if not title:
            return jsonify({'success': False, 'message': '笔记标题不能为空'})

        post.platform_post_id = (data.get('platform_post_id') or '').strip()
        post.title = title
        post.post_url = (data.get('post_url') or '').strip()
        post.publish_time = _parse_datetime(data.get('publish_time'))
        post.topic_title = (data.get('topic_title') or '').strip()
        post.views = _safe_int(data.get('views'))
        post.exposures = _safe_int(data.get('exposures'))
        post.likes = _safe_int(data.get('likes'))
        post.favorites = _safe_int(data.get('favorites'))
        post.comments = _safe_int(data.get('comments'))
        post.shares = _safe_int(data.get('shares'))
        post.follower_delta = _safe_int(data.get('follower_delta'))
        raw_is_viral = data.get('is_viral')
        if raw_is_viral is None:
            post.is_viral = _infer_viral_post(
                views=post.views,
                likes=post.likes,
                favorites=post.favorites,
                comments=post.comments,
                exposures=post.exposures
            )
        else:
            post.is_viral = _coerce_bool(raw_is_viral)
        post.source_channel = (data.get('source_channel') or post.source_channel or 'manual').strip()
        post.raw_payload = json.dumps(data, ensure_ascii=False)
        account.last_synced_at = datetime.now()
        db.session.flush()
        _log_operation('save', 'creator_post', target_id=post.id, message='保存账号笔记表现', detail={
            'creator_account_id': account.id,
            'title': post.title,
            'views': post.views,
            'is_viral': bool(post.is_viral),
        })
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '账号笔记已保存',
            'item': _serialize_creator_post(post)
        })

    post_query = CreatorPost.query.filter_by(creator_account_id=account.id)
    post_query, _, _ = _apply_creator_post_range(post_query, request.args)
    posts = post_query.order_by(
        CreatorPost.publish_time.desc(), CreatorPost.created_at.desc()
    ).limit(200).all()
    return jsonify({
        'success': True,
        'account': _serialize_creator_account(account),
        'items': [_serialize_creator_post(post) for post in posts]
    })


@app.route('/api/creator_accounts/<int:account_id>/posts/<int:post_id>/viral', methods=['POST'])
def update_creator_post_viral(account_id, post_id):
    guard = _admin_json_guard()
    if guard:
        return guard

    account = CreatorAccount.query.get_or_404(account_id)
    post = CreatorPost.query.filter_by(id=post_id, creator_account_id=account.id).first()
    if not post:
        return jsonify({'success': False, 'message': '笔记不存在'})

    data = request.json or {}
    is_viral = _coerce_bool(data.get('is_viral'))
    post.is_viral = is_viral
    _log_operation('mark_viral', 'creator_post', target_id=post.id, message='人工修正爆款标记', detail={
        'creator_account_id': account.id,
        'title': post.title,
        'is_viral': is_viral,
    })
    db.session.commit()
    return jsonify({
        'success': True,
        'message': f'已将笔记标记为{"爆款" if is_viral else "普通"}',
        'item': _serialize_creator_post(post)
    })


@app.route('/api/creator_accounts/<int:account_id>/snapshots', methods=['GET', 'POST'])
def creator_account_snapshots(account_id):
    guard = _admin_json_guard()
    if guard:
        return guard

    account = CreatorAccount.query.get_or_404(account_id)
    if request.method == 'POST':
        data = request.json or {}
        snapshot_date = _parse_date(data.get('snapshot_date')) or datetime.now().date()
        snapshot = CreatorAccountSnapshot(
            creator_account_id=account.id,
            snapshot_date=snapshot_date,
            follower_count=_safe_int(data.get('follower_count'), account.follower_count or 0),
            post_count=_safe_int(data.get('post_count')),
            total_views=_safe_int(data.get('total_views')),
            total_interactions=_safe_int(data.get('total_interactions')),
            source_channel=(data.get('source_channel') or 'manual').strip()
        )
        account.follower_count = snapshot.follower_count
        account.last_synced_at = datetime.now()
        db.session.add(snapshot)
        db.session.flush()
        _log_operation('save', 'creator_snapshot', message='保存账号快照', detail={
            'snapshot_id': snapshot.id,
            'creator_account_id': account.id,
            'snapshot_date': snapshot_date.isoformat() if snapshot_date else '',
            'follower_count': snapshot.follower_count,
        })
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '账号快照已保存',
            'item': {
                'id': snapshot.id,
                'snapshot_date': snapshot.snapshot_date.isoformat() if snapshot.snapshot_date else '',
                'follower_count': snapshot.follower_count or 0,
                'post_count': snapshot.post_count or 0,
                'total_views': snapshot.total_views or 0,
                'total_interactions': snapshot.total_interactions or 0,
                'source_channel': snapshot.source_channel or '',
                'created_at': snapshot.created_at.strftime('%Y-%m-%d %H:%M:%S') if snapshot.created_at else '',
            }
        })

    snapshot_query = CreatorAccountSnapshot.query.filter_by(creator_account_id=account.id)
    date_from = _parse_date(request.args.get('date_from'))
    date_to = _parse_date(request.args.get('date_to'))
    if date_from:
        snapshot_query = snapshot_query.filter(CreatorAccountSnapshot.snapshot_date >= date_from)
    if date_to:
        snapshot_query = snapshot_query.filter(CreatorAccountSnapshot.snapshot_date <= date_to)

    snapshots = snapshot_query.order_by(
        CreatorAccountSnapshot.snapshot_date.desc(), CreatorAccountSnapshot.created_at.desc()
    ).limit(120).all()
    return jsonify({
        'success': True,
        'account': _serialize_creator_account(account),
        'items': [{
            'id': snapshot.id,
            'snapshot_date': snapshot.snapshot_date.isoformat() if snapshot.snapshot_date else '',
            'follower_count': snapshot.follower_count or 0,
            'post_count': snapshot.post_count or 0,
            'total_views': snapshot.total_views or 0,
            'total_interactions': snapshot.total_interactions or 0,
            'source_channel': snapshot.source_channel or '',
            'created_at': snapshot.created_at.strftime('%Y-%m-%d %H:%M:%S') if snapshot.created_at else '',
        } for snapshot in snapshots]
    })


@app.route('/api/creator_accounts/<int:account_id>/analytics')
def creator_account_analytics(account_id):
    guard = _admin_json_guard()
    if guard:
        return guard

    account = CreatorAccount.query.get_or_404(account_id)
    post_query = CreatorPost.query.filter_by(creator_account_id=account.id)
    post_query, date_from, date_to = _apply_creator_post_range(post_query, request.args)
    posts = post_query.order_by(CreatorPost.publish_time.asc(), CreatorPost.created_at.asc()).all()

    snapshot_query = CreatorAccountSnapshot.query.filter_by(creator_account_id=account.id)
    if date_from:
        snapshot_query = snapshot_query.filter(CreatorAccountSnapshot.snapshot_date >= date_from)
    if date_to:
        snapshot_query = snapshot_query.filter(CreatorAccountSnapshot.snapshot_date <= date_to)
    snapshots = snapshot_query.order_by(CreatorAccountSnapshot.snapshot_date.asc(), CreatorAccountSnapshot.created_at.asc()).all()

    daily_map = defaultdict(lambda: {
        'post_count': 0,
        'viral_posts': 0,
        'views': 0,
        'exposures': 0,
        'interactions': 0,
        'follower_delta': 0,
    })
    topic_map = defaultdict(lambda: {'post_count': 0, 'views': 0, 'interactions': 0})
    for post in posts:
        base_dt = post.publish_time or post.created_at or datetime.now()
        day_key = base_dt.strftime('%Y-%m-%d')
        interactions = (post.likes or 0) + (post.favorites or 0) + (post.comments or 0)
        row = daily_map[day_key]
        row['post_count'] += 1
        row['viral_posts'] += 1 if post.is_viral else 0
        row['views'] += post.views or 0
        row['exposures'] += post.exposures or 0
        row['interactions'] += interactions
        row['follower_delta'] += post.follower_delta or 0

        topic_key = (post.topic_title or '未关联话题').strip()
        topic_row = topic_map[topic_key]
        topic_row['post_count'] += 1
        topic_row['views'] += post.views or 0
        topic_row['interactions'] += interactions

    daily_rows = []
    for day_key in sorted(daily_map.keys()):
        item = daily_map[day_key]
        daily_rows.append({
            'date': day_key,
            **item,
        })

    snapshot_rows = [{
        'date': snapshot.snapshot_date.isoformat() if snapshot.snapshot_date else '',
        'follower_count': snapshot.follower_count or 0,
        'post_count': snapshot.post_count or 0,
        'total_views': snapshot.total_views or 0,
        'total_interactions': snapshot.total_interactions or 0,
    } for snapshot in snapshots]

    top_topics = []
    for topic_name, item in topic_map.items():
        top_topics.append({
            'topic_title': topic_name,
            **item,
        })
    top_topics.sort(key=lambda row: (row['interactions'], row['views'], row['post_count']), reverse=True)

    total_views = sum(post.views or 0 for post in posts)
    total_exposures = sum(post.exposures or 0 for post in posts)
    total_interactions = sum((post.likes or 0) + (post.favorites or 0) + (post.comments or 0) for post in posts)
    total_follower_delta = sum(post.follower_delta or 0 for post in posts)
    viral_posts = len([post for post in posts if post.is_viral])
    best_post = sorted(
        posts,
        key=lambda item: ((item.views or 0), ((item.likes or 0) + (item.favorites or 0) + (item.comments or 0)), (item.follower_delta or 0)),
        reverse=True
    )[0] if posts else None

    overview = {
        'post_count': len(posts),
        'viral_posts': viral_posts,
        'total_views': total_views,
        'total_exposures': total_exposures,
        'total_interactions': total_interactions,
        'total_follower_delta': total_follower_delta,
        'avg_views': round(total_views / len(posts), 2) if posts else 0,
        'avg_interactions': round(total_interactions / len(posts), 2) if posts else 0,
        'best_post': _serialize_creator_post(best_post) if best_post else None,
        'date_from': date_from.isoformat() if date_from else '',
        'date_to': date_to.isoformat() if date_to else '',
    }

    return jsonify({
        'success': True,
        'account': _serialize_creator_account(account),
        'overview': overview,
        'daily_posts': daily_rows,
        'daily_snapshots': snapshot_rows,
        'top_topics': top_topics[:10],
    })

# 活动管理
@app.route('/activity')
def activity_list():
    activities = Activity.query.order_by(Activity.created_at.desc()).all()
    return render_template('activity_list.html', activities=activities)

@app.route('/activity/<int:activity_id>')
def activity_detail(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    return render_template('activity_detail.html', activity=activity)

@app.route('/api/stats/<int:activity_id>')
def get_stats(activity_id):
    return jsonify(_build_dashboard_stats(activity_id, request.args))


@app.route('/api/weekly_report/<int:activity_id>')
def export_weekly_report(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    stats = _build_dashboard_stats(activity_id, request.args)

    group_lines = [
        f"- {row['group']}：参与{row['count']}，已发布{row['published']}，发布率{round(row['completion_rate'], 2)}%"
        for row in stats['group_completion']
    ]
    top_lines = [
        f"{idx}. {row['name']}｜{row['group']}｜互动{row['interactions']}｜{row['topic']}"
        for idx, row in enumerate(stats['personal_rankings']['all_platform'][:20], 1)
    ]
    platform_lines = [
        f"- {platform['label']}：参与人数{platform['participants']}，发布条数{platform['published_count']}，传播量{platform['views']}，互动率{platform['interaction_rate_display']}"
        for platform in stats['platforms'].values()
    ]
    type_line = '、'.join([
        f"{name}{count}" for name, count in sorted(
            stats['content_type_stats'].items(),
            key=lambda item: item[1],
            reverse=True
        )
    ]) if stats['content_type_stats'] else '暂无'

    report = f"""# {activity.name} 周报（{activity.title}）

生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
统计区间：{stats['range']['label']} {stats['range']['start_date'] or ''} {('~ ' + stats['range']['end_date']) if stats['range']['end_date'] else ''}

## 一、固定口径
{chr(10).join([f"- {line}" for line in stats['definitions']])}

## 二、总览区
- 总参与人数：{stats['overview']['total_participants']}
- 总发布条数：{stats['overview']['total_published']}
- 总体发布率：{stats['overview']['publish_rate_display']}
- 总传播量：{stats['total_views']}
- 总互动：{stats['total_interactions']}（点赞{stats['total_likes']} + 收藏{stats['total_favorites']} + 评论{stats['total_comments']}）

## 三、平台分层
{chr(10).join(platform_lines) if platform_lines else '- 暂无平台数据'}

## 四、小组排名
{chr(10).join(group_lines) if group_lines else '- 暂无小组数据'}

## 五、优秀个人TOP20（小红书+抖音+视频号）
{chr(10).join(top_lines) if top_lines else '暂无数据'}

## 六、内容类型分布
- {type_line}
- 当前最佳内容类型：{stats['best_content_type'] or '暂无'}

## 七、优化建议
{chr(10).join([f"- {line}" for line in stats['note_improvement_suggestions']])}

## 八、下期选题建议
{chr(10).join([f"- {line}" for line in stats['next_topic_suggestions']])}
"""

    return report, 200, {
        'Content-Type': 'text/markdown; charset=utf-8',
        'Content-Disposition': f"attachment; filename=weekly_report_activity_{activity_id}.md"
    }


@app.route('/api/activity/<int:activity_id>/snapshots')
def list_activity_snapshots(activity_id):
    guard = _admin_json_guard()
    if guard:
        return guard

    snapshots = ActivitySnapshot.query.filter_by(activity_id=activity_id).order_by(ActivitySnapshot.created_at.desc()).all()
    items = []
    for snapshot in snapshots:
        _, summary = _snapshot_payload_and_summary(snapshot)
        items.append({
            'id': snapshot.id,
            'activity_id': snapshot.activity_id,
            'snapshot_name': snapshot.snapshot_name or '',
            'source_status': snapshot.source_status or '',
            'topic_count': summary.get('topic_count', 0),
            'registration_count': summary.get('registration_count', 0),
            'submission_count': summary.get('submission_count', 0),
            'created_at': snapshot.created_at.strftime('%Y-%m-%d %H:%M:%S') if snapshot.created_at else '',
        })
    return jsonify({'success': True, 'items': items})


@app.route('/api/activity_snapshots/<int:snapshot_id>')
def activity_snapshot_detail(snapshot_id):
    guard = _admin_json_guard()
    if guard:
        return guard

    snapshot = ActivitySnapshot.query.get_or_404(snapshot_id)
    payload, _ = _snapshot_payload_and_summary(snapshot)
    return jsonify({
        'success': True,
        'item': {
            'id': snapshot.id,
            'activity_id': snapshot.activity_id,
            'snapshot_name': snapshot.snapshot_name or '',
            'source_status': snapshot.source_status or '',
            'created_at': snapshot.created_at.strftime('%Y-%m-%d %H:%M:%S') if snapshot.created_at else '',
            'payload': payload,
        }
    })


@app.route('/api/operation_logs')
def operation_logs():
    guard = _admin_json_guard()
    if guard:
        return guard

    action = (request.args.get('action') or '').strip()
    target_type = (request.args.get('target_type') or '').strip()
    keyword = (request.args.get('keyword') or '').strip()
    limit = min(max(_safe_int(request.args.get('limit'), 50), 1), 500)

    query = OperationLog.query
    if action:
        query = query.filter_by(action=action)
    if target_type:
        query = query.filter_by(target_type=target_type)
    if keyword:
        query = query.filter(or_(
            OperationLog.actor.contains(keyword),
            OperationLog.message.contains(keyword),
            OperationLog.detail.contains(keyword),
        ))

    logs = query.order_by(OperationLog.created_at.desc(), OperationLog.id.desc()).limit(limit).all()
    return jsonify({
        'success': True,
        'items': [_serialize_operation_log(log) for log in logs]
    })


@app.route('/api/jobs/ping', methods=['POST'])
def trigger_worker_ping():
    guard = _admin_json_guard()
    if guard:
        return guard

    from celery_app import ping

    task = ping.delay()
    _log_operation('dispatch_job', 'worker', message='触发 Worker 联通检查', detail={
        'task_id': task.id,
        'job': 'system.ping',
    })
    db.session.commit()
    return jsonify({
        'success': True,
        'message': '已触发 Worker 联通检查',
        'task_id': task.id,
        'job': 'system.ping',
    })


@app.route('/api/jobs/hotwords/run', methods=['POST'])
def trigger_hotword_sync_job():
    guard = _admin_json_guard()
    if guard:
        return guard

    payload = request.json or {}
    source_platform = (payload.get('source_platform') or '小红书').strip()
    source_channel = (payload.get('source_channel') or 'Worker骨架').strip()
    mode = (payload.get('mode') or 'skeleton').strip() or 'skeleton'
    keyword_limit = min(max(_safe_int(payload.get('keyword_limit'), 10), 1), 30)
    batch_name = (payload.get('batch_name') or datetime.now().strftime('hotword_%Y%m%d_%H%M%S')).strip()[:120]
    raw_keywords = payload.get('keywords')
    if isinstance(raw_keywords, list):
        keyword_items = [str(item).strip() for item in raw_keywords if str(item).strip()]
    else:
        keyword_items = _split_keywords(raw_keywords or '')
    keywords = keyword_items[:keyword_limit] if keyword_items else _automation_keyword_seeds()[:keyword_limit]

    task_record = DataSourceTask(
        task_type='hotword_sync',
        source_platform=source_platform,
        source_channel=source_channel,
        mode=mode,
        status='queued',
        batch_name=batch_name,
        keyword_limit=len(keywords),
        activity_id=_safe_int(payload.get('activity_id'), 0) or None,
        message='等待 Worker 执行热点抓取骨架',
        params_payload=json.dumps({
            'keywords': keywords,
            'keyword_limit': keyword_limit,
            'source_platform': source_platform,
            'source_channel': source_channel,
            'mode': mode,
            'batch_name': batch_name,
        }, ensure_ascii=False),
    )
    db.session.add(task_record)
    db.session.flush()
    _append_data_source_log(task_record.id, '已创建热点抓取任务，等待 Worker 处理', detail={
        'keywords': keywords,
        'source_platform': source_platform,
        'source_channel': source_channel,
        'mode': mode,
        'batch_name': batch_name,
    })

    from celery_app import sync_hotwords_job

    async_task = sync_hotwords_job.delay(task_record.id)
    task_record.celery_task_id = async_task.id
    task_record.updated_at = datetime.now()
    _log_operation('dispatch_job', 'data_source_task', target_id=task_record.id, message='触发热点抓取 Worker 任务', detail={
        'task_id': async_task.id,
        'job': 'jobs.hotwords.sync',
        'source_platform': source_platform,
        'batch_name': batch_name,
        'keyword_count': len(keywords),
    })
    db.session.commit()
    return jsonify({
        'success': True,
        'message': f'已触发热点抓取任务，关键词 {len(keywords)} 个',
        'task_id': async_task.id,
        'job': 'jobs.hotwords.sync',
        'data_source_task_id': task_record.id,
    })


@app.route('/api/jobs/assets/generate', methods=['POST'])
def trigger_asset_generation_job():
    data = request.json or {}
    registration_id = _safe_int(data.get('registration_id'), 0)
    reg = Registration.query.get(registration_id) if registration_id else None
    if not reg:
        return jsonify({'success': False, 'message': '报名信息不存在'})

    selected_content = (data.get('selected_content') or '').strip()
    style_preset = (data.get('style_preset') or '小红书图文').strip()[:50]
    image_count = min(max(_safe_int(data.get('image_count'), 3), 1), 4)
    title_hint = (data.get('title_hint') or _extract_title_from_version(selected_content) or reg.topic.topic_name).strip()[:200]
    prompt_text = _build_asset_generation_prompt(
        reg.topic,
        selected_content=selected_content,
        style_preset=style_preset,
        title_hint=title_hint,
    )

    task = AssetGenerationTask(
        registration_id=reg.id,
        topic_id=reg.topic_id,
        source_provider=(os.environ.get('ASSET_IMAGE_PROVIDER') or 'svg_fallback').strip() or 'svg_fallback',
        model_name=(os.environ.get('ASSET_IMAGE_MODEL') or '').strip()[:100],
        style_preset=style_preset,
        image_count=image_count,
        status='queued',
        title_hint=title_hint,
        prompt_text=prompt_text,
        selected_content=selected_content,
        message='等待 Worker 生成图片任务',
    )
    db.session.add(task)
    db.session.flush()
    _log_operation('dispatch_job', 'asset_generation_task', target_id=task.id, message='触发图片生成任务', detail={
        'registration_id': reg.id,
        'topic_id': reg.topic_id,
        'style_preset': style_preset,
        'image_count': image_count,
        'source_provider': task.source_provider,
    })

    from celery_app import generate_asset_images_job

    async_task = generate_asset_images_job.delay(task.id)
    task.celery_task_id = async_task.id
    db.session.commit()
    return jsonify({
        'success': True,
        'message': f'已创建图片生成任务，预计输出 {image_count} 张',
        'task_id': async_task.id,
        'asset_task_id': task.id,
        'job': 'jobs.assets.generate',
    })


@app.route('/api/jobs/topic_ideas/generate', methods=['POST'])
def trigger_generate_topic_ideas_job():
    guard = _admin_json_guard()
    if guard:
        return guard

    data = request.json or {}
    count = min(max(_safe_int(data.get('count'), 80), 1), 120)
    activity_id = data.get('activity_id')
    quota = _normalize_quota(data.get('quota'))

    from celery_app import generate_topic_ideas_job

    task = generate_topic_ideas_job.delay(count=count, activity_id=activity_id, quota=quota)
    _log_operation('dispatch_job', 'topic_idea', message='触发异步生成候选话题', detail={
        'task_id': task.id,
        'count': count,
        'activity_id': activity_id,
        'quota': quota,
    })
    db.session.commit()
    return jsonify({
        'success': True,
        'message': '已触发异步生成候选话题任务',
        'task_id': task.id,
        'job': 'jobs.generate_topic_ideas',
    })


@app.route('/api/jobs/<task_id>')
def get_job_status(task_id):
    guard = _admin_json_guard()
    if guard:
        return guard

    from celery.result import AsyncResult
    from celery_app import celery

    result = AsyncResult(task_id, app=celery)
    payload = result.result
    if not isinstance(payload, (dict, list, str, int, float, bool, type(None))):
        payload = str(payload)
    return jsonify({
        'success': True,
        'task_id': task_id,
        'state': result.state,
        'result': payload,
    })


@app.route('/api/jobs/history')
def get_job_history():
    guard = _admin_json_guard()
    if guard:
        return guard

    from celery.result import AsyncResult
    from celery_app import celery

    limit = min(max(_safe_int(request.args.get('limit'), 20), 1), 200)
    logs = OperationLog.query.filter(OperationLog.action.in_(['dispatch_job', 'worker_generate', 'worker_sync', 'worker_generate_asset'])).order_by(
        OperationLog.created_at.desc(),
        OperationLog.id.desc()
    ).limit(limit).all()
    items = []
    for log in logs:
        detail_obj = _deserialize_operation_detail(log.detail)
        items.append({
            'id': log.id,
            'created_at': log.created_at.strftime('%Y-%m-%d %H:%M:%S') if log.created_at else '',
            'actor': log.actor or 'system',
            'action': log.action,
            'target_type': log.target_type,
            'target_id': log.target_id,
            'message': log.message or '',
            'detail': detail_obj,
            'task_id': detail_obj.get('task_id') or '',
            'state': '',
        })
        task_id = detail_obj.get('task_id')
        if task_id:
            try:
                async_result = AsyncResult(task_id, app=celery)
                items[-1]['state'] = async_result.state
            except Exception:
                items[-1]['state'] = 'UNKNOWN'
    return jsonify({
        'success': True,
        'items': items,
    })


@app.route('/admin/activity_snapshots/<int:snapshot_id>/restore', methods=['POST'])
def restore_activity_snapshot(snapshot_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': '未登录'})

    snapshot = ActivitySnapshot.query.get(snapshot_id)
    if not snapshot:
        return jsonify({'success': False, 'message': '快照不存在'})

    data = request.json if request.is_json else request.form
    restored = _restore_activity_from_snapshot(
        snapshot,
        name=(data.get('name') or '').strip() if data else '',
        title=(data.get('title') or '').strip() if data else '',
        description=(data.get('description') or '').strip() if data else None,
    )
    db.session.flush()
    _log_operation('restore_snapshot', 'activity', target_id=restored.id, message='从活动快照恢复新活动', detail={
        'snapshot_id': snapshot.id,
        'restored_name': restored.name,
        'source_activity_id': snapshot.activity_id,
    })
    db.session.commit()
    return jsonify({
        'success': True,
        'message': f'快照已恢复为新活动：{restored.name}',
        'activity': _serialize_activity(restored),
    })

@app.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    activities = Activity.query.order_by(Activity.created_at.desc()).all()
    return render_template('admin.html', activities=activities, default_topic_quota=_default_topic_quota())

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == _admin_username() and password == _admin_password():
            session['admin_logged_in'] = True
            session['admin_username'] = username
            return redirect(url_for('admin'))
        else:
            return render_template('admin_login.html', error='用户名或密码错误')

    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/activity/add', methods=['POST'])
def add_activity():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': '未登录'})

    activity = Activity(
        name=request.form.get('name'),
        title=request.form.get('title'),
        description=request.form.get('description'),
        status='draft'
    )
    db.session.add(activity)
    db.session.flush()
    _log_operation('create', 'activity', target_id=activity.id, message='新增活动', detail={
        'name': activity.name,
        'title': activity.title,
    })
    db.session.commit()

    return jsonify({'success': True, 'message': '活动创建成功'})

@app.route('/admin/topic/add', methods=['POST'])
def add_topic():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': '未登录'})

    quota = _normalize_quota(request.form.get('quota'))
    topic = Topic(
        activity_id=request.form.get('activity_id'),
        topic_name=request.form.get('topic_name'),
        keywords=request.form.get('keywords'),
        direction=request.form.get('direction'),
        reference_content=request.form.get('reference_content'),
        reference_link=request.form.get('reference_link'),
        quota=quota,
        group_num=request.form.get('group_num'),
        pool_status='formal',
        source_type='manual',
        published_at=datetime.now()
    )
    db.session.add(topic)
    db.session.flush()
    _log_operation('create', 'topic', target_id=topic.id, message='手工新增正式话题', detail={
        'activity_id': topic.activity_id,
        'topic_name': topic.topic_name,
        'quota': topic.quota,
    })
    db.session.commit()

    return jsonify({'success': True, 'message': '话题创建成功'})

@app.route('/admin/activity/<int:activity_id>/publish')
def publish_activity(activity_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': '未登录'})

    activity = Activity.query.get(activity_id)
    if not activity:
        return jsonify({'success': False, 'message': '活动不存在'})
    activity.status = 'published'
    activity.archived_at = None
    _log_operation('publish', 'activity', target_id=activity.id, message='发布活动', detail={
        'name': activity.name,
        'title': activity.title,
    })
    db.session.commit()

    return jsonify({'success': True, 'message': '发布成功'})


@app.route('/admin/activity/<int:activity_id>/archive', methods=['POST'])
def archive_activity(activity_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': '未登录'})

    activity = Activity.query.get(activity_id)
    if not activity:
        return jsonify({'success': False, 'message': '活动不存在'})
    if activity.status == 'archived':
        return jsonify({'success': False, 'message': '该活动已归档'})

    snapshot_name = (request.json or {}).get('snapshot_name', '') if request.is_json else ''
    snapshot = _create_activity_snapshot(activity, snapshot_name=snapshot_name)
    activity.status = 'archived'
    activity.archived_at = datetime.now()
    db.session.flush()
    _log_operation('archive', 'activity', target_id=activity.id, message='归档活动并生成快照', detail={
        'name': activity.name,
        'snapshot_id': snapshot.id,
    })
    db.session.commit()
    return jsonify({
        'success': True,
        'message': '活动已归档并生成快照',
        'activity': _serialize_activity(activity),
    })


@app.route('/admin/activity/<int:activity_id>/clone', methods=['POST'])
def clone_activity(activity_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': '未登录'})

    activity = Activity.query.get(activity_id)
    if not activity:
        return jsonify({'success': False, 'message': '活动不存在'})

    data = request.json if request.is_json else request.form
    cloned = _clone_activity(
        activity,
        name=(data.get('name') or '').strip() if data else '',
        title=(data.get('title') or '').strip() if data else '',
        description=(data.get('description') or '').strip() if data else None,
    )
    db.session.flush()
    _log_operation('clone', 'activity', target_id=cloned.id, message='复制活动为新一期', detail={
        'source_activity_id': activity.id,
        'cloned_name': cloned.name,
    })
    db.session.commit()
    return jsonify({
        'success': True,
        'message': f'已复制为新活动：{cloned.name}',
        'activity': _serialize_activity(cloned),
    })

@app.route('/admin/export/<int:activity_id>')
def export_data(activity_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    topics = Topic.query.filter_by(activity_id=activity_id).all()
    topic_ids = [t.id for t in topics]

    registrations = Registration.query.filter(Registration.topic_id.in_(topic_ids)).all()

    # 生成CSV（多平台）
    csv_content = "姓名,小组号,小红书账号,联系方式,话题,小红书链接,小红书传播量,小红书点赞量,小红书收藏量,小红书评论量,抖音链接,抖音传播量,抖音点赞量,抖音收藏量,抖音评论量,视频号链接,视频号传播量,视频号点赞量,视频号收藏量,视频号评论量,微博链接,微博传播量,微博点赞量,微博收藏量,微博评论量\n"
    for reg in registrations:
        topic = reg.topic
        sub = reg.submission
        csv_content += f"{reg.name},{reg.group_num},{reg.xhs_account},{reg.phone},{topic.topic_name},{sub.xhs_link if sub else ''},{sub.xhs_views if sub else 0},{sub.xhs_likes if sub else 0},{sub.xhs_favorites if sub else 0},{sub.xhs_comments if sub else 0},{sub.douyin_link if sub else ''},{sub.douyin_views if sub else 0},{sub.douyin_likes if sub else 0},{sub.douyin_favorites if sub else 0},{sub.douyin_comments if sub else 0},{sub.video_link if sub else ''},{sub.video_views if sub else 0},{sub.video_likes if sub else 0},{sub.video_favorites if sub else 0},{sub.video_comments if sub else 0},{sub.weibo_link if sub else ''},{sub.weibo_views if sub else 0},{sub.weibo_likes if sub else 0},{sub.weibo_favorites if sub else 0},{sub.weibo_comments if sub else 0}\n"

    return csv_content, 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': f'attachment; filename=activity_{activity_id}_data.csv'
    }

# ==================== 初始化 ====================

def init_db():
    with app.app_context():
        db.create_all()

        if _is_sqlite_backend():
            # 历史 SQLite 数据库迁移：补齐新增字段
            conn = db.engine.raw_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(activity)")
                activity_columns = {row[1] for row in cursor.fetchall()}
                if 'archived_at' not in activity_columns:
                    cursor.execute("ALTER TABLE activity ADD COLUMN archived_at DATETIME")
                activity_required_columns = {
                    'source_type': "VARCHAR(30) DEFAULT 'manual'",
                    'source_activity_id': 'INTEGER',
                    'source_snapshot_id': 'INTEGER',
                }
                for col, col_type in activity_required_columns.items():
                    if col not in activity_columns:
                        cursor.execute(f"ALTER TABLE activity ADD COLUMN {col} {col_type}")

                cursor.execute("PRAGMA table_info(topic)")
                topic_columns = {row[1] for row in cursor.fetchall()}
                topic_required_columns = {
                    'pool_status': "VARCHAR(20) DEFAULT 'formal'",
                    'source_type': "VARCHAR(30) DEFAULT 'manual'",
                    'source_ref_id': 'INTEGER',
                    'source_snapshot_id': 'INTEGER',
                    'published_at': 'DATETIME',
                }
                for col, col_type in topic_required_columns.items():
                    if col not in topic_columns:
                        cursor.execute(f"ALTER TABLE topic ADD COLUMN {col} {col_type}")

                cursor.execute("PRAGMA table_info(corpus_entry)")
                corpus_columns = {row[1] for row in cursor.fetchall()}
                if 'pool_status' not in corpus_columns:
                    cursor.execute("ALTER TABLE corpus_entry ADD COLUMN pool_status VARCHAR(20) DEFAULT 'reserve'")

                cursor.execute("PRAGMA table_info(trend_note)")
                trend_columns = {row[1] for row in cursor.fetchall()}
                if 'pool_status' not in trend_columns:
                    cursor.execute("ALTER TABLE trend_note ADD COLUMN pool_status VARCHAR(20) DEFAULT 'reserve'")

                cursor.execute("PRAGMA table_info(submission)")
                existing_columns = {row[1] for row in cursor.fetchall()}

                required_columns = {
                    'xhs_views': 'INTEGER DEFAULT 0',
                    'xhs_likes': 'INTEGER DEFAULT 0',
                    'xhs_favorites': 'INTEGER DEFAULT 0',
                    'xhs_comments': 'INTEGER DEFAULT 0',
                    'douyin_link': 'VARCHAR(500)',
                    'douyin_views': 'INTEGER DEFAULT 0',
                    'douyin_likes': 'INTEGER DEFAULT 0',
                    'douyin_favorites': 'INTEGER DEFAULT 0',
                    'douyin_comments': 'INTEGER DEFAULT 0',
                    'video_link': 'VARCHAR(500)',
                    'video_views': 'INTEGER DEFAULT 0',
                    'video_likes': 'INTEGER DEFAULT 0',
                    'video_favorites': 'INTEGER DEFAULT 0',
                    'video_comments': 'INTEGER DEFAULT 0',
                    'weibo_link': 'VARCHAR(500)',
                    'weibo_views': 'INTEGER DEFAULT 0',
                    'weibo_likes': 'INTEGER DEFAULT 0',
                    'weibo_favorites': 'INTEGER DEFAULT 0',
                    'weibo_comments': 'INTEGER DEFAULT 0',
                    'content_type': "VARCHAR(30) DEFAULT '未识别'",
                    'note_title': 'VARCHAR(300)',
                    'note_content': 'TEXT',
                }

                for col, col_type in required_columns.items():
                    if col not in existing_columns:
                        cursor.execute(f"ALTER TABLE submission ADD COLUMN {col} {col_type}")

                if {'likes', 'favorites', 'comments'}.issubset(existing_columns):
                    cursor.execute("UPDATE submission SET xhs_likes = COALESCE(xhs_likes, likes), xhs_favorites = COALESCE(xhs_favorites, favorites), xhs_comments = COALESCE(xhs_comments, comments)")

                cursor.execute("PRAGMA table_info(topic_idea)")
                topic_idea_columns = {row[1] for row in cursor.fetchall()}
                topic_idea_required_columns = {
                    'quota': 'INTEGER DEFAULT 30',
                    'review_note': 'TEXT',
                    'reviewed_at': 'DATETIME',
                    'published_at': 'DATETIME',
                    'published_topic_id': 'INTEGER',
                }
                for col, col_type in topic_idea_required_columns.items():
                    if col not in topic_idea_columns:
                        cursor.execute(f"ALTER TABLE topic_idea ADD COLUMN {col} {col_type}")

                if 'quota' in topic_idea_columns or 'quota' in topic_idea_required_columns:
                    cursor.execute("UPDATE topic_idea SET quota = COALESCE(quota, 30)")

                cursor.execute(
                    "UPDATE topic_idea SET status = 'pending_review' "
                    "WHERE status IS NULL OR status = '' OR status = 'draft'"
                )

                cursor.execute("UPDATE topic SET pool_status = COALESCE(pool_status, 'formal')")
                cursor.execute("UPDATE topic SET source_type = COALESCE(source_type, 'manual')")
                cursor.execute("UPDATE topic SET published_at = COALESCE(published_at, created_at)")
                cursor.execute("UPDATE activity SET source_type = COALESCE(source_type, 'manual')")
                cursor.execute("UPDATE corpus_entry SET pool_status = COALESCE(pool_status, 'reserve')")
                cursor.execute("UPDATE trend_note SET pool_status = COALESCE(pool_status, 'reserve')")

                conn.commit()
            finally:
                conn.close()

        # 通用回填：PostgreSQL/SQLite 都可安全执行
        Activity.query.filter(Activity.source_type.is_(None)).update(
            {'source_type': 'manual'},
            synchronize_session=False
        )
        Topic.query.filter(Topic.pool_status.is_(None)).update(
            {'pool_status': 'formal'},
            synchronize_session=False
        )
        Topic.query.filter(Topic.source_type.is_(None)).update(
            {'source_type': 'manual'},
            synchronize_session=False
        )
        CorpusEntry.query.filter(CorpusEntry.pool_status.is_(None)).update(
            {'pool_status': 'reserve'},
            synchronize_session=False
        )
        TrendNote.query.filter(TrendNote.pool_status.is_(None)).update(
            {'pool_status': 'reserve'},
            synchronize_session=False
        )
        TopicIdea.query.filter(or_(TopicIdea.status.is_(None), TopicIdea.status == '', TopicIdea.status == 'draft')).update(
            {'status': 'pending_review'},
            synchronize_session=False
        )
        db.session.commit()

        if CorpusEntry.query.count() == 0:
            for seed in CORPUS_SEED_ENTRIES:
                db.session.add(CorpusEntry(**seed))
            db.session.commit()

        keyword_setting = Settings.query.filter_by(key='automation_keyword_seeds').first()
        if not keyword_setting:
            keyword_setting = Settings(key='automation_keyword_seeds', value=json.dumps(LIVER_KEYWORD_SEEDS, ensure_ascii=False))
            db.session.add(keyword_setting)
            db.session.commit()

        default_quota_setting = Settings.query.filter_by(key='default_topic_quota').first()
        if not default_quota_setting:
            default_quota_setting = Settings(key='default_topic_quota', value='30')
            db.session.add(default_quota_setting)
            db.session.commit()
        default_quota = _default_topic_quota()

        Topic.query.filter(or_(Topic.quota.is_(None), Topic.quota <= 0)).update(
            {'quota': default_quota},
            synchronize_session=False
        )
        TopicIdea.query.filter(or_(TopicIdea.quota.is_(None), TopicIdea.quota <= 0)).update(
            {'quota': default_quota},
            synchronize_session=False
        )
        db.session.commit()

        if SiteTheme.query.count() == 0:
            site_theme = SiteTheme(theme_key=DEFAULT_SITE_THEME['theme_key'], name=DEFAULT_SITE_THEME['name'], is_active=True)
            for field, value in DEFAULT_SITE_THEME.items():
                if field in {'theme_key', 'name'}:
                    continue
                setattr(site_theme, field, value)
            db.session.add(site_theme)
            db.session.commit()
        elif not SiteTheme.query.filter_by(is_active=True).first():
            first_theme = SiteTheme.query.order_by(SiteTheme.id.asc()).first()
            if first_theme:
                first_theme.is_active = True
                db.session.commit()

        home_page_config = SitePageConfig.query.filter_by(page_key=DEFAULT_HOME_PAGE_CONFIG['page_key']).first()
        if not home_page_config:
            home_page_config = SitePageConfig(
                page_key=DEFAULT_HOME_PAGE_CONFIG['page_key'],
                site_name=DEFAULT_HOME_PAGE_CONFIG['site_name'],
                page_title=DEFAULT_HOME_PAGE_CONFIG['page_title'],
                hero_badge=DEFAULT_HOME_PAGE_CONFIG['hero_badge'],
                hero_title=DEFAULT_HOME_PAGE_CONFIG['hero_title'],
                hero_subtitle=DEFAULT_HOME_PAGE_CONFIG['hero_subtitle'],
                announcement_title=DEFAULT_HOME_PAGE_CONFIG['announcement_title'],
                trend_title=DEFAULT_HOME_PAGE_CONFIG['trend_title'],
                primary_section_title=DEFAULT_HOME_PAGE_CONFIG['primary_section_title'],
                primary_section_icon=DEFAULT_HOME_PAGE_CONFIG['primary_section_icon'],
                secondary_section_title=DEFAULT_HOME_PAGE_CONFIG['secondary_section_title'],
                secondary_section_icon=DEFAULT_HOME_PAGE_CONFIG['secondary_section_icon'],
                primary_topic_limit=DEFAULT_HOME_PAGE_CONFIG['primary_topic_limit'],
                footer_text=DEFAULT_HOME_PAGE_CONFIG['footer_text'],
                nav_items=json.dumps(DEFAULT_SITE_NAV_ITEMS, ensure_ascii=False),
            )
            db.session.add(home_page_config)
            db.session.commit()
        elif not home_page_config.nav_items:
            home_page_config.nav_items = json.dumps(DEFAULT_SITE_NAV_ITEMS, ensure_ascii=False)
            db.session.commit()

        # 如果没有活动，创建默认活动
        if Activity.query.count() == 0:
            activity = Activity(
                name='第1期',
                title='福瑞医科小红书任务第一期',
                description='邀请员工参与小红书推广任务',
                status='published'
            )
            db.session.add(activity)
            db.session.commit()

            # 添加示例话题
            topics = [
                {'topic_name': 'FibroScan肝纤维化检测', 'keywords': 'FibroScan,肝纤维化,肝脏健康', 'direction': '分享FibroScan检测体验', 'quota': default_quota, 'group_num': '第一组'},
                {'topic_name': '脂肪肝科普', 'keywords': '脂肪肝,肝脏健康,体检', 'direction': '科普脂肪肝知识', 'quota': default_quota, 'group_num': '第一组'},
                {'topic_name': '护肝片推荐', 'keywords': '护肝,肝脏保健,复方鳖甲', 'direction': '分享护肝产品', 'quota': default_quota, 'group_num': '第二组'},
            ]
            for t in topics:
                topic = Topic(activity_id=activity.id, **t)
                db.session.add(topic)
            db.session.commit()
            print("数据库初始化完成")


if __name__ == '__main__':
    init_db()
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', '5000')),
        debug=_env_flag('FLASK_DEBUG', False)
    )
