import cv2


CAMERA_INDEX = 0


# ----------------------------------------
# PHONE REGION
# ----------------------------------------
# We will adjust these numbers together.
# For now they are just starting values.

PHONE_X = 100
PHONE_Y = 100

PHONE_WIDTH = 200
PHONE_HEIGHT = 400


def main():

    camera = cv2.VideoCapture(
        CAMERA_INDEX
    )


    if not camera.isOpened():

        print(
            "ERROR: Could not open camera."
        )

        return


    print(
        "\n========================================"
    )

    print(
        "GAMEWATCH PHONE CROP TEST"
    )

    print(
        "========================================"
    )

    print(
        "\nAdjust the PHONE values "
        "until the box covers your phone."
    )

    print(
        "Press Q to quit."
    )


    while True:

        success, frame = camera.read()


        if not success:

            print(
                "ERROR: Could not read camera."
            )

            break


        # Get camera size

        frame_height, frame_width = (
            frame.shape[:2]
        )


        # Make sure crop stays inside camera

        x = max(
            0,
            PHONE_X
        )

        y = max(
            0,
            PHONE_Y
        )

        width = min(
            PHONE_WIDTH,
            frame_width - x
        )

        height = min(
            PHONE_HEIGHT,
            frame_height - y
        )


        # --------------------------------
        # CROP PHONE
        # --------------------------------

        phone_frame = frame[
            y:y + height,
            x:x + width
        ]


        # --------------------------------
        # DRAW PHONE BOX
        # --------------------------------

        cv2.rectangle(

            frame,

            (x, y),

            (
                x + width,
                y + height
            ),

            (0, 255, 0),

            2

        )


        cv2.putText(

            frame,

            "PHONE SCREEN",

            (
                x,
                max(30, y - 10)
            ),

            cv2.FONT_HERSHEY_SIMPLEX,

            0.7,

            (0, 255, 0),

            2

        )


        # --------------------------------
        # ZOOM PHONE CROP
        # --------------------------------

        if phone_frame.size > 0:

            zoomed_phone = cv2.resize(

                phone_frame,

                None,

                fx=2,

                fy=2,

                interpolation=cv2.INTER_CUBIC

            )


            cv2.imshow(

                "GameWatch - Zoomed Phone",

                zoomed_phone

            )


        # --------------------------------
        # SHOW FULL CAMERA
        # --------------------------------

        cv2.imshow(

            "GameWatch - Full Camera",

            frame

        )


        key = cv2.waitKey(1) & 0xFF


        if key == ord("q"):

            break


    camera.release()

    cv2.destroyAllWindows()


if __name__ == "__main__":

    main()