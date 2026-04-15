from flask import jsonify, redirect, render_template, request, session, url_for

from models import (
    Activity,
    AssetGenerationTask,
    AssetLibrary,
    AutomationSchedule,
    CorpusEntry,
    DataSourceTask,
    Settings,
    TopicIdea,
    TrendNote,
)


def register_automation_dashboard_routes(app, helpers):
    admin_json_guard = helpers['admin_json_guard']
    default_topic_quota = helpers['default_topic_quota']
    asset_style_type_options = helpers['asset_style_type_options']
    image_provider_options = helpers['image_provider_options']
    image_provider_presets = helpers['image_provider_presets']
    image_model_options = helpers['image_model_options']
    safe_int = helpers['safe_int']
    build_readiness_checks = helpers['build_readiness_checks']
    build_project_status_payload = helpers['build_project_status_payload']
    bootstrap_demo_operational_data = helpers['bootstrap_demo_operational_data']
    clear_demo_operational_data = helpers['clear_demo_operational_data']
    build_deployment_helper_payload = helpers['build_deployment_helper_payload']
    build_deployment_blockers_payload = helpers['build_deployment_blockers_payload']
    build_integration_checklist_payload = helpers['build_integration_checklist_payload']
    build_capacity_readiness_payload = helpers['build_capacity_readiness_payload']
    build_recent_failed_jobs_payload = helpers['build_recent_failed_jobs_payload']
    build_service_matrix_payload = helpers['build_service_matrix_payload']
    hotword_runtime_settings = helpers['hotword_runtime_settings']
    creator_sync_runtime_settings = helpers['creator_sync_runtime_settings']
    image_provider_capabilities = helpers['image_provider_capabilities']
    image_provider_healthcheck = helpers['image_provider_healthcheck']
    image_provider_request_preview = helpers['build_asset_provider_request_preview']
    asset_prompt_from_context = helpers['build_asset_generation_prompt_from_context']
    asset_style_meta = helpers['asset_style_meta']
    hotword_source_template_meta = helpers['hotword_source_template_meta']
    hotword_source_template_options = helpers['hotword_source_template_options']
    hotword_remote_source_presets = helpers['hotword_remote_source_presets']
    automation_keyword_seeds = helpers['automation_keyword_seeds']
    build_hotword_remote_preview = helpers['build_hotword_remote_preview']
    resolved_hotword_mode = helpers['resolved_hotword_mode']
    build_creator_sync_remote_preview = helpers['build_creator_sync_remote_preview']
    resolved_creator_sync_mode = helpers['resolved_creator_sync_mode']
    tracked_creator_sync_targets = helpers['tracked_creator_sync_targets']
    log_operation = helpers['log_operation']

    @app.route('/automation_center')
    def automation_center():
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))

        activities = Activity.query.order_by(Activity.created_at.desc()).all()
        return render_template(
            'automation_center.html',
            activities=activities,
            default_topic_quota=default_topic_quota(),
            asset_style_types=asset_style_type_options(),
            image_provider_options=image_provider_options(),
            image_model_options=image_model_options('volcengine_las'),
        )

    @app.route('/api/automation/overview')
    def automation_overview():
        guard = admin_json_guard()
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
                'asset_library_items': AssetLibrary.query.count(),
                'automation_schedules': AutomationSchedule.query.count(),
                'enabled_schedules': AutomationSchedule.query.filter_by(enabled=True).count(),
            },
            'default_keywords': automation_keyword_seeds(),
            'capabilities': image_provider_capabilities(),
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
        guard = admin_json_guard()
        if guard:
            return guard

        task_type = (request.args.get('task_type') or '').strip()
        status = (request.args.get('status') or '').strip()
        source_platform = (request.args.get('source_platform') or '').strip()
        limit = min(max(safe_int(request.args.get('limit'), 20), 1), 100)

        query = DataSourceTask.query
        if task_type:
            query = query.filter_by(task_type=task_type)
        if status:
            query = query.filter_by(status=status)
        if source_platform:
            query = query.filter_by(source_platform=source_platform)

        items = query.order_by(DataSourceTask.created_at.desc(), DataSourceTask.id.desc()).limit(limit).all()
        return jsonify({
            'success': True,
            'items': [helpers['serialize_data_source_task'](item) for item in items]
        })

    @app.route('/api/admin/data-source-tasks/<int:task_id>')
    def data_source_task_detail(task_id):
        guard = admin_json_guard()
        if guard:
            return guard

        task = DataSourceTask.query.get_or_404(task_id)
        return jsonify({
            'success': True,
            'item': helpers['serialize_data_source_task'](task, detail=True),
        })

    @app.route('/api/admin/runtime-diagnostics')
    def runtime_diagnostics():
        guard = admin_json_guard()
        if guard:
            return guard

        hotword_settings = hotword_runtime_settings()
        hotword_health = helpers['hotword_healthcheck'](timeout_seconds=2)
        creator_sync_settings = creator_sync_runtime_settings()
        creator_sync_health = helpers['creator_sync_healthcheck'](timeout_seconds=2)
        image_health = image_provider_healthcheck(timeout_seconds=5)
        last_worker_ping = helpers['latest_worker_ping_snapshot']()
        worker_health_status = 'unknown'
        worker_health_message = '尚未执行 Worker 联通检查'
        if last_worker_ping.get('has_result'):
            if last_worker_ping.get('status') == 'success':
                worker_health_status = 'healthy'
                worker_health_message = last_worker_ping.get('message') or '最近一次 Worker 联通检查成功'
            else:
                worker_health_status = 'degraded'
                worker_health_message = last_worker_ping.get('message') or '最近一次 Worker 联通检查失败'

        schedules = AutomationSchedule.query.order_by(AutomationSchedule.id.asc()).all()
        next_runs = [{
            'job_key': item.job_key,
            'name': item.name,
            'enabled': bool(item.enabled),
            'next_run_at': helpers['format_datetime'](item.next_run_at),
            'last_status': item.last_status or 'idle',
        } for item in schedules[:10]]

        recent_jobs = helpers['operation_log_model'].query.filter(
            helpers['operation_log_model'].action.in_([
                'dispatch_job', 'worker_generate', 'worker_sync', 'worker_generate_asset', 'scheduler_tick', 'worker_ping_check', 'worker_ping_check_failed'
            ])
        ).order_by(helpers['operation_log_model'].created_at.desc()).limit(10).all()

        return jsonify({
            'success': True,
            'runtime': {
                'database_backend': 'sqlite' if helpers['is_sqlite_backend']() else 'postgresql',
                'database_url_configured': bool((helpers['os'].environ.get('DATABASE_URL') or '').strip()),
                'redis_url_configured': bool((helpers['os'].environ.get('REDIS_URL') or '').strip()),
                'celery_broker_configured': bool((helpers['os'].environ.get('CELERY_BROKER_URL') or '').strip()),
                'celery_backend_configured': bool((helpers['os'].environ.get('CELERY_RESULT_BACKEND') or '').strip()),
                'secret_key_configured': bool((helpers['os'].environ.get('SECRET_KEY') or '').strip()),
                'deepseek_configured': bool((helpers['os'].environ.get('DEEPSEEK_API_KEY') or '').strip()),
                'preferred_url_scheme': helpers['os'].environ.get('PREFERRED_URL_SCHEME', 'https'),
                'session_cookie_secure': helpers['env_flag']('SESSION_COOKIE_SECURE', False),
                'inline_automation_jobs': helpers['env_flag']('INLINE_AUTOMATION_JOBS', False),
                'default_topic_quota': default_topic_quota(),
                'beat_enabled': helpers['coerce_bool'](helpers['os'].environ.get('ENABLE_AUTOMATION_BEAT', 'true')),
                'hotword_fetch_mode': resolved_hotword_mode(hotword_settings),
                'hotword_api_url': hotword_settings.get('hotword_api_url') or '',
                'hotword_api_method': hotword_settings.get('hotword_api_method') or 'GET',
                'hotword_result_path': hotword_settings.get('hotword_result_path') or '',
                'hotword_auto_generate_topic_ideas': bool(hotword_settings.get('hotword_auto_generate_topic_ideas')),
                'hotword_auto_generate_topic_count': hotword_settings.get('hotword_auto_generate_topic_count') or 20,
                'creator_sync_fetch_mode': resolved_creator_sync_mode(creator_sync_settings),
                'creator_sync_api_url': creator_sync_settings.get('creator_sync_api_url') or '',
                'creator_sync_api_method': creator_sync_settings.get('creator_sync_api_method') or 'POST',
                'creator_sync_result_path': creator_sync_settings.get('creator_sync_result_path') or '',
            },
            'worker': {
                'broker_ready': bool((helpers['os'].environ.get('CELERY_BROKER_URL') or '').strip()),
                'result_backend_ready': bool((helpers['os'].environ.get('CELERY_RESULT_BACKEND') or '').strip()),
                'health_status': worker_health_status,
                'health_message': worker_health_message,
                'last_ping': last_worker_ping,
            },
            'hotword_health': hotword_health,
            'creator_sync_health': creator_sync_health,
            'image_health': image_health,
            'service_matrix': build_service_matrix_payload(),
            'deployment_blockers': build_deployment_blockers_payload(),
            'capacity': build_capacity_readiness_payload(),
            'capabilities': image_provider_capabilities(),
            'counts': {
                'activities': Activity.query.count(),
                'topics': helpers['topic_model'].query.count(),
                'registrations': helpers['registration_model'].query.count(),
                'submissions': helpers['submission_model'].query.count(),
                'trend_notes': TrendNote.query.count(),
                'corpus_entries': CorpusEntry.query.count(),
                'topic_ideas': TopicIdea.query.count(),
                'data_source_tasks': DataSourceTask.query.count(),
                'asset_generation_tasks': AssetGenerationTask.query.count(),
                'schedules': AutomationSchedule.query.count(),
                'enabled_schedules': AutomationSchedule.query.filter_by(enabled=True).count(),
            },
            'schedules': next_runs,
            'recent_jobs': [helpers['serialize_operation_log'](item) for item in recent_jobs],
        })

    @app.route('/api/admin/readiness-check')
    def readiness_check():
        guard = admin_json_guard()
        if guard:
            return guard
        checks = build_readiness_checks()
        return jsonify({'success': True, **checks})

    @app.route('/api/admin/project-status')
    def project_status():
        guard = admin_json_guard()
        if guard:
            return guard
        return jsonify(build_project_status_payload())

    @app.route('/api/admin/project-status/bootstrap-demo-data', methods=['POST'])
    def bootstrap_project_demo_data():
        guard = admin_json_guard()
        if guard:
            return guard
        result = bootstrap_demo_operational_data()
        db.session.commit()
        return jsonify({'success': True, **result, 'project_status': build_project_status_payload()})

    @app.route('/api/admin/project-status/clear-demo-data', methods=['POST'])
    def clear_project_demo_data():
        guard = admin_json_guard()
        if guard:
            return guard
        result = clear_demo_operational_data()
        db.session.commit()
        return jsonify({'success': True, **result, 'project_status': build_project_status_payload()})

    @app.route('/api/admin/deployment-helper')
    def deployment_helper():
        guard = admin_json_guard()
        if guard:
            return guard
        return jsonify(build_deployment_helper_payload())

    @app.route('/api/admin/integration-checklist')
    def integration_checklist():
        guard = admin_json_guard()
        if guard:
            return guard
        return jsonify({
            'success': True,
            'items': build_integration_checklist_payload(),
        })

    @app.route('/api/admin/failed-jobs')
    def failed_jobs():
        guard = admin_json_guard()
        if guard:
            return guard
        limit = request.args.get('limit')
        return jsonify(build_recent_failed_jobs_payload(limit=limit))

    @app.route('/api/admin/automation-config', methods=['GET', 'POST'])
    def automation_config():
        guard = admin_json_guard()
        if guard:
            return guard

        if request.method == 'POST':
            data = request.json or {}
            current = _automation_runtime_config()
            next_config = dict(current)
            next_config['hotword_source_platform'] = (data.get('hotword_source_platform') or current['hotword_source_platform']).strip()[:50]
            next_config['hotword_source_template'] = (data.get('hotword_source_template') or current['hotword_source_template']).strip()[:50]
            next_config['hotword_source_channel'] = (data.get('hotword_source_channel') or current['hotword_source_channel']).strip()[:50]
            next_config['hotword_keyword_limit'] = min(max(safe_int(data.get('hotword_keyword_limit'), current['hotword_keyword_limit']), 1), 30)
            next_config['hotword_fetch_mode'] = (data.get('hotword_fetch_mode') or current.get('hotword_fetch_mode') or 'auto').strip()[:20]
            next_config['hotword_api_url'] = (data.get('hotword_api_url') or current.get('hotword_api_url') or '').strip()[:500]
            next_config['hotword_api_method'] = (data.get('hotword_api_method') or current.get('hotword_api_method') or 'GET').strip()[:10]
            next_config['hotword_api_headers_json'] = (data.get('hotword_api_headers_json') or current.get('hotword_api_headers_json') or '').strip()[:4000]
            next_config['hotword_api_query_json'] = (data.get('hotword_api_query_json') or current.get('hotword_api_query_json') or '').strip()[:4000]
            next_config['hotword_api_body_json'] = (data.get('hotword_api_body_json') or current.get('hotword_api_body_json') or '').strip()[:4000]
            next_config['hotword_result_path'] = (data.get('hotword_result_path') or current.get('hotword_result_path') or '').strip()[:200]
            next_config['hotword_keyword_param'] = (data.get('hotword_keyword_param') or current.get('hotword_keyword_param') or 'keyword').strip()[:50]
            next_config['hotword_timeout_seconds'] = min(max(safe_int(data.get('hotword_timeout_seconds'), current.get('hotword_timeout_seconds') or 30), 5), 120)
            next_config['hotword_auto_generate_topic_ideas'] = helpers['coerce_bool'](data.get('hotword_auto_generate_topic_ideas'))
            next_config['hotword_auto_generate_topic_count'] = min(max(safe_int(data.get('hotword_auto_generate_topic_count'), current.get('hotword_auto_generate_topic_count') or 20), 1), 120)
            next_config['hotword_auto_generate_topic_activity_id'] = max(safe_int(data.get('hotword_auto_generate_topic_activity_id'), current.get('hotword_auto_generate_topic_activity_id') or 0), 0)
            next_config['hotword_auto_generate_topic_quota'] = min(max(safe_int(data.get('hotword_auto_generate_topic_quota'), current.get('hotword_auto_generate_topic_quota') or default_topic_quota()), 1), 300)
            next_config['creator_sync_source_channel'] = (data.get('creator_sync_source_channel') or current.get('creator_sync_source_channel') or 'Crawler服务').strip()[:50]
            next_config['creator_sync_fetch_mode'] = (data.get('creator_sync_fetch_mode') or current.get('creator_sync_fetch_mode') or 'auto').strip()[:20]
            next_config['creator_sync_api_url'] = (data.get('creator_sync_api_url') or current.get('creator_sync_api_url') or '').strip()[:500]
            next_config['creator_sync_api_method'] = (data.get('creator_sync_api_method') or current.get('creator_sync_api_method') or 'POST').strip()[:10]
            next_config['creator_sync_api_headers_json'] = (data.get('creator_sync_api_headers_json') or current.get('creator_sync_api_headers_json') or '').strip()[:4000]
            next_config['creator_sync_api_query_json'] = (data.get('creator_sync_api_query_json') or current.get('creator_sync_api_query_json') or '').strip()[:4000]
            next_config['creator_sync_api_body_json'] = (data.get('creator_sync_api_body_json') or current.get('creator_sync_api_body_json') or '').strip()[:4000]
            next_config['creator_sync_result_path'] = (data.get('creator_sync_result_path') or current.get('creator_sync_result_path') or '').strip()[:200]
            next_config['creator_sync_timeout_seconds'] = min(max(safe_int(data.get('creator_sync_timeout_seconds'), current.get('creator_sync_timeout_seconds') or 60), 5), 300)
            next_config['creator_sync_batch_limit'] = min(max(safe_int(data.get('creator_sync_batch_limit'), current.get('creator_sync_batch_limit') or 20), 1), 200)
            next_config['image_provider'] = (data.get('image_provider') or current['image_provider']).strip()[:50]
            next_config['image_api_base'] = (data.get('image_api_base') or current['image_api_base']).strip()[:500]
            next_config['image_api_url'] = (data.get('image_api_url') or current['image_api_url']).strip()[:500]
            next_config['image_model'] = (data.get('image_model') or current['image_model']).strip()[:100]
            next_config['image_size'] = (data.get('image_size') or current['image_size']).strip()[:50]
            next_config['image_timeout_seconds'] = min(max(safe_int(data.get('image_timeout_seconds'), current['image_timeout_seconds']), 10), 300)
            next_config['image_style_preset'] = (data.get('image_style_preset') or current['image_style_preset']).strip()[:50]
            next_config['image_default_style_type'] = (data.get('image_default_style_type') or current['image_default_style_type']).strip()[:50]
            next_config['image_optimize_prompt_mode'] = (data.get('image_optimize_prompt_mode') or current['image_optimize_prompt_mode']).strip()[:50]
            next_config['image_prompt_suffix'] = (data.get('image_prompt_suffix') or current['image_prompt_suffix']).strip()[:500]

            setting = Settings.query.filter_by(key='automation_runtime_config').first()
            if not setting:
                setting = Settings(key='automation_runtime_config', value='{}')
                db.session.add(setting)
            setting.value = helpers['json'].dumps(next_config, ensure_ascii=False)
            log_operation('save', 'automation_runtime_config', message='更新自动化运维配置', detail=next_config)
            db.session.commit()

        runtime_config = hotword_runtime_settings()
        creator_runtime_config = creator_sync_runtime_settings()
        runtime_config.update(creator_runtime_config)
        capabilities = image_provider_capabilities()
        return jsonify({
            'success': True,
            'config': runtime_config,
            'capabilities': capabilities,
            'provider_options': image_provider_options(),
            'provider_presets': image_provider_presets(),
            'style_types': asset_style_type_options(),
            'model_options': image_model_options(runtime_config.get('image_provider')),
            'hotword_templates': hotword_source_template_options(),
            'hotword_remote_presets': hotword_remote_source_presets(),
            'notes': {
                'api_key_managed_by_env': True,
                'api_key_configured': capabilities.get('api_key_configured', False),
            }
        })

    @app.route('/api/admin/automation-config/preview')
    def automation_config_preview():
        guard = admin_json_guard()
        if guard:
            return guard

        runtime_config = hotword_runtime_settings()
        creator_runtime_config = creator_sync_runtime_settings()
        runtime_config.update(creator_runtime_config)
        capabilities = image_provider_capabilities()
        hotword_preview = {
            'source_platform': runtime_config.get('hotword_source_platform'),
            'source_template': runtime_config.get('hotword_source_template'),
            'source_channel': runtime_config.get('hotword_source_channel'),
            'keyword_limit': runtime_config.get('hotword_keyword_limit'),
            'keywords': automation_keyword_seeds()[:min(max(safe_int(runtime_config.get('hotword_keyword_limit'), 10), 1), 10)],
            'fetch_mode': resolved_hotword_mode(runtime_config),
            'api_url': runtime_config.get('hotword_api_url') or '',
            'api_method': runtime_config.get('hotword_api_method') or 'GET',
            'result_path': runtime_config.get('hotword_result_path') or '',
            'keyword_param': runtime_config.get('hotword_keyword_param') or 'keyword',
            'timeout_seconds': runtime_config.get('hotword_timeout_seconds') or 30,
            'auto_generate_topic_ideas': bool(runtime_config.get('hotword_auto_generate_topic_ideas')),
            'auto_generate_topic_count': runtime_config.get('hotword_auto_generate_topic_count') or 20,
            'auto_generate_topic_activity_id': runtime_config.get('hotword_auto_generate_topic_activity_id') or 0,
            'auto_generate_topic_activity_resolved_id': helpers['default_activity_id_for_automation']() if bool(runtime_config.get('hotword_auto_generate_topic_ideas')) and not (runtime_config.get('hotword_auto_generate_topic_activity_id') or 0) else (runtime_config.get('hotword_auto_generate_topic_activity_id') or 0),
            'auto_generate_topic_quota': runtime_config.get('hotword_auto_generate_topic_quota') or default_topic_quota(),
        }
        hotword_request_preview = {}
        hotword_preview_error = ''
        if hotword_preview['fetch_mode'] == 'remote':
            try:
                hotword_request_preview = build_hotword_remote_preview(
                    runtime_config,
                    hotword_preview['keywords'],
                    source_platform=hotword_preview['source_platform'],
                    source_channel=hotword_preview['source_channel'],
                    batch_name='preview_runtime_config',
                )
            except Exception as exc:
                hotword_preview_error = str(exc)
        creator_sync_targets = tracked_creator_sync_targets(
            limit=min(max(safe_int(creator_runtime_config.get('creator_sync_batch_limit'), 20), 1), 10)
        )
        creator_sync_preview = {
            'source_channel': creator_runtime_config.get('creator_sync_source_channel') or 'Crawler服务',
            'fetch_mode': resolved_creator_sync_mode(creator_runtime_config),
            'api_url': creator_runtime_config.get('creator_sync_api_url') or '',
            'api_method': creator_runtime_config.get('creator_sync_api_method') or 'POST',
            'result_path': creator_runtime_config.get('creator_sync_result_path') or '',
            'timeout_seconds': creator_runtime_config.get('creator_sync_timeout_seconds') or 60,
            'batch_limit': creator_runtime_config.get('creator_sync_batch_limit') or 20,
            'target_count': len(creator_sync_targets),
            'sample_targets': creator_sync_targets[:3],
        }
        creator_sync_request_preview = {}
        creator_sync_preview_error = ''
        if creator_sync_preview['fetch_mode'] == 'remote':
            try:
                creator_sync_request_preview = build_creator_sync_remote_preview(
                    creator_runtime_config,
                    creator_sync_targets,
                    source_channel=creator_sync_preview['source_channel'],
                    batch_name='preview_creator_sync',
                )
            except Exception as exc:
                creator_sync_preview_error = str(exc)
        image_prompt_preview = asset_prompt_from_context(
            topic_name='脂肪肝管理',
            topic_keywords='脂肪肝,瘦型脂肪肝,内脏脂肪',
            selected_content='标题：什么是瘦型脂肪肝？\n内文：体重正常也可能有脂肪肝。先解释成因，再讲风险和检查建议，适合做收藏型知识卡片。',
            style_preset=capabilities.get('image_default_style_type') or runtime_config.get('image_default_style_type') or 'medical_science',
            title_hint='什么是瘦型脂肪肝？',
        )
        image_request_preview = image_provider_request_preview(
            capabilities.get('image_provider_name'),
            capabilities.get('image_provider_model'),
            image_prompt_preview + (' ' + capabilities.get('image_prompt_suffix', '') if capabilities.get('image_prompt_suffix') else ''),
            capabilities.get('image_provider_size'),
            asset_style_meta(capabilities.get('image_default_style_type')).get('label'),
            image_count=3,
        )
        return jsonify({
            'success': True,
            'hotword_preview': hotword_preview,
            'hotword_template': hotword_source_template_meta(runtime_config.get('hotword_source_template')),
            'hotword_request_preview': hotword_request_preview,
            'hotword_preview_error': hotword_preview_error,
            'creator_sync_preview': creator_sync_preview,
            'creator_sync_request_preview': creator_sync_request_preview,
            'creator_sync_preview_error': creator_sync_preview_error,
            'image_request_preview': image_request_preview,
            'capabilities': capabilities,
            'style_meta': asset_style_meta(capabilities.get('image_default_style_type')),
        })
