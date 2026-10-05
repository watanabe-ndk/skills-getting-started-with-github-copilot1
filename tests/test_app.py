from copy import deepcopy
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from src import app as app_module


INITIAL_ACTIVITIES = deepcopy(app_module.activities)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(app_module, "activities", deepcopy(INITIAL_ACTIVITIES))
    with TestClient(app_module.app, follow_redirects=False) as test_client:
        yield test_client


def signup_path(activity_name):
    return f"/activities/{quote(activity_name, safe='')}/signup"


def test_root_redirects_to_static_index(client):
    response = client.get("/")

    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_static_index_is_served(client):
    response = client.get("/static/index.html")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_get_activities_returns_seeded_participants(client):
    response = client.get("/activities")

    assert response.status_code == 200
    assert response.json() == INITIAL_ACTIVITIES
    assert response.json()["Chess Club"]["participants"] == [
        "michael@mergington.edu",
        "daniel@mergington.edu",
    ]


def test_signup_adds_participant(client):
    email = "new-student@mergington.edu"

    response = client.post(signup_path("Chess Club"), params={"email": email})

    assert response.status_code == 200
    assert response.json() == {"message": f"Signed up {email} for Chess Club"}
    assert email in client.get("/activities").json()["Chess Club"]["participants"]


def test_signup_rejects_duplicate_without_changing_participants(client):
    email = "michael@mergington.edu"

    response = client.post(signup_path("Chess Club"), params={"email": email})

    assert response.status_code == 400
    assert response.json()["detail"] == "Student already signed up"
    assert client.get("/activities").json()["Chess Club"]["participants"] == INITIAL_ACTIVITIES[
        "Chess Club"
    ]["participants"]


def test_signup_returns_404_for_unknown_activity(client):
    response = client.post(signup_path("Unknown Club"), params={"email": "student@example.com"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_cancel_signup_removes_participant(client):
    email = "michael@mergington.edu"

    response = client.delete(signup_path("Chess Club"), params={"email": email})

    assert response.status_code == 200
    assert response.json() == {
        "message": f"Cancelled signup for {email} in Chess Club"
    }
    assert email not in client.get("/activities").json()["Chess Club"]["participants"]


def test_cancel_signup_returns_404_for_unknown_activity(client):
    response = client.delete(
        signup_path("Unknown Club"), params={"email": "student@example.com"}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_cancel_signup_returns_404_for_unregistered_participant(client):
    response = client.delete(
        signup_path("Chess Club"), params={"email": "student@example.com"}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Student is not signed up for this activity"


@pytest.mark.parametrize("method", ["post", "delete"])
def test_signup_routes_require_email(client, method):
    response = client.request(method, signup_path("Chess Club"))

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "email"]