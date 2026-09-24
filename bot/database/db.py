import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATABASE_PATH = BASE_DIR / "database.db"


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_database() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL UNIQUE,
                username TEXT,
                first_name TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS contests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                owner_id INTEGER NOT NULL,

                channel_id INTEGER NOT NULL,
                channel_title TEXT,
                channel_username TEXT,
                channel_message_id INTEGER,

                post_type TEXT NOT NULL,
                post_text TEXT,
                post_file_id TEXT,

                start_at TEXT NOT NULL,

                end_type TEXT NOT NULL,
                end_at TEXT,
                participant_limit INTEGER,

                winners_count INTEGER NOT NULL,

                button_text TEXT NOT NULL
                    DEFAULT '🎟 Ishtirok etish',

                status TEXT NOT NULL
                    DEFAULT 'scheduled',

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (owner_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS required_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                contest_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                channel_title TEXT,
                channel_username TEXT,
                invite_link TEXT,

                FOREIGN KEY (contest_id)
                    REFERENCES contests(id)
                    ON DELETE CASCADE,

                UNIQUE (contest_id, channel_id)
            );

            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                telegram_user_id INTEGER NOT NULL,
                contest_id INTEGER NOT NULL,

                joined_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (contest_id)
                    REFERENCES contests(id)
                    ON DELETE CASCADE,

                UNIQUE (telegram_user_id, contest_id)
            );

            CREATE TABLE IF NOT EXISTS winners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                contest_id INTEGER NOT NULL,
                telegram_user_id INTEGER NOT NULL,

                selected_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (contest_id)
                    REFERENCES contests(id)
                    ON DELETE CASCADE,

                UNIQUE (contest_id, telegram_user_id)
            );

            CREATE INDEX IF NOT EXISTS idx_contests_owner_id
                ON contests(owner_id);

            CREATE INDEX IF NOT EXISTS idx_contests_status
                ON contests(status);

            CREATE INDEX IF NOT EXISTS idx_required_channels_contest_id
                ON required_channels(contest_id);

            CREATE INDEX IF NOT EXISTS idx_participants_contest_id
                ON participants(contest_id);

            CREATE INDEX IF NOT EXISTS idx_winners_contest_id
                ON winners(contest_id);
            """
        )

        _add_column_if_missing(
            connection,
            "contests",
            "channel_title",
            "TEXT",
        )

        _add_column_if_missing(
            connection,
            "contests",
            "channel_username",
            "TEXT",
        )

        _add_column_if_missing(
            connection,
            "contests",
            "channel_message_id",
            "INTEGER",
        )

        _add_column_if_missing(
            connection,
            "contests",
            "post_type",
            "TEXT",
        )

        _add_column_if_missing(
            connection,
            "contests",
            "post_text",
            "TEXT",
        )

        _add_column_if_missing(
            connection,
            "contests",
            "post_file_id",
            "TEXT",
        )

        _add_column_if_missing(
            connection,
            "contests",
            "end_type",
            "TEXT",
        )


def _add_column_if_missing(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_type: str,
) -> None:
    columns = connection.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    existing_columns = {
        column["name"]
        for column in columns
    }

    if column_name not in existing_columns:
        connection.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_name} {column_type}
            """
        )