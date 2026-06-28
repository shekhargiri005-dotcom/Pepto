from flask import Blueprint, request
from app.utils.helpers import success_response, error_response, paginate_query
from app.utils.decorators import require_auth, validate_json, provider_required, admin_required
from app.schemas.review_schemas import ReviewCreate, ProviderResponseSchema
from app.models.review import Review
from app.models.booking import Booking
from app.extensions import db
from app.utils.exceptions import PeptoException
import logging

logger = logging.getLogger(__name__)
reviews_bp = Blueprint('reviews_bp', __name__)

@reviews_bp.route('', methods=['POST'])
@require_auth
@validate_json(ReviewCreate)
def create_review(current_user):
    try:
        data = request.json
        booking = db.session.get(Booking, data['booking_id'])
        if not booking:
            return error_response("Booking not found", 404)
        if booking.customer_id != current_user.id:
            return error_response("Unauthorized", 403)
        if booking.status.name != 'completed':
            return error_response("Can only review completed bookings", 400)
            
        review = Review(
            booking_id=booking.id,
            reviewer_id=current_user.id,
            provider_id=booking.provider_id,
            rating=data['rating'],
            comment=data.get('comment')
        )
        db.session.add(review)
        db.session.commit()
        return success_response(review.to_dict(), "Review created", 201)
    except Exception as e:
        db.session.rollback()
        logger.exception("Error creating review")
        return error_response("Internal server error", 500)

@reviews_bp.route('/my', methods=['GET'])
@require_auth
def my_reviews(current_user):
    try:
        page = int(request.args.get('page', 1))
        query = Review.query.filter_by(reviewer_id=current_user.id)
        result = paginate_query(query, page, 20)
        return success_response(result)
    except Exception as e:
        logger.exception("Error fetching reviews")
        return error_response("Internal server error", 500)

@reviews_bp.route('/<uuid:review_id>/response', methods=['PUT'])
@require_auth
@provider_required
@validate_json(ProviderResponseSchema)
def provider_response(current_user, review_id):
    try:
        review = db.session.get(Review, review_id)
        if not review:
            return error_response("Review not found", 404)
        if review.provider_id != current_user.provider_profile.id:
            return error_response("Unauthorized", 403)
            
        review.provider_response = request.json['response']
        review.provider_response_at = db.func.now()
        db.session.commit()
        return success_response(review.to_dict(), "Response added")
    except Exception as e:
        db.session.rollback()
        logger.exception("Error adding response")
        return error_response("Internal server error", 500)
