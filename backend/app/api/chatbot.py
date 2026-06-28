from flask import Blueprint, request
from app.utils.helpers import success_response, error_response
from app.services.chatbot_service import ChatbotService
from app.utils.decorators import require_auth
from app.utils.exceptions import PeptoException
import logging

logger = logging.getLogger(__name__)
chatbot_bp = Blueprint('chatbot_bp', __name__)
chatbot_service = ChatbotService()

@chatbot_bp.route('/message', methods=['POST'])
def send_message():
    try:
        data = request.json
        if not data or 'message' not in data or 'session_id' not in data:
            return error_response("Missing message or session_id", 400)
            
        user_id = data.get('user_id')
        result = chatbot_service.process_message(
            session_id=data['session_id'],
            message=data['message'],
            user_id=user_id
        )
        return success_response(result)
    except Exception as e:
        logger.exception("Error processing message")
        return error_response("Internal server error", 500)

@chatbot_bp.route('/session/<session_id>', methods=['GET'])
def get_history(session_id):
    try:
        history = chatbot_service.get_or_create_session(session_id)
        return success_response({"history": history})
    except Exception as e:
        logger.exception("Error getting history")
        return error_response("Internal server error", 500)
