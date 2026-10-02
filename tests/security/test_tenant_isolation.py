from fastapi.testclient import TestClient

from agropolia.main import create_app
from tests.integration.test_auth_flow import register


def test_cross_tenant_org_is_hidden():
    app = create_app()
    with TestClient(app) as client:
        a, _ = register(client, "+79000002001", "200001001")
        b, _ = register(client, "+79000002002", "200001002")
        headers_a = {"Authorization": f"Bearer {a['access_token']}", "X-Client-Platform": "android", "X-Client-Version": "0.1.0"}
        org_b = client.get("/api/v1/me", headers={"Authorization": f"Bearer {b['access_token']}", "X-Client-Platform": "android"}).json()["organization"]["id"]
        forbidden = client.get(f"/api/v1/organizations/{org_b}", headers={**headers_a, "X-Org-Id": org_b})
        assert forbidden.status_code == 404
        assert forbidden.json()["code"] == "NOT_FOUND"
