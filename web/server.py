#!/usr/bin/env python3
"""
Web server for Strava Run Art
This serves the web UI and provides API endpoints for the frontend
"""

import os
import sys
import json
from flask import Flask, render_template_string, jsonify, request, send_file, redirect, url_for, session
from flask_cors import CORS
from pathlib import Path
import secrets

# Add parent directory to path to import main.py functions
sys.path.append(str(Path(__file__).parent.parent))

# Import functions from main.py
try:
    from main import (
        get_strava_client, 
        fetch_activities, 
        create_activity_prompt,
        generate_image_with_openai,
        save_image
    )
    MAIN_IMPORTED = True
except ImportError:
    MAIN_IMPORTED = False
    print("Warning: Could not import main.py functions. Running in demo mode.")

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))
CORS(app)

# Serve static files
@app.route('/')
def index():
    return send_file('index.html')

@app.route('/styles.css')
def styles():
    return send_file('styles.css', mimetype='text/css')

@app.route('/app.js')
def javascript():
    return send_file('app.js', mimetype='application/javascript')

# API endpoints
@app.route('/api/auth/status')
def auth_status():
    """Check if user is authenticated with Strava"""
    # Check if we have valid tokens in session or environment
    authenticated = bool(os.getenv('STRAVA_REFRESH_TOKEN')) if MAIN_IMPORTED else False
    return jsonify({'authenticated': authenticated})

@app.route('/api/auth/strava')
def strava_auth():
    """Redirect to Strava OAuth (placeholder for now)"""
    # In production, this would redirect to Strava's OAuth page
    # For now, just redirect back to home
    client_id = os.getenv('STRAVA_CLIENT_ID')
    if client_id:
        redirect_uri = request.url_root + 'api/auth/callback'
        strava_auth_url = f"https://www.strava.com/oauth/authorize?client_id={client_id}&response_type=code&redirect_uri={redirect_uri}&scope=activity:read"
        return redirect(strava_auth_url)
    return redirect('/')

@app.route('/api/auth/callback')
def strava_callback():
    """Handle Strava OAuth callback"""
    # This would handle the OAuth callback in production
    return redirect('/')

@app.route('/api/activities')
def get_activities():
    """Fetch recent activities from Strava"""
    if not MAIN_IMPORTED:
        # Return mock data if main.py not available
        return jsonify([
            {
                "id": 1,
                "name": "Morning Run",
                "distance": 8046.72,
                "moving_time": 1800,
                "start_date": "2024-01-15T07:00:00Z",
                "type": "Run"
            }
        ])
    
    try:
        client = get_strava_client()
        activities = fetch_activities(client, limit=5)
        
        # Convert activities to JSON-serializable format
        activities_data = []
        for activity in activities:
            activities_data.append({
                'id': activity.id,
                'name': activity.name,
                'distance': float(activity.distance),
                'moving_time': int(activity.moving_time.total_seconds()),
                'start_date': activity.start_date.isoformat(),
                'type': activity.type,
                'average_speed': float(activity.average_speed) if hasattr(activity, 'average_speed') else None,
                'total_elevation_gain': float(activity.total_elevation_gain) if hasattr(activity, 'total_elevation_gain') else None
            })
        
        return jsonify(activities_data)
    except Exception as e:
        print(f"Error fetching activities: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-artwork', methods=['POST'])
def generate_artwork():
    """Generate artwork for a specific activity"""
    if not MAIN_IMPORTED:
        # Return mock response if main.py not available
        return jsonify({
            'success': True,
            'imageUrl': '/api/images/placeholder.png'
        })
    
    try:
        data = request.json
        activity_id = data.get('activityId')
        
        if not activity_id:
            return jsonify({'error': 'Activity ID required'}), 400
        
        # Fetch the specific activity
        client = get_strava_client()
        activity = client.get_activity(activity_id)
        
        # Get detailed activity data
        detailed_activity = client.get_activity(activity_id, include_all_efforts=True)
        
        # Create prompt
        prompt = create_activity_prompt(detailed_activity, {
            'location': 'Unknown',  # You can enhance this with location detection
            'is_run': activity.type == 'Run'
        })
        
        # Generate image
        image_data = generate_image_with_openai(prompt)
        
        # Save image
        timestamp = detailed_activity.start_date.strftime("%Y%m%d_%H%M%S")
        filename = f"{activity.type.lower()}_{timestamp}.png"
        filepath = save_image(image_data, filename)
        
        # Return relative path for web access
        image_url = f"/api/images/{filename}"
        
        return jsonify({
            'success': True,
            'imageUrl': image_url,
            'prompt': prompt
        })
        
    except Exception as e:
        print(f"Error generating artwork: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/images/<filename>')
def serve_image(filename):
    """Serve generated images"""
    # Ensure filename is safe
    if '..' in filename or '/' in filename:
        return "Invalid filename", 400
    
    image_dir = Path(__file__).parent.parent / 'generated_images'
    image_path = image_dir / filename
    
    if image_path.exists():
        return send_file(str(image_path), mimetype='image/png')
    else:
        # Return placeholder if image not found
        return "Image not found", 404

if __name__ == '__main__':
    # Check if .env file exists in parent directory
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        from dotenv import load_dotenv
        load_dotenv(env_path)
    
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    print(f"Starting Strava Run Art web server on http://localhost:{port}")
    print(f"Debug mode: {debug}")
    print(f"Main.py imported: {MAIN_IMPORTED}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)