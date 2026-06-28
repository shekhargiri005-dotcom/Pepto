from celery_app import celery
from app.services.notification_service import NotificationService
from app.extensions import db
from app.models.booking import Booking
from app.models.user import User

notification_service = NotificationService()

@celery.task(bind=True, max_retries=3)
def send_booking_confirmation_task(self, booking_id):
    try:
        booking = db.session.get(Booking, booking_id)
        if booking:
            notification_service.send_booking_confirmation(booking)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)

@celery.task(bind=True, max_retries=3)
def send_status_update_task(self, booking_id, old_status, new_status):
    try:
        booking = db.session.get(Booking, booking_id)
        if booking:
            notification_service.send_status_update(booking, old_status, new_status)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)

@celery.task(bind=True, max_retries=3)
def send_review_request_task(self, booking_id):
    try:
        booking = db.session.get(Booking, booking_id)
        if booking:
            notification_service.send_review_request(booking)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)

@celery.task(bind=True, max_retries=3)
def send_verification_email_task(self, user_id, token):
    try:
        user = db.session.get(User, user_id)
        if user:
            notification_service.send_verification_email(user, token)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
