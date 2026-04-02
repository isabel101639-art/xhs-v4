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
    return 'pong'
