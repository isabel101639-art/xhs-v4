import json
import os
import uuid
from collections import Counter, defaultdict

from flask import jsonify, request
from werkzeug.utils import secure_filename

from models import AssetGenerationTask, AssetLibrary, AssetPlanDraft, AutomationSchedule, DataSourceTask


def register_automation_asset_routes(app, helpers):
    admin_json_guard = helpers['admin_json_guard']
    safe_int = helpers['safe_int']
    serialize_asset_generation_task = helpers['serialize_asset_generation_task']
    serialize_asset_plan_draft = helpers['serialize_asset_plan_draft']
    serialize_asset_library_item = helpers['serialize_asset_library_item']
    serialize_automation_schedule = helpers['serialize_automation_schedule']
    pool_status_label = helpers['pool_status_label']
    current_actor = helpers['current_actor']
    load_json_value = helpers['load_json_value']
    dispatch_asset_generation = helpers['dispatch_asset_generation']
    dispatch_hotword_sync = helpers['dispatch_hotword_sync']
    dispatch_creator_account_sync = helpers['dispatch_creator_account_sync']
    dispatch_automation_schedule = helpers['dispatch_automation_schedule']
    build_asset_generation_plan_payload = helpers['build_asset_generation_plan_payload']
    build_batch_asset_plan_drafts = helpers['build_batch_asset_plan_drafts']
    build_asset_style_recommendation_payload = helpers['build_asset_style_recommendation_payload']
    log_operation = helpers['log_operation']
    db = helpers['db']
    datetime = helpers['datetime']
    normalize_quota = helpers['normalize_quota']
    product_profile_meta = helpers['product_profile_meta']
    product_profile_options = helpers['product_profile_options']
    allowed_upload_exts = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}

    def _asset_upload_dir():
        base_dir = os.path.join(app.static_folder, 'uploads', 'asset_library')
        os.makedirs(base_dir, exist_ok=True)
        return base_dir

    def _save_asset_upload(file_storage):
        raw_name = secure_filename(file_storage.filename or '') or 'asset'
        _, ext = os.path.splitext(raw_name.lower())
        if ext not in allowed_upload_exts:
            raise ValueError('仅支持 png/jpg/jpeg/webp/gif 图片文件')
        unique_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"
        upload_dir = _asset_upload_dir()
        abs_path = os.path.join(upload_dir, unique_name)
        file_storage.save(abs_path)
        rel_path = f"/static/uploads/asset_library/{unique_name}"
        return {
            'absolute_path': abs_path,
            'preview_url': rel_path,
            'download_name': raw_name[:200],
        }

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

    @app.route('/api/admin/assets/plan-preview', methods=['POST'])
    def preview_asset_generation_plan():
        guard = admin_json_guard()
        if guard:
            return guard
        payload = request.json or {}
        return jsonify(build_asset_generation_plan_payload(payload))

    @app.route('/api/admin/assets/batch-plan-preview', methods=['POST'])
    def preview_batch_asset_plan():
        guard = admin_json_guard()
        if guard:
            return guard
        payload = request.json or {}
        return jsonify(build_batch_asset_plan_drafts(payload))

    @app.route('/api/admin/assets/draft-plans')
    def list_asset_plan_drafts():
        guard = admin_json_guard()
        if guard:
            return guard

        status = (request.args.get('status') or '').strip()
        limit = min(max(safe_int(request.args.get('limit'), 30), 1), 100)
        query = AssetPlanDraft.query
        if status:
            query = query.filter_by(status=status)
        items = query.order_by(AssetPlanDraft.updated_at.desc(), AssetPlanDraft.created_at.desc(), AssetPlanDraft.id.desc()).limit(limit).all()
        return jsonify({
            'success': True,
            'items': [serialize_asset_plan_draft(item) for item in items],
        })

    @app.route('/api/admin/assets/draft-plans/save-batch', methods=['POST'])
    def save_asset_plan_drafts_batch():
        guard = admin_json_guard()
        if guard:
            return guard

        data = request.json or {}
        source_type = (data.get('source_type') or '').strip()[:20]
        bucket_label = (data.get('bucket_label') or '').strip()[:100]
        raw_items = data.get('items') or []
        kept_items = [item for item in raw_items if isinstance(item, dict)]
        if not kept_items:
            return jsonify({'success': False, 'message': '当前没有可保存的草案'})

        saved = []
        for row in kept_items[:20]:
            source_id = safe_int(row.get('source_id'), 0)
            cover_style_type = (row.get('plan', {}) or {}).get('cover_style_type') or row.get('cover_style_type') or ''
            inner_style_type = (row.get('plan', {}) or {}).get('inner_style_type') or row.get('inner_style_type') or ''
            generation_mode = (row.get('plan', {}) or {}).get('generation_mode') or 'smart_bundle'
            draft = AssetPlanDraft.query.filter_by(
                source_type=source_type or (row.get('source_type') or '')[:20],
                source_id=source_id or None,
                cover_style_type=str(cover_style_type or '')[:50],
                inner_style_type=str(inner_style_type or '')[:50],
                generation_mode=str(generation_mode or '')[:50],
                status='active',
            ).first()
            if not draft:
                draft = AssetPlanDraft(
                    source_type=source_type or (row.get('source_type') or '')[:20],
                    source_id=source_id or None,
                    cover_style_type=str(cover_style_type or '')[:50],
                    inner_style_type=str(inner_style_type or '')[:50],
                    generation_mode=str(generation_mode or '')[:50],
                    status='active',
                )
                db.session.add(draft)
            draft.source_title = (row.get('source_title') or '')[:200]
            draft.bucket_label = bucket_label or (row.get('template_agent_label') or '')[:100]
            draft.template_agent_label = (row.get('template_agent_label') or '')[:100]
            draft.image_skill_label = (row.get('image_skill_label') or '')[:100]
            draft.style_type = str(((row.get('plan') or {}).get('style_type') or row.get('style_type') or ''))[:50]
            draft.title_hint = str(((row.get('plan') or {}).get('title_hint') or row.get('source_title') or ''))[:200]
            draft.selected_content = str(row.get('selected_content') or '')[:4000]
            draft.draft_payload = json.dumps(row, ensure_ascii=False)
            saved.append(draft)

        db.session.flush()
        log_operation('save_batch', 'asset_plan_draft', message='批量保存图片草案', detail={
            'source_type': source_type,
            'bucket_label': bucket_label,
            'count': len(saved),
            'actor': current_actor(),
        })
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'已保存 {len(saved)} 条图片草案到待办池',
            'items': [serialize_asset_plan_draft(item) for item in saved],
        })

    @app.route('/api/admin/assets/draft-plans/<int:draft_id>/status', methods=['POST'])
    def update_asset_plan_draft_status(draft_id):
        guard = admin_json_guard()
        if guard:
            return guard

        draft = AssetPlanDraft.query.get_or_404(draft_id)
        data = request.json or {}
        status = (data.get('status') or '').strip()
        if status not in {'active', 'archived'}:
            return jsonify({'success': False, 'message': '不支持的草案状态'})
        draft.status = status
        log_operation('update_status', 'asset_plan_draft', target_id=draft.id, message='更新图片草案状态', detail={
            'status': status,
            'source_type': draft.source_type,
            'source_id': draft.source_id,
            'actor': current_actor(),
        })
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '图片草案状态已更新',
            'item': serialize_asset_plan_draft(draft),
        })

    @app.route('/api/admin/assets/draft-plans/confirm-batch', methods=['POST'])
    def confirm_asset_plan_drafts_batch():
        guard = admin_json_guard()
        if guard:
            return guard

        data = request.json or {}
        raw_ids = data.get('draft_ids') or []
        draft_ids = []
        for item in raw_ids:
            value = safe_int(item, 0)
            if value > 0:
                draft_ids.append(value)
        draft_ids = list(dict.fromkeys(draft_ids))[:30]
        if not draft_ids:
            return jsonify({'success': False, 'message': '请先选择要确认的图片草案'})

        drafts = AssetPlanDraft.query.filter(AssetPlanDraft.id.in_(draft_ids)).all()
        if not drafts:
            return jsonify({'success': False, 'message': '未找到可确认的图片草案'})

        created_tasks = []
        archive_after = data.get('archive_after', True)
        for draft in drafts:
            payload = load_json_value(draft.draft_payload, {})
            plan = payload.get('plan') if isinstance(payload, dict) else {}
            task = AssetGenerationTask(
                registration_id=None,
                topic_id=None,
                draft_source_type=(draft.source_type or '')[:20],
                draft_source_id=draft.source_id,
                draft_plan_id=draft.id,
                source_provider='draft_pool',
                model_name='',
                style_preset=(plan.get('style_label') or draft.style_type or '图片草案')[:50],
                generation_mode=(draft.generation_mode or 'smart_bundle')[:50],
                cover_style_type=(draft.cover_style_type or '')[:50],
                inner_style_type=(draft.inner_style_type or '')[:50],
                image_count=1,
                status='draft',
                title_hint=(draft.title_hint or draft.source_title or '图片草案')[:200],
                prompt_text=(plan.get('strategy_reason') or draft.selected_content or '')[:5000],
                selected_content=draft.selected_content or '',
                message='已从图片草案确认，待补报名ID后执行',
            )
            db.session.add(task)
            created_tasks.append(task)
            if archive_after:
                draft.status = 'archived'

        db.session.flush()
        log_operation('confirm_batch', 'asset_plan_draft', message='批量确认图片草案为待执行图片任务', detail={
            'draft_count': len(drafts),
            'task_count': len(created_tasks),
            'archive_after': bool(archive_after),
            'actor': current_actor(),
        })
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'已生成 {len(created_tasks)} 条待执行图片任务',
            'items': [serialize_asset_generation_task(item) for item in created_tasks],
        })

    @app.route('/api/admin/assets/style-recommendations', methods=['POST'])
    def asset_style_recommendations():
        guard = admin_json_guard()
        if guard:
            return guard
        payload = request.json or {}
        return jsonify(build_asset_style_recommendation_payload(payload))

    @app.route('/api/admin/assets/library')
    def list_asset_library():
        guard = admin_json_guard()
        if guard:
            return guard

        library_type = (request.args.get('library_type') or '').strip()
        style_type_key_raw = (request.args.get('style_type_key') or '').strip()
        pool_status = (request.args.get('pool_status') or '').strip()
        source_provider = (request.args.get('source_provider') or '').strip()
        product_category = (request.args.get('product_category') or '').strip()
        product_name = (request.args.get('product_name') or '').strip()
        visual_role = (request.args.get('visual_role') or '').strip()
        keyword = (request.args.get('keyword') or '').strip()
        limit = min(max(safe_int(request.args.get('limit'), 30), 1), 100)

        query = AssetLibrary.query
        if library_type:
            query = query.filter_by(library_type=library_type)
        if style_type_key_raw:
            style_type_keys = [item.strip() for item in style_type_key_raw.split(',') if item.strip()]
            if len(style_type_keys) == 1:
                query = query.filter_by(style_type_key=style_type_keys[0])
            elif style_type_keys:
                query = query.filter(AssetLibrary.style_type_key.in_(style_type_keys))
        if pool_status:
            query = query.filter_by(pool_status=pool_status)
        if source_provider:
            query = query.filter_by(source_provider=source_provider)
        if product_category:
            query = query.filter_by(product_category=product_category)
        if product_name:
            query = query.filter(AssetLibrary.product_name.contains(product_name))
        if visual_role:
            query = query.filter_by(visual_role=visual_role)
        if keyword:
            query = query.filter(
                (AssetLibrary.title.contains(keyword)) |
                (AssetLibrary.subtitle.contains(keyword)) |
                (AssetLibrary.tags.contains(keyword)) |
                (AssetLibrary.product_name.contains(keyword)) |
                (AssetLibrary.product_indication.contains(keyword))
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
        if library_type not in {'generated', 'product', 'content', 'reference'}:
            return jsonify({'success': False, 'message': '不支持的图库类型'})

        title = (data.get('title') or '').strip()
        preview_url = (data.get('preview_url') or '').strip()
        if not title:
            return jsonify({'success': False, 'message': '资产标题不能为空'})
        if not preview_url:
            return jsonify({'success': False, 'message': '预览链接不能为空'})
        style_type_key = (data.get('style_type_key') or '').strip()[:50]
        profile_meta = product_profile_meta(data.get('product_profile') or '')
        product_category = (data.get('product_category') or profile_meta.get('product_category') or '').strip()[:30]
        product_name = (data.get('product_name') or profile_meta.get('product_name') or '').strip()[:200]
        product_indication = (data.get('product_indication') or profile_meta.get('product_indication') or '').strip()[:200]
        visual_role = (data.get('visual_role') or profile_meta.get('default_visual_role') or '').strip()[:50]
        merged_tags = ','.join(filter(None, [
            (data.get('tags') or '').strip(),
            ','.join(profile_meta.get('default_tags') or []),
        ]))[:300]

        item = AssetLibrary(
            library_type=library_type,
            style_type_key=style_type_key,
            asset_type=(data.get('asset_type') or '知识卡片').strip()[:50],
            title=title[:200],
            subtitle=(data.get('subtitle') or '').strip()[:300],
            source_provider=(data.get('source_provider') or 'manual_upload').strip()[:50],
            model_name=(data.get('model_name') or '').strip()[:100],
            pool_status=(data.get('pool_status') or 'reserve').strip()[:20],
            status='active',
            product_category=product_category,
            product_name=product_name,
            product_indication=product_indication,
            visual_role=visual_role,
            tags=merged_tags,
            prompt_text=(data.get('prompt_text') or '').strip(),
            preview_url=preview_url,
            download_name=(data.get('download_name') or '').strip()[:200],
            raw_payload=json.dumps({
                'manual': True,
                'library_type': library_type,
                'style_type_key': style_type_key,
                'preview_url': preview_url,
                'product_profile': (data.get('product_profile') or '').strip(),
                'product_category': product_category,
                'product_name': product_name,
                'product_indication': product_indication,
                'visual_role': visual_role,
            }, ensure_ascii=False),
        )
        db.session.add(item)
        db.session.flush()
        log_operation('create', 'asset_library', target_id=item.id, message='手工新增图片资产', detail={
            'title': item.title,
            'library_type': item.library_type,
            'style_type_key': item.style_type_key,
            'asset_type': item.asset_type,
            'pool_status': item.pool_status,
            'product_category': item.product_category,
            'product_name': item.product_name,
            'visual_role': item.visual_role,
        })
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '图片资产已入库',
            'item': serialize_asset_library_item(item)
        })

    @app.route('/api/admin/assets/library/upload', methods=['POST'])
    def upload_asset_library_file():
        guard = admin_json_guard()
        if guard:
            return guard

        file_storage = request.files.get('file')
        if not file_storage or not (file_storage.filename or '').strip():
            return jsonify({'success': False, 'message': '请先选择图片文件'})

        library_type = (request.form.get('library_type') or 'content').strip()
        if library_type not in {'generated', 'product', 'content', 'reference'}:
            return jsonify({'success': False, 'message': '不支持的图库类型'})

        title = (request.form.get('title') or '').strip()
        if not title:
            return jsonify({'success': False, 'message': '资产标题不能为空'})
        style_type_key = (request.form.get('style_type_key') or '').strip()[:50]
        profile_meta = product_profile_meta(request.form.get('product_profile') or '')
        product_category = (request.form.get('product_category') or profile_meta.get('product_category') or '').strip()[:30]
        product_name = (request.form.get('product_name') or profile_meta.get('product_name') or '').strip()[:200]
        product_indication = (request.form.get('product_indication') or profile_meta.get('product_indication') or '').strip()[:200]
        visual_role = (request.form.get('visual_role') or profile_meta.get('default_visual_role') or '').strip()[:50]
        merged_tags = ','.join(filter(None, [
            (request.form.get('tags') or '').strip(),
            ','.join(profile_meta.get('default_tags') or []),
        ]))[:300]

        try:
            upload_result = _save_asset_upload(file_storage)
        except ValueError as exc:
            return jsonify({'success': False, 'message': str(exc)})

        item = AssetLibrary(
            library_type=library_type,
            style_type_key=style_type_key,
            asset_type=(request.form.get('asset_type') or '知识卡片').strip()[:50],
            title=title[:200],
            subtitle=(request.form.get('subtitle') or '').strip()[:300],
            source_provider=(request.form.get('source_provider') or 'manual_upload').strip()[:50],
            model_name=(request.form.get('model_name') or '').strip()[:100],
            pool_status=(request.form.get('pool_status') or 'reserve').strip()[:20],
            status='active',
            product_category=product_category,
            product_name=product_name,
            product_indication=product_indication,
            visual_role=visual_role,
            tags=merged_tags,
            prompt_text=(request.form.get('prompt_text') or '').strip(),
            preview_url=upload_result['preview_url'],
            download_name=((request.form.get('download_name') or '').strip()[:200] or upload_result['download_name']),
            raw_payload=json.dumps({
                'manual': True,
                'upload_type': 'local_file',
                'style_type_key': style_type_key,
                'original_filename': file_storage.filename,
                'stored_path': upload_result['preview_url'],
                'product_profile': (request.form.get('product_profile') or '').strip(),
                'product_category': product_category,
                'product_name': product_name,
                'product_indication': product_indication,
                'visual_role': visual_role,
            }, ensure_ascii=False),
        )
        db.session.add(item)
        db.session.flush()
        log_operation('create', 'asset_library', target_id=item.id, message='上传图片资产到资产库', detail={
            'title': item.title,
            'library_type': item.library_type,
            'style_type_key': item.style_type_key,
            'asset_type': item.asset_type,
            'pool_status': item.pool_status,
            'preview_url': item.preview_url,
            'product_category': item.product_category,
            'product_name': item.product_name,
            'visual_role': item.visual_role,
        })
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '图片文件已上传并入库',
            'item': serialize_asset_library_item(item)
        })

    @app.route('/api/admin/assets/library/export')
    def export_asset_library():
        guard = admin_json_guard()
        if guard:
            return guard

        library_type = (request.args.get('library_type') or '').strip()
        style_type_key_raw = (request.args.get('style_type_key') or '').strip()
        pool_status = (request.args.get('pool_status') or '').strip()
        source_provider = (request.args.get('source_provider') or '').strip()
        product_category = (request.args.get('product_category') or '').strip()
        product_name = (request.args.get('product_name') or '').strip()
        visual_role = (request.args.get('visual_role') or '').strip()
        keyword = (request.args.get('keyword') or '').strip()

        query = AssetLibrary.query
        if library_type:
            query = query.filter_by(library_type=library_type)
        if style_type_key_raw:
            style_type_keys = [item.strip() for item in style_type_key_raw.split(',') if item.strip()]
            if len(style_type_keys) == 1:
                query = query.filter_by(style_type_key=style_type_keys[0])
            elif style_type_keys:
                query = query.filter(AssetLibrary.style_type_key.in_(style_type_keys))
        if pool_status:
            query = query.filter_by(pool_status=pool_status)
        if source_provider:
            query = query.filter_by(source_provider=source_provider)
        if product_category:
            query = query.filter_by(product_category=product_category)
        if product_name:
            query = query.filter(AssetLibrary.product_name.contains(product_name))
        if visual_role:
            query = query.filter_by(visual_role=visual_role)
        if keyword:
            query = query.filter(
                (AssetLibrary.title.contains(keyword)) |
                (AssetLibrary.subtitle.contains(keyword)) |
                (AssetLibrary.tags.contains(keyword)) |
                (AssetLibrary.product_name.contains(keyword)) |
                (AssetLibrary.product_indication.contains(keyword))
            )

        items = query.order_by(AssetLibrary.created_at.desc(), AssetLibrary.id.desc()).all()
        rows = ['图库类型,参考风格,产品分类,产品名称,适应方向,视觉角色,资产类型,标题,副标题,来源提供方,模型,池状态,标签,预览链接,创建时间']
        for item in items:
            serialized = serialize_asset_library_item(item)
            rows.append(','.join([
                (serialized.get('library_type_label') or '').replace(',', ' '),
                (serialized.get('style_type_label') or serialized.get('style_type_key') or '').replace(',', ' '),
                (serialized.get('product_category_label') or '').replace(',', ' '),
                (serialized.get('product_name') or '').replace(',', ' '),
                (serialized.get('product_indication') or '').replace(',', ' '),
                (serialized.get('visual_role') or '').replace(',', ' '),
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
            'style_type_key': style_type_key_raw,
            'pool_status': pool_status,
            'source_provider': source_provider,
            'product_category': product_category,
            'product_name': product_name,
            'visual_role': visual_role,
            'keyword': keyword,
            'count': len(items),
        })
        db.session.commit()
        content = '\n'.join(rows)
        return content, 200, {
            'Content-Type': 'text/csv; charset=utf-8',
            'Content-Disposition': 'attachment; filename=asset_library.csv'
        }

    @app.route('/api/admin/assets/library/insights')
    def asset_library_insights():
        guard = admin_json_guard()
        if guard:
            return guard

        items = AssetLibrary.query.order_by(AssetLibrary.created_at.desc(), AssetLibrary.id.desc()).all()
        library_counter = Counter()
        category_counter = Counter()
        role_counter = Counter()
        product_counter = Counter()
        style_counter = Counter()
        category_rows = defaultdict(lambda: {'count': 0, 'products': set()})
        role_map_by_product = defaultdict(set)
        source_map_by_product = defaultdict(lambda: {'product_assets': 0, 'generated_assets': 0, 'reference_assets': 0})
        for item in items:
            library_counter[item.library_type or 'generated'] += 1
            category_key = (item.product_category or '未分类').strip() or '未分类'
            role_key = (item.visual_role or '未标记').strip() or '未标记'
            product_key = (item.product_name or '未指定产品').strip() or '未指定产品'
            category_counter[category_key] += 1
            role_counter[role_key] += 1
            product_counter[product_key] += 1
            if (item.style_type_key or '').strip():
                style_counter[item.style_type_key.strip()] += 1
            category_rows[category_key]['count'] += 1
            category_rows[category_key]['products'].add(product_key)
            role_map_by_product[product_key].add(role_key)
            bucket_key = f"{(item.library_type or 'generated')}_assets"
            if bucket_key in source_map_by_product[product_key]:
                source_map_by_product[product_key][bucket_key] += 1

        coverage_rows = []
        for profile in product_profile_options():
            product_name = (profile.get('product_name') or '').strip() or profile.get('label') or '未命名产品'
            existing_roles = role_map_by_product.get(product_name, set())
            source_stats = source_map_by_product.get(product_name, {'product_assets': 0, 'generated_assets': 0, 'reference_assets': 0})
            if profile.get('product_category') == 'device':
                expected_roles = {'hero', 'detail', 'scene'}
            else:
                expected_roles = {'standard_pack', 'detail', 'instruction'}
            if profile.get('default_visual_role'):
                expected_roles.add(profile['default_visual_role'])
            missing_roles = sorted([role for role in expected_roles if role not in existing_roles])
            coverage_rows.append({
                'profile_key': profile.get('key') or '',
                'product_name': product_name,
                'product_category': profile.get('product_category') or '',
                'existing_roles': sorted([role for role in existing_roles if role and role != '未标记']),
                'missing_roles': missing_roles,
                'asset_count': product_counter.get(product_name, 0),
                'product_asset_count': source_stats.get('product_assets', 0),
                'generated_asset_count': source_stats.get('generated_assets', 0),
                'reference_asset_count': source_stats.get('reference_assets', 0),
            })

        return jsonify({
            'success': True,
            'summary': {
                'total': len(items),
                'product_assets': sum(1 for item in items if (item.library_type or '') == 'product'),
                'reference_assets': sum(1 for item in items if (item.library_type or '') == 'reference'),
                'distinct_products': len([key for key in product_counter.keys() if key != '未指定产品']),
            },
            'library_types': [{'key': key, 'count': count} for key, count in library_counter.items()],
            'product_categories': [{
                'key': key,
                'count': value['count'],
                'product_count': len([name for name in value['products'] if name != '未指定产品']),
            } for key, value in category_rows.items()],
            'visual_roles': [{'key': key, 'count': count} for key, count in role_counter.most_common(10)],
            'style_types': [{'key': key, 'count': count} for key, count in style_counter.most_common(12)],
            'products': [{'name': key, 'count': count} for key, count in product_counter.most_common(12)],
            'coverage': coverage_rows,
        })

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

    @app.route('/api/admin/assets/tasks/<int:task_id>/activate-draft', methods=['POST'])
    def activate_draft_asset_generation_task(task_id):
        guard = admin_json_guard()
        if guard:
            return guard

        task = AssetGenerationTask.query.get_or_404(task_id)
        if (task.status or '').strip() != 'draft':
            return jsonify({'success': False, 'message': '只有待执行图片任务才支持补报名ID并派发'})

        data = request.json or {}
        registration_id = safe_int(data.get('registration_id'), 0)
        if registration_id <= 0:
            return jsonify({'success': False, 'message': '请先填写有效的报名ID'})

        payload = {
            'registration_id': registration_id,
            'selected_content': task.selected_content or '',
            'style_type': (task.cover_style_type or task.inner_style_type or task.style_preset or 'medical_science'),
            'generation_mode': task.generation_mode or 'smart_bundle',
            'cover_style_type': task.cover_style_type or '',
            'inner_style_type': task.inner_style_type or '',
            'title_hint': task.title_hint or '',
            'product_profile': task.product_profile or '',
            'product_category': task.product_category or '',
            'product_name': task.product_name or '',
            'product_indication': task.product_indication or '',
            'product_asset_ids': task.product_asset_ids or '',
            'reference_asset_ids': task.reference_asset_ids or '',
            'image_count': task.image_count or 1,
        }
        try:
            dispatched = dispatch_asset_generation(payload, actor=current_actor())
        except ValueError as exc:
            return jsonify({'success': False, 'message': str(exc)})

        task.status = 'archived'
        task.message = f'已补报名ID并转正式任务 #{dispatched["task_record"].id}'
        log_operation('activate_draft', 'asset_generation_task', target_id=task.id, message='待执行图片任务补报名ID并派发', detail={
            'registration_id': registration_id,
            'new_asset_task_id': dispatched['task_record'].id,
            'new_celery_task_id': dispatched['task_id'],
            'actor': current_actor(),
        })
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '已补报名ID并派发正式图片任务',
            'task_id': dispatched['task_id'],
            'asset_task_id': dispatched['task_record'].id,
            'draft_item': serialize_asset_generation_task(task),
            'item': serialize_asset_generation_task(dispatched['task_record']),
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
        if task.task_type == 'creator_account_sync':
            dispatched = dispatch_creator_account_sync(payload, actor=current_actor())
            return jsonify({
                'success': True,
                'message': '已重新派发报名人账号同步任务',
                'task_id': dispatched['task_id'],
                'data_source_task_id': dispatched['task_record'].id,
            })
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

    @app.route('/api/admin/schedules/hotword-sync/upsert', methods=['POST'])
    def upsert_hotword_schedule():
        guard = admin_json_guard()
        if guard:
            return guard

        data = request.json or {}
        schedule = AutomationSchedule.query.filter_by(job_key='hotword_sync_daily').first()
        if not schedule:
            schedule = AutomationSchedule(
                job_key='hotword_sync_daily',
                name='热点抓取骨架巡检',
                task_type='hotword_sync',
            )
            db.session.add(schedule)

        schedule.name = (data.get('name') or schedule.name or '热点抓取骨架巡检').strip()[:120] or '热点抓取骨架巡检'
        schedule.task_type = 'hotword_sync'
        previous_enabled = bool(schedule.enabled)
        schedule.enabled = helpers['coerce_bool'](data.get('enabled'))
        schedule.interval_minutes = min(max(safe_int(data.get('interval_minutes'), schedule.interval_minutes or 360), 1), 10080)
        params_payload = data.get('params_payload')
        if isinstance(params_payload, dict):
            clean_payload = dict(params_payload)
            clean_payload.pop('batch_name', None)
            schedule.params_payload = json.dumps(clean_payload, ensure_ascii=False)
        if schedule.enabled and (not previous_enabled or not schedule.next_run_at):
            schedule.next_run_at = helpers['next_schedule_time'](schedule.interval_minutes)
            schedule.last_status = 'queued'
            schedule.last_message = '已根据当前热点配置启用默认热点调度'
        if not schedule.enabled:
            schedule.last_status = 'paused'
            schedule.last_message = '已暂停默认热点调度'
        log_operation('save_schedule', 'automation_schedule', target_id=schedule.id, message='按当前热点配置更新默认调度', detail={
            'job_key': schedule.job_key,
            'enabled': bool(schedule.enabled),
            'interval_minutes': schedule.interval_minutes,
            'name': schedule.name,
        })
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '默认热点调度已按当前配置更新',
            'item': serialize_automation_schedule(schedule),
        })

    @app.route('/api/admin/schedules/creator-sync/upsert', methods=['POST'])
    def upsert_creator_sync_schedule():
        guard = admin_json_guard()
        if guard:
            return guard

        data = request.json or {}
        schedule = AutomationSchedule.query.filter_by(job_key='creator_accounts_sync_half_hourly').first()
        if not schedule:
            schedule = AutomationSchedule(
                job_key='creator_accounts_sync_half_hourly',
                name='报名人账号持续同步',
                task_type='creator_account_sync',
            )
            db.session.add(schedule)

        schedule.name = (data.get('name') or schedule.name or '报名人账号持续同步').strip()[:120] or '报名人账号持续同步'
        schedule.task_type = 'creator_account_sync'
        previous_enabled = bool(schedule.enabled)
        schedule.enabled = helpers['coerce_bool'](data.get('enabled'))
        schedule.interval_minutes = min(max(safe_int(data.get('interval_minutes'), schedule.interval_minutes or 30), 1), 10080)
        params_payload = data.get('params_payload')
        if isinstance(params_payload, dict):
            clean_payload = dict(params_payload)
            for transient_key in ['batch_name', 'registration_id', 'creator_account_id']:
                clean_payload.pop(transient_key, None)
            schedule.params_payload = json.dumps(clean_payload, ensure_ascii=False)
        if schedule.enabled and (not previous_enabled or not schedule.next_run_at):
            schedule.next_run_at = helpers['next_schedule_time'](schedule.interval_minutes)
            schedule.last_status = 'queued'
            schedule.last_message = '已根据当前账号同步配置启用默认调度'
        if not schedule.enabled:
            schedule.last_status = 'paused'
            schedule.last_message = '已暂停默认账号同步调度'
        log_operation('save_schedule', 'automation_schedule', target_id=schedule.id, message='按当前账号同步配置更新默认调度', detail={
            'job_key': schedule.job_key,
            'enabled': bool(schedule.enabled),
            'interval_minutes': schedule.interval_minutes,
            'name': schedule.name,
        })
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '默认账号同步调度已按当前配置更新',
            'item': serialize_automation_schedule(schedule),
        })

    @app.route('/api/admin/schedules/topic-ideas/upsert', methods=['POST'])
    def upsert_topic_ideas_schedule():
        guard = admin_json_guard()
        if guard:
            return guard

        data = request.json or {}
        schedule = AutomationSchedule.query.filter_by(job_key='topic_ideas_daily').first()
        if not schedule:
            schedule = AutomationSchedule(
                job_key='topic_ideas_daily',
                name='候选话题自动生成',
                task_type='topic_idea_generate',
            )
            db.session.add(schedule)

        schedule.name = (data.get('name') or schedule.name or '候选话题自动生成').strip()[:120] or '候选话题自动生成'
        schedule.task_type = 'topic_idea_generate'
        previous_enabled = bool(schedule.enabled)
        schedule.enabled = helpers['coerce_bool'](data.get('enabled'))
        schedule.interval_minutes = min(max(safe_int(data.get('interval_minutes'), schedule.interval_minutes or 1440), 1), 10080)
        params_payload = data.get('params_payload')
        if isinstance(params_payload, dict):
            schedule.params_payload = json.dumps(dict(params_payload), ensure_ascii=False)
        if schedule.enabled and (not previous_enabled or not schedule.next_run_at):
            schedule.next_run_at = helpers['next_schedule_time'](schedule.interval_minutes)
            schedule.last_status = 'queued'
            schedule.last_message = '已根据当前候选话题配置启用默认调度'
        if not schedule.enabled:
            schedule.last_status = 'paused'
            schedule.last_message = '已暂停默认候选话题调度'
        log_operation('save_schedule', 'automation_schedule', target_id=schedule.id, message='按当前候选话题配置更新默认调度', detail={
            'job_key': schedule.job_key,
            'enabled': bool(schedule.enabled),
            'interval_minutes': schedule.interval_minutes,
            'name': schedule.name,
        })
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '默认候选话题调度已按当前配置更新',
            'item': serialize_automation_schedule(schedule),
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
