from db_manager import (
    add_tv,
    get_all_tvs,
    start_session,
    add_completed_game,
    get_active_sessions,
    checkout_session,
    get_transactions,
    get_daily_summary
)


# --------------------------------
# ADD OUR TWO TVs
# --------------------------------

add_tv(1, "TV 1")
add_tv(2, "TV 2")


print("\nALL TVs")

for tv in get_all_tvs():

    print(
        f"{tv['id']} - "
        f"{tv['name']} - "
        f"Active: {tv['active']}"
    )


# --------------------------------
# START TV 1
# --------------------------------

print("\nSTART SESSION")

result = start_session(1)

print(result)


# --------------------------------
# ADD TWO GAMES
# --------------------------------

print("\nADD GAME")

print(
    add_completed_game(1)
)

print(
    add_completed_game(1)
)


# --------------------------------
# SHOW ACTIVE SESSIONS
# --------------------------------

print("\nACTIVE SESSIONS")

for session in get_active_sessions():

    print(
        f"{session['tv_name']} | "
        f"Games: "
        f"{session['completed_games']}"
    )


# --------------------------------
# CHECKOUT
# --------------------------------

print("\nCHECKOUT")

result = checkout_session(

    tv_id=1,

    unfinished_game_charge=25,

    payment_method="CASH"
)

print(result)


# --------------------------------
# TRANSACTION HISTORY
# --------------------------------

print("\nTRANSACTIONS")

for transaction in get_transactions():

    print(
        f"TV {transaction['tv_id']} | "
        f"{transaction['total']} ETB | "
        f"{transaction['payment_method']}"
    )


# --------------------------------
# DAILY SUMMARY
# --------------------------------

print("\nDAILY SUMMARY")

summary = get_daily_summary()

print(
    f"Transactions: "
    f"{summary['transactions']}"
)

print(
    f"Total Revenue: "
    f"{summary['total_revenue']} ETB"
)

print("\nPAYMENT BREAKDOWN")

for payment in summary["payments"]:

    print(
        f"{payment['payment_method']}: "
        f"{payment['total']} ETB"
    )