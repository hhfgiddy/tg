from typing import Any

from bot.database.db import get_connection


def create_contest(
    owner_id: int,
    data: dict[str, Any],
) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO contests (
                owner_id,
                channel_id,
                channel_title,
                channel_username,
                post_type,
                post_text,
                post_file_id,
                start_at,
                end_type,
                end_at,
                participant_limit,
                winners_count,
                button_text,
                status
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                owner_id,
                data["channel_id"],
                data.get("channel_title"),
                data.get("channel_username"),
                data["post_type"],
                data.get("post_text"),
                data.get("post_file_id"),
                data["start_at"],
                data["end_type"],
                data.get("end_at"),
                data.get("participant_limit"),
                data["winners_count"],
                data.get(
                    "button_text",
                    "🎟 Ishtirok etish",
                ),
                "scheduled",
            ),
        )

        contest_id = cursor.lastrowid

        for channel in data["required_channels"]:
            connection.execute(
                """
                INSERT INTO required_channels (
                    contest_id,
                    channel_id,
                    channel_title,
                    channel_username
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    contest_id,
                    channel["channel_id"],
                    channel["channel_title"],
                    channel.get("channel_username"),
                ),
            )

        return int(contest_id)