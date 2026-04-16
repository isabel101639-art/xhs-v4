import json
import os

from celery import Celery

from app import app as flask_app


def make_celery(app):
    broker_url = os.environ.get('CELERY_BROKER_URL') or os.environ.get('REDIS_URL', 'redis://redis:6379/0')
    result_backend = os.environ.get('CELERY_RESULT_BACKEND', broker_url)

    celery = Celery(
        app.import_name,
        broker=broker_url,
        backend=result_backend,
    )
    celery.conf.update(
        timezone=os.environ.get('TZ', 'Asia/Shanghai'),
        enable_utc=False,
        task_track_started=True,
        task_time_limit=int(os.environ.get('CELERY_TASK_TIME_LIMIT', '1200')),
        task_soft_time_limit=int(os.environ.get('CELERY_TASK_SOFT_TIME_LIMIT', '900')),
    )

    class FlaskContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return super().__call__(*args, **kwargs)

    celery.Task = FlaskContextTask
    return celery


celery = make_celery(flask_app)
celery.conf.beat_schedule = {
    'automation-scheduler-tick': {
        'task': 'jobs.scheduler.tick',
        'schedule': 60.0,
    }
}


@celery.task(name='system.ping')
def ping():
    return {
        'message': 'pong',
        'service': 'worker',
    }


@celery.task(name='jobs.scheduler.tick')
def scheduler_tick():
    from app import (
        _dispatch_automation_schedule,
        _log_operation,
        AutomationSchedule,
        db,
        datetime,
        os,
    )

    enabled_flag = str(os.environ.get('ENABLE_AUTOMATION_BEAT', 'true')).strip().lower() in {'1', 'true', 'yes', 'y', 'on'}
    if not enabled_flag:
        return {
            'success': True,
            'message': 'automation beat disabled by env',
            'dispatched': 0,
        }

    now = datetime.now()
    schedules = AutomationSchedule.query.filter_by(enabled=True).all()
    dispatched = []
    for schedule in schedules:
        if schedule.next_run_at and schedule.next_run_at > now:
            continue
        try:
            result = _dispatch_automation_schedule(schedule, actor='scheduler')
            dispatched.append({
                'schedule_id': schedule.id,
                'job_key': schedule.job_key,
                'task_id': result.get('task_id', ''),
            })
        except Exception as exc:
            schedule.last_run_at = now
            schedule.last_status = 'failed'
            schedule.last_message = str(exc)[:300]
            db.session.commit()

    if dispatched:
        _log_operation('scheduler_tick', 'automation_schedule', message='Scheduler 自动派发任务', detail={
            'count': len(dispatched),
            'items': dispatched,
        })
        db.session.commit()

    return {
        'success': True,
        'dispatched': len(dispatched),
        'items': dispatched,
    }


@celery.task(name='jobs.generate_topic_ideas')
def generate_topic_ideas_job(count=80, activity_id=None, quota=None):
    from app import (
        _generate_topic_ideas,
        _matching_corpus_snippets,
        _log_operation,
        _normalize_quota,
        _safe_int,
        CorpusEntry,
        LIVER_KEYWORD_SEEDS,
        db,
    )

    safe_count = min(max(_safe_int(count, 80), 1), 120)
    safe_quota = _normalize_quota(quota)
    ideas = _generate_topic_ideas(count=safe_count, activity_id=activity_id, quota=safe_quota)
    for idea in ideas:
        db.session.add(idea)

    if ideas:
        matching_ids = {entry.id for entry in _matching_corpus_snippets(','.join(LIVER_KEYWORD_SEEDS[:5]), limit=5)}
        matched_entries = CorpusEntry.query.filter(CorpusEntry.id.in_(matching_ids)).all() if matching_ids else []
        for entry in matched_entries:
            entry.usage_count = (entry.usage_count or 0) + 1

    db.session.flush()
    _log_operation('worker_generate', 'topic_idea', message='Worker 异步生成候选话题', detail={
        'count': len(ideas),
        'activity_id': activity_id,
        'quota': safe_quota,
        'idea_ids': [idea.id for idea in ideas],
    })
    db.session.commit()
    return {
        'count': len(ideas),
        'activity_id': activity_id,
        'quota': safe_quota,
        'idea_ids': [idea.id for idea in ideas],
    }


@celery.task(name='jobs.hotwords.sync')
def sync_hotwords_job(data_source_task_id):
    from app import (
        _append_data_source_log,
        _automation_keyword_seeds,
        _load_json_value,
        _log_operation,
        _resolve_hotword_rows,
        _safe_int,
        DataSourceTask,
        TrendNote,
        db,
        datetime,
        json,
    )

    task_record = DataSourceTask.query.get(data_source_task_id)
    if not task_record:
        return {
            'success': False,
            'message': '数据源任务不存在',
            'data_source_task_id': data_source_task_id,
        }

    try:
        task_record.status = 'running'
        task_record.started_at = datetime.now()
        task_record.message = 'Worker 正在执行热点抓取任务'
        db.session.flush()
        _append_data_source_log(task_record.id, 'Worker 已接管任务，开始生成热点抓取骨架', detail={
            'batch_name': task_record.batch_name,
            'source_platform': task_record.source_platform,
            'mode': task_record.mode,
        })
        db.session.commit()

        params = _load_json_value(task_record.params_payload, {})
        keywords = params.get('keywords') if isinstance(params, dict) else []
        if not isinstance(keywords, list) or not keywords:
            keywords = _automation_keyword_seeds()[:max(task_record.keyword_limit or 10, 1)]
        keywords = [str(item).strip() for item in keywords if str(item).strip()]
        resolved = _resolve_hotword_rows(task_record, params, keywords)
        rows = resolved.get('rows') or []
        mode = resolved.get('mode') or task_record.mode or 'skeleton'
        template_key = resolved.get('template_key') or params.get('template_key') or 'generic_lines'
        request_preview = resolved.get('request_preview') or {}
        response_preview = resolved.get('response_preview') or {}
        auto_generate_topic_ideas = bool(params.get('hotword_auto_generate_topic_ideas'))
        auto_generate_topic_count = min(max(_safe_int(params.get('hotword_auto_generate_topic_count'), 20), 1), 120)
        auto_generate_topic_activity_id = _safe_int(params.get('hotword_auto_generate_topic_activity_id'), 0) or None
        auto_generate_topic_quota = min(max(_safe_int(params.get('hotword_auto_generate_topic_quota'), 30), 1), 300)

        inserted_count = 0
        for row in rows:
            note = TrendNote(
                source_platform=row.get('source_platform') or task_record.source_platform or '小红书',
                source_channel=row.get('source_channel') or task_record.source_channel or 'Worker骨架',
                source_template_key=template_key,
                import_batch=row.get('import_batch') or task_record.batch_name,
                keyword=row.get('keyword') or '',
                topic_category=row.get('topic_category') or '热点骨架',
                title=row.get('title') or '热点抓取骨架样例',
                author=row.get('author') or '',
                link=row.get('link') or '',
                views=row.get('views') or 0,
                likes=row.get('likes') or 0,
                favorites=row.get('favorites') or 0,
                comments=row.get('comments') or 0,
                publish_time=datetime.now(),
                summary=row.get('summary') or '',
                raw_payload=json.dumps(row.get('raw_payload') or {}, ensure_ascii=False),
                pool_status='reserve',
            )
            db.session.add(note)
            inserted_count += 1

        task_record.status = 'success'
        task_record.item_count = inserted_count
        task_record.finished_at = datetime.now()
        task_record.message = (
            f'远端热点抓取执行完成，已生成 {inserted_count} 条热点'
            if mode == 'remote' else
            f'热点抓取骨架执行完成，已生成 {inserted_count} 条热点样例'
        )
        task_record.result_payload = json.dumps({
            'inserted_count': inserted_count,
            'batch_name': task_record.batch_name,
            'keywords': keywords,
            'mode': mode,
            'template_key': template_key,
            'request_preview': request_preview,
            'response_preview': response_preview,
        }, ensure_ascii=False)
        db.session.flush()
        _append_data_source_log(task_record.id, '热点抓取任务执行完成，已写入热点池', detail={
            'inserted_count': inserted_count,
            'batch_name': task_record.batch_name,
            'keywords': keywords,
            'mode': mode,
            'template_key': template_key,
        })
        _log_operation('worker_sync', 'data_source_task', target_id=task_record.id, message='Worker 执行热点抓取骨架任务', detail={
            'inserted_count': inserted_count,
            'batch_name': task_record.batch_name,
            'source_platform': task_record.source_platform,
            'mode': mode,
            'template_key': template_key,
        })
        db.session.commit()

        topic_generation_result = None
        if auto_generate_topic_ideas and inserted_count > 0:
            topic_generation_result = generate_topic_ideas_job(
                count=auto_generate_topic_count,
                activity_id=auto_generate_topic_activity_id,
                quota=auto_generate_topic_quota,
            )
            task_record = DataSourceTask.query.get(data_source_task_id)
            if task_record:
                task_record.message = (
                    f'{task_record.message}，并自动生成 {topic_generation_result.get("count", 0)} 个候选话题'
                )[:300]
                task_record.result_payload = json.dumps({
                    'inserted_count': inserted_count,
                    'batch_name': task_record.batch_name,
                    'keywords': keywords,
                    'mode': mode,
                    'template_key': template_key,
                    'request_preview': request_preview,
                    'response_preview': response_preview,
                    'topic_generation': topic_generation_result,
                }, ensure_ascii=False)
                db.session.flush()
                _append_data_source_log(task_record.id, '热点抓取后已自动生成候选话题', detail={
                    'generated_count': topic_generation_result.get('count', 0),
                    'activity_id': auto_generate_topic_activity_id,
                    'quota': auto_generate_topic_quota,
                })
                db.session.commit()
        return {
            'success': True,
            'data_source_task_id': task_record.id,
            'inserted_count': inserted_count,
            'batch_name': task_record.batch_name,
            'mode': mode,
            'topic_generation': topic_generation_result,
        }
    except Exception as exc:
        db.session.rollback()
        task_record = DataSourceTask.query.get(data_source_task_id)
        if task_record:
            task_record.status = 'failed'
            task_record.finished_at = datetime.now()
            task_record.message = f'热点抓取骨架执行失败：{exc}'
            task_record.result_payload = json.dumps({'error': str(exc)}, ensure_ascii=False)
            db.session.flush()
            _append_data_source_log(task_record.id, '热点抓取骨架执行失败', level='error', detail={'error': str(exc)})
            db.session.commit()
        raise


@celery.task(name='jobs.creator_accounts.sync')
def sync_creator_accounts_job(data_source_task_id):
    from app import (
        _append_data_source_log,
        _log_operation,
        DataSourceTask,
        db,
        datetime,
        fetch_remote_creator_bundle,
        _load_json_value,
    )
    from creator_import import import_creator_bundle

    task_record = DataSourceTask.query.get(data_source_task_id)
    if not task_record:
        return {
            'success': False,
            'message': '账号同步任务不存在',
            'data_source_task_id': data_source_task_id,
        }

    try:
        task_record.status = 'running'
        task_record.started_at = datetime.now()
        task_record.message = 'Worker 正在同步报名人账号数据'
        db.session.flush()
        _append_data_source_log(task_record.id, 'Worker 已接管报名人账号同步任务', detail={
            'batch_name': task_record.batch_name,
            'source_platform': task_record.source_platform,
            'mode': task_record.mode,
        })
        db.session.commit()

        params = _load_json_value(task_record.params_payload, {})
        targets = params.get('targets') if isinstance(params.get('targets'), list) else []
        remote_result = fetch_remote_creator_bundle(
            {
                'api_url': params.get('creator_sync_api_url'),
                'api_method': params.get('creator_sync_api_method'),
                'headers_json': params.get('creator_sync_api_headers_json'),
                'query_json': params.get('creator_sync_api_query_json'),
                'body_json': params.get('creator_sync_api_body_json'),
                'result_path': params.get('creator_sync_result_path'),
                'timeout_seconds': params.get('creator_sync_timeout_seconds'),
            },
            targets,
            source_channel=task_record.source_channel or 'Crawler服务',
            batch_name=task_record.batch_name or '',
        )
        bundle = remote_result.get('bundle') or {'accounts': [], 'posts': [], 'snapshots': []}
        response_preview = remote_result.get('response_preview') or {}
        if isinstance(response_preview, dict):
            preview_copy = dict(response_preview)
            for key in ['accounts', 'creator_accounts', 'posts', 'creator_posts', 'snapshots', 'creator_snapshots', 'items']:
                if isinstance(preview_copy.get(key), list):
                    preview_copy[key] = preview_copy[key][:5]
            response_preview = preview_copy
        elif isinstance(response_preview, list):
            response_preview = response_preview[:5]
        for section_key in ['accounts', 'posts', 'snapshots']:
            normalized_rows = []
            for row in bundle.get(section_key, []) or []:
                if not isinstance(row, dict):
                    continue
                next_row = dict(row)
                next_row['source_channel'] = (row.get('source_channel') or task_record.source_channel or 'creator_sync').strip()
                normalized_rows.append(next_row)
            bundle[section_key] = normalized_rows

        import_result = import_creator_bundle(bundle, log_operation=_log_operation)
        summary = import_result.get('summary') or {}
        touched_count = (
            (summary.get('posts_create', 0) or 0) +
            (summary.get('posts_update', 0) or 0) +
            (summary.get('accounts_create', 0) or 0) +
            (summary.get('accounts_update', 0) or 0)
        )

        task_record = DataSourceTask.query.get(data_source_task_id)
        task_record.status = 'success'
        task_record.item_count = touched_count
        task_record.finished_at = datetime.now()
        task_record.message = (
            f'报名人账号同步完成，账号新增 {summary.get("accounts_create", 0)} / 更新 {summary.get("accounts_update", 0)}，'
            f'笔记新增 {summary.get("posts_create", 0)} / 更新 {summary.get("posts_update", 0)}'
        )
        task_record.result_payload = json.dumps({
            'summary': summary,
            'target_count': len(targets),
            'request_preview': remote_result.get('request_preview') or {},
            'response_preview': response_preview,
        }, ensure_ascii=False)
        db.session.flush()
        _append_data_source_log(task_record.id, '报名人账号同步任务执行完成', detail={
            'summary': summary,
            'target_count': len(targets),
        })
        _log_operation('worker_sync', 'data_source_task', target_id=task_record.id, message='Worker 执行报名人账号同步任务', detail={
            'summary': summary,
            'target_count': len(targets),
            'batch_name': task_record.batch_name,
            'source_platform': task_record.source_platform,
        })
        db.session.commit()
        return {
            'success': True,
            'data_source_task_id': task_record.id,
            'summary': summary,
            'target_count': len(targets),
        }
    except Exception as exc:
        db.session.rollback()
        task_record = DataSourceTask.query.get(data_source_task_id)
        if task_record:
            task_record.status = 'failed'
            task_record.finished_at = datetime.now()
            task_record.message = f'报名人账号同步失败：{exc}'
            task_record.result_payload = json.dumps({'error': str(exc)}, ensure_ascii=False)
            db.session.flush()
            _append_data_source_log(task_record.id, '报名人账号同步执行失败', level='error', detail={'error': str(exc)})
            db.session.commit()
        raise


@celery.task(name='jobs.assets.generate')
def generate_asset_images_job(asset_task_id):
    from app import (
        _image_provider_capabilities,
        _build_asset_provider_request_preview,
        _build_asset_generation_fallback_results,
        _log_operation,
        _resolve_reference_asset_rows,
        AssetLibrary,
        AssetGenerationTask,
        Topic,
        db,
        datetime,
        json,
    )
    import requests

    task = AssetGenerationTask.query.get(asset_task_id)
    if not task:
        return {
            'success': False,
            'message': '图片任务不存在',
            'asset_task_id': asset_task_id,
        }

    topic = Topic.query.get(task.topic_id) if task.topic_id else None
    if not topic:
        task.status = 'failed'
        task.finished_at = datetime.now()
        task.message = '图片任务缺少话题信息'
        task.result_payload = json.dumps({'error': 'topic missing'}, ensure_ascii=False)
        db.session.commit()
        return {
            'success': False,
            'message': 'topic missing',
            'asset_task_id': asset_task_id,
        }

    capabilities = _image_provider_capabilities()
    api_url = (capabilities.get('image_provider_api_url') or '').strip()
    api_key = (
        os.environ.get('ASSET_IMAGE_API_KEY')
        or os.environ.get('ARK_API_KEY')
        or os.environ.get('LAS_API_KEY')
        or ''
    ).strip()
    provider = (capabilities.get('image_provider_name') or task.source_provider or 'svg_fallback').strip() or 'svg_fallback'
    model_name = (capabilities.get('image_provider_model') or task.model_name or '').strip()
    image_size = (capabilities.get('image_provider_size') or '1024x1536').strip()
    timeout_seconds = min(max(int(capabilities.get('image_timeout_seconds') or 90), 10), 300)

    def normalize_external_results(payload):
        candidates = []
        if isinstance(payload, dict):
            for key in ['data', 'images', 'output', 'results']:
                value = payload.get(key)
                if isinstance(value, list):
                    candidates = value
                    break
        elif isinstance(payload, list):
            candidates = payload

        normalized = []
        for index, item in enumerate(candidates, start=1):
            if isinstance(item, str):
                normalized.append({
                    'index': index,
                    'type': task.style_preset or 'AI图片',
                    'title': task.title_hint or f'AI生成图{index}',
                    'subtitle': '',
                    'image_prompt': task.prompt_text or '',
                    'preview_url': item,
                    'download_name': f'asset_task_{task.id}_{index}.png',
                    'provider': provider,
                    'format': 'url',
                    'bullets': [],
                })
                continue
            if not isinstance(item, dict):
                continue

            if item.get('b64_json'):
                normalized.append({
                    'index': index,
                    'type': task.style_preset or 'AI图片',
                    'title': task.title_hint or f'AI生成图{index}',
                    'subtitle': '',
                    'image_prompt': task.prompt_text or '',
                    'preview_url': f"data:image/png;base64,{item.get('b64_json')}",
                    'download_name': f'asset_task_{task.id}_{index}.png',
                    'provider': provider,
                    'format': 'png',
                    'bullets': [],
                })
            elif item.get('image_base64'):
                normalized.append({
                    'index': index,
                    'type': task.style_preset or 'AI图片',
                    'title': task.title_hint or f'AI生成图{index}',
                    'subtitle': '',
                    'image_prompt': task.prompt_text or '',
                    'preview_url': f"data:image/png;base64,{item.get('image_base64')}",
                    'download_name': f'asset_task_{task.id}_{index}.png',
                    'provider': provider,
                    'format': 'png',
                    'bullets': [],
                })
            elif item.get('url') or item.get('image_url'):
                normalized.append({
                    'index': index,
                    'type': task.style_preset or 'AI图片',
                    'title': task.title_hint or f'AI生成图{index}',
                    'subtitle': '',
                    'image_prompt': task.prompt_text or '',
                    'preview_url': item.get('url') or item.get('image_url'),
                    'download_name': f'asset_task_{task.id}_{index}.png',
                    'provider': provider,
                    'format': 'url',
                    'bullets': [],
                })
            elif isinstance(item.get('content'), list):
                for content_item in item.get('content') or []:
                    if not isinstance(content_item, dict):
                        continue
                    image_base64 = content_item.get('image_base64') or content_item.get('b64_json')
                    image_url = content_item.get('image_url') or content_item.get('url')
                    if image_base64:
                        normalized.append({
                            'index': index,
                            'type': task.style_preset or 'AI图片',
                            'title': task.title_hint or f'AI生成图{index}',
                            'subtitle': '',
                            'image_prompt': task.prompt_text or '',
                            'preview_url': f"data:image/png;base64,{image_base64}",
                            'download_name': f'asset_task_{task.id}_{index}.png',
                            'provider': provider,
                            'format': 'png',
                            'bullets': [],
                        })
                        break
                    if image_url:
                        normalized.append({
                            'index': index,
                            'type': task.style_preset or 'AI图片',
                            'title': task.title_hint or f'AI生成图{index}',
                            'subtitle': '',
                            'image_prompt': task.prompt_text or '',
                            'preview_url': image_url,
                            'download_name': f'asset_task_{task.id}_{index}.png',
                            'provider': provider,
                            'format': 'url',
                            'bullets': [],
                        })
                        break
        return normalized

    task.status = 'running'
    task.started_at = datetime.now()
    task.message = 'Worker 正在生成图片'
    db.session.commit()

    results = []
    message = ''
    actual_provider = provider
    reference_rows = _resolve_reference_asset_rows(task.reference_asset_ids or '', limit=20)
    reference_assets = [{
        'id': item.id,
        'title': item.title or '',
        'preview_url': item.preview_url or '',
        'product_name': item.product_name or '',
    } for item in reference_rows]
    product_context = {
        'product_profile': task.product_profile or '',
        'product_category': task.product_category or '',
        'product_name': task.product_name or '',
        'product_indication': task.product_indication or '',
    }

    if api_url and api_key:
        try:
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            }
            payload = _build_asset_provider_request_preview(
                provider,
                model_name,
                task.prompt_text or '',
                image_size,
                task.style_preset or '小红书图文',
                image_count=task.image_count or 3,
                reference_assets=reference_assets,
                product_context=product_context,
            )
            response = requests.post(api_url, json=payload, headers=headers, timeout=timeout_seconds)
            response.raise_for_status()
            results = normalize_external_results(response.json())
            if results:
                message = f'图片模型返回 {len(results)} 张结果'
            else:
                message = '外部图片模型无可识别结果，已切换 SVG 兜底'
                actual_provider = 'svg_fallback'
        except Exception as exc:
            message = f'外部图片模型调用失败，已切换 SVG 兜底：{exc}'
            actual_provider = 'svg_fallback'
    else:
        message = '未配置图片模型环境变量，使用 SVG 兜底生成'
        actual_provider = 'svg_fallback'

    if not results:
        results = _build_asset_generation_fallback_results(
            topic,
            selected_content=task.selected_content or '',
            image_count=task.image_count or 3,
            style_preset=task.style_preset or '',
            title_hint=task.title_hint or '',
        )

    for item in results:
        tags = ','.join(filter(None, [topic.topic_name if topic else '', item.get('type') or '', task.style_preset or '']))
        db.session.add(AssetLibrary(
            asset_generation_task_id=task.id,
            registration_id=task.registration_id,
            topic_id=task.topic_id,
            library_type='generated',
            asset_type=item.get('type') or '知识卡片',
            title=item.get('title') or task.title_hint or '',
            subtitle=item.get('subtitle') or '',
            source_provider=actual_provider,
            model_name=model_name or task.model_name or '',
            pool_status='reserve',
            status='active',
            product_category=task.product_category,
            product_name=task.product_name,
            product_indication=task.product_indication,
            visual_role='hero' if task.product_name else '',
            tags=tags[:300],
            prompt_text=item.get('image_prompt') or task.prompt_text or '',
            preview_url=item.get('preview_url') or '',
            download_name=item.get('download_name') or '',
            raw_payload=json.dumps({
                **item,
                'product_profile': task.product_profile or '',
                'product_category': task.product_category or '',
                'product_name': task.product_name or '',
                'product_indication': task.product_indication or '',
                'reference_asset_ids': task.reference_asset_ids or '',
            }, ensure_ascii=False),
        ))

    task.status = 'success'
    task.source_provider = actual_provider
    task.model_name = model_name or task.model_name
    task.finished_at = datetime.now()
    task.message = message
    task.result_payload = json.dumps(results, ensure_ascii=False)
    db.session.flush()
    _log_operation('worker_generate_asset', 'asset_generation_task', target_id=task.id, message='Worker 执行图片生成任务', detail={
        'provider': actual_provider,
        'image_count': len(results),
        'library_items_created': len(results),
        'registration_id': task.registration_id,
        'topic_id': task.topic_id,
        'product_name': task.product_name or '',
        'reference_asset_ids': task.reference_asset_ids or '',
    })
    db.session.commit()
    return {
        'success': True,
        'asset_task_id': task.id,
        'provider': actual_provider,
        'image_count': len(results),
    }
