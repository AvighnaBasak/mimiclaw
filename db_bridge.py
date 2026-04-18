"""Stdout JSON bridge — called by Electron main process to query the SQLite DB."""
import sys
import json
import os
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import (
    get_session,
    get_all_assignments,
    get_completed_assignments,
    get_pending_assignments,
    get_reminders,
    Assignment,
)


def _serialize_assignment(a) -> dict:
    return {
        "id": a.id,
        "course_name": a.course_name,
        "title": a.title,
        "description": a.description or "",
        "due_date": a.due_date.isoformat() if a.due_date else None,
        "status": a.status,
        "drive_folder_url": a.drive_folder_url,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def main():
    query_type = sys.argv[1] if len(sys.argv) > 1 else "assignments"
    session = get_session()
    try:
        if query_type == "assignments":
            data = [_serialize_assignment(a) for a in get_all_assignments(session)]

        elif query_type == "pending":
            data = [_serialize_assignment(a) for a in get_pending_assignments(session)]

        elif query_type == "completed":
            assignments = get_completed_assignments(session, limit=20)
            data = []
            for a in assignments:
                d = _serialize_assignment(a)
                d["files"] = [
                    {"filename": f.filename, "url": f.drive_url} for f in a.files
                ]
                data.append(d)

        elif query_type == "reminders":
            data = [
                {
                    "id": r.id,
                    "text": r.text,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in get_reminders(session)
            ]

        elif query_type == "stats":
            from sqlalchemy import func

            total = session.query(func.count(Assignment.id)).scalar() or 0
            completed = (
                session.query(func.count(Assignment.id))
                .filter(Assignment.status == "completed")
                .scalar()
                or 0
            )
            pending = (
                session.query(func.count(Assignment.id))
                .filter(Assignment.status.in_(["pending", "notified"]))
                .scalar()
                or 0
            )
            today = date.today().isoformat()
            overdue = (
                session.query(func.count(Assignment.id))
                .filter(
                    Assignment.status.in_(["pending", "notified"]),
                    Assignment.due_date < today,
                )
                .scalar()
                or 0
            )
            data = {
                "total": total,
                "completed": completed,
                "pending": pending,
                "overdue": overdue,
            }

        else:
            data = []

        print(json.dumps(data))

    finally:
        session.close()


if __name__ == "__main__":
    main()
