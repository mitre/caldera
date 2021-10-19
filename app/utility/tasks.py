from celery import current_app

celery_app = current_app


@celery_app.task()
def test_task():
    print("First celery task")
