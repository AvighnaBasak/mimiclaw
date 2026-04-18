import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)


def create_scheduler(app_context: dict) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        _poll_classroom,
        "interval",
        minutes=15,
        id="poll_classroom",
        kwargs={"ctx": app_context},
    )

    scheduler.add_job(
        _due_date_reminders,
        "cron",
        hour=9,
        minute=0,
        id="due_date_reminders",
        kwargs={"ctx": app_context},
    )

    scheduler.add_job(
        _sync_submission_states,
        "interval",
        minutes=15,
        id="sync_submissions",
        kwargs={"ctx": app_context},
    )

    scheduler.add_job(
        _verify_drive_links,
        "interval",
        minutes=30,
        id="verify_drive_links",
        kwargs={"ctx": app_context},
    )

    return scheduler


async def _poll_classroom(ctx: dict):
    from db import get_session, insert_assignment, assignment_id_exists

    classroom = ctx["classroom"]
    notify_fn = ctx["notify_new_assignments"]

    session = get_session()
    try:
        new_assignments = classroom.get_all_new_assignments(session)
        if not new_assignments:
            return
        for a in new_assignments:
            if not assignment_id_exists(session, a["id"]):
                db_data = {
                    "id": a["id"],
                    "course_id": a["course_id"],
                    "course_name": a["course_name"],
                    "title": a["title"],
                    "description": a["description"],
                    "due_date": a.get("due_date"),
                    "status": "pending",
                }
                insert_assignment(session, db_data)
        await notify_fn(new_assignments)
    except Exception as e:
        logger.error(f"poll_classroom error: {e}")
        error_fn = ctx.get("notify_error")
        if error_fn:
            await error_fn(f"Classroom poll error: {e}")
    finally:
        session.close()


async def _due_date_reminders(ctx: dict):
    from db import get_session, get_pending_assignments, update_assignment_status

    remind_fn = ctx["notify_due_date"]
    session = get_session()
    try:
        pending = get_pending_assignments(session)
        now = datetime.utcnow()
        today = now.date()
        for a in pending:
            if not a.due_date:
                continue
            if a.due_date <= today:
                continue
            cutoff = now - timedelta(hours=24)
            if a.last_pinged_at and a.last_pinged_at > cutoff:
                continue
            await remind_fn(a)
            update_assignment_status(
                session, a.id, a.status, last_pinged_at=now
            )
    except Exception as e:
        logger.error(f"due_date_reminders error: {e}")
        error_fn = ctx.get("notify_error")
        if error_fn:
            await error_fn(f"Reminder job error: {e}")
    finally:
        session.close()


async def _sync_submission_states(ctx: dict):
    """Check Classroom for submitted assignments and mark them completed."""
    from db import get_session, get_pending_assignments, update_assignment_status

    classroom = ctx["classroom"]
    session = get_session()
    try:
        pending = get_pending_assignments(session)
        for a in pending:
            try:
                state = classroom._get_submission_state(a.course_id, a.id)
                if state in ("TURNED_IN", "RETURNED"):
                    update_assignment_status(session, a.id, "completed")
                    logger.info(f"Marked '{a.title}' as completed (submitted on Classroom)")
            except Exception:
                continue
    except Exception as e:
        logger.error(f"sync_submission_states error: {e}")
    finally:
        session.close()


async def _verify_drive_links(ctx: dict):
    """Clear Drive links for folders that no longer exist."""
    from db import get_session, Assignment
    from drive import DriveClient

    drive = DriveClient()
    session = get_session()
    try:
        assignments = (
            session.query(Assignment)
            .filter(Assignment.drive_folder_url.isnot(None))
            .all()
        )
        for a in assignments:
            try:
                if not drive.folder_url_valid(a.drive_folder_url):
                    a.drive_folder_url = None
                    # Also clear associated file records
                    for f in a.files:
                        session.delete(f)
                    session.commit()
                    logger.info(f"Cleared deleted Drive link for '{a.title}'")
            except Exception:
                continue
    except Exception as e:
        logger.error(f"verify_drive_links error: {e}")
    finally:
        session.close()
