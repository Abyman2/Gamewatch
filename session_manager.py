import json
import os
from datetime import datetime


PRICE_PER_GAME = 25

SESSIONS_FILE = "active_sessions.json"
TRANSACTIONS_FILE = "transactions.json"


# -----------------------------------
# FILE HELPERS
# -----------------------------------

def load_json(filename, default_data):

    if not os.path.exists(filename):

        with open(filename, "w") as file:
            json.dump(default_data, file, indent=4)

        return default_data

    try:

        with open(filename, "r") as file:
            return json.load(file)

    except json.JSONDecodeError:

        print(f"WARNING: {filename} is corrupted.")
        return default_data


def save_json(filename, data):

    with open(filename, "w") as file:

        json.dump(
            data,
            file,
            indent=4
        )


# -----------------------------------
# LOAD TV REGIONS
# -----------------------------------

with open("tv_regions.json", "r") as file:

    tv_regions = json.load(file)


# -----------------------------------
# CREATE DEFAULT TV DATA
# -----------------------------------

default_sessions = {}

for tv in tv_regions:

    tv_id = str(tv["tv_id"])

    default_sessions[tv_id] = {

        "active": False,

        "start_time": None,

        "completed_games": 0
    }


# -----------------------------------
# LOAD SAVED DATA
# -----------------------------------

tvs = load_json(
    SESSIONS_FILE,
    default_sessions
)


transactions = load_json(
    TRANSACTIONS_FILE,
    []
)


# Make sure newly added TVs exist

for tv_id, default_data in default_sessions.items():

    if tv_id not in tvs:

        tvs[tv_id] = default_data

save_json(
    SESSIONS_FILE,
    tvs
)


# -----------------------------------
# FUNCTIONS
# -----------------------------------

def show_tvs():

    print("\n" + "=" * 40)

    print("          GAMEWATCH")

    print("=" * 40)


    for tv_id, tv in tvs.items():

        status = (
            "ACTIVE"
            if tv["active"]
            else "AVAILABLE"
        )


        print(f"\nTV {tv_id}")

        print(f"Status: {status}")


        if tv["active"]:

            print(
                f"Started: "
                f"{tv['start_time']}"
            )

            print(
                f"Completed Games: "
                f"{tv['completed_games']}"
            )


def start_session():

    tv_id = input(
        "\nEnter TV number: "
    )


    if tv_id not in tvs:

        print("TV not found.")

        return


    if tvs[tv_id]["active"]:

        print(
            "This TV already has "
            "an active session."
        )

        return


    tvs[tv_id]["active"] = True


    tvs[tv_id]["start_time"] = (
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )


    tvs[tv_id]["completed_games"] = 0


    save_json(
        SESSIONS_FILE,
        tvs
    )


    print(
        f"\n✓ TV {tv_id} "
        "session started!"
    )


def add_game():

    tv_id = input(
        "\nEnter TV number: "
    )


    if tv_id not in tvs:

        print("TV not found.")

        return


    if not tvs[tv_id]["active"]:

        print(
            "No active session "
            "on this TV."
        )

        return


    tvs[tv_id][
        "completed_games"
    ] += 1


    save_json(
        SESSIONS_FILE,
        tvs
    )


    print(
        f"\n🎮 GAME ADDED "
        f"TO TV {tv_id}"
    )


    print(
        f"Completed Games: "
        f"{tvs[tv_id]['completed_games']}"
    )


def checkout():

    tv_id = input(
        "\nEnter TV number: "
    )


    if tv_id not in tvs:

        print("TV not found.")

        return


    tv = tvs[tv_id]


    if not tv["active"]:

        print(
            "No active session "
            "on this TV."
        )

        return


    completed_games = (
        tv["completed_games"]
    )


    completed_total = (
        completed_games *
        PRICE_PER_GAME
    )


    print("\n" + "=" * 40)

    print(f"CHECKOUT — TV {tv_id}")

    print("=" * 40)


    print(
        f"\nCompleted Games: "
        f"{completed_games}"
    )


    print(
        f"{completed_games} × "
        f"{PRICE_PER_GAME} ETB "
        f"= {completed_total} ETB"
    )


    print(
        "\nIs there a game "
        "currently in progress?"
    )


    answer = input(
        "1 = Yes | 2 = No: "
    )


    unfinished_charge = 0


    if answer == "1":

        print(
            "\nCharge unfinished game?"
        )

        print(
            "1 = Charge 25 ETB"
        )

        print(
            "2 = Free / Charge 0 ETB"
        )


        choice = input(
            "Choose: "
        )


        if choice == "1":

            unfinished_charge = (
                PRICE_PER_GAME
            )


    total = (
        completed_total +
        unfinished_charge
    )


    print("\n" + "=" * 40)

    print("FINAL BILL")

    print("=" * 40)


    print(
        f"Completed Games: "
        f"{completed_total} ETB"
    )


    print(
        f"Unfinished Game: "
        f"{unfinished_charge} ETB"
    )


    print(
        f"\nTOTAL: {total} ETB"
    )


    confirm = input(
        "\nConfirm checkout? "
        "(y/n): "
    )


    if confirm.lower() == "y":

        transaction = {

            "tv_id": tv_id,

            "start_time":
                tv["start_time"],

            "checkout_time":
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),

            "completed_games":
                completed_games,

            "price_per_game":
                PRICE_PER_GAME,

            "completed_games_total":
                completed_total,

            "unfinished_game_charge":
                unfinished_charge,

            "total":
                total
        }


        transactions.append(
            transaction
        )


        save_json(
            TRANSACTIONS_FILE,
            transactions
        )


        # Reset TV

        tvs[tv_id] = {

            "active": False,

            "start_time": None,

            "completed_games": 0
        }


        save_json(
            SESSIONS_FILE,
            tvs
        )


        print(
            f"\n✓ TV {tv_id} "
            "CHECKED OUT"
        )


        print(
            f"Amount Paid: "
            f"{total} ETB"
        )


    else:

        print(
            "\nCheckout cancelled."
        )


def show_transactions():

    print("\n" + "=" * 50)

    print("        TRANSACTION HISTORY")

    print("=" * 50)


    if not transactions:

        print(
            "\nNo transactions yet."
        )

        return


    total_earned = 0


    for index, transaction in enumerate(
        transactions,
        start=1
    ):

        print(
            f"\nTransaction #{index}"
        )

        print(
            f"TV: "
            f"{transaction['tv_id']}"
        )

        print(
            f"Games: "
            f"{transaction['completed_games']}"
        )

        print(
            f"Total: "
            f"{transaction['total']} ETB"
        )

        print(
            f"Time: "
            f"{transaction['checkout_time']}"
        )


        total_earned += (
            transaction["total"]
        )


    print(
        "\n" + "-" * 50
    )

    print(
        f"TODAY / ALL SAVED TOTAL: "
        f"{total_earned} ETB"
    )


# -----------------------------------
# MAIN MENU
# -----------------------------------

while True:

    print("\n" + "=" * 40)

    print("GAMEWATCH MENU")

    print("=" * 40)


    print("1. View TVs")

    print("2. Start Session")

    print("3. Add Completed Game")

    print("4. Checkout TV")

    print("5. Transaction History")

    print("6. Exit")


    choice = input(
        "\nChoose an option: "
    )


    if choice == "1":

        show_tvs()


    elif choice == "2":

        start_session()


    elif choice == "3":

        add_game()


    elif choice == "4":

        checkout()


    elif choice == "5":

        show_transactions()


    elif choice == "6":

        print(
            "\nGameWatch closed."
        )

        break


    else:

        print(
            "\nInvalid option."
        )