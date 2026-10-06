import os
import shutil
from datetime import datetime


PROOF_FOLDER = "payment_proofs"


def save_payment_proof(source_path, transaction_id):

    # ----------------------------------------
    # CLEAN USER INPUT
    # ----------------------------------------

    if not source_path:
        return {
            "success": False,
            "message": "No proof file selected."
        }

    # Remove spaces around the path
    source_path = source_path.strip()

    # Remove quotation marks if the user
    # pasted the Windows path inside quotes
    source_path = source_path.strip('"').strip("'")

    # Convert to absolute path
    source_path = os.path.abspath(source_path)


    # ----------------------------------------
    # MAKE PROOF FOLDER
    # ----------------------------------------

    os.makedirs(
        PROOF_FOLDER,
        exist_ok=True
    )


    # ----------------------------------------
    # CHECK FILE EXISTS
    # ----------------------------------------

    if not os.path.isfile(source_path):

        return {
            "success": False,
            "message":
                f"Proof file not found: {source_path}"
        }


    # ----------------------------------------
    # CHECK FILE TYPE
    # ----------------------------------------

    _, extension = os.path.splitext(
        source_path
    )

    allowed_extensions = [
        ".jpg",
        ".jpeg",
        ".png",
        ".webp"
    ]


    if extension.lower() not in allowed_extensions:

        return {
            "success": False,
            "message":
                "Unsupported file type. "
                "Use JPG, JPEG, PNG, or WEBP."
        }


    # ----------------------------------------
    # CREATE UNIQUE FILENAME
    # ----------------------------------------

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )


    filename = (
        f"transaction_"
        f"{transaction_id}_"
        f"{timestamp}"
        f"{extension.lower()}"
    )


    destination = os.path.join(
        PROOF_FOLDER,
        filename
    )


    # ----------------------------------------
    # COPY FILE
    # ----------------------------------------

    try:

        shutil.copy2(
            source_path,
            destination
        )


        # Verify that the destination
        # actually exists after copying

        if not os.path.isfile(destination):

            return {
                "success": False,
                "message":
                    "Proof copy failed."
            }


        return {
            "success": True,
            "path": destination,
            "message":
                "Payment proof saved successfully."
        }


    except Exception as error:

        return {
            "success": False,
            "message":
                f"Error saving proof: {error}"
        }