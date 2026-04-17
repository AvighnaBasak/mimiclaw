import io
import os

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDS_FILE = os.path.join(BASE_DIR, "credentials", "google_credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "credentials", "token_drive.json")


class DriveClient:
    def __init__(self):
        self._service = None

    def _auth(self):
        creds = None
        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
        self._service = build("drive", "v3", credentials=creds)

    def _get_service(self):
        if not self._service:
            self._auth()
        return self._service

    def get_or_create_folder(self, name: str, parent_id: str | None = None) -> str:
        svc = self._get_service()
        query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        result = svc.files().list(q=query, fields="files(id, name)").execute()
        files = result.get("files", [])
        if files:
            return files[0]["id"]
        metadata = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            metadata["parents"] = [parent_id]
        folder = svc.files().create(body=metadata, fields="id").execute()
        return folder["id"]

    def upload_text_as_doc(self, title: str, content: str, folder_id: str) -> dict:
        svc = self._get_service()
        metadata = {"name": title, "parents": [folder_id]}
        media = MediaIoBaseUpload(
            io.BytesIO(content.encode("utf-8")),
            mimetype="text/plain",
            resumable=False,
        )
        uploaded = (
            svc.files()
            .create(body=metadata, media_body=media, fields="id, webViewLink")
            .execute()
        )
        return {"id": uploaded["id"], "webViewLink": uploaded.get("webViewLink", "")}

    def create_assignment_folder(
        self, course_name: str, assignment_title: str, assignment_number: int | None = None
    ) -> str:
        svc = self._get_service()
        root_id = self.get_or_create_folder("MimiClaw Assignments")
        course_id = self.get_or_create_folder(course_name, parent_id=root_id)
        label = assignment_title
        if assignment_number is not None:
            label = f"{assignment_number}. {assignment_title}"
        folder_id = self.get_or_create_folder(label, parent_id=course_id)
        result = (
            svc.files()
            .get(fileId=folder_id, fields="webViewLink")
            .execute()
        )
        return result.get("webViewLink", "")

    def get_folder_id_for_assignment(
        self, course_name: str, assignment_title: str
    ) -> str:
        root_id = self.get_or_create_folder("MimiClaw Assignments")
        course_id = self.get_or_create_folder(course_name, parent_id=root_id)
        return self.get_or_create_folder(assignment_title, parent_id=course_id)

    def upload_multiple_files(self, files_list: list[dict], folder_id: str) -> list[dict]:
        results = []
        for f in files_list:
            try:
                uploaded = self.upload_text_as_doc(f["filename"], f["content"], folder_id)
                results.append({"filename": f["filename"], "url": uploaded["webViewLink"]})
            except Exception as e:
                results.append({"filename": f["filename"], "url": f"Error: {e}"})
        return results

    def download_file(self, file_id: str) -> bytes:
        svc = self._get_service()
        request = svc.files().get_media(fileId=file_id)
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buf.getvalue()
