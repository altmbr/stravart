import os
import sys
import json
from flask import Flask, request, jsonify, send_file, session
from flask_cors import CORS
from datetime import datetime, timedelta
import secrets

# Add parent directory to path to import main app modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

try:
    from stravalib import Client
    from strava_client import get_strava_access_token, get_recent_runs, get_activity_details
    from image_generator import build_prompt, generate_image
    from config import STRAVA_REFRESH_TOKEN, STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET
except ImportError as e:
    print(f"Warning: Could not import main app modules: {e}")
    print("Running in demo mode")

app = Flask(__name__)
app.secret_key = secrets.token_urlsafe(32)
CORS(app)

# Store generated images temporarily
GENERATED_IMAGES = {}

@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_file('index.html')

@app.route('/api/auth/status')
def auth_status():
    """Check if user is authenticated with Strava"""
    # For now, we'll use the existing refresh token from .env
    # In production, you'd implement proper OAuth flow
    is_authenticated = bool(os.getenv('STRAVA_REFRESH_TOKEN'))
    return jsonify({'authenticated': is_authenticated})

@app.route('/api/auth/connect', methods=['POST'])
def connect_strava():
    """Mock connection to Strava - in production this would redirect to OAuth"""
    # For demo purposes, we'll just return success if we have credentials
    if os.getenv('STRAVA_REFRESH_TOKEN'):
        session['authenticated'] = True
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'No Strava credentials configured'}), 400

@app.route('/api/activities')
def get_activities():
    """Get recent activities from Strava"""
    try:
        # Get access token
        access_token, expires_at = get_strava_access_token()
        
        # Initialize Strava client
        strava_client = Client(access_token=access_token)
        strava_client.refresh_token = STRAVA_REFRESH_TOKEN
        strava_client.client_id = STRAVA_CLIENT_ID
        strava_client.client_secret = STRAVA_CLIENT_SECRET
        strava_client.token_expires = expires_at
        
        # Get recent activities
        activities = get_recent_runs(strava_client, limit=5)
        
        # Format activities for frontend
        formatted_activities = []
        for activity in activities:
            # Get basic activity info
            distance_meters = getattr(activity, 'distance', 0)
            distance_miles = round(distance_meters / 1609.34, 2)
            
            # Format duration
            moving_time = activity.moving_time
            if isinstance(moving_time, timedelta):
                total_seconds = moving_time.total_seconds()
            else:
                total_seconds = moving_time
            
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            seconds = int(total_seconds % 60)
            
            if hours > 0:
                duration = f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                duration = f"{minutes}:{seconds:02d}"
            
            # Calculate pace
            if distance_miles > 0 and total_seconds > 0:
                pace_seconds_per_mile = total_seconds / distance_miles
                pace_minutes = int(pace_seconds_per_mile // 60)
                pace_seconds = int(pace_seconds_per_mile % 60)
                pace = f"{pace_minutes}:{pace_seconds:02d}"
            else:
                pace = "N/A"
            
            formatted_activities.append({
                'id': activity.id,
                'name': activity.name,
                'date': activity.start_date_local.isoformat(),
                'distance': str(distance_miles),
                'duration': duration,
                'pace': pace
            })
        
        return jsonify(formatted_activities)
    
    except Exception as e:
        print(f"Error getting activities: {e}")
        # Return mock data for demo
        return jsonify([
            {
                'id': 1,
                'name': "Morning Run",
                'date': datetime.now().isoformat(),
                'distance': "5.2",
                'duration': "42:15",
                'pace': "8:07"
            },
            {
                'id': 2,
                'name': "Interval Training",
                'date': (datetime.now() - timedelta(days=1)).isoformat(),
                'distance': "3.1",
                'duration': "25:30",
                'pace': "8:14"
            }
        ])

@app.route('/api/generate', methods=['POST'])
def generate_artwork():
    """Generate artwork for selected activity"""
    try:
        data = request.get_json()
        activity_id = data.get('activityId')
        
        if not activity_id:
            return jsonify({'error': 'No activity selected'}), 400
        
        # Get access token
        access_token, expires_at = get_strava_access_token()
        
        # Initialize Strava client
        strava_client = Client(access_token=access_token)
        strava_client.refresh_token = STRAVA_REFRESH_TOKEN
        strava_client.client_id = STRAVA_CLIENT_ID
        strava_client.client_secret = STRAVA_CLIENT_SECRET
        strava_client.token_expires = expires_at
        
        # Get detailed activity
        activity = get_activity_details(strava_client, activity_id)
        
        # Build prompt and generate image
        # Temporarily change to parent directory for image generation
        original_cwd = os.getcwd()
        os.chdir(parent_dir)
        try:
            prompt = build_prompt(activity)
            image_path = generate_image(prompt)
        finally:
            os.chdir(original_cwd)
        
        # Store the image path for serving
        image_key = f"{activity_id}_{int(datetime.now().timestamp())}"
        GENERATED_IMAGES[image_key] = image_path
        
        # Return URL to access the image
        image_url = f"/api/images/{image_key}"
        
        return jsonify({'imageUrl': image_url})
    
    except Exception as e:
        print(f"Error generating artwork: {e}")
        return jsonify({'error': 'Failed to generate artwork'}), 500

@app.route('/api/images/<image_key>')
def serve_image(image_key):
    """Serve generated images"""
    if image_key in GENERATED_IMAGES:
        image_path = GENERATED_IMAGES[image_key]
        # Convert to absolute path if needed
        if not os.path.isabs(image_path):
            image_path = os.path.join(parent_dir, image_path)
        if os.path.exists(image_path):
            return send_file(image_path, mimetype='image/png')
    
    return jsonify({'error': 'Image not found'}), 404

@app.route('/styles.css')
def serve_css():
    """Serve CSS file"""
    return send_file('styles.css', mimetype='text/css')

@app.route('/app.js')
def serve_js():
    """Serve JavaScript file"""
    return send_file('app.js', mimetype='application/javascript')

if __name__ == '__main__':
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    print("Starting StravaRunArt Web Server...")
    print("Access the app at: http://localhost:5001")
    app.run(debug=True, port=5001)