from db_manager import (
    get_all_tvs,
    start_session,
    add_completed_game,
    get_active_session,
    checkout_session,
    get_transactions,
    get_daily_summary,
    add_payment_proof
)

from show_qr import show_payment_qr
from lounge_settings import load_settings
from payment_proof_manager import save_payment_proof


PRICE_PER_GAME = 25


# ----------------------------------------
# SHOW TVs
# ----------------------------------------

def show_tvs():

    print("\n" + "=" * 50)
    print("               GAMEWATCH")
    print("=" * 50)

    tvs = get_all_tvs()

    for tv in tvs:

        tv_id = tv["id"]

        print(f"\n📺 {tv['name']}")

        if tv["active"]:

            print("Status: 🟢 ACTIVE")

            session = get_active_session(tv_id)

            if session:

                print(
                    f"Started: "
                    f"{session['start_time']}"
                )

                print(
                    f"Completed Games: "
                    f"{session['completed_games']}"
                )

        else:

            print("Status: ⚪ AVAILABLE")


# ----------------------------------------
# START SESSION
# ----------------------------------------

def start_tv_session():

    try:

        tv_id = int(
            input("\nEnter TV number: ")
        )

    except ValueError:

        print(
            "Please enter a valid number."
        )

        return


    result = start_session(tv_id)

    print(
        f"\n{result['message']}"
    )


# ----------------------------------------
# ADD COMPLETED GAME
# ----------------------------------------

def add_game():

    try:

        tv_id = int(
            input("\nEnter TV number: ")
        )

    except ValueError:

        print(
            "Please enter a valid number."
        )

        return


    result = add_completed_game(tv_id)


    if result["success"]:

        print(
            f"\n🎮 GAME ADDED — TV {tv_id}"
        )

        print(
            f"Completed Games: "
            f"{result['completed_games']}"
        )

    else:

        print(
            f"\n{result['message']}"
        )


# ----------------------------------------
# TRANSACTION HISTORY
# ----------------------------------------

def show_transactions():

    transactions = get_transactions()


    print("\n" + "=" * 50)

    print(
        "        TRANSACTION HISTORY"
    )

    print("=" * 50)


    if not transactions:

        print(
            "\nNo transactions yet."
        )

        return


    total_revenue = 0


    for transaction in transactions:

        # sqlite3.Row works with
        # transaction["column_name"]

        transaction_id = transaction["id"]

        tv_id = transaction["tv_id"]

        total = transaction["total"]

        payment_method = transaction[
            "payment_method"
        ]


        # Your database may use one
        # of these timestamp names.
        # We safely check available columns.

        columns = transaction.keys()

        if "checkout_time" in columns:

            timestamp = transaction[
        "checkout_time"
    ]

        else:

            timestamp = "Unknown"


        # Payment proof is optional.
        # This also works before migration.

        if "payment_proof" in columns:

            proof = transaction[
                "payment_proof"
            ]

        else:

            proof = None


        print(
            f"\nTransaction #{transaction_id}"
        )

        print(
            f"TV: {tv_id}"
        )

        print(
            f"Total: {total} ETB"
        )

        print(
            f"Payment: {payment_method}"
        )

        print(
            f"Time: {timestamp}"
        )


        if proof:

            print(
                "Proof: 📷 ATTACHED"
            )

        else:

            print(
                "Proof: None"
            )


        print(
            "-" * 50
        )


        total_revenue += total


    print(
        f"\nALL SAVED TOTAL: "
        f"{total_revenue} ETB"
    )

# ----------------------------------------
# CHECKOUT
# ----------------------------------------

def checkout_tv():

    proof_source_path = None
    
    proof_result = {
        "success": False
    }


    try:

        tv_id = int(
            input("\nEnter TV number: ")
        )

    except ValueError:

        print(
            "Please enter a valid number."
        )

        return


    session = get_active_session(tv_id)


    if session is None:

        print(
            "\nNo active session on this TV."
        )

        return


    completed_games = (
        session["completed_games"]
    )


    completed_total = (
        completed_games *
        PRICE_PER_GAME
    )


    print("\n" + "=" * 50)

    print(
        f"           CHECKOUT — TV {tv_id}"
    )

    print("=" * 50)


    print(
        f"\nCompleted Games: "
        f"{completed_games}"
    )

    print(
        f"{completed_games} × "
        f"{PRICE_PER_GAME} ETB "
        f"= {completed_total} ETB"
    )


    # ------------------------------------
    # UNFINISHED GAME
    # ------------------------------------

    print(
        "\nIs there a game currently "
        "in progress?"
    )

    print("1. Yes")
    print("2. No")


    unfinished_answer = input(
        "Choose: "
    )


    unfinished_charge = 0


    if unfinished_answer == "1":

        print(
            "\nCharge unfinished game?"
        )

        print(
            f"1. Charge {PRICE_PER_GAME} ETB"
        )

        print(
            "2. Free / 0 ETB"
        )


        unfinished_choice = input(
            "Choose: "
        )


        if unfinished_choice == "1":

            unfinished_charge = (
                PRICE_PER_GAME
            )


    elif unfinished_answer != "2":

        print(
            "\nInvalid choice."
        )

        return


    # ------------------------------------
    # CALCULATE TOTAL
    # ------------------------------------

    total = (
        completed_total +
        unfinished_charge
    )


    print("\n" + "-" * 50)

    print(
        f"Completed Games: "
        f"{completed_total} ETB"
    )

    print(
        f"Unfinished Game: "
        f"{unfinished_charge} ETB"
    )

    print(
        f"\nTOTAL TO PAY: "
        f"{total} ETB"
    )

    print("-" * 50)


    # ------------------------------------
    # PAYMENT METHOD
    # ------------------------------------

    print("\nSELECT PAYMENT METHOD")

    print("1. 💵 CASH")

    print("2. 📱 TELEBIRR")

    print("3. 🏦 CBE")

    print("4. Cancel")


    payment_choice = input(
        "\nChoose: "
    )


    payment_methods = {

        "1": "CASH",
        "2": "TELEBIRR",
        "3": "CBE"

    }


    if payment_choice == "4":

        print(
            "\nCheckout cancelled."
        )

        return


    if payment_choice not in payment_methods:

        print(
            "\nInvalid payment method."
        )

        return


    payment_method = (
        payment_methods[payment_choice]
    )


    # ------------------------------------
    # CASH PAYMENT
    # ------------------------------------

    if payment_method == "CASH":

        print("\n" + "=" * 50)

        print(
            "CASH PAYMENT"
        )

        print("=" * 50)

        print(
            f"\nAmount to receive: "
            f"{total} ETB"
        )


        confirm = input(
            "\nCash received? (y/n): "
        )


        if confirm.lower() != "y":

            print(
                "\nPayment not confirmed."
            )

            return


    # ------------------------------------
    # DIGITAL PAYMENT
    # ------------------------------------

    else:

        settings = load_settings()


        print("\n" + "=" * 50)

        print(
            f"PAY WITH {payment_method}"
        )

        print("=" * 50)

        print(
            f"\nTotal to pay: "
            f"{total} ETB"
        )


        if payment_method == "TELEBIRR":

            recipient = (
                settings["telebirr"][
                    "recipient_name"
                ]
            )

        else:

            recipient = (
                settings["cbe"][
                    "recipient_name"
                ]
            )


        print(
            f"Recipient: "
            f"{recipient}"
        )


        print(
            "\nOpening QR code..."
        )


        show_payment_qr(
            payment_method
        )


        # --------------------------------
        # PAYMENT CONFIRMATION
        # --------------------------------

        print("\n" + "=" * 50)

        print(
            "PAYMENT CONFIRMATION"
        )

        print("=" * 50)


        print(
            "\n1. ✓ Confirm Payment Received"
        )

        print(
            "2. 📷 Confirm + Save Proof"
        )

        print(
            "3. Cancel"
        )


        confirmation_choice = input(
            "\nChoose: "
        )


        if confirmation_choice == "3":

            print(
                "\nPayment cancelled."
            )

            return


        elif confirmation_choice == "1":

            print(
                "\n✓ Payment manually verified."
            )


        elif confirmation_choice == "2":

            print(
                "\nEnter the full path of the "
                "payment screenshot/photo."
            )

            print(
                "\nExample:"
            )

            print(
                r"C:\Users\YourName\Pictures\payment.jpg"
            )


            proof_source_path = input(
                "\nProof file path: "
            ).strip()


            # Remove quotation marks
            # if the path was pasted
            # with quotes

            proof_source_path = (
                proof_source_path
                .strip('"')
                .strip("'")
            )


            if not proof_source_path:

                print(
                    "\nNo proof selected."
                )

                return


            print(
                "\n✓ Payment proof selected."
            )

            print(
                "✓ Payment manually verified."
            )


        else:

            print(
                "\nInvalid choice."
            )

            return


    # ------------------------------------
    # FINAL PAYMENT SUMMARY
    # ------------------------------------

    print("\n" + "=" * 50)

    print(
        "PAYMENT SUMMARY"
    )

    print("=" * 50)


    print(
        f"TV: {tv_id}"
    )

    print(
        f"Total: {total} ETB"
    )

    print(
        f"Payment Method: "
        f"{payment_method}"
    )


    if proof_source_path:

        print(
            "Payment Proof: Selected"
        )


    confirm_final = input(
        "\nFinalize checkout? (y/n): "
    )


    if confirm_final.lower() != "y":

        print(
            "\nCheckout cancelled."
        )

        return


    # ------------------------------------
    # SAVE TRANSACTION
    # ------------------------------------

    result = checkout_session(

        tv_id=tv_id,

        unfinished_game_charge=
            unfinished_charge,

        payment_method=
            payment_method

    )


    # ------------------------------------
    # CHECK RESULT
    # ------------------------------------

    if result["success"]:

        transaction_id = (
            result["transaction_id"]
        )


        # --------------------------------
        # SAVE PAYMENT PROOF
        # --------------------------------

        if proof_source_path:

            proof_result = (
                save_payment_proof(
                    proof_source_path,
                    transaction_id
                )
            )


            if proof_result["success"]:

                db_result = (
                    add_payment_proof(
                        transaction_id,
                        proof_result["path"]
                    )
                )


                if db_result["success"]:

                    print(
                        "\n📷 Payment proof saved."
                    )

                else:

                    print(
                        "\nWarning: Proof was copied "
                        "but could not be linked to "
                        "the transaction."
                    )


            else:

                print(
                    "\nWarning: "
                    f"{proof_result['message']}"
                )


        # --------------------------------
        # SUCCESS MESSAGE
        # --------------------------------

        print("\n" + "=" * 50)

        print(
            "✓ PAYMENT RECORDED"
        )

        print("=" * 50)


        print(
            f"TV {tv_id} checked out."
        )

        print(
            f"Amount: "
            f"{result['total']} ETB"
        )

        print(
            f"Method: "
            f"{result['payment_method']}"
        )


        if proof_result.get("success"):

         print(
        "Proof: 📷 SAVED"
    )

        else:

         print(
        "Proof: None"
    )


    else:

        print(
            f"\nError: "
            f"{result['message']}"
        )


# ----------------------------------------
# DAILY SUMMARY
# ----------------------------------------

def show_daily_summary():

    summary = get_daily_summary()


    print("\n" + "=" * 50)

    print(
        "             TODAY'S SUMMARY"
    )

    print("=" * 50)


    print(
        f"\nTransactions: "
        f"{summary['transactions']}"
    )

    print(
        f"Total Revenue: "
        f"{summary['total_revenue']} ETB"
    )


    print(
        "\nPAYMENT BREAKDOWN"
    )

    print("-" * 50)


    cash_total = 0
    digital_total = 0


    if not summary["payments"]:

        print(
            "No payments today."
        )


    for payment in summary["payments"]:

        method = (
            payment["payment_method"]
        )

        amount = (
            payment["total"]
        )


        print(
            f"{method}: "
            f"{amount} ETB"
        )


        if method == "CASH":

            cash_total += amount

        else:

            digital_total += amount


    print("-" * 50)


    print(
        f"💵 CASH TO COLLECT: "
        f"{cash_total} ETB"
    )

    print(
        f"📱 DIGITAL PAYMENTS: "
        f"{digital_total} ETB"
    )


# ----------------------------------------
# MAIN MENU
# ----------------------------------------

def main():

    while True:

        print("\n" + "=" * 50)

        print(
            "            🎮 GAMEWATCH"
        )

        print("=" * 50)


        print("\n1. View TVs")

        print("2. Start Session")

        print("3. Add Completed Game")

        print("4. Checkout TV")

        print("5. Transaction History")

        print("6. Today's Summary")

        print("7. Exit")


        choice = input(
            "\nChoose an option: "
        )


        if choice == "1":

            show_tvs()


        elif choice == "2":

            start_tv_session()


        elif choice == "3":

            add_game()


        elif choice == "4":

            checkout_tv()


        elif choice == "5":

            show_transactions()


        elif choice == "6":

            show_daily_summary()


        elif choice == "7":

            print(
                "\nGameWatch closed."
            )

            break


        else:

            print(
                "\nInvalid option."
            )


if __name__ == "__main__":

    main()