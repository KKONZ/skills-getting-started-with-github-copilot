"""
Comprehensive tests for the Mergington High School Management System API

Tests cover:
- Root endpoint and redirects
- Activities listing
- Student signup functionality
- Error handling and edge cases
"""

import pytest
import copy
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def fresh_activities():
    """Provide a fresh copy of activities and reset after each test"""
    original = copy.deepcopy(activities)
    yield
    # Reset activities to original state after each test
    activities.clear()
    activities.update(original)


class TestRootEndpoint:
    """Tests for the root endpoint"""

    def test_root_redirect(self, client):
        """Test that root endpoint redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"

    def test_root_redirect_follow(self, client):
        """Test following the redirect returns static content"""
        response = client.get("/", follow_redirects=True)
        # Should eventually return HTML content or 200
        assert response.status_code in [200, 307]


class TestGetActivities:
    """Tests for the GET /activities endpoint"""

    def test_get_all_activities(self, client, fresh_activities):
        """Test retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data

    def test_activity_structure(self, client, fresh_activities):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_info in data.items():
            assert "description" in activity_info
            assert "schedule" in activity_info
            assert "max_participants" in activity_info
            assert "participants" in activity_info
            assert isinstance(activity_info["participants"], list)
            assert isinstance(activity_info["max_participants"], int)

    def test_activities_have_participants(self, client, fresh_activities):
        """Test that activities have valid participant lists"""
        response = client.get("/activities")
        data = response.json()
        
        chess_club = data["Chess Club"]
        assert "michael@mergington.edu" in chess_club["participants"]
        assert "daniel@mergington.edu" in chess_club["participants"]

    def test_response_content_type(self, client, fresh_activities):
        """Test that response content type is JSON"""
        response = client.get("/activities")
        assert "application/json" in response.headers["content-type"]


class TestSignupForActivity:
    """Tests for the POST /activities/{activity_name}/signup endpoint"""

    def test_successful_signup(self, client, fresh_activities):
        """Test successful signup for an activity"""
        email = "newstudent@mergington.edu"
        activity_name = "Chess Club"
        
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 200
        assert response.json()["message"] == f"Signed up {email} for {activity_name}"
        
        # Verify student was added to participants
        updated_response = client.get("/activities")
        updated_data = updated_response.json()
        assert email in updated_data[activity_name]["participants"]

    def test_signup_multiple_students(self, client, fresh_activities):
        """Test multiple students can sign up for same activity"""
        activity_name = "Art Studio"
        emails = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        
        for email in emails:
            response = client.post(
                f"/activities/{activity_name}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify all students are registered
        activities_response = client.get("/activities")
        participants = activities_response.json()[activity_name]["participants"]
        for email in emails:
            assert email in participants

    def test_signup_activity_not_found(self, client, fresh_activities):
        """Test signup for non-existent activity returns 404"""
        response = client.post(
            "/activities/Non-Existent Activity/signup",
            params={"email": "student@mergington.edu"}
        )
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_signup_already_registered(self, client, fresh_activities):
        """Test that student cannot sign up twice"""
        email = "michael@mergington.edu"  # Already in Chess Club
        activity_name = "Chess Club"
        
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 400
        assert response.json()["detail"] == "Student already signed up for this activity"

    def test_signup_different_activities(self, client, fresh_activities):
        """Test student can sign up for multiple different activities"""
        email = "multiactivity@mergington.edu"
        activities_list = ["Chess Club", "Programming Class", "Gym Class"]
        
        for activity_name in activities_list:
            response = client.post(
                f"/activities/{activity_name}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify student is in all activities
        activities_response = client.get("/activities")
        data = activities_response.json()
        for activity_name in activities_list:
            assert email in data[activity_name]["participants"]

    def test_signup_case_sensitive_activity_name(self, client, fresh_activities):
        """Test activity names are case-sensitive"""
        response = client.post(
            "/activities/chess club/signup",
            params={"email": "student@mergington.edu"}
        )
        
        assert response.status_code == 404

    def test_signup_with_special_characters_email(self, client, fresh_activities):
        """Test signup with various email formats"""
        emails = [
            "student.name@mergington.edu",
            "student+tag@mergington.edu",
            "s@mergington.edu"
        ]
        activity_name = "Theater Club"
        
        for email in emails:
            response = client.post(
                f"/activities/{activity_name}/signup",
                params={"email": email}
            )
            assert response.status_code == 200

    def test_signup_empty_email(self, client, fresh_activities):
        """Test signup with empty email"""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": ""}
        )
        # Should work as endpoint accepts empty string
        assert response.status_code == 200


class TestUnregisterFromActivity:
    """Tests for the DELETE /activities/{activity_name}/signup endpoint"""

    def test_successful_unregister(self, client, fresh_activities):
        """Test successful unregistration from an activity"""
        email = "michael@mergington.edu"
        activity_name = "Chess Club"
        
        # Verify student is registered
        get_response = client.get("/activities")
        assert email in get_response.json()[activity_name]["participants"]
        
        # Unregister
        response = client.delete(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 200
        assert response.json()["message"] == f"Unregistered {email} from {activity_name}"
        
        # Verify student was removed
        updated_response = client.get("/activities")
        assert email not in updated_response.json()[activity_name]["participants"]

    def test_unregister_activity_not_found(self, client, fresh_activities):
        """Test unregister for non-existent activity returns 404"""
        response = client.delete(
            "/activities/Non-Existent Activity/signup",
            params={"email": "student@mergington.edu"}
        )
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_unregister_not_signed_up(self, client, fresh_activities):
        """Test unregister when student is not signed up"""
        email = "notstudent@mergington.edu"
        activity_name = "Chess Club"
        
        response = client.delete(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"].lower()

    def test_unregister_multiple_students(self, client, fresh_activities):
        """Test unregistering multiple students from same activity"""
        activity_name = "Programming Class"
        emails = ["emma@mergington.edu", "sophia@mergington.edu"]
        
        for email in emails:
            response = client.delete(
                f"/activities/{activity_name}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify all were removed
        activities_response = client.get("/activities")
        participants = activities_response.json()[activity_name]["participants"]
        for email in emails:
            assert email not in participants

    def test_signup_then_unregister(self, client, fresh_activities):
        """Test signup followed by unregister"""
        email = "temporary@mergington.edu"
        activity_name = "Tennis Club"
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        assert signup_response.status_code == 200
        
        # Verify signup
        get_response = client.get("/activities")
        assert email in get_response.json()[activity_name]["participants"]
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        assert unregister_response.status_code == 200
        
        # Verify removal
        final_response = client.get("/activities")
        assert email not in final_response.json()[activity_name]["participants"]


class TestEdgeCases:
    """Tests for edge cases and error conditions"""

    def test_activity_with_url_special_characters(self, client, fresh_activities):
        """Test accessing activities with special characters in name"""
        response = client.post(
            "/activities/Activity%20Name/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404

    def test_concurrent_signups_same_activity(self, client, fresh_activities):
        """Test multiple signups to same activity"""
        activity_name = "Basketball Team"
        emails = [f"student{i}@mergington.edu" for i in range(5)]
        
        for email in emails:
            response = client.post(
                f"/activities/{activity_name}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify all students are added
        activities_response = client.get("/activities")
        assert len(activities_response.json()[activity_name]["participants"]) == 6

    def test_response_message_format(self, client, fresh_activities):
        """Test response message has correct format"""
        email = "test@mergington.edu"
        activity_name = "Debate Team"
        
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert activity_name in data["message"]

    def test_activities_list_not_mutated_across_requests(self, client, fresh_activities):
        """Test that activities data structure is maintained correctly"""
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()["Chess Club"]["participants"])
        
        # Signup
        client.post(
            "/activities/Chess Club/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        
        # Try to signup to different activity
        client.post(
            "/activities/Programming Class/signup",
            params={"email": "another@mergington.edu"}
        )
        
        # Verify Chess Club only increased by 1
        final_response = client.get("/activities")
        final_count = len(final_response.json()["Chess Club"]["participants"])
        assert final_count == initial_count + 1

    def test_numeric_activity_name_parameter(self, client, fresh_activities):
        """Test handling of numeric values in activity name"""
        response = client.post(
            "/activities/123/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404

    def test_very_long_email(self, client, fresh_activities):
        """Test signup with very long email address"""
        long_email = "a" * 200 + "@mergington.edu"
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": long_email}
        )
        assert response.status_code == 200


class TestDataIntegrity:
    """Tests for data integrity and consistency"""

    def test_participants_list_is_list_type(self, client, fresh_activities):
        """Test that participants are stored as list"""
        response = client.get("/activities")
        data = response.json()
        
        for activity in data.values():
            assert isinstance(activity["participants"], list)

    def test_max_participants_is_integer(self, client, fresh_activities):
        """Test that max_participants values are integers"""
        response = client.get("/activities")
        data = response.json()
        
        for activity in data.values():
            assert isinstance(activity["max_participants"], int)
            assert activity["max_participants"] > 0

    def test_activity_descriptions_are_strings(self, client, fresh_activities):
        """Test that descriptions are non-empty strings"""
        response = client.get("/activities")
        data = response.json()
        
        for activity in data.values():
            assert isinstance(activity["description"], str)
            assert len(activity["description"]) > 0

    def test_all_required_activities_present(self, client, fresh_activities):
        """Test that all expected activities are present"""
        expected_activities = [
            "Chess Club",
            "Programming Class",
            "Gym Class",
            "Basketball Team",
            "Tennis Club",
            "Art Studio",
            "Theater Club",
            "Math Olympiad",
            "Debate Team"
        ]
        
        response = client.get("/activities")
        data = response.json()
        
        for activity in expected_activities:
            assert activity in data
