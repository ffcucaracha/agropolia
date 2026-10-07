from fastapi.testclient import TestClient

from agropolia.main import create_app
from tests.integration.helpers import valid_inn


def register(client: TestClient, phone: str, prefix9: str, platform: str = "android"):
    headers = {"X-Client-Platform": platform, "X-Client-Version": "0.1.0"}
    device = f"device-{prefix9}"
    otp = client.post("/api/v1/auth/otp/request", headers=headers, json={"phone": phone, "device_id": device, "purpose": "register"})
    assert otp.status_code == 200
    code = otp.json()["dev_code"]
    verified = client.post("/api/v1/auth/otp/verify", headers=headers, json={"phone": phone, "device_id": device, "purpose": "register", "code": code})
    registration_token = verified.json()["registration_token"]
    response = client.post("/api/v1/auth/register", headers=headers, json={"registration_token": registration_token,"name": "Тестовый пользователь","organization_type": "KFH","organization_inn": valid_inn(prefix9),"organization_name": f"КФХ {prefix9}","consent_version": "i0-pd-1","consent_accepted": True})
    assert response.status_code == 200, response.text
    return response.json(), device


def test_registration_me_logout_and_login():
    app = create_app()
    with TestClient(app) as client:
        tokens, device = register(client, "+79000001001", "100001001")
        headers = {"Authorization": f"Bearer {tokens['access_token']}", "X-Client-Platform": "android", "X-Client-Version": "0.1.0"}
        me = client.get("/api/v1/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["organization"]["inn"] == valid_inn("100001001")
        assert me.json()["membership"]["role"] == "owner"
        assert client.post("/api/v1/auth/logout", headers=headers, json={}).status_code == 204
        assert client.get("/api/v1/me", headers=headers).status_code == 401
        otp = client.post("/api/v1/auth/otp/request", headers={"X-Client-Platform": "android"}, json={"phone": "+79000001001", "device_id": device, "purpose": "login"}).json()
        login = client.post("/api/v1/auth/otp/verify", headers={"X-Client-Platform": "android"}, json={"phone": "+79000001001", "device_id": device, "purpose": "login", "code": otp["dev_code"]})
        assert login.status_code == 200
        assert login.json()["tokens"]["refresh_token"]


def test_refresh_rotation_reuse_revokes_session():
    app = create_app()
    with TestClient(app) as client:
        tokens, device = register(client, "+79000001002", "100001002")
        old_refresh = tokens["refresh_token"]
        first = client.post("/api/v1/auth/refresh", headers={"X-Client-Platform": "android"}, json={"refresh_token": old_refresh, "device_id": device})
        assert first.status_code == 200
        new_refresh = first.json()["refresh_token"]
        reused = client.post("/api/v1/auth/refresh", headers={"X-Client-Platform": "android"}, json={"refresh_token": old_refresh, "device_id": device})
        assert reused.status_code == 401
        assert reused.json()["code"] == "REFRESH_REUSED"
        revoked = client.post("/api/v1/auth/refresh", headers={"X-Client-Platform": "android"}, json={"refresh_token": new_refresh, "device_id": device})
        assert revoked.status_code == 401
