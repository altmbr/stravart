# Strava Run Art

Generate an AI‑designed poster for your most recent Strava run and append the image link to the activity description.

## Setup

1. Clone this repo and `cd` into it (or just copy the files somewhere).
2. Create and activate a virtual environment (optional but recommended).
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create a `.env` file alongside `main.py` with the following keys:

```
STRAVA_CLIENT_ID=12345
STRAVA_CLIENT_SECRET=your_strava_client_secret
STRAVA_REFRESH_TOKEN=your_strava_refresh_token
OPENAI_API_KEY=sk-...
# Optional overrides
USER_IMAGES_DIR=/path/to/portraits
OPENAI_IMAGE_SIZE=1024x1024
OUTPUT_DIR=generated_images
```

To obtain Strava credentials, create an “API Application” at <https://www.strava.com/settings/api> and perform the OAuth flow once to capture a `refresh_token` (see the Strava docs). The app must have the `activity:read` and `activity:write` scopes.

## Usage

```bash
python main.py
```

The script will:

1. Refresh your Strava `access_token`.
2. Pull your latest activity (limit=1).
3. Build a DALL·E prompt summarising the run.
4. Generate a poster image, download it locally, and embed the public URL in the activity description.

Strava’s public API currently **does not allow adding photos** to an existing activity, so this script appends a link instead. If Strava adds that capability in the future, update `update_strava_description` accordingly.
