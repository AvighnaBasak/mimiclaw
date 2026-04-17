"""Run this once locally to authenticate with Google APIs before deploying."""
import os
import sys

os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDS_FILE = os.path.join(BASE_DIR, "credentials", "google_credentials.json")

CLASSROOM_SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.coursework.me.readonly",
    "https://www.googleapis.com/auth/classroom.student-submissions.me.readonly",
]
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]

CLASSROOM_TOKEN = os.path.join(BASE_DIR, "credentials", "token_classroom.json")
DRIVE_TOKEN = os.path.join(BASE_DIR, "credentials", "token_drive.json")


def auth_service(scopes: list[str], token_file: str, name: str):
    print(f"\n{'='*50}")
    print(f"Step: Authenticating {name}")
    print(f"{'='*50}")
    print("A browser window will open. Sign in with your Google account.")
    print("Make sure to use the account that has access to your Google Classroom.")

    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, scopes)
            creds = flow.run_local_server(port=0)
        with open(token_file, "w") as f:
            f.write(creds.to_json())
        print(f"[OK] {name} token saved to: {token_file}")
    else:
        print(f"[OK] {name} token already valid.")


def main():
    if not os.path.exists(CREDS_FILE):
        print("ERROR: credentials/google_credentials.json not found.")
        print("Please download your OAuth 2.0 client secret from Google Cloud Console:")
        print("  1. Go to https://console.cloud.google.com/")
        print("  2. Create a project or select existing")
        print("  3. Enable: Google Classroom API, Google Drive API")
        print("  4. Go to APIs & Services > Credentials")
        print("  5. Create OAuth 2.0 Client ID (Desktop app)")
        print("  6. Download JSON and save as credentials/google_credentials.json")
        sys.exit(1)

    os.makedirs(os.path.join(BASE_DIR, "credentials"), exist_ok=True)

    auth_service(CLASSROOM_SCOPES, CLASSROOM_TOKEN, "Google Classroom")
    auth_service(DRIVE_SCOPES, DRIVE_TOKEN, "Google Drive")

    print("\n" + "=" * 50)
    print("[OK] Both tokens saved. You can now run bot.py and the dashboard.")
    print("=" * 50)


if __name__ == "__main__":
    main()
