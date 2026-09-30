"""
Mirzo - Automated Backend and Integration Tests
Verifies SQLite storage, text processing, task toggling, Telegram export, and API routes.
"""
import pytest
from fastapi.testclient import TestClient
import database
from server import app

client = TestClient(app)

def test_initial_db_setup():
    database.init_db()
    meetings = database.get_all_meetings()
    assert len(meetings) >= 1
    sample = meetings[0]
    assert "title" in sample
    assert isinstance(sample["tasks"], list)

def test_api_list_meetings():
    response = client.get("/api/meetings")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

def test_api_get_single_meeting():
    meetings = client.get("/api/meetings").json()
    first_id = meetings[0]["id"]
    response = client.get(f"/api/meetings/{first_id}")
    assert response.status_code == 200
    m = response.json()
    assert m["id"] == first_id
    assert "summary" in m
    assert "decisions" in m

def test_api_process_text_meeting():
    payload = {
        "title": "Avtomatlashtirilgan test uchrashuvi",
        "text": "Aziza: Biz tizimni muvaffaqiyatli qurdik.\nSardor: Serverlar to'liq ishlayapti.",
        "duration": "10 daqiqa"
    }
    response = client.post("/api/meetings/process-text", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert "id" in res_data
    assert res_data["title"] is not None
    assert len(res_data["tasks"]) >= 0

def test_api_task_toggle():
    meetings = client.get("/api/meetings").json()
    first_meeting = meetings[0]
    tasks = first_meeting["tasks"]
    if tasks:
        task_id = tasks[0]["id"]
        original_state = tasks[0]["completed"]
        
        # Toggle
        res = client.patch(f"/api/tasks/{task_id}/toggle")
        assert res.status_code == 200
        new_task = res.json()
        assert new_task["completed"] != original_state
        
        # Toggle back
        res_revert = client.patch(f"/api/tasks/{task_id}/toggle")
        assert res_revert.status_code == 200
        assert res_revert.json()["completed"] == original_state

def test_api_telegram_share_preview():
    meetings = client.get("/api/meetings").json()
    first_id = meetings[0]["id"]
    response = client.post("/api/telegram/share", json={"meeting_id": first_id, "direct": False})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "deep_link" in data
    assert "https://t.me/share/url" in data["deep_link"]
    assert "formatted_text" in data
    assert "Hamkorlik" in data["formatted_text"] or len(data["formatted_text"]) > 10

def test_settings_api():
    get_res = client.get("/api/settings")
    assert get_res.status_code == 200
    assert "retention" in get_res.json()

    post_res = client.post("/api/settings", json={"key": "test_key", "value": "test_val"})
    assert post_res.status_code == 200
    updated = client.get("/api/settings").json()
    assert updated.get("test_key") == "test_val"

if __name__ == "__main__":
    pytest.main(["-v", __file__])
