import json
import os


SETTINGS_FILE = "lounge_settings.json"


DEFAULT_SETTINGS = {
    "lounge_name": "GameWatch Test Lounge",

    "telebirr": {
        "enabled": True,
        "recipient_name": "GameWatch Test Lounge",
        "qr_image": "payment_qr/telebirr_qr.png"
    },

    "cbe": {
        "enabled": True,
        "recipient_name": "GameWatch Test Lounge",
        "qr_image": "payment_qr/cbe_qr.png"
    }
}


def load_settings():

    if not os.path.exists(SETTINGS_FILE):

        save_settings(DEFAULT_SETTINGS)

        return DEFAULT_SETTINGS

    try:

        with open(
            SETTINGS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except (
        json.JSONDecodeError,
        FileNotFoundError
    ):

        print(
            "Warning: Settings file could not be read."
        )

        return DEFAULT_SETTINGS


def save_settings(settings):

    with open(
        SETTINGS_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            settings,
            file,
            indent=4,
            ensure_ascii=False
        )


def show_settings():

    settings = load_settings()

    print("\n" + "=" * 50)
    print("          LOUNGE SETTINGS")
    print("=" * 50)

    print(
        f"\nLounge Name: "
        f"{settings['lounge_name']}"
    )

    print("\nTELEBIRR")

    print(
        f"Recipient: "
        f"{settings['telebirr']['recipient_name']}"
    )

    print(
        f"QR: "
        f"{settings['telebirr']['qr_image']}"
    )

    print("\nCBE")

    print(
        f"Recipient: "
        f"{settings['cbe']['recipient_name']}"
    )

    print(
        f"QR: "
        f"{settings['cbe']['qr_image']}"
    )


if __name__ == "__main__":

    show_settings()