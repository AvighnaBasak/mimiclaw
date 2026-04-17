import os
import json
from datetime import date

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.coursework.me.readonly",
    "https://www.googleapis.com/auth/classroom.student-submissions.me.readonly",
]
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDS_FILE = os.path.join(BASE_DIR, "credentials", "google_credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "credentials", "token_classroom.json")


class ClassroomClient:
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
        self._service = build("classroom", "v1", credentials=creds)

    def _get_service(self):
        if not self._service:
            self._auth()
        return self._service

    def get_active_courses(self) -> list[dict]:
        svc = self._get_service()
        result = svc.courses().list(courseStates=["ACTIVE"]).execute()
        courses = result.get("courses", [])
        return [{"id": c["id"], "name": c.get("name", "Unknown")} for c in courses]

    def get_assignments(self, course_id: str, course_name: str = "") -> list[dict]:
        svc = self._get_service()
        result = (
            svc.courses()
            .courseWork()
            .list(courseId=course_id, courseWorkStates=["PUBLISHED"])
            .execute()
        )
        items = result.get("courseWork", [])
        assignments = []
        for item in items:
            due = None
            if "dueDate" in item:
                d = item["dueDate"]
                try:
                    due = date(d["year"], d["month"], d["day"])
                except Exception:
                    pass
            attachments = []
            for mat in item.get("materials", []):
                if "driveFile" in mat:
                    df = mat["driveFile"]["driveFile"]
                    attachments.append({
                        "type": "drive_file",
                        "url": df.get("alternateLink", ""),
                        "title": df.get("title", ""),
                        "id": df.get("id", ""),
                    })
                elif "link" in mat:
                    lnk = mat["link"]
                    attachments.append({
                        "type": "link",
                        "url": lnk.get("url", ""),
                        "title": lnk.get("title", ""),
                    })
                elif "form" in mat:
                    frm = mat["form"]
                    attachments.append({
                        "type": "form",
                        "url": frm.get("formUrl", ""),
                        "title": frm.get("title", ""),
                    })
            assignments.append({
                "id": item["id"],
                "course_id": course_id,
                "course_name": course_name,
                "title": item.get("title", "Untitled"),
                "description": item.get("description", ""),
                "due_date": due,
                "attachments": attachments,
            })
        return assignments

    def get_all_new_assignments(self, session) -> list[dict]:
        from db import assignment_id_exists

        courses = self.get_active_courses()
        new_assignments = []
        for course in courses:
            try:
                assignments = self.get_assignments(course["id"], course["name"])
                for a in assignments:
                    if not assignment_id_exists(session, a["id"]):
                        new_assignments.append(a)
            except Exception:
                continue
        return new_assignments

    def get_student_submission(self, course_id: str, assignment_id: str) -> dict | None:
        svc = self._get_service()
        try:
            result = (
                svc.courses()
                .courseWork()
                .studentSubmissions()
                .list(courseId=course_id, courseWorkId=assignment_id, userId="me")
                .execute()
            )
            submissions = result.get("studentSubmissions", [])
            if submissions:
                return submissions[0]
        except Exception:
            pass
        return None
