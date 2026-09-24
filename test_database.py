from bot.database.db import get_connection, init_database
from bot.database.users import create_or_update_user


def main() -> None:
    init_database()

    user_id = create_or_update_user(
        telegram_user_id=123456789,
        username="test_user",
        first_name="Test",
    )

    print(f"User database ID: {user_id}")

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                id,
                telegram_user_id,
                username,
                first_name
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()

        print(dict(row))


if __name__ == "__main__":
    main()