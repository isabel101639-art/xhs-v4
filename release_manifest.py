from datetime import datetime


CURRENT_RELEASE_VERSION = 'v1-2026-04-26'
CURRENT_RELEASE_DATE = '2026-04-26'
CURRENT_RELEASE_TARGET_DATE = '2026-05-02'
CURRENT_RELEASE_STAGE = 'pre_go_live'
CURRENT_RELEASE_STAGE_LABELS = {
    'pre_go_live': '上线前收口',
    'trial_ready': '可试运行',
    'go_live_ready': '可正式上线',
}
CURRENT_RELEASE_SCOPE = [
    'copywriter_quality',
    'image_quality',
    'task_workspace',
    'data_analysis',
    'automation_import',
]
CURRENT_RELEASE_FEATURE_LABELS = {
    'copy_quality_scoring': '文案质量分与重排',
    'image_workflow_decision': '图片决策统一与封面 fallback',
    'task_workspace': '我的任务工作台',
    'task_funnel_analysis': '任务漏斗与策略结论',
    'trend_csv_import': 'CSV / 表格文本热点导入',
    'release_gate': '发版总闸与上线验活',
}
CURRENT_RELEASE_FEATURES = {
    'copy_quality_scoring': True,
    'image_workflow_decision': True,
    'task_workspace': True,
    'task_funnel_analysis': True,
    'trend_csv_import': True,
    'release_gate': True,
}
CURRENT_RELEASE_UI_MARKERS = {
    'automation_center': [
        'data-release-manifest="release-manifest"',
        'trendPayloadFile',
        'releaseManifestWrap',
        'releaseManifestPayload',
    ],
    'data_analysis': [
        'data-release-manifest="release-manifest"',
        'taskFunnelWrap',
        'strategySummaryWrap',
        'releaseSummaryBar',
        'releaseManifestPayload',
    ],
    'my_registration': [
        'data-release-manifest="release-manifest"',
        'task-filter-chip',
        '建议优先处理',
        'releasePublicSummary',
        'releaseManifestPayload',
    ],
    'register_success': [
        'data-release-manifest="release-manifest"',
        'copy-quality-chip',
        'applyWorkflowDecision',
        'releaseStudioSummary',
        'releaseManifestPayload',
    ],
}
CURRENT_RELEASE_FINGERPRINT = 'copy-quality+image-decision+task-workspace+data-funnel+trend-csv+release-gate'


def build_release_manifest_payload(include_generated_at=True):
    payload = {
        'release_version': CURRENT_RELEASE_VERSION,
        'release_date': CURRENT_RELEASE_DATE,
        'release_target_date': CURRENT_RELEASE_TARGET_DATE,
        'release_stage': CURRENT_RELEASE_STAGE,
        'release_stage_label': CURRENT_RELEASE_STAGE_LABELS.get(CURRENT_RELEASE_STAGE) or CURRENT_RELEASE_STAGE,
        'release_scope': list(CURRENT_RELEASE_SCOPE),
        'release_features': dict(CURRENT_RELEASE_FEATURES),
        'release_feature_items': [
            {
                'key': key,
                'label': CURRENT_RELEASE_FEATURE_LABELS.get(key) or key,
                'enabled': bool(enabled),
            }
            for key, enabled in CURRENT_RELEASE_FEATURES.items()
        ],
        'ui_markers': {key: list(value) for key, value in CURRENT_RELEASE_UI_MARKERS.items()},
        'release_fingerprint': CURRENT_RELEASE_FINGERPRINT,
    }
    if include_generated_at:
        payload['generated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return payload
