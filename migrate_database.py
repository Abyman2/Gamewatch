import sqlite3


DATABASE_NAME = "gamewatch.db"


def column_exists(cursor, table, column):

    cursor.execute(
        f"PRAGMA table_info({table})"
    )

    columns = cursor.fetchall()

    for col in columns:

        if col[1] == column:

            return True

    return False


def migrate():

    connection = sqlite3.connect(
        DATABASE_NAME
    )

    cursor = connection.cursor()


    # Add payment proof path
    # to transactions table

    if not column_exists(
        cursor,
        "transactions",
        "payment_proof"
    ):

        cursor.execute("""
            ALTER TABLE transactions
            ADD COLUMN payment_proof TEXT
        """)

        print(
            "✓ Added payment_proof column."
        )

    else:

        print(
            "✓ payment_proof column already exists."
        )


    connection.commit()

    connection.close()

    print(
        "\n✓ Database migration complete!"
    )


if __name__ == "__main__":

    migrate()