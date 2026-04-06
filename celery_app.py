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


@celery.task(name='system.ping')
def ping():
    return {
        'message': 'pong',
        'service': 'worker',
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
