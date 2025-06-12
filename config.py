import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from a .env file if present

# Required environment variables
STRAVA_CLIENT_ID = int(os.getenv("STRAVA_CLIENT_ID"))
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
STRAVA_REFRESH_TOKEN = os.getenv("STRAVA_REFRESH_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Optional settings
USER_IMAGES_DIR = os.getenv("USER_IMAGES_DIR", "/Users/bryanaltman/StravaPictures")
BRYAN_IMAGES_DIR = os.getenv("BRYAN_IMAGES_DIR", "bryanphotos")  # Directory with photos of Bryan
IMAGE_SIZE = os.getenv("OPENAI_IMAGE_SIZE", "1024x1024")
IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")  # Latest OpenAI image model
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "generated_images")

# Basic validation to catch missing credentials early
for var_name in ("STRAVA_CLIENT_ID", "STRAVA_CLIENT_SECRET", "STRAVA_REFRESH_TOKEN", "OPENAI_API_KEY"):
    if not globals()[var_name]:
        raise EnvironmentError(f"Environment variable {var_name} is not set.")