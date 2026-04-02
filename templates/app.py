#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小红书任务管理系统 v4.0 - 福瑞医科
完全基于需求定制开发
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
import json
from datetime import datetime, timedelta
import random

app = Flask(__name__)
app.secret_key = 'xhs_furui_2026_secret_key'

# 配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "xhs_system.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_AS_ASCII'] = False

db = SQLAlchemy(app)
CORS(app)

# ==================== 数据库模型 ====================

# 活动期数
class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))  # 第1期、第2期等
    title = db.Column(db.String(200))  # 活动标题
    description = db.Column(db.Text)  # 活动描述
    status = db.Column(db.String(20), default='draft')  # draft, published, closed
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    topics = db.relationship('Topic', backref='activity', lazy=True)

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
    quota = db.Column(db.Integer, default=0)  # 名额上限
    group_num = db.Column(db.String(50))  # 组号
    filled = db.Column(db.Integer, default=0)  # 已报名人数
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
    xhs_link = db.Column(db.String(500))  # 小红书链接
    content_screenshot = db.Column(db.Text)  # 正文截图
    likes = db.Column(db.Integer, default=0)  # 点赞数
    favorites = db.Column(db.Integer, default=0)  # 收藏数
    comments = db.Column(db.Integer, default=0)  # 评论数
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    keyword_check = db.Column(db.Boolean, default=False)  # 关键词检查
    created_at = db.Column(db.DateTime, default=datetime.now)

# 系统设置
class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True)
    value = db.Column(db.Text)

# ==================== 路由 ====================

@app.route('/')
def index():
    # 获取当前活动
    activity = Activity.query.filter_by(status='published').order_by(Activity.created_at.desc()).first()
    if not activity:
        activities = Activity.query.order_by(Activity.created_at.desc()).all()
        if activities:
            activity = activities[0]
    return render_template('index.html', activity=activity)

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
    # 如果有reg_id参数，显示报名成功页面（带一键生成文案）
    reg_id = request.args.get('reg_id')
    if reg_id:
        reg = Registration.query.get(int(reg_id))
        if reg:
            return render_template('register_success.html', registration=reg)
    
    if request.method == 'POST':
        group_num = request.form.get('group_num')
        name = request.form.get('name')
        
        reg = Registration.query.filter_by(group_num=group_num, name=name).first()
        if reg:
            # 使用报名成功页面模板（带一键生成文案功能）
            return render_template('register_success.html', registration=reg)
        else:
            return render_template('my_registration.html', error='未找到报名信息')
    
    return render_template('my_registration.html')

@app.route('/api/topics/<int:activity_id>')
def get_topics(activity_id):
    topics = Topic.query.filter_by(activity_id=activity_id).all()
    return jsonify([{
        'id': t.id,
        'topic_name': t.topic_name,
        'keywords': t.keywords,
        'direction': t.direction,
        'quota': t.quota,
        'filled': t.filled,
        'group_num': t.group_num,
        'available': t.quota - t.filled
    } for t in topics])

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
DEEPSEEK_API_URL = 'https://api.deepseek.com/v1/chat/completions'

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
    
    reg = Registration.query.get(registration_id)
    if not reg:
        return jsonify({'success': False, 'message': '报名信息不存在'})
    
    topic = reg.topic
    
    # 获取话题信息
    keywords = topic.keywords or ""
    direction = topic.direction or ""
    writing_example = topic.writing_example or ""
    
    # 获取小红书热门参考
    xhs_notes = fetch_xhs_trending(keywords)
    xhs_ref = ""
    if xhs_notes:
        for i, note in enumerate(xhs_notes):
            title = note.get('note_card', {}).get('title', '')[:50]
            user = note.get('note_card', {}).get('user', {}).get('nickname', '')
            if title:
                xhs_ref += f"\n参考{i+1}: {title} (作者:{user})"
    
    # 判断产品类型
    if '体检' in topic.topic_name or 'FibroScan' in topic.topic_name:
        product = "FibroScan肝脏弹性检测"
    else:
        product = "鳖甲软肝片"
    
    # 生成提示词 - 小红书爆款逻辑
    prompt = f"""你是一个小红书爆款文案专家。请根据以下信息生成3版小红书种草文案：

话题：{topic.topic_name}
关键词：{keywords}
撰写说明：{direction}
撰写示例：{writing_example}
{xhs_ref}

产品：{product}

要求：
1. **极度生活化**：就像你真的在跟朋友聊天分享，语气自然亲切，像真人发的朋友圈
2. **避免AI感**：不要用"首先""其次""综上所述"这种套路句式，用"诶""真的""绝了""你们懂吗"这种口语
3. **细节真实**：可以加一些生活细节，比如"昨天带爸妈去""正好碰到""随口问了医生一句"
4. **符合小红书风格**：
   - 标题要吸引人但不做作
   - 中间加一些真实的小故事或经历
   - 结尾引导互动
5. **软植入产品**：自然提到产品，不要硬广
6. **合规**：不用"最好""第一""最有效"等绝对化用语

请直接输出3版完全生活化的文案，用"===版本N==="分隔"""

    # 调用DeepSeek API
    versions = []
    try:
        if DEEPSEEK_API_KEY:
            headers = {'Authorization': f'Bearer {DEEPSEEK_API_KEY}', 'Content-Type': 'application/json'}
            payload = {
                'model': 'deepseek-chat',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.8
            }
            resp = requests.post(DEEPSEEK_API_URL, json=payload, headers=headers, timeout=30)
            if resp.status_code == 200:
                result = resp.json()
                content = result['choices'][0]['message']['content']
                # 解析3个版本
                parts = content.split('===版本')
                for p in parts:
                    if p.strip():
                        version_text = p.strip()
                        if version_text[0].isdigit():
                            version_text = version_text[1:].strip()
                        if version_text.strip():
                            versions.append(version_text)
        else:
            raise Exception('No API key')
    except Exception as e:
        print(f"DeepSeek API error: {e}")
        # 如果API调用失败，使用本地生成
        versions = generate_local_copy(topic, keywords, product)
    
    if not versions:
        versions = generate_local_copy(topic, keywords, product)
    
    return jsonify({
        'success': True,
        'versions': versions,
        'reg_id': registration_id
    })

def generate_local_copy(topic, keywords, product):
    """本地生成文案（无API时使用）"""
    import random
    
    hooks = [
        "后悔没早点知道...",
        "花了冤枉钱才总结出...",
        "所有父母必须看！",
        "这个坑千万别踩！",
        "90%的人都搞错了..."
    ]
    
    interactions = [
        "你们也有这种情况吗？评论区说说",
        "你们觉得怎么样？求支招",
        "你们还有什么想问的？",
        "你们觉得哪个更靠谱？投票",
        "有同样经历的姐妹吗？评论区见"
    ]
    
    versions = []
    for i in range(3):
        hook = random.choice(hooks)
        inter = random.choice(interactions)
        
        if '体检' in topic.topic_name:
            version = f"""【标题】{hook}带父母体检项目怎么选？看这篇就够了！

【正文】
每年带爸妈体检都一头雾水？我花了3年才搞明白！

✅ 必做项目清单：
1. 肝功能检查
2. FibroScan肝脏弹性检测（这个很多人忽略！）
3. 血常规、尿常规
4. 肿瘤标志物

💡 小贴士：提前预约可以少排队~

{inter}

#父母体检 #体检必做项目 #带父母体检 #体检经验"""
        else:
            version = f"""【标题】{hook}肝纤维化逆转分享！

【正文】
查出肝纤维化后整个人都慌了...后来找到了方法！

吃了段时间，配合检查，真的有改善！

✅ 经验分享：
1. 遵医嘱用药
2. 定期复查FibroScan
3. 注意饮食作息

{inter}

#肝纤维化 #肝脏健康 #养生调理"""
        
        versions.append(version)
    
    return versions

# 合规检查API
@app.route('/api/check_compliance', methods=['POST'])
def check_compliance():
    data = request.json
    content = data.get('content', '')
    
    # 合规关键词检查
    forbidden_words = ['最好', '第一', '最有效', '根治', '治愈', '特效', '保证', '绝对', '100%', '最先进']
    warnings = []
    
    for word in forbidden_words:
        if word in content:
            warnings.append(f'包含绝对化用语：{word}')
    
    # 三品一械检查
    if any(k in content for k in ['药品', '药', '治疗', '疗效', '治病']):
        if any(k in content for k in ['最好', '最有效', '根治', '治愈']):
            warnings.append('涉及药品功效需谨慎表述')
    
    return jsonify({
        'success': True,
        'passed': len(warnings) == 0,
        'warnings': warnings
    })

@app.route('/api/submit', methods=['POST'])
def submit_data():
    data = request.json
    reg = Registration.query.get(data.get('registration_id'))
    
    if not reg:
        return jsonify({'success': False, 'message': '报名信息不存在'})
    
    # 检查关键词
    topic = reg.topic
    keywords = topic.keywords.split(',') if topic.keywords else []
    link = data.get('xhs_link', '')
    keyword_check = any(k.strip() in link for k in keywords if k.strip())
    
    submission = Submission(
        registration_id=reg.id,
        xhs_link=data.get('xhs_link'),
        likes=data.get('likes', 0),
        favorites=data.get('favorites', 0),
        comments=data.get('comments', 0),
        keyword_check=keyword_check
    )
    db.session.add(submission)
    reg.status = 'submitted'
    db.session.commit()
    
    return jsonify({'success': True, 'message': '提交成功'})

@app.route('/data_analysis')
def data_analysis():
    activities = Activity.query.order_by(Activity.created_at.desc()).all()
    return render_template('data_analysis.html', activities=activities)

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
    topics = Topic.query.filter_by(activity_id=activity_id).all()
    topic_ids = [t.id for t in topics]
    
    registrations = Registration.query.filter(Registration.topic_id.in_(topic_ids)).all()
    submissions = Submission.query.join(Registration).filter(
        Registration.topic_id.in_(topic_ids)
    ).all()
    
    total_registrations = len(registrations)
    total_published = len([r for r in registrations if r.status == 'submitted'])
    total_likes = sum(s.likes for s in submissions)
    total_favorites = sum(s.favorites for s in submissions)
    total_comments = sum(s.comments for s in submissions)
    total_interactions = total_likes + total_favorites + total_comments
    
    # 各组报名统计
    group_stats = {}
    for reg in registrations:
        g = reg.group_num
        if g not in group_stats:
            group_stats[g] = {'count': 0, 'published': 0}
        group_stats[g]['count'] += 1
        if reg.status == 'submitted':
            group_stats[g]['published'] += 1
    
    return jsonify({
        'total_registrations': total_registrations,
        'total_published': total_published,
        'total_likes': total_likes,
        'total_favorites': total_favorites,
        'total_comments': total_comments,
        'total_interactions': total_interactions,
        'group_stats': group_stats
    })

@app.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    activities = Activity.query.order_by(Activity.created_at.desc()).all()
    return render_template('admin.html', activities=activities)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == 'furui' and password == 'wangdandan39':
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        else:
            return render_template('admin_login.html', error='用户名或密码错误')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
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
    db.session.commit()
    
    return jsonify({'success': True, 'message': '活动创建成功'})

@app.route('/admin/topic/add', methods=['POST'])
def add_topic():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': '未登录'})
    
    topic = Topic(
        activity_id=request.form.get('activity_id'),
        topic_name=request.form.get('topic_name'),
        keywords=request.form.get('keywords'),
        direction=request.form.get('direction'),
        reference_content=request.form.get('reference_content'),
        reference_link=request.form.get('reference_link'),
        quota=int(request.form.get('quota', 0)),
        group_num=request.form.get('group_num')
    )
    db.session.add(topic)
    db.session.commit()
    
    return jsonify({'success': True, 'message': '话题创建成功'})

@app.route('/admin/activity/<int:activity_id>/publish')
def publish_activity(activity_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': '未登录'})
    
    activity = Activity.query.get(activity_id)
    activity.status = 'published'
    db.session.commit()
    
    return jsonify({'success': True, 'message': '发布成功'})

@app.route('/admin/export/<int:activity_id>')
def export_data(activity_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    topics = Topic.query.filter_by(activity_id=activity_id).all()
    topic_ids = [t.id for t in topics]
    
    registrations = Registration.query.filter(Registration.topic_id.in_(topic_ids)).all()
    
    # 生成CSV
    csv_content = "姓名,小组号,小红书账号,联系方式,话题,小红书链接,点赞,收藏,评论,互动总数\n"
    for reg in registrations:
        topic = reg.topic
        sub = reg.submission
        total = (sub.likes + sub.favorites + sub.comments) if sub else 0
        link = sub.xhs_link if sub else ''
        csv_content += f"{reg.name},{reg.group_num},{reg.xhs_account},{reg.phone},{topic.topic_name},{link},{sub.likes if sub else 0},{sub.favorites if sub else 0},{sub.comments if sub else 0},{total}\n"
    
    return csv_content, 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': f'attachment; filename=activity_{activity_id}_data.csv'
    }

# ==================== 初始化 ====================

def init_db():
    with app.app_context():
        db.create_all()
        
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
                {'topic_name': 'FibroScan肝纤维化检测', 'keywords': 'FibroScan,肝纤维化,肝脏健康', 'direction': '分享FibroScan检测体验', 'quota': 20, 'group_num': '第一组'},
                {'topic_name': '脂肪肝科普', 'keywords': '脂肪肝,肝脏健康,体检', 'direction': '科普脂肪肝知识', 'quota': 20, 'group_num': '第一组'},
                {'topic_name': '护肝片推荐', 'keywords': '护肝,肝脏保健,复方鳖甲', 'direction': '分享护肝产品', 'quota': 20, 'group_num': '第二组'},
            ]
            for t in topics:
                topic = Topic(activity_id=activity.id, **t)
                db.session.add(topic)
            db.session.commit()
            print("数据库初始化完成")

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
