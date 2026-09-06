from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()
celery_app = Celery(
    "stock_briefing",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)
celery_app.conf.update(
    timezone="Asia/Seoul",
    enable_utc=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "create-morning-briefings": {
            "task": "app.workers.tasks.create_morning_briefings",
            "schedule": crontab(hour=7, minute=30),
        }
    },
)
