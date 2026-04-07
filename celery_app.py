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
        _build_hotword_skeleton_rows,
        _load_json_value,
        _log_operation,
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
        task_record.message = 'Worker 正在生成热点抓取骨架结果'
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
        rows = _build_hotword_skeleton_rows(
            keywords,
            source_platform=task_record.source_platform or '小红书',
            source_channel=task_record.source_channel or 'Worker骨架',
            batch_name=task_record.batch_name or '',
        )

        inserted_count = 0
        for row in rows:
            note = TrendNote(
                source_platform=row.get('source_platform') or task_record.source_platform or '小红书',
                source_channel=row.get('source_channel') or task_record.source_channel or 'Worker骨架',
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
        task_record.message = f'热点抓取骨架执行完成，已生成 {inserted_count} 条热点样例'
        task_record.result_payload = json.dumps({
            'inserted_count': inserted_count,
            'batch_name': task_record.batch_name,
            'keywords': keywords,
            'mode': task_record.mode,
        }, ensure_ascii=False)
        db.session.flush()
        _append_data_source_log(task_record.id, '热点抓取骨架执行完成，已写入热点池', detail={
            'inserted_count': inserted_count,
            'batch_name': task_record.batch_name,
            'keywords': keywords,
        })
        _log_operation('worker_sync', 'data_source_task', target_id=task_record.id, message='Worker 执行热点抓取骨架任务', detail={
            'inserted_count': inserted_count,
            'batch_name': task_record.batch_name,
            'source_platform': task_record.source_platform,
        })
        db.session.commit()
        return {
            'success': True,
            'data_source_task_id': task_record.id,
            'inserted_count': inserted_count,
            'batch_name': task_record.batch_name,
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


@celery.task(name='jobs.assets.generate')
def generate_asset_images_job(asset_task_id):
    from app import (
        _image_provider_capabilities,
        _build_asset_provider_request_preview,
        _build_asset_generation_fallback_results,
        _log_operation,
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
    api_key = (os.environ.get('ASSET_IMAGE_API_KEY') or '').strip()
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
        )

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
        'registration_id': task.registration_id,
        'topic_id': task.topic_id,
    })
    db.session.commit()
    return {
        'success': True,
        'asset_task_id': task.id,
        'provider': actual_provider,
        'image_count': len(results),
    }
