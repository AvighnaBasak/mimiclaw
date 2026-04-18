import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, render_template

from db import (
    get_all_assignments,
    get_completed_assignments,
    get_pending_assignments,
    get_session,
)


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/assignments")
    def api_assignments():
        session = get_session()
        try:
            items = get_all_assignments(session)
            return jsonify([_serialize(a) for a in items])
        finally:
            session.close()

    @app.route("/api/completed")
    def api_completed():
        session = get_session()
        try:
            items = get_completed_assignments(session, limit=10)
            result = []
            for a in items:
                d = _serialize(a)
                d["files"] = [
                    {"filename": f.filename, "url": f.drive_url}
                    for f in a.files
                ]
                result.append(d)
            return jsonify(result)
        finally:
            session.close()

    @app.route("/api/upcoming")
    def api_upcoming():
        session = get_session()
        try:
            items = get_pending_assignments(session)
            return jsonify([_serialize(a) for a in items])
        finally:
            session.close()

    return app


def _serialize(a) -> dict:
    return {
        "id": a.id,
        "course_name": a.course_name,
        "title": a.title,
        "description": a.description,
        "due_date": a.due_date.isoformat() if a.due_date else None,
        "status": a.status,
        "drive_folder_url": a.drive_folder_url,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }
