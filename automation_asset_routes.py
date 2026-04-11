import json

from flask import jsonify, request

from models import AssetGenerationTask, AssetLibrary, AutomationSchedule, DataSourceTask


def register_automation_asset_routes(app, helpers):
    admin_json_guard = helpers['admin_json_guard']
    safe_int = helpers['safe_int']
    serialize_asset_generation_task = helpers['serialize_asset_generation_task']
    serialize_asset_library_item = helpers['serialize_asset_library_item']
    serialize_automation_schedule = helpers['serialize_automation_schedule']
    pool_status_label = helpers['pool_status_label']
    current_actor = helpers['current_actor']
    load_json_value = helpers['load_json_value']
    dispatch_asset_generation = helpers['dispatch_asset_generation']
    dispatch_hotword_sync = helpers['dispatch_hotword_sync']
    dispatch_automation_schedule = helpers['dispatch_automation_schedule']
    log_operation = helpers['log_operation']
    db = helpers['db']
    datetime = helpers['datetime']
    normalize_quota = helpers['normalize_quota']

    @app.route('/api/admin/assets/tasks')
    def list_asset_generation_tasks():
        guard = admin_json_guard()
        if guard:
            return guard

        status = (request.args.get('status') or '').strip()
        source_provider = (request.args.get('source_provider') or '').strip()
        limit = min(max(safe_int(request.args.get('limit'), 20), 1), 100)
        query = AssetGenerationTask.query
        if status:
            query = query.filter_by(status=status)
        if source_provider:
            query = query.filter_by(source_provider=source_provider)

        items = query.order_by(AssetGenerationTask.created_at.desc(), AssetGenerationTask.id.desc()).limit(limit).all()
        return jsonify({
            'success': True,
            'items': [serialize_asset_generation_task(item) for item in items]
        })

    @app.route('/api/admin/assets/library')
    def list_asset_library():
        guard = admin_json_guard()
        if guard:
            return guard

        library_type = (request.args.get('library_type') or '').strip()
        pool_status = (request.args.get('pool_status') or '').strip()
        source_provider = (request.args.get('source_provider') or '').strip()
        keyword = (request.args.get('keyword') or '').strip()
        limit = min(max(safe_int(request.args.get('limit'), 30), 1), 100)

        query = AssetLibrary.query
        if library_type:
            query = query.filter_by(library_type=library_type)
        if pool_status:
            query = query.filter_by(pool_status=pool_status)
        if source_provider:
            query = query.filter_by(source_provider=source_provider)
        if keyword:
            query = query.filter(
                (AssetLibrary.title.contains(keyword)) |
                (AssetLibrary.subtitle.contains(keyword)) |
                (AssetLibrary.tags.contains(keyword))
            )

        items = query.order_by(AssetLibrary.created_at.desc(), AssetLibrary.id.desc()).limit(limit).all()
        return jsonify({
            'success': True,
            'items': [serialize_asset_library_item(item) for item in items]
        })

    @app.route('/api/admin/assets/library', methods=['POST'])
    def save_asset_library_item():
        guard = admin_json_guard()
        if guard:
            return guard

        data = request.json or {}
        library_type = (data.get('library_type') or 'content').strip()
        if library_type not in {'generated', 'product', 'content'}:
            return jsonify({'success': False, 'message': '不支持的图库类型'})

        title = (data.get('title') or '').strip()
        preview_url = (data.get('preview_url') or '').strip()
        if not title:
            return jsonify({'success': False, 'message': '资产标题不能为空'})
        if not preview_url:
            return jsonify({'success': False, 'message': '预览链接不能为空'})

        item = AssetLibrary(
            library_type=library_type,
            asset_type=(data.get('asset_type') or '知识卡片').strip()[:50],
            title=title[:200],
            subtitle=(data.get('subtitle') or '').strip()[:300],
            source_provider=(data.get('source_provider') or 'manual_upload').strip()[:50],
            model_name=(data.get('model_name') or '').strip()[:100],
            pool_status=(data.get('pool_status') or 'reserve').strip()[:20],
            status='active',
            tags=(data.get('tags') or '').strip()[:300],
            prompt_text=(data.get('prompt_text') or '').strip(),
            preview_url=preview_url,
            download_name=(data.get('download_name') or '').strip()[:200],
            raw_payload=json.dumps({
                'manual': True,
                'library_type': library_type,
                'preview_url': preview_url,
            }, ensure_ascii=False),
        )
        db.session.add(item)
        db.session.flush()
        log_operation('create', 'asset_library', target_id=item.id, message='手工新增图片资产', detail={
            'title': item.title,
            'library_type': item.library_type,
            'asset_type': item.asset_type,
            'pool_status': item.pool_status,
        })
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '图片资产已入库',
            'item': serialize_asset_library_item(item)
        })

    @app.route('/api/admin/assets/library/export')
    def export_asset_library():
        guard = admin_json_guard()
        if guard:
            return guard

        library_type = (request.args.get('library_type') or '').strip()
        pool_status = (request.args.get('pool_status') or '').strip()
        source_provider = (request.args.get('source_provider') or '').strip()
        keyword = (request.args.get('keyword') or '').strip()

        query = AssetLibrary.query
        if library_type:
            query = query.filter_by(library_type=library_type)
        if pool_status:
            query = query.filter_by(pool_status=pool_status)
        if source_provider:
            query = query.filter_by(source_provider=source_provider)
        if keyword:
            query = query.filter(
                (AssetLibrary.title.contains(keyword)) |
                (AssetLibrary.subtitle.contains(keyword)) |
                (AssetLibrary.tags.contains(keyword))
            )

        items = query.order_by(AssetLibrary.created_at.desc(), AssetLibrary.id.desc()).all()
        rows = ['图库类型,资产类型,标题,副标题,来源提供方,模型,池状态,标签,预览链接,创建时间']
        for item in items:
            serialized = serialize_asset_library_item(item)
            rows.append(','.join([
                (serialized.get('library_type_label') or '').replace(',', ' '),
                (serialized.get('asset_type') or '').replace(',', ' '),
                (serialized.get('title') or '').replace(',', ' '),
                (serialized.get('subtitle') or '').replace(',', ' '),
                (serialized.get('source_provider') or '').replace(',', ' '),
                (serialized.get('model_name') or '').replace(',', ' '),
                (serialized.get('pool_status_label') or '').replace(',', ' '),
                (serialized.get('tags') or '').replace(',', ' '),
                (serialized.get('preview_url') or '').replace(',', ' '),
                (serialized.get('created_at') or '').replace(',', ' '),
            ]))

        log_operation('export', 'asset_library', message='导出图片资产库', detail={
            'library_type': library_type,
            'pool_status': pool_status,
            'source_provider': source_provider,
            'keyword': keyword,
            'count': len(items),
        })
        db.session.commit()
        content = '\n'.join(rows)
        return content, 200, {
            'Content-Type': 'text/csv; charset=utf-8',
            'Content-Disposition': 'attachment; filename=asset_library.csv'
        }

    @app.route('/api/admin/assets/library/<int:item_id>')
    def asset_library_detail(item_id):
        guard = admin_json_guard()
        if guard:
            return guard

        item = AssetLibrary.query.get_or_404(item_id)
        return jsonify({
            'success': True,
            'item': serialize_asset_library_item(item, detail=True)
        })

    @app.route('/api/admin/assets/library/<int:item_id>/pool_status', methods=['POST'])
    def update_asset_library_pool_status(item_id):
        guard = admin_json_guard()
        if guard:
            return guard

        payload = request.json or {}
        pool_status = (payload.get('pool_status') or '').strip()
        if pool_status not in {'reserve', 'candidate', 'formal', 'archived'}:
            return jsonify({'success': False, 'message': '不支持的资产池状态'})

        item = AssetLibrary.query.get_or_404(item_id)
        item.pool_status = pool_status
        if pool_status == 'archived':
            item.status = 'archived'
        elif item.status == 'archived':
            item.status = 'active'
        log_operation('move_pool', 'asset_library', target_id=item.id, message='更新图片资产池状态', detail={
            'title': item.title,
            'pool_status': pool_status,
        })
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'图片资产已移动到{pool_status_label(pool_status)}',
            'item': serialize_asset_library_item(item)
        })

    @app.route('/api/admin/assets/tasks/<int:task_id>')
    def admin_asset_generation_task_detail(task_id):
        guard = admin_json_guard()
        if guard:
            return guard

        task = AssetGenerationTask.query.get_or_404(task_id)
        return jsonify({
            'success': True,
            'item': serialize_asset_generation_task(task, detail=True),
        })

    @app.route('/api/admin/assets/tasks/<int:task_id>/retry', methods=['POST'])
    def retry_asset_generation_task(task_id):
        guard = admin_json_guard()
        if guard:
            return guard

        task = AssetGenerationTask.query.get_or_404(task_id)
        payload = {
            'registration_id': task.registration_id,
            'selected_content': task.selected_content or '',
            'style_preset': task.style_preset or '小红书图文',
            'image_count': task.image_count or 3,
            'title_hint': task.title_hint or '',
        }
        try:
            dispatched = dispatch_asset_generation(payload, actor=current_actor())
        except ValueError as exc:
            return jsonify({'success': False, 'message': str(exc)})
        return jsonify({
            'success': True,
            'message': '已重新派发图片生成任务',
            'task_id': dispatched['task_id'],
            'asset_task_id': dispatched['task_record'].id,
        })

    @app.route('/api/asset_tasks/<int:task_id>')
    def asset_generation_task_detail(task_id):
        task = AssetGenerationTask.query.get_or_404(task_id)
        registration_id = safe_int(request.args.get('registration_id'), 0)
        if task.registration_id:
            if not registration_id or task.registration_id != registration_id:
                return jsonify({'success': False, 'message': '任务归属不匹配'}), 403
        return jsonify({
            'success': True,
            'item': serialize_asset_generation_task(task)
        })

    @app.route('/api/admin/data-source-tasks/<int:task_id>/retry', methods=['POST'])
    def retry_data_source_task(task_id):
        guard = admin_json_guard()
        if guard:
            return guard

        task = DataSourceTask.query.get_or_404(task_id)
        payload = load_json_value(task.params_payload, {})
        payload['source_platform'] = payload.get('source_platform') or task.source_platform or '小红书'
        payload['source_channel'] = payload.get('source_channel') or task.source_channel or 'Worker骨架'
        payload['mode'] = payload.get('mode') or task.mode or 'skeleton'
        payload['batch_name'] = f"{task.batch_name or 'retry'}_retry_{datetime.now().strftime('%H%M%S')}"
        dispatched = dispatch_hotword_sync(payload, actor=current_actor())
        return jsonify({
            'success': True,
            'message': '已重新派发热点抓取任务',
            'task_id': dispatched['task_id'],
            'data_source_task_id': dispatched['task_record'].id,
        })

    @app.route('/api/admin/schedules')
    def list_automation_schedules():
        guard = admin_json_guard()
        if guard:
            return guard

        items = AutomationSchedule.query.order_by(AutomationSchedule.id.asc()).all()
        return jsonify({
            'success': True,
            'items': [serialize_automation_schedule(item) for item in items]
        })

    @app.route('/api/admin/schedules/<int:schedule_id>', methods=['POST'])
    def save_automation_schedule(schedule_id):
        guard = admin_json_guard()
        if guard:
            return guard

        schedule = AutomationSchedule.query.get_or_404(schedule_id)
        data = request.json or {}
        previous_enabled = bool(schedule.enabled)
        schedule.enabled = helpers['coerce_bool'](data.get('enabled'))
        schedule.interval_minutes = min(max(safe_int(data.get('interval_minutes'), schedule.interval_minutes or 60), 1), 10080)
        params_payload = data.get('params_payload')
        if isinstance(params_payload, dict):
            schedule.params_payload = json.dumps(params_payload, ensure_ascii=False)
        if schedule.enabled and (not previous_enabled or not schedule.next_run_at):
            schedule.next_run_at = helpers['next_schedule_time'](schedule.interval_minutes)
        if not schedule.enabled:
            schedule.last_status = 'paused'
            schedule.last_message = '已暂停自动调度'
        log_operation('save_schedule', 'automation_schedule', target_id=schedule.id, message='更新自动化调度配置', detail={
            'job_key': schedule.job_key,
            'enabled': bool(schedule.enabled),
            'interval_minutes': schedule.interval_minutes,
        })
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '调度配置已保存',
            'item': serialize_automation_schedule(schedule),
        })

    @app.route('/api/admin/schedules/<int:schedule_id>/run', methods=['POST'])
    def run_automation_schedule(schedule_id):
        guard = admin_json_guard()
        if guard:
            return guard

        schedule = AutomationSchedule.query.get_or_404(schedule_id)
        try:
            dispatched = dispatch_automation_schedule(schedule, actor=current_actor())
        except ValueError as exc:
            return jsonify({'success': False, 'message': str(exc)})
        return jsonify({
            'success': True,
            'message': '已立即执行调度任务',
            'task_id': dispatched.get('task_id', ''),
            'item': serialize_automation_schedule(schedule),
        })
