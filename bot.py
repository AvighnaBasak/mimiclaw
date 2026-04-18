import asyncio
import logging
import os
from io import BytesIO

from dotenv import load_dotenv
from telegram import (
    Bot,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from ai import AIClient
from classroom import ClassroomClient
from db import (
    add_chat_message,
    add_completed_file,
    add_reminder,
    get_all_assignments,
    get_assignment,
    get_chat_history,
    get_pending_assignments,
    get_recent_files,
    get_reminders,
    get_session,
    init_db,
    update_assignment_status,
    insert_assignment,
)
from drive import DriveClient
from pdf_reader import cleanup_temp, download_and_extract
from scheduler import create_scheduler

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ALLOWED_USER_ID = int(os.getenv("TELEGRAM_ALLOWED_USER_ID", "0"))

ai_client = AIClient()
classroom_client = ClassroomClient()
drive_client = DriveClient()

# Tracks user state: when a user selects an assignment, we store it here
# and wait for their custom prompt before completing it
awaiting_prompt: dict[int, dict] = {}


def _is_allowed(update: Update) -> bool:
    uid = update.effective_user.id if update.effective_user else None
    return uid == ALLOWED_USER_ID


def _format_date(d) -> str:
    if d is None:
        return "No due date"
    return d.strftime("%b %d, %Y") if hasattr(d, "strftime") else str(d)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    await update.message.reply_text(
        "🦞 *MimiClaw* is online!\n\n"
        "I monitor your Google Classroom, complete assignments with AI, and save them to Drive.\n\n"
        "Commands:\n"
        "/assignments — list pending assignments (tap to do one)\n"
        "/check — poll Classroom now\n"
        "/done <id> — mark assignment done manually\n"
        "/remind <text> — save a reminder\n"
        "/reminders — list reminders\n"
        "/drive — recent Drive files\n"
        "/help — show this list",
        parse_mode="Markdown",
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    await cmd_start(update, ctx)


async def cmd_assignments(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    session = get_session()
    try:
        items = get_pending_assignments(session)
        if not items:
            await update.message.reply_text("No pending assignments. 🎉")
            return
        lines = ["📚 *Pending Assignments:*\n"]
        buttons = []
        for i, a in enumerate(items, 1):
            lines.append(
                f"{i}. *{a.title}*\n"
                f"   {a.course_name} — Due: {_format_date(a.due_date)}"
            )
            buttons.append(
                [InlineKeyboardButton(
                    f"📝 {i}. {a.title[:40]}",
                    callback_data=f"select:{a.id}",
                )]
            )
        lines.append("\n👆 Tap an assignment above to start working on it.")
        keyboard = InlineKeyboardMarkup(buttons)
        await update.message.reply_text(
            "\n".join(lines), parse_mode="Markdown", reply_markup=keyboard
        )
    finally:
        session.close()


async def cmd_check(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    await update.message.reply_text("🔍 Checking Google Classroom now...")
    session = get_session()
    try:
        new = classroom_client.get_all_new_assignments(session)
        if not new:
            await update.message.reply_text("No new assignments found.")
            return
        for a in new:
            from db import assignment_id_exists
            if not assignment_id_exists(session, a["id"]):
                insert_assignment(session, {
                    "id": a["id"],
                    "course_id": a["course_id"],
                    "course_name": a["course_name"],
                    "title": a["title"],
                    "description": a["description"],
                    "due_date": a.get("due_date"),
                    "status": "pending",
                })
        await _notify_new_assignments(new, update.effective_chat.id, ctx.bot)
    except Exception as e:
        await update.message.reply_text(f"Error checking Classroom: {e}")
    finally:
        session.close()


async def cmd_done(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    args = ctx.args
    if not args:
        await update.message.reply_text("Usage: /done <assignment_id>")
        return
    assignment_id = args[0]
    session = get_session()
    try:
        a = update_assignment_status(session, assignment_id, "completed")
        if a:
            await update.message.reply_text(f"✅ Marked *{a.title}* as completed.", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"Assignment {assignment_id} not found.")
    finally:
        session.close()


async def cmd_remind(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    text = " ".join(ctx.args) if ctx.args else ""
    if not text:
        await update.message.reply_text("Usage: /remind <text>")
        return
    session = get_session()
    try:
        add_reminder(session, text)
        await update.message.reply_text(f"🔔 Reminder saved: {text}")
    finally:
        session.close()


async def cmd_reminders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    session = get_session()
    try:
        reminders = get_reminders(session)
        if not reminders:
            await update.message.reply_text("No reminders saved.")
            return
        lines = ["🔔 *Your Reminders:*\n"]
        for r in reminders:
            lines.append(f"• {r.text} _{r.created_at.strftime('%b %d')}_")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    finally:
        session.close()


async def cmd_drive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    session = get_session()
    try:
        files = get_recent_files(session)
        if not files:
            await update.message.reply_text("No files saved to Drive yet.")
            return
        lines = ["📁 *Recent Drive Files:*\n"]
        for f in files:
            lines.append(f"• [{f.filename}]({f.drive_url}) _{f.created_at.strftime('%b %d')}_")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown", disable_web_page_preview=True)
    finally:
        session.close()


async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_allowed(update):
        return
    text = update.message.text.strip()
    uid = update.effective_user.id

    # If we're waiting for a custom prompt for an assignment
    if uid in awaiting_prompt:
        assignment_info = awaiting_prompt.pop(uid)
        custom_prompt = None if text.lower() in ("none", "no", "nope", "skip", "-") else text
        await _do_assignment(
            assignment_info["id"],
            update.effective_chat.id,
            ctx.bot,
            custom_prompt=custom_prompt,
            pdf_text=assignment_info.get("pdf_text"),
        )
        return

    # General chat
    session = get_session()
    try:
        history = get_chat_history(session, limit=10)
        add_chat_message(session, "user", text)
        reply = ai_client.chat(text, history)
        add_chat_message(session, "assistant", reply)
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text(f"AI error: {e}")
    finally:
        session.close()


async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not query.from_user or query.from_user.id != ALLOWED_USER_ID:
        return
    data = query.data

    if data.startswith("select:"):
        assignment_id = data.split(":", 1)[1]
        await _preview_assignment(assignment_id, query, ctx.bot)
    elif data.startswith("do_assignment:"):
        assignment_id = data.split(":", 1)[1]
        await _do_assignment(assignment_id, query.message.chat_id, ctx.bot, query=query)
    elif data.startswith("skip_assignment:"):
        assignment_id = data.split(":", 1)[1]
        session = get_session()
        try:
            update_assignment_status(session, assignment_id, "skipped")
        finally:
            session.close()
        await query.edit_message_text("⏭️ Skipped. I'll stop pinging you about this one.")
    elif data.startswith("remind_do:"):
        assignment_id = data.split(":", 1)[1]
        await _preview_assignment(assignment_id, query, ctx.bot)
    elif data.startswith("remind_skip:"):
        assignment_id = data.split(":", 1)[1]
        session = get_session()
        try:
            update_assignment_status(session, assignment_id, "skipped")
        finally:
            session.close()
        await query.edit_message_text("⏭️ Skipped.")


async def _preview_assignment(assignment_id: str, query, bot: Bot):
    """Show assignment details, send attachments, and ask for custom prompt."""
    chat_id = query.message.chat_id
    uid = query.from_user.id
    session = get_session()
    try:
        a = get_assignment(session, assignment_id)
        if not a:
            await query.edit_message_text("Assignment not found.")
            return

        desc = a.description or "No description provided."
        due = _format_date(a.due_date)
        msg = (
            f"📚 *{a.title}*\n"
            f"📖 {a.course_name}\n"
            f"📅 Due: {due}\n\n"
            f"*Description:*\n{desc}"
        )
        await query.edit_message_text(msg, parse_mode="Markdown")

        # Fetch attachments from Classroom and send them
        pdf_text = None
        try:
            assignments = classroom_client.get_assignments(a.course_id, a.course_name)
            classroom_data = next((x for x in assignments if x["id"] == a.id), None)
            if classroom_data:
                for att in classroom_data.get("attachments", []):
                    if att["type"] == "drive_file" and att.get("id"):
                        try:
                            file_bytes = drive_client.download_file(att["id"])
                            filename = att.get("title", "attachment")
                            doc_buf = BytesIO(file_bytes)
                            doc_buf.name = filename
                            await bot.send_document(
                                chat_id=chat_id,
                                document=doc_buf,
                                filename=filename,
                                caption=f"📎 Attachment: {filename}",
                            )
                            # Try to extract text from PDF for AI context
                            if filename.lower().endswith(".pdf"):
                                try:
                                    import tempfile, fitz
                                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                                        tmp.write(file_bytes)
                                        tmp_path = tmp.name
                                    doc = fitz.open(tmp_path)
                                    pages = [page.get_text() for page in doc]
                                    doc.close()
                                    os.remove(tmp_path)
                                    extracted = "\n".join(pages).strip()
                                    if extracted:
                                        pdf_text = (pdf_text or "") + "\n\n" + extracted
                                except Exception as e:
                                    logger.warning(f"PDF text extraction failed: {e}")
                        except Exception as e:
                            logger.warning(f"Failed to send attachment {att.get('title')}: {e}")
                            await bot.send_message(
                                chat_id=chat_id,
                                text=f"⚠️ Couldn't download attachment: {att.get('title', 'unknown')}",
                            )
                    elif att["type"] == "link":
                        await bot.send_message(
                            chat_id=chat_id,
                            text=f"🔗 Link: [{att.get('title', 'Link')}]({att['url']})",
                            parse_mode="Markdown",
                            disable_web_page_preview=True,
                        )
        except Exception as e:
            logger.warning(f"Failed to fetch attachments from Classroom: {e}")

        # Store state and ask for custom prompt
        awaiting_prompt[uid] = {
            "id": a.id,
            "pdf_text": pdf_text,
        }
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "✏️ Do you have any specific instructions I should follow for this assignment?\n\n"
                "For example: _write it in a human tone, keep it under 500 words, "
                "focus on section 3, use APA format_, etc.\n\n"
                'Type your instructions, or send *none* to proceed without any.'
            ),
            parse_mode="Markdown",
        )
    finally:
        session.close()


async def _do_assignment(
    assignment_id: str,
    chat_id: int,
    bot: Bot,
    query=None,
    custom_prompt: str | None = None,
    pdf_text: str | None = None,
):
    session = get_session()
    try:
        a = get_assignment(session, assignment_id)
        if not a:
            if query:
                await query.edit_message_text("Assignment not found.")
            return
        update_assignment_status(session, assignment_id, "in_progress")
    finally:
        session.close()

    session = get_session()
    try:
        a = get_assignment(session, assignment_id)
        assignment_dict = {
            "id": a.id,
            "course_id": a.course_id,
            "course_name": a.course_name,
            "title": a.title,
            "description": a.description,
            "due_date": a.due_date,
        }

        if custom_prompt:
            assignment_dict["description"] = (
                (assignment_dict["description"] or "") +
                f"\n\n--- Student's Instructions ---\n{custom_prompt}"
            )

        # Step 1: Plan what files are needed
        await bot.send_message(chat_id=chat_id, text="🤖 Analyzing assignment...")
        filenames = ai_client.plan_files(assignment_dict, pdf_text=pdf_text)
        await bot.send_message(
            chat_id=chat_id,
            text=f"📋 Will generate {len(filenames)} file(s): {', '.join(filenames)}",
        )

        # Step 2: Create Drive folder
        folder_url = drive_client.create_assignment_folder(a.course_name, a.title)
        folder_id = drive_client.get_folder_id_for_assignment(a.course_name, a.title)

        # Step 3: Generate each file one by one, upload and send immediately
        uploaded = []
        for i, filename in enumerate(filenames, 1):
            await bot.send_message(
                chat_id=chat_id,
                text=f"⚙️ Generating file {i}/{len(filenames)}: {filename}...",
            )

            try:
                content = ai_client.generate_file(filename, assignment_dict, pdf_text=pdf_text)
            except Exception as e:
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ Failed to generate {filename}: {e}",
                )
                continue

            # Upload to Drive
            try:
                result = drive_client.upload_text_as_doc(filename, content, folder_id)
                file_url = result.get("webViewLink", "")
                uploaded.append({"filename": filename, "url": file_url})
                add_completed_file(session, a.id, filename, file_url)
            except Exception as e:
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ Failed to upload {filename} to Drive: {e}",
                )

            # Send file in Telegram immediately
            doc_buf = BytesIO(content.encode("utf-8"))
            doc_buf.name = filename
            await bot.send_document(
                chat_id=chat_id,
                document=doc_buf,
                filename=filename,
                caption=f"📄 {filename} ({i}/{len(filenames)})",
            )

        # Step 4: Update status and send Drive link
        update_assignment_status(session, a.id, "pending", drive_folder_url=folder_url)

        if not uploaded:
            await bot.send_message(chat_id=chat_id, text="❌ No files were generated successfully.")
        elif len(uploaded) == 1:
            await bot.send_message(
                chat_id=chat_id,
                text=f"✅ Done! Saved to Drive: [Open]({uploaded[0]['url']})",
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
        else:
            filenames_str = ", ".join(f["filename"] for f in uploaded)
            await bot.send_message(
                chat_id=chat_id,
                text=(
                    f"✅ Done! {len(uploaded)} files saved to Drive folder: "
                    f"[Open Folder]({folder_url})\n"
                    f"Files: {filenames_str}"
                ),
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
    except Exception as e:
        logger.error(f"Assignment error: {e}", exc_info=True)
        update_assignment_status(session, assignment_id, "pending")
        await bot.send_message(chat_id=chat_id, text=f"Error completing assignment: {e}")
    finally:
        session.close()


async def _notify_new_assignments(assignments: list[dict], chat_id: int, bot: Bot):
    if len(assignments) == 1:
        a = assignments[0]
        due = _format_date(a.get("due_date"))
        desc = a.get("description", "") or "No description."
        msg = (
            f"📚 New assignment in *{a['course_name']}*:\n\n"
            f"*{a['title']}*\n"
            f"📅 Due: {due}\n\n"
            f"{desc}"
        )
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Do it", callback_data=f"select:{a['id']}"),
                InlineKeyboardButton("⏭️ Skip", callback_data=f"skip_assignment:{a['id']}"),
            ]
        ])
        await bot.send_message(
            chat_id=chat_id, text=msg, reply_markup=keyboard, parse_mode="Markdown"
        )
    else:
        lines = [f"📚 *{len(assignments)} new assignments found:*\n"]
        buttons = []
        for i, a in enumerate(assignments, 1):
            due = _format_date(a.get("due_date"))
            lines.append(f"{i}. *{a['title']}* — {a['course_name']} (due {due})")
            buttons.append(
                [InlineKeyboardButton(
                    f"📝 {i}. {a['title'][:40]}",
                    callback_data=f"select:{a['id']}",
                )]
            )
        keyboard = InlineKeyboardMarkup(buttons)
        await bot.send_message(
            chat_id=chat_id, text="\n".join(lines), parse_mode="Markdown", reply_markup=keyboard
        )


async def _notify_due_date(assignment, bot: Bot, chat_id: int):
    due = _format_date(assignment.due_date)
    msg = (
        f"⏰ Reminder: *{assignment.title}* ({assignment.course_name}) is due on {due}.\n"
        "It hasn't been completed yet. Want me to do it now?"
    )
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes", callback_data=f"remind_do:{assignment.id}"),
            InlineKeyboardButton("⏭️ Skip", callback_data=f"remind_skip:{assignment.id}"),
        ]
    ])
    await bot.send_message(
        chat_id=chat_id, text=msg, reply_markup=keyboard, parse_mode="Markdown"
    )


async def _notify_error(message: str, bot: Bot, chat_id: int):
    await bot.send_message(chat_id=chat_id, text=f"⚠️ MimiClaw error: {message}")


def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("assignments", cmd_assignments))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(CommandHandler("done", cmd_done))
    app.add_handler(CommandHandler("remind", cmd_remind))
    app.add_handler(CommandHandler("reminders", cmd_reminders))
    app.add_handler(CommandHandler("drive", cmd_drive))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    async def post_init(application: Application):
        chat_id = ALLOWED_USER_ID

        async def notify_fn(assignments):
            await _notify_new_assignments(assignments, chat_id, application.bot)

        async def remind_fn(a):
            await _notify_due_date(a, application.bot, chat_id)

        async def error_fn(msg):
            await _notify_error(msg, application.bot, chat_id)

        ctx = {
            "classroom": classroom_client,
            "notify_new_assignments": notify_fn,
            "notify_due_date": remind_fn,
            "notify_error": error_fn,
        }
        scheduler = create_scheduler(ctx)
        scheduler.start()

    app.post_init = post_init
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
