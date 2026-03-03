import os
import sqlite3
from datetime import datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

DB_PATH = "assistant.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def now():
    return datetime.now().isoformat(timespec="seconds")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Я твой ассистент.\n\n"
        "Команды:\n"
        "/t <текст> — добавить задачу\n"
        "/tl — список задач\n"
        "/td <id> — завершить задачу\n"
        "/n <текст> — заметка\n"
        "/nl — последние заметки"
    )


async def task_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    title = " ".join(context.args).strip()

    if not title:
        await update.message.reply_text("Напиши так: /t купить воду")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO tasks (chat_id, title, created_at, done) VALUES (?, ?, ?, 0)",
        (chat_id, title, now()),
    )
    conn.commit()
    conn.close()

    await update.message.reply_text(f"✅ Задача добавлена: {title}")


async def task_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, title, done FROM tasks WHERE chat_id = ? ORDER BY done, id DESC LIMIT 50",
        (chat_id,),
    ).fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("🫙 Задач нет.")
        return

    lines = []
    for tid, title, done in rows:
        icon = "✅" if done else "🟡"
        lines.append(f"{icon} {tid}: {title}")

    await update.message.reply_text("\n".join(lines))


async def task_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Напиши так: /td 3")
        return

    tid = int(context.args[0])

    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "UPDATE tasks SET done = 1 WHERE chat_id = ? AND id = ?",
        (chat_id, tid),
    )
    conn.commit()
    conn.close()

    if cur.rowcount == 0:
        await update.message.reply_text("❌ Не нашёл такую задачу.")
    else:
        await update.message.reply_text(f"✅ Готово: {tid}")


async def note_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = " ".join(context.args).strip()

    if not text:
        await update.message.reply_text("Напиши так: /n идея для ассистента")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO notes (chat_id, text, created_at) VALUES (?, ?, ?)",
        (chat_id, text, now()),
    )
    conn.commit()
    conn.close()

    await update.message.reply_text("📝 Заметка сохранена.")


async def note_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, created_at, text FROM notes WHERE chat_id = ? ORDER BY id DESC LIMIT 20",
        (chat_id,),
    ).fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("🫙 Заметок нет.")
        return

    lines = [f"🗒️ {nid} | {created_at} — {text}" for nid, created_at, text in rows]

    await update.message.reply_text("\n".join(lines))


def main():
    init_db()

    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN not set")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("t", task_add))
    app.add_handler(CommandHandler("tl", task_list))
    app.add_handler(CommandHandler("td", task_done))
    app.add_handler(CommandHandler("n", note_add))
    app.add_handler(CommandHandler("nl", note_list))

    print("Bot started...")
    app.run_polling()


if __name__ == "__main__":
    main()
