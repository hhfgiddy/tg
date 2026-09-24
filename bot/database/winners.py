import secrets

from bot.database.db import get_connection


def select_winners(
    contest_id: int,
    winners_count: int,
) -> list[dict]:
    with get_connection() as connection:

        # Agar g‘oliblar oldin tanlangan bo‘lsa,
        # aynan o‘sha g‘oliblarni qaytaramiz.
        existing = connection.execute(
            """
            SELECT
                w.telegram_user_id,
                u.username,
                u.first_name
            FROM winners w
            LEFT JOIN users u
                ON u.telegram_user_id = w.telegram_user_id
            WHERE w.contest_id = ?
            ORDER BY w.id ASC
            """,
            (contest_id,),
        ).fetchall()

        if existing:
            return [dict(row) for row in existing]

        # Konkurs qatnashchilarini olish
        participants = connection.execute(
            """
            SELECT
                p.telegram_user_id,
                u.username,
                u.first_name
            FROM participants p
            LEFT JOIN users u
                ON u.telegram_user_id = p.telegram_user_id
            WHERE p.contest_id = ?
            """,
            (contest_id,),
        ).fetchall()

        if not participants:
            return []

        # G‘oliblar soni qatnashchilar sonidan oshib ketmasin
        amount = min(
            winners_count,
            len(participants),
        )

        # Tasodifiy va takrorlanmaydigan g‘oliblar
        selected = secrets.SystemRandom().sample(
            participants,
            amount,
        )

        # Database'ga saqlash
        for participant in selected:
            connection.execute(
                """
                INSERT OR IGNORE INTO winners (
                    contest_id,
                    telegram_user_id
                )
                VALUES (?, ?)
                """,
                (
                    contest_id,
                    participant["telegram_user_id"],
                ),
            )

        return [
            dict(participant)
            for participant in selected
        ]