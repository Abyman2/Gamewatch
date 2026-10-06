from PIL import Image
from lounge_settings import load_settings


def show_payment_qr(method):

    settings = load_settings()

    if method == "TELEBIRR":

        payment = settings["telebirr"]

    elif method == "CBE":

        payment = settings["cbe"]

    else:

        print("Unknown payment method.")

        return


    print("\n" + "=" * 50)

    print(f"PAY WITH {method}")

    print("=" * 50)

    print(
        f"\nRecipient: "
        f"{payment['recipient_name']}"
    )

    print("\nScan the QR code to pay.")

    try:

        image = Image.open(
            payment["qr_image"]
        )

        image.show()

    except FileNotFoundError:

        print(
            "\nQR image not found:"
        )

        print(
            payment["qr_image"]
        )


if __name__ == "__main__":

    print("1. Telebirr")

    print("2. CBE")

    choice = input(
        "\nChoose payment method: "
    )


    if choice == "1":

        show_payment_qr(
            "TELEBIRR"
        )

    elif choice == "2":

        show_payment_qr(
            "CBE"
        )

    else:

        print("Invalid choice.")