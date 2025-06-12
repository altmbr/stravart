import requests
from stravalib import Client
from config import STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REFRESH_TOKEN


def get_strava_access_token() -> tuple[str, int]:
    """Exchange the refresh token for a short‑lived access token."""
    resp = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": STRAVA_CLIENT_ID,
            "client_secret": STRAVA_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": STRAVA_REFRESH_TOKEN,
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["access_token"], data["expires_at"]


def get_last_run(client: Client):
    """Return the most recent activity (run) for the authenticated athlete."""
    # Get the most recent activity
    activities = list(client.get_activities(limit=1))
    if not activities:
        raise RuntimeError("No activities found for athlete.")
    
    activity = activities[0]
    
    # Ensure we have detailed information by requesting the full activity
    # This will include splits and detailed metrics
    detailed_activity = client.get_activity(activity.id)
    
    return detailed_activity


def get_recent_runs(client: Client, limit: int = 5):
    """Return the most recent activities (runs) for the authenticated athlete."""
    # Get recent activities
    activities = list(client.get_activities(limit=limit))
    if not activities:
        raise RuntimeError("No activities found for athlete.")
    
    return activities


def get_activity_details(client: Client, activity_id: int):
    """Fetch detailed information for a specific activity."""
    # Request the full activity with detailed information
    detailed_activity = client.get_activity(activity_id)
    return detailed_activity