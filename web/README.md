# StravaRunArt Web Interface

A mobile-first web interface for StravaRunArt that allows users to generate artistic posters from their Strava activities.

## Features

- 📱 Mobile-first responsive design
- 🔐 Strava authentication (using existing credentials)
- 🏃 View recent runs with key metrics
- 🎨 Generate custom artwork for selected activities
- 💾 Download generated images
- ⚡ Fast and intuitive user interface

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure your parent directory has a `.env` file with Strava credentials:
```
STRAVA_CLIENT_ID=your_client_id
STRAVA_CLIENT_SECRET=your_client_secret
STRAVA_REFRESH_TOKEN=your_refresh_token
OPENAI_API_KEY=your_openai_key
```

3. Run the development server:
```bash
python api.py
```

4. Open your browser to `http://localhost:5000`

## Development

The web interface consists of:
- `index.html` - Main HTML structure
- `styles.css` - Mobile-first CSS styling
- `app.js` - JavaScript for UI interactions
- `api.py` - Flask backend API

## Deployment to Netlify

For deployment to Netlify, you'll need to:

1. Create a serverless function to handle the API endpoints
2. Configure environment variables in Netlify
3. Update API endpoints in `app.js` to use Netlify functions

### Netlify Function Example

Create `netlify/functions/api.js`:
```javascript
exports.handler = async (event, context) => {
  // Proxy requests to your Python API
  // Or reimplement the logic in JavaScript
};
```

## API Endpoints

- `GET /api/auth/status` - Check authentication status
- `POST /api/auth/connect` - Connect to Strava
- `GET /api/activities` - Get recent activities
- `POST /api/generate` - Generate artwork for an activity
- `GET /api/images/:key` - Serve generated images

## Mobile Optimization

The interface is optimized for mobile devices with:
- Touch-friendly buttons and interactions
- Responsive grid layouts
- Optimized font sizes and spacing
- Smooth scrolling and transitions
- PWA capabilities (can be added to home screen)