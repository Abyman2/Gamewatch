import os
import qrcode


# Make sure the folder exists
os.makedirs("payment_qr", exist_ok=True)


def create_qr(filename, payment_name, recipient_name):

    payment_text = (
        f"GAMEWATCH TEST PAYMENT\n"
        f"METHOD: {payment_name}\n"
        f"RECIPIENT: {recipient_name}"
    )

    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4
    )

    qr.add_data(payment_text)

    qr.make(fit=True)

    image = qr.make_image(
        fill_color="black",
        back_color="white"
    )

    path = os.path.join(
        "payment_qr",
        filename
    )

    image.save(path)

    print(f"✓ Created: {path}")


create_qr(
    "telebirr_qr.png",
    "TELEBIRR",
    "GameWatch Test Lounge"
)

create_qr(
    "cbe_qr.png",
    "CBE",
    "GameWatch Test Lounge"
)