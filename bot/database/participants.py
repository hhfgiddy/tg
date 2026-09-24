from bot.database.db import get_connection


def add_participant(
    telegram_user_id: int,
    contest_id: int,
) -> bool:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO participants (
                telegram_user_id,
                contest_id
            )
            VALUES (?, ?)
            """,
            (
                telegram_user_id,
                contest_id,
            ),
        )

        return cursor.rowcount > 0


def is_participant(
    telegram_user_id: int,
    contest_id: int,
) -> bool:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id
            FROM participants
            WHERE telegram_user_id = ?
              AND contest_id = ?
            """,
            (
                telegram_user_id,
                contest_id,
            ),
        ).fetchone()

        return row is not None


def get_participant_count(
    contest_id: int,
) -> int:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM participants
            WHERE contest_id = ?
            """,
            (contest_id,),
        ).fetchone()

        return int(row["count"])