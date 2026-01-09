"""Tests for the Mergington High School API"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add the src directory to the path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    # Store original state
    original_activities = {
        key: {
            "description": val["description"],
            "schedule": val["schedule"],
            "max_participants": val["max_participants"],
            "participants": val["participants"].copy(),
        }
        for key, val in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for key in activities:
        activities[key]["participants"] = original_activities[key]["participants"].copy()


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_activities_returns_dict(self, client):
        """Test that /activities returns a dictionary of activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0

    def test_get_activities_has_required_fields(self, client):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)

    def test_get_activities_contains_chess_club(self, client):
        """Test that Chess Club is in the activities"""
        response = client.get("/activities")
        data = response.json()
        assert "Chess Club" in data


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_for_activity_success(self, client, reset_activities):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "new_student@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Signed up" in data["message"]
        
        # Verify participant was added
        assert "new_student@mergington.edu" in activities["Chess Club"]["participants"]

    def test_signup_nonexistent_activity(self, client):
        """Test signup for a non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Club/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_signup_already_registered(self, client, reset_activities):
        """Test signup for an activity when already registered"""
        email = "michael@mergington.edu"  # Already in Chess Club
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_multiple_activities(self, client, reset_activities):
        """Test signing up for multiple different activities"""
        email = "multi_student@mergington.edu"
        
        # Sign up for Chess Club
        response1 = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Sign up for Programming Class
        response2 = client.post(
            "/activities/Programming Class/signup",
            params={"email": email}
        )
        assert response2.status_code == 200
        
        # Verify in both activities
        assert email in activities["Chess Club"]["participants"]
        assert email in activities["Programming Class"]["participants"]


class TestUnregisterFromActivity:
    """Tests for POST /activities/{activity_name}/unregister endpoint"""

    def test_unregister_success(self, client, reset_activities):
        """Test successful unregistration from an activity"""
        email = "michael@mergington.edu"  # Already in Chess Club
        response = client.post(
            "/activities/Chess Club/unregister",
            params={"email": email}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Unregistered" in data["message"]
        
        # Verify participant was removed
        assert email not in activities["Chess Club"]["participants"]

    def test_unregister_nonexistent_activity(self, client):
        """Test unregister from a non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Club/unregister",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_unregister_not_registered(self, client, reset_activities):
        """Test unregister when not registered for the activity"""
        response = client.post(
            "/activities/Chess Club/unregister",
            params={"email": "not_registered@mergington.edu"}
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]

    def test_signup_then_unregister(self, client, reset_activities):
        """Test signing up and then unregistering"""
        email = "temp_student@mergington.edu"
        
        # Sign up
        response1 = client.post(
            "/activities/Tennis Team/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        assert email in activities["Tennis Team"]["participants"]
        
        # Unregister
        response2 = client.post(
            "/activities/Tennis Team/unregister",
            params={"email": email}
        )
        assert response2.status_code == 200
        assert email not in activities["Tennis Team"]["participants"]


class TestActivityParticipantCounts:
    """Tests for participant counts"""

    def test_participant_count_matches(self, client):
        """Test that participant count matches actual participants"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            actual_count = len(activity_details["participants"])
            # Verify we can compare with max_participants
            assert actual_count <= activity_details["max_participants"]

    def test_signup_increases_participant_count(self, client, reset_activities):
        """Test that signing up increases the participant count"""
        email = "count_student@mergington.edu"
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()["Debate Team"]["participants"])
        
        # Sign up
        client.post(
            "/activities/Debate Team/signup",
            params={"email": email}
        )
        
        final_response = client.get("/activities")
        final_count = len(final_response.json()["Debate Team"]["participants"])
        
        assert final_count == initial_count + 1
