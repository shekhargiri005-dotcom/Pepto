from app.schemas.auth_schemas import RegisterRequest, LoginRequest
from app.utils.exceptions import ValidationError
from pydantic import ValidationError as PydanticValidationError

def validate_register_input(data):
    try:
        return RegisterRequest(**data).model_dump()
    except PydanticValidationError as e:
        raise ValidationError(str(e))

def validate_login_input(data):
    try:
        obj = LoginRequest(**data)
        return obj.email, obj.password
    except PydanticValidationError as e:
        raise ValidationError(str(e))

def validate_update_profile_input(data):
    # Just basic validation for update profile
    return data
