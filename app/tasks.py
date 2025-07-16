import time
from app.celery_app import celery_app

@celery_app.task
def send_mock_email(email: str):
    print(f"[Task] Sending email to {email}...")
    time.sleep(10)
    print(f"[Task] Email sent to {email}")