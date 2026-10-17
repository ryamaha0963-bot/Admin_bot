import aiosqlite
from config import DB_PATH


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS promoted_admins (
                chat_id INTEGER,
                user_id INTEGER,
                promoted_by INTEGER,
                promoted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (chat_id, user_id)
            )
        """)
        await db.commit()


async def save_promoted_admin(chat_id, user_id, promoted_by):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO promoted_admins (chat_id, user_id, promoted_by) VALUES (?, ?, ?)",
            (chat_id, user_id, promoted_by),
        )
        await db.commit()


async def is_bot_promoted(chat_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM promoted_admins WHERE chat_id=? AND user_id=?",
            (chat_id, user_id),
        ) as cur:
            return await cur.fetchone() is not None


async def delete_promoted_admin(chat_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM promoted_admins WHERE chat_id=? AND user_id=?",
            (chat_id, user_id),
        )
        await db.commit()
