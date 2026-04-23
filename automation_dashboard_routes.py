import json

from flask import Response, jsonify, redirect, render_template, request, session, url_for

from models import (
    Activity,
    AssetGenerationTask,
    AssetLibrary,
    AssetPlanDraft,
    AutomationSchedule,
    CorpusEntry,
    DataSourceTask,
    HotTopicEntry,
    LiverIpProfilePlan,
    Settings,
    TopicIdea,
    TrendNote,
    db,
)


def register_automation_dashboard_routes(app, helpers):
    admin_json_guard = helpers['admin_json_guard']
    default_topic_quota = helpers['default_topic_quota']
    asset_style_type_options = helpers['asset_style_type_options']
    image_provider_options = helpers['image_provider_options']
    image_provider_presets = helpers['image_provider_presets']
    image_model_options = helpers['image_model_options']
    product_category_options = helpers['product_category_options']
    product_visual_role_options = helpers['product_visual_role_options']
    product_profile_options = helpers['product_profile_options']
    safe_int = helpers['safe_int']
    build_readiness_checks = helpers['build_readiness_checks']
    build_project_status_payload = helpers['build_project_status_payload']
    bootstrap_demo_operational_data = helpers['bootstrap_demo_operational_data']
    clear_demo_operational_data = helpers['clear_demo_operational_data']
    build_deployment_helper_payload = helpers['build_deployment_helper_payload']
    build_deployment_blockers_payload = helpers['build_deployment_blockers_payload']
    build_launch_milestones_payload = helpers['build_launch_milestones_payload']
    build_integration_checklist_payload = helpers['build_integration_checklist_payload']
    build_integration_ping_history_payload = helpers['build_integration_ping_history_payload']
    build_first_run_playbooks_payload = helpers['build_first_run_playbooks_payload']
    build_integration_contract_payload = helpers['build_integration_contract_payload']
    build_integration_acceptance_payload = helpers['build_integration_acceptance_payload']
    build_trial_readiness_payload = helpers['build_trial_readiness_payload']
    build_go_live_readiness_payload = helpers['build_go_live_readiness_payload']
    build_go_live_checklist_payload = helpers['build_go_live_checklist_payload']
    build_post_launch_watchlist_payload = helpers['build_post_launch_watchlist_payload']
    build_integration_handoff_pack_payload = helpers['build_integration_handoff_pack_payload']
    build_capacity_readiness_payload = helpers['build_capacity_readiness_payload']
    build_recent_failed_jobs_payload = helpers['build_recent_failed_jobs_payload']
    build_service_matrix_payload = helpers['build_service_matrix_payload']
    build_crawler_probe_payload = helpers['build_crawler_probe_payload']
    automation_runtime_config = helpers['automation_runtime_config']
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
    copywriter_capabilities = helpers['copywriter_capabilities']
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
            image_model_options=image_model_options(image_provider_capabilities().get('image_provider_name') or 'svg_fallback'),
            product_category_options=product_category_options(),
            product_visual_role_options=product_visual_role_options(),
            product_profile_options=product_profile_options(),
        )

    def build_weekly_delivery_payload():
        project_status = build_project_status_payload()
        trial = build_trial_readiness_payload()
        go_live = build_go_live_readiness_payload()
        go_live_checklist = build_go_live_checklist_payload()
        counts = dict(project_status.get('counts') or {})
        counts.update({
            'active_hot_topics': HotTopicEntry.query.filter_by(status='active').count(),
            'asset_plan_drafts': AssetPlanDraft.query.filter_by(status='active').count(),
            'draft_asset_tasks': AssetGenerationTask.query.filter_by(status='draft').count(),
            'completed_asset_tasks': AssetGenerationTask.query.filter_by(status='success').count(),
            'liver_ip_profiles': LiverIpProfilePlan.query.count(),
        })
        external_dependencies = list((project_status.get('summary') or {}).get('external_dependencies') or [])
        image_capability = image_provider_capabilities()

        def module_card(key, label, status, progress, summary, completed, remaining, evidence=''):
            return {
                'key': key,
                'label': label,
                'status': status,
                'status_label': {
                    'ready': 'V1可交付',
                    'attention': '还需收口',
                    'blocked': '存在阻塞',
                }.get(status, status),
                'progress': progress,
                'summary': summary,
                'completed': completed,
                'remaining': remaining,
                'evidence': evidence,
            }

        modules = [
            module_card(
                'ip_agent',
                '肝健康IP Agent',
                'ready',
                90,
                '已经具备 IP 规划、方向/人设/栏目规划、持久化和“保存并去生成文案”的主链路。',
                [
                    '肝健康IP 页面、方向地图、人设地图已上线',
                    'IP Agent 结果可保存到数据库并带去生成页',
                    '科普内容、栏目规划、爆款案例和模板语料已能集中展示',
                ],
                [
                    '多轮连续对话体验仍可继续增强',
                    '长期成长档案和数据反馈可作为下一阶段优化',
                ],
                evidence=f'IP规划档案 {counts.get("liver_ip_profiles", 0)} 条',
            ),
            module_card(
                'copy_image',
                '文案 + 图片一键生成',
                'ready' if image_capability.get('image_provider_configured') or counts.get('draft_asset_tasks') or counts.get('completed_asset_tasks') else 'attention',
                92 if (image_capability.get('image_provider_configured') or counts.get('draft_asset_tasks') or counts.get('completed_asset_tasks')) else 84,
                '已经具备技能包、标题池、封面推荐、图片模板 Agent、图片草案池、待执行任务与正式派发链路，文案模型也已纳入可配置和可检测状态。',
                [
                    '文案生成支持方向、人设、写作/标题/图片技能包',
                    '文案模型支持 DeepSeek 或其他 OpenAI 兼容模型',
                    '热搜和候选话题都能走图片模板分桶',
                    '草案可保留、忽略、套用、保存、转待执行任务',
                    '待执行任务已支持补报名ID后正式派发',
                ],
                [
                    '文案模型仍建议完成正式联调验收，避免回退本地兜底',
                    '真实图片 provider 还建议继续做稳定性回归',
                    '批量执行后的审批和运营动作还能继续打磨',
                ],
                evidence=f'图片草案 {counts.get("asset_plan_drafts", 0)} 条 ｜ 待执行任务 {counts.get("draft_asset_tasks", 0)} 条 ｜ 已完成任务 {counts.get("completed_asset_tasks", 0)} 条',
            ),
            module_card(
                'automation',
                '自动化热点规划',
                'attention' if external_dependencies else 'ready',
                88 if external_dependencies else 93,
                '已经具备三块搜索、时间窗口、热点确认分流、热搜话题页、候选话题池、图片模板分桶和草案工作台。',
                [
                    '支持近3天 / 近7天 / 近30天 / 自定义日期',
                    '支持肝病+共病 / 科普问题 / 平台热搜 三块自动搜索',
                    '热点结果可进入当前广场 / 下一期 / IP栏目 / 热搜话题',
                    '热点与候选话题都能直接走图片模板分桶与草案流程',
                ],
                [
                    '真实热点 / 账号同步 / 图片接口的最终上线验收仍受外部依赖影响',
                    '生产级调度容错和持续回归仍建议在本周收口后继续压测',
                ],
                evidence=f'热点 {counts.get("trend_notes", 0)} 条 ｜ 候选话题 {counts.get("topic_ideas", 0)} 条 ｜ 热搜话题 {counts.get("active_hot_topics", 0)} 条',
            ),
        ]

        return {
            'success': True,
            'summary': {
                'delivery_status': '本周可冲 V1 收口',
                'updated_at': project_status.get('updated_at') or '',
                'current_stage': (project_status.get('summary') or {}).get('current_stage') or '',
                'readiness_rate': (project_status.get('summary') or {}).get('readiness_rate') or 0,
                'key_message': (project_status.get('summary') or {}).get('key_message') or '',
                'trial_status_label': (trial.get('summary') or {}).get('overall_status_label') or '',
                'go_live_status_label': (go_live.get('summary') or {}).get('overall_status_label') or '',
            },
            'counts': counts,
            'this_week_definition': [
                '定义“完成”为 V1 可演示、可运营、可继续联调，不追求所有理想功能一次拉满。',
                '三大板块必须打通主链路：IP Agent、图文生成、自动化规划。',
                '自动发现内容默认先进候选区或草案区，必须经过人工确认后再执行。',
            ],
            'modules': modules,
            'external_blockers': [
                {
                    'label': item,
                    'detail': '这是影响正式验收和上线判断的外部条件，不影响继续做内部功能收口。'
                }
                for item in external_dependencies
            ] or [{
                'label': '当前没有明显外部阻塞项',
                'detail': '可以继续按验收和回归节奏推进本周收口。',
            }],
            'launch_checklist': (go_live_checklist.get('items') or [])[:8],
            'not_in_this_week': [
                '多轮长期记忆型 Agent',
                '生产级调度容错与异常恢复的全面压测',
                '所有图片供应商/模型的深度成本优化',
            ],
        }

    @app.route('/admin/weekly-delivery')
    def weekly_delivery_page():
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return render_template('weekly_delivery.html', payload=build_weekly_delivery_payload())

    @app.route('/api/admin/weekly-delivery')
    def weekly_delivery_payload():
        guard = admin_json_guard()
        if guard:
            return guard
        return jsonify(build_weekly_delivery_payload())

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
                'active_hot_topics': HotTopicEntry.query.filter_by(status='active').count(),
                'data_source_tasks': DataSourceTask.query.count(),
                'running_data_source_tasks': DataSourceTask.query.filter(DataSourceTask.status.in_(['queued', 'running'])).count(),
                'asset_generation_tasks': AssetGenerationTask.query.count(),
                'draft_asset_tasks': AssetGenerationTask.query.filter_by(status='draft').count(),
                'completed_asset_tasks': AssetGenerationTask.query.filter_by(status='success').count(),
                'active_asset_plan_drafts': AssetPlanDraft.query.filter_by(status='active').count(),
                'asset_library_items': AssetLibrary.query.count(),
                'automation_schedules': AutomationSchedule.query.count(),
                'enabled_schedules': AutomationSchedule.query.filter_by(enabled=True).count(),
            },
            'default_keywords': automation_keyword_seeds(),
            'capabilities': image_provider_capabilities(),
            'copywriter': copywriter_capabilities(),
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
        copywriter_health = helpers['copywriter_healthcheck'](timeout_seconds=5)
        copywriter = helpers['copywriter_capabilities']()
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
                'copywriter_configured': bool(copywriter.get('copywriter_configured')),
                'copywriter_provider': copywriter.get('copywriter_provider') or '',
                'copywriter_model': copywriter.get('copywriter_model') or '',
                'preferred_url_scheme': helpers['os'].environ.get('PREFERRED_URL_SCHEME', 'https'),
                'session_cookie_secure': helpers['env_flag']('SESSION_COOKIE_SECURE', False),
                'inline_automation_jobs': helpers['env_flag']('INLINE_AUTOMATION_JOBS', False),
                'default_topic_quota': default_topic_quota(),
                'beat_enabled': helpers['coerce_bool'](helpers['os'].environ.get('ENABLE_AUTOMATION_BEAT', 'true')),
                'hotword_fetch_mode': resolved_hotword_mode(hotword_settings),
                'hotword_api_url': hotword_settings.get('hotword_api_url') or '',
                'hotword_api_method': hotword_settings.get('hotword_api_method') or 'GET',
                'hotword_result_path': hotword_settings.get('hotword_result_path') or '',
                'hotword_trend_type': hotword_settings.get('hotword_trend_type') or 'note_search',
                'hotword_page_size': hotword_settings.get('hotword_page_size') or 20,
                'hotword_max_related_queries': hotword_settings.get('hotword_max_related_queries') or 20,
                'hotword_auto_generate_topic_ideas': bool(hotword_settings.get('hotword_auto_generate_topic_ideas')),
                'hotword_auto_generate_topic_count': hotword_settings.get('hotword_auto_generate_topic_count') or 20,
                'hotword_auto_convert_corpus_templates': bool(hotword_settings.get('hotword_auto_convert_corpus_templates')),
                'hotword_auto_convert_corpus_limit': hotword_settings.get('hotword_auto_convert_corpus_limit') or 10,
                'creator_sync_fetch_mode': resolved_creator_sync_mode(creator_sync_settings),
                'creator_sync_api_url': creator_sync_settings.get('creator_sync_api_url') or '',
                'creator_sync_api_method': creator_sync_settings.get('creator_sync_api_method') or 'POST',
                'creator_sync_result_path': creator_sync_settings.get('creator_sync_result_path') or '',
                'creator_sync_current_month_only': bool(creator_sync_settings.get('creator_sync_current_month_only')),
                'creator_sync_date_from': creator_sync_settings.get('creator_sync_date_from') or '',
                'creator_sync_date_to': creator_sync_settings.get('creator_sync_date_to') or '',
                'creator_sync_max_posts_per_account': creator_sync_settings.get('creator_sync_max_posts_per_account') or 60,
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
            'copywriter_health': copywriter_health,
            'image_health': image_health,
            'service_matrix': build_service_matrix_payload(),
            'crawler_probe': build_crawler_probe_payload(),
            'deployment_blockers': build_deployment_blockers_payload(),
            'launch_milestones': build_launch_milestones_payload(
                hotword_health=hotword_health,
                creator_sync_health=creator_sync_health,
                image_health=image_health,
            ),
            'capacity': build_capacity_readiness_payload(),
            'capabilities': image_provider_capabilities(),
            'copywriter': copywriter,
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

    @app.route('/api/admin/integration-pings')
    def integration_pings():
        guard = admin_json_guard()
        if guard:
            return guard
        limit = request.args.get('limit')
        return jsonify(build_integration_ping_history_payload(limit=limit))

    @app.route('/api/admin/first-run-playbooks')
    def first_run_playbooks():
        guard = admin_json_guard()
        if guard:
            return guard
        return jsonify(build_first_run_playbooks_payload())

    @app.route('/api/admin/integration-contracts')
    def integration_contracts():
        guard = admin_json_guard()
        if guard:
            return guard
        return jsonify(build_integration_contract_payload())

    @app.route('/api/admin/integration-acceptance')
    def integration_acceptance():
        guard = admin_json_guard()
        if guard:
            return guard
        return jsonify(build_integration_acceptance_payload())

    @app.route('/api/admin/trial-readiness')
    def trial_readiness():
        guard = admin_json_guard()
        if guard:
            return guard
        return jsonify(build_trial_readiness_payload())

    @app.route('/api/admin/go-live-readiness')
    def go_live_readiness():
        guard = admin_json_guard()
        if guard:
            return guard
        return jsonify(build_go_live_readiness_payload())

    @app.route('/api/admin/go-live-checklist')
    def go_live_checklist():
        guard = admin_json_guard()
        if guard:
            return guard
        return jsonify(build_go_live_checklist_payload())

    @app.route('/api/admin/post-launch-watchlist')
    def post_launch_watchlist():
        guard = admin_json_guard()
        if guard:
            return guard
        return jsonify(build_post_launch_watchlist_payload())

    @app.route('/api/admin/integration-handoff-pack')
    def integration_handoff_pack():
        guard = admin_json_guard()
        if guard:
            return guard
        scope = (request.args.get('scope') or 'all').strip()
        return jsonify(build_integration_handoff_pack_payload(scope=scope))

    @app.route('/api/admin/integration-handoff-pack/export')
    def export_integration_handoff_pack():
        guard = admin_json_guard()
        if guard:
            return guard
        scope = (request.args.get('scope') or 'all').strip()
        payload = build_integration_handoff_pack_payload(scope=scope)
        filename_scope = (payload.get('summary', {}).get('scope') or 'all').strip() or 'all'
        filename = f'integration_handoff_pack_{filename_scope}.json'
        body = json.dumps(payload.get('package') or {}, ensure_ascii=False, indent=2)
        return Response(
            body,
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment; filename=\"{filename}\"'
            }
        )

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
            current = automation_runtime_config()
            next_config = dict(current)
            next_config['hotword_source_platform'] = (data.get('hotword_source_platform') or current['hotword_source_platform']).strip()[:50]
            next_config['hotword_source_template'] = (data.get('hotword_source_template') or current['hotword_source_template']).strip()[:50]
            next_config['hotword_source_channel'] = (data.get('hotword_source_channel') or current['hotword_source_channel']).strip()[:50]
            next_config['hotword_keyword_limit'] = min(max(safe_int(data.get('hotword_keyword_limit'), current['hotword_keyword_limit']), 1), 30)
            next_config['hotword_scope_preset'] = (data.get('hotword_scope_preset') or current.get('hotword_scope_preset') or 'liver_comorbidity').strip()[:50]
            next_config['hotword_time_window'] = (data.get('hotword_time_window') or current.get('hotword_time_window') or '30d').strip()[:20]
            next_config['hotword_date_from'] = (data.get('hotword_date_from') or current.get('hotword_date_from') or '').strip()[:20]
            next_config['hotword_date_to'] = (data.get('hotword_date_to') or current.get('hotword_date_to') or '').strip()[:20]
            next_config['hotword_fetch_mode'] = (data.get('hotword_fetch_mode') or current.get('hotword_fetch_mode') or 'auto').strip()[:20]
            next_config['hotword_api_url'] = (data.get('hotword_api_url') or current.get('hotword_api_url') or '').strip()[:500]
            next_config['hotword_api_method'] = (data.get('hotword_api_method') or current.get('hotword_api_method') or 'GET').strip()[:10]
            next_config['hotword_api_headers_json'] = (data.get('hotword_api_headers_json') or current.get('hotword_api_headers_json') or '').strip()[:4000]
            next_config['hotword_api_query_json'] = (data.get('hotword_api_query_json') or current.get('hotword_api_query_json') or '').strip()[:4000]
            next_config['hotword_api_body_json'] = (data.get('hotword_api_body_json') or current.get('hotword_api_body_json') or '').strip()[:4000]
            next_config['hotword_result_path'] = (data.get('hotword_result_path') or current.get('hotword_result_path') or '').strip()[:200]
            next_config['hotword_keyword_param'] = (data.get('hotword_keyword_param') or current.get('hotword_keyword_param') or 'keyword').strip()[:50]
            next_config['hotword_timeout_seconds'] = min(max(safe_int(data.get('hotword_timeout_seconds'), current.get('hotword_timeout_seconds') or 30), 5), 120)
            next_config['hotword_trend_type'] = (data.get('hotword_trend_type') or current.get('hotword_trend_type') or 'note_search').strip()[:30]
            next_config['hotword_page_size'] = min(max(safe_int(data.get('hotword_page_size'), current.get('hotword_page_size') or 20), 1), 50)
            next_config['hotword_max_related_queries'] = min(max(safe_int(data.get('hotword_max_related_queries'), current.get('hotword_max_related_queries') or 20), 1), 50)
            next_config['hotword_auto_generate_topic_ideas'] = helpers['coerce_bool'](data.get('hotword_auto_generate_topic_ideas'))
            next_config['hotword_auto_generate_topic_count'] = min(max(safe_int(data.get('hotword_auto_generate_topic_count'), current.get('hotword_auto_generate_topic_count') or 20), 1), 120)
            next_config['hotword_auto_generate_topic_activity_id'] = max(safe_int(data.get('hotword_auto_generate_topic_activity_id'), current.get('hotword_auto_generate_topic_activity_id') or 0), 0)
            next_config['hotword_auto_generate_topic_quota'] = min(max(safe_int(data.get('hotword_auto_generate_topic_quota'), current.get('hotword_auto_generate_topic_quota') or default_topic_quota()), 1), 300)
            next_config['hotword_auto_convert_corpus_templates'] = helpers['coerce_bool'](data.get('hotword_auto_convert_corpus_templates'))
            next_config['hotword_auto_convert_corpus_limit'] = min(max(safe_int(data.get('hotword_auto_convert_corpus_limit'), current.get('hotword_auto_convert_corpus_limit') or 10), 1), 50)
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
            next_config['creator_sync_current_month_only'] = helpers['coerce_bool'](
                data.get('creator_sync_current_month_only')
                if 'creator_sync_current_month_only' in data
                else current.get('creator_sync_current_month_only')
            )
            next_config['creator_sync_date_from'] = (
                data.get('creator_sync_date_from')
                if 'creator_sync_date_from' in data
                else current.get('creator_sync_date_from') or ''
            ).strip()[:20]
            next_config['creator_sync_date_to'] = (
                data.get('creator_sync_date_to')
                if 'creator_sync_date_to' in data
                else current.get('creator_sync_date_to') or ''
            ).strip()[:20]
            next_config['creator_sync_max_posts_per_account'] = min(max(
                safe_int(data.get('creator_sync_max_posts_per_account'), current.get('creator_sync_max_posts_per_account') or 60),
                1,
            ), 100)
            next_config['copywriter_api_url'] = (data.get('copywriter_api_url') or current.get('copywriter_api_url') or '').strip()[:500]
            next_config['copywriter_model'] = (data.get('copywriter_model') or current.get('copywriter_model') or '').strip()[:100]
            next_config['copywriter_backup_api_url'] = (data.get('copywriter_backup_api_url') or current.get('copywriter_backup_api_url') or '').strip()[:500]
            next_config['copywriter_backup_model'] = (data.get('copywriter_backup_model') or current.get('copywriter_backup_model') or '').strip()[:100]
            next_config['copywriter_third_api_url'] = (data.get('copywriter_third_api_url') or current.get('copywriter_third_api_url') or '').strip()[:500]
            next_config['copywriter_third_model'] = (data.get('copywriter_third_model') or current.get('copywriter_third_model') or '').strip()[:100]
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
        copywriter = copywriter_capabilities()
        return jsonify({
            'success': True,
            'config': runtime_config,
            'capabilities': capabilities,
            'copywriter': copywriter,
            'provider_options': image_provider_options(),
            'provider_presets': image_provider_presets(),
            'style_types': asset_style_type_options(),
            'model_options': image_model_options(runtime_config.get('image_provider')),
            'hotword_templates': hotword_source_template_options(),
            'hotword_remote_presets': hotword_remote_source_presets(),
            'notes': {
                'api_key_managed_by_env': True,
                'api_key_configured': capabilities.get('api_key_configured', False),
                'copywriter_key_configured': copywriter.get('api_key_configured', False),
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
        copywriter = copywriter_capabilities()
        resolved_window = helpers['resolve_hotword_date_window'](
            runtime_config.get('hotword_time_window') or '30d',
            runtime_config.get('hotword_date_from') or '',
            runtime_config.get('hotword_date_to') or '',
        )
        runtime_config['hotword_date_from'] = resolved_window.get('date_from') or ''
        runtime_config['hotword_date_to'] = resolved_window.get('date_to') or ''
        scope_meta = helpers['hotword_scope_preset_meta'](runtime_config.get('hotword_scope_preset') or '')
        hotword_preview = {
            'source_platform': runtime_config.get('hotword_source_platform'),
            'source_template': runtime_config.get('hotword_source_template'),
            'source_channel': runtime_config.get('hotword_source_channel'),
            'keyword_limit': runtime_config.get('hotword_keyword_limit'),
            'scope_preset': runtime_config.get('hotword_scope_preset') or 'liver_comorbidity',
            'scope_label': scope_meta.get('label') or '',
            'time_window': resolved_window.get('window_key') or '30d',
            'time_window_label': resolved_window.get('label') or '',
            'date_from': resolved_window.get('date_from') or '',
            'date_to': resolved_window.get('date_to') or '',
            'keywords': helpers['resolve_hotword_scope_keywords'](
                runtime_config.get('hotword_scope_preset') or 'liver_comorbidity',
                '',
            )[:min(max(safe_int(runtime_config.get('hotword_keyword_limit'), 10), 1), 10)] or automation_keyword_seeds()[:min(max(safe_int(runtime_config.get('hotword_keyword_limit'), 10), 1), 10)],
            'fetch_mode': resolved_hotword_mode(runtime_config),
            'api_url': runtime_config.get('hotword_api_url') or '',
            'api_method': runtime_config.get('hotword_api_method') or 'GET',
            'result_path': runtime_config.get('hotword_result_path') or '',
            'keyword_param': runtime_config.get('hotword_keyword_param') or 'keyword',
            'timeout_seconds': runtime_config.get('hotword_timeout_seconds') or 30,
            'trend_type': runtime_config.get('hotword_trend_type') or 'note_search',
            'page_size': runtime_config.get('hotword_page_size') or 20,
            'max_related_queries': runtime_config.get('hotword_max_related_queries') or 20,
            'auto_generate_topic_ideas': bool(runtime_config.get('hotword_auto_generate_topic_ideas')),
            'auto_generate_topic_count': runtime_config.get('hotword_auto_generate_topic_count') or 20,
            'auto_generate_topic_activity_id': runtime_config.get('hotword_auto_generate_topic_activity_id') or 0,
            'auto_generate_topic_activity_resolved_id': helpers['default_activity_id_for_automation']() if bool(runtime_config.get('hotword_auto_generate_topic_ideas')) and not (runtime_config.get('hotword_auto_generate_topic_activity_id') or 0) else (runtime_config.get('hotword_auto_generate_topic_activity_id') or 0),
            'auto_generate_topic_quota': runtime_config.get('hotword_auto_generate_topic_quota') or default_topic_quota(),
            'auto_convert_corpus_templates': bool(runtime_config.get('hotword_auto_convert_corpus_templates')),
            'auto_convert_corpus_limit': runtime_config.get('hotword_auto_convert_corpus_limit') or 10,
        }
        hotword_request_preview = {}
        hotword_preview_error = ''
        if hotword_preview['fetch_mode'] == 'remote':
            try:
                hotword_request_preview = build_hotword_remote_preview(
                    runtime_config,
                    helpers['resolve_hotword_scope_keywords'](
                        hotword_preview['scope_preset'],
                        '',
                    )[:min(max(safe_int(runtime_config.get('hotword_keyword_limit'), 10), 1), 10)] or hotword_preview['keywords'],
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
            'current_month_only': bool(creator_runtime_config.get('creator_sync_current_month_only')),
            'date_from': creator_runtime_config.get('creator_sync_date_from') or '',
            'date_to': creator_runtime_config.get('creator_sync_date_to') or '',
            'max_posts_per_account': creator_runtime_config.get('creator_sync_max_posts_per_account') or 60,
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
                creator_sync_preview['current_month_only'] = creator_sync_request_preview.get('current_month_only', creator_sync_preview['current_month_only'])
                creator_sync_preview['date_from'] = creator_sync_request_preview.get('date_from', creator_sync_preview['date_from'])
                creator_sync_preview['date_to'] = creator_sync_request_preview.get('date_to', creator_sync_preview['date_to'])
                creator_sync_preview['max_posts_per_account'] = creator_sync_request_preview.get('max_posts_per_account', creator_sync_preview['max_posts_per_account'])
            except Exception as exc:
                creator_sync_preview_error = str(exc)
        copywriter_preview = {
            'provider': copywriter.get('copywriter_provider') or 'local_fallback',
            'label': copywriter.get('copywriter_label') or '本地兜底生成',
            'api_url': copywriter.get('copywriter_api_url') or '',
            'model': copywriter.get('copywriter_model') or '',
            'configured': bool(copywriter.get('copywriter_configured')),
            'server_side_only': True,
            'end_user_needs_vpn': False,
            'candidate_count': copywriter.get('candidate_count') or 0,
            'candidate_chain': copywriter.get('candidate_chain') or [],
        }
        copywriter_request_preview = {
            'prompt': '请用更像真人的小红书口语风，写一句关于肝健康的开头。',
            'api_url': copywriter.get('copywriter_api_url') or '',
            'model': copywriter.get('copywriter_model') or '',
            'backup_api_url': runtime_config.get('copywriter_backup_api_url') or '',
            'backup_model': runtime_config.get('copywriter_backup_model') or '',
            'third_api_url': runtime_config.get('copywriter_third_api_url') or '',
            'third_model': runtime_config.get('copywriter_third_model') or '',
        }
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
            'copywriter_preview': copywriter_preview,
            'copywriter_request_preview': copywriter_request_preview,
            'image_request_preview': image_request_preview,
            'capabilities': capabilities,
            'style_meta': asset_style_meta(capabilities.get('image_default_style_type')),
        })
