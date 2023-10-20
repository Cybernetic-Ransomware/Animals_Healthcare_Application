import time

from celery import Celery

celery_obj = Celery(
    "my_celery", broker="redis://redis:6379/0", backend="redis://redis:6379/0"
)


@celery_obj.task()
def my_task():
    time.sleep(30)
    return "Succeeded"
