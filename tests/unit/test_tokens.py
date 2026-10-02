import uuid
from agropolia.auth.tokens import TokenService
from agropolia.config import Settings

def test_access_token_contains_only_session_identity():
    service = TokenService(Settings(jwt_secret="unit-test-secret-at-least-32-characters")); user_id=uuid.uuid4(); session_id=uuid.uuid4(); payload=service.decode_access(service.create_access(user_id, session_id)); assert payload["sub"]==str(user_id); assert payload["sid"]==str(session_id); assert "org_id" not in payload
