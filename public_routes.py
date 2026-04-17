from flask import jsonify, render_template, request

from models import Activity, AssetLibrary, CorpusEntry, Registration, Submission, Topic, TrendNote


def register_public_routes(app, helpers):
    build_public_shell_context = helpers['build_public_shell_context']
    build_registration_tracking_summary = helpers['build_registration_tracking_summary']
    serialize_topic = helpers['serialize_topic']
    serialize_announcement = helpers['serialize_announcement']
    list_announcements = helpers['list_announcements']
    serialize_site_page_config = helpers['serialize_site_page_config']
    serialize_site_theme = helpers['serialize_site_theme']
    get_site_page_config = helpers['get_site_page_config']
    get_active_site_theme = helpers['get_active_site_theme']
    normalize_quota = helpers['normalize_quota']
    default_home_page_config = helpers['default_home_page_config']
    default_site_nav_items = helpers['default_site_nav_items']
    asset_style_type_options = helpers['asset_style_type_options']
    validate_required_platform_data = helpers['validate_required_platform_data']
    validate_partial_platform_data = helpers['validate_partial_platform_data']
    auto_detect_content_type = helpers['auto_detect_content_type']
    sync_tracking_from_submission = helpers['sync_tracking_from_submission']
    db = helpers['db']
    datetime = helpers['datetime']

    def build_public_context():
        context = dict(build_public_shell_context())
        site_config = dict(context.get('site_config') or {})
        nav_items = [dict(item) for item in (site_config.get('nav_items') or [dict(item) for item in default_site_nav_items])]
        has_image_library = any(
            (item.get('label') or '').strip() == '图片库' or (item.get('url') or '').strip() == '/image-library'
            for item in nav_items
        )
        if not has_image_library:
            insert_at = next(
                (index + 1 for index, item in enumerate(nav_items) if (item.get('label') or '').strip() == '数据分析'),
                min(len(nav_items), 3),
            )
            nav_items.insert(insert_at, {
                'label': '图片库',
                'url': '/image-library',
                'icon': 'bi-images',
                'target': '_self',
            })
        site_config['nav_items'] = nav_items[:8]
        context['site_config'] = site_config
        return context

    def serialize_public_trend(note):
        return {
            'id': note.id,
            'title': note.title or '',
            'keyword': note.keyword or '',
            'source_platform': note.source_platform or '',
            'source_channel': note.source_channel or '',
            'author': note.author or '',
            'views': note.views or 0,
            'likes': note.likes or 0,
            'favorites': note.favorites or 0,
            'comments': note.comments or 0,
            'summary': note.summary or '',
            'link': note.link or '',
            'created_at': note.created_at.strftime('%Y-%m-%d %H:%M:%S') if note.created_at else '',
        }

    def serialize_public_asset(item):
        tags = [part.strip() for part in (item.tags or '').split(',') if part.strip()]
        library_type_label_map = {
            'generated': '生成资产',
            'product': '产品图库',
            'content': '内容素材库',
            'reference': '风格参考库',
        }
        return {
            'id': item.id,
            'title': item.title or '未命名图片',
            'subtitle': item.subtitle or '',
            'preview_url': item.preview_url or '',
            'product_name': item.product_name or '',
            'product_category': item.product_category or '',
            'product_indication': item.product_indication or '',
            'library_type': library_type_label_map.get(item.library_type or 'generated', item.library_type or '生成资产'),
            'asset_type': item.asset_type or '',
            'style_type_key': item.style_type_key or '',
            'visual_role': item.visual_role or '',
            'source_provider': item.source_provider or '',
            'download_name': item.download_name or '',
            'tags': tags[:8],
            'created_at': item.created_at.strftime('%Y-%m-%d %H:%M:%S') if item.created_at else '',
        }

    def serialize_public_corpus(entry):
        tags = [part.strip() for part in (entry.tags or '').split(',') if part.strip()]
        return {
            'id': entry.id,
            'title': entry.title or '未命名科普内容',
            'category': entry.category or '医学科普',
            'source': entry.source or '',
            'content': entry.content or '',
            'tags': tags[:8],
            'created_at': entry.created_at.strftime('%Y-%m-%d %H:%M:%S') if entry.created_at else '',
        }

    def render_my_registration_page(registrations=None, error=''):
        registrations = registrations or []
        tracking_summaries = {
            reg.id: build_registration_tracking_summary(reg)
            for reg in registrations
        }
        return render_template(
            'my_registration.html',
            registrations=registrations,
            error=error,
            tracking_summaries=tracking_summaries,
            **build_public_context(),
        )

    @app.route('/')
    def index():
        activity = Activity.query.filter_by(status='published').order_by(Activity.created_at.desc()).first()
        if not activity:
            activities = Activity.query.order_by(Activity.created_at.desc()).all()
            if activities:
                activity = activities[0]

        public_context = build_public_context()
        site_config = dict(public_context.get('site_config') or {})
        site_theme = dict(public_context.get('site_theme') or {})

        split_index = normalize_quota(
            site_config.get('primary_topic_limit'),
            default=default_home_page_config['primary_topic_limit'],
            min_value=1,
            max_value=120,
        )
        all_topics = list(activity.topics) if activity else []
        primary_topics = all_topics[:split_index]
        secondary_topics = all_topics[split_index:]
        first_available_topic = next((topic for topic in all_topics if (topic.filled or 0) < (topic.quota or 0)), None)
        announcement_count = len(list_announcements())
        trend_note_count = TrendNote.query.count()

        hero_title = (site_config.get('hero_title') or '').strip() or (activity.title if activity else '')
        hero_subtitle = (site_config.get('hero_subtitle') or '').strip() or (activity.description if activity else '')
        hero_badge = (site_config.get('hero_badge') or '').strip() or (activity.name if activity else '内容运营平台')

        return render_template(
            'index.html',
            activity=activity,
            primary_topics=primary_topics,
            secondary_topics=secondary_topics,
            first_available_topic=first_available_topic,
            announcement_count=announcement_count,
            trend_note_count=trend_note_count,
            site_config={
                **site_config,
                'hero_title': hero_title,
                'hero_subtitle': hero_subtitle,
                'hero_badge': hero_badge,
            },
            site_theme=site_theme,
        )

    @app.route('/announcements')
    def announcement_list():
        context = build_public_context()
        items = [serialize_announcement(item) for item in list_announcements()]
        return render_template(
            'public_collection.html',
            page_title='在线公告',
            page_heading='在线公告',
            page_description='查看当前正在生效的公告、通知和活动说明。',
            page_badge='公告中心',
            page_kind='announcement',
            items=items,
            empty_message='当前还没有生效中的公告。',
            **context,
        )

    @app.route('/trends')
    def trend_list():
        context = build_public_context()
        items = [
            serialize_public_trend(note)
            for note in TrendNote.query.order_by(TrendNote.created_at.desc(), TrendNote.id.desc()).limit(40).all()
        ]
        return render_template(
            'public_collection.html',
            page_title='热点速览',
            page_heading='热点速览',
            page_description='集中查看热点池里最近入库的热点和互动数据。',
            page_badge='热点池',
            page_kind='trend',
            items=items,
            empty_message='热点池暂时为空，可以稍后再看。',
            **context,
        )

    @app.route('/liver-science')
    def liver_science():
        context = build_public_context()
        items = CorpusEntry.query.filter_by(status='active').filter(
            CorpusEntry.category.in_(['医学科普', '合规表达'])
        ).order_by(
            CorpusEntry.usage_count.desc(),
            CorpusEntry.updated_at.desc(),
            CorpusEntry.id.desc(),
        ).limit(24).all()
        if not items:
            items = CorpusEntry.query.filter_by(status='active').order_by(
                CorpusEntry.usage_count.desc(),
                CorpusEntry.updated_at.desc(),
                CorpusEntry.id.desc(),
            ).limit(24).all()

        return render_template(
            'public_collection.html',
            page_title='肝病科普',
            page_heading='肝病科普',
            page_description='集中查看适合前台用户浏览的肝病知识、检查解读和常见误区说明。',
            page_badge='健康知识',
            page_kind='science',
            items=[serialize_public_corpus(item) for item in items],
            empty_message='当前还没有可展示的科普内容。',
            **context,
        )

    @app.route('/image-library')
    def public_image_library():
        context = build_public_context()
        base_query = AssetLibrary.query.filter_by(status='active').filter(
            AssetLibrary.preview_url.isnot(None),
            AssetLibrary.preview_url != '',
        )
        items = base_query.filter_by(pool_status='formal').order_by(
            AssetLibrary.created_at.desc(),
            AssetLibrary.id.desc(),
        ).limit(60).all()
        visibility_note = '当前展示正式图片库内容。'
        if not items:
            items = base_query.filter(AssetLibrary.pool_status != 'archived').order_by(
                AssetLibrary.created_at.desc(),
                AssetLibrary.id.desc(),
            ).limit(60).all()
            visibility_note = '当前正式图片库为空，已临时展示非归档图片内容。'

        return render_template(
            'public_image_library.html',
            page_title='图片库',
            page_heading='图片库',
            page_description='集中查看可直接参考或下载的图片素材。',
            page_badge='内容素材',
            items=[serialize_public_asset(item) for item in items],
            visibility_note=visibility_note,
            **context,
        )

    @app.route('/topic/<int:topic_id>')
    def topic_detail(topic_id):
        topic = Topic.query.get_or_404(topic_id)
        return render_template('topic_detail.html', topic=topic, **build_public_context())

    @app.route('/register_success/<int:reg_id>')
    def register_success(reg_id):
        reg = Registration.query.get_or_404(reg_id)
        return render_template(
            'register_success.html',
            registration=reg,
            tracking_summary=build_registration_tracking_summary(reg),
            asset_style_types=asset_style_type_options(),
            **build_public_context(),
        )

    @app.route('/my_registration', methods=['GET', 'POST'])
    def my_registration():
        reg_id = request.args.get('reg_id')
        if reg_id:
            reg = Registration.query.get(int(reg_id))
            if reg:
                return render_my_registration_page(registrations=[reg])

        if request.method == 'POST':
            group_num = request.form.get('group_num')
            name = request.form.get('name')
            regs = Registration.query.filter_by(group_num=group_num, name=name).all()
            if regs:
                return render_my_registration_page(registrations=regs)
            return render_my_registration_page(error='未找到报名信息')

        return render_my_registration_page()

    @app.route('/api/topics/<int:activity_id>')
    def get_topics(activity_id):
        topics = Topic.query.filter_by(activity_id=activity_id).all()
        return jsonify([serialize_topic(topic) for topic in topics])

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
                'group_num': reg.group_num or '',
                'xhs_profile_link': reg.submission.xhs_profile_link if reg.submission and reg.submission.xhs_profile_link else '',
            }
        })

    @app.route('/api/register', methods=['POST'])
    def register():
        data = request.json
        topic = Topic.query.get(data.get('topic_id'))

        if not topic:
            return jsonify({'success': False, 'message': '话题不存在'})
        if topic.filled >= topic.quota:
            return jsonify({'success': False, 'message': '名额已满'})

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

    @app.route('/api/submit', methods=['POST'])
    def submit_data():
        data = request.json or {}
        reg = Registration.query.get(data.get('registration_id'))

        if not reg:
            return jsonify({'success': False, 'message': '报名信息不存在'})

        try:
            normalized = validate_required_platform_data(data)
        except ValueError as e:
            return jsonify({'success': False, 'message': str(e)})

        note_title = (data.get('note_title') or '').strip()
        note_content = (data.get('note_content') or '').strip()
        auto_type = auto_detect_content_type(f"{note_title} {note_content}", reg.topic.topic_name if reg and reg.topic else '')
        if note_title:
            normalized['note_title'] = note_title
        if note_content:
            normalized['note_content'] = note_content
        normalized['content_type'] = auto_type

        topic = reg.topic
        keywords = topic.keywords.split(',') if topic.keywords else []
        existing_submission = Submission.query.filter_by(registration_id=reg.id).first()
        xhs_for_check = normalized.get('xhs_link')
        if not xhs_for_check and existing_submission:
            xhs_for_check = existing_submission.xhs_link or ''
        keyword_check = any(k.strip() in (xhs_for_check or '') for k in keywords if k.strip())

        if existing_submission:
            for key, value in normalized.items():
                setattr(existing_submission, key, value)
            existing_submission.keyword_check = keyword_check
            existing_submission.created_at = datetime.now()
            submission = existing_submission
        else:
            submission = Submission(
                registration_id=reg.id,
                keyword_check=keyword_check,
                **normalized
            )
            db.session.add(submission)
            db.session.flush()

        tracking_summary = sync_tracking_from_submission(reg, submission, data)
        reg.status = 'submitted'
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '提交成功，已开启小红书账号持续跟踪' if tracking_summary.get('enabled') else '提交成功',
            'tracking': tracking_summary,
        })

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
            partial = validate_partial_platform_data(data, require_at_least_one_link=False)
        except ValueError as e:
            return jsonify({'success': False, 'message': str(e)})

        for key, value in partial.items():
            setattr(submission, key, value)

        note_title = (data.get('note_title') or '').strip()
        note_content = (data.get('note_content') or '').strip()
        if note_title:
            submission.note_title = note_title
        if note_content:
            submission.note_content = note_content
        if note_title or note_content or (submission.note_title or submission.note_content):
            submission.content_type = auto_detect_content_type(
                f"{submission.note_title or ''} {submission.note_content or ''}",
                reg.topic.topic_name if reg and reg.topic else '',
            )

        db.session.flush()
        tracking_summary = sync_tracking_from_submission(reg, submission, data)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '数据更新成功，账号持续跟踪已同步' if tracking_summary.get('enabled') else '数据更新成功',
            'tracking': tracking_summary,
        })
