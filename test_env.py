import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def print_env_status():
    print("=== ENVIRONMENT VARIABLES LOAD TEST ===")
    print(f"Server Port: {os.getenv('PORT')}")
    print(f"Environment: {os.getenv('ENVIRONMENT')}")
    print(f"Cloudinary Cloud Name: {os.getenv('CLOUDINARY_CLOUD_NAME')}")
    print(f"Google Credentials Path: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")
    print(f"Google Sheet ID: {os.getenv('GOOGLE_SHEET_ID')}")
    print(f"Portfolio Website URL: {os.getenv('PORTFOLIO_WEBSITE_URL')}")
    print(f"Scraping URLs: {os.getenv('SCRAPING_TARGET_URLS')}")
    print(f"Model Name: {os.getenv('MODEL_NAME')}")
    print("=======================================")

if __name__ == "__main__":
    print_env_status()
