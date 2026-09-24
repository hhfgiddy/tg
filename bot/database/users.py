from typing import Optional

from bot.database.db import get_connection


def create_or_update_user(
    telegram_user_id: int,
    username: Optional[str],
    first_name: Optional[str],
) -> int:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO users (
                telegram_user_id,
                username,
                first_name
            )
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_user_id)
            DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name
            """,
            (
                telegram_user_id,
                username,
                first_name,
            ),
        )

        row = connection.execute(
            """
            SELECT id
            FROM users
            WHERE telegram_user_id = ?
            """,
            (telegram_user_id,),
        ).fetchone()

        return int(row["id"])