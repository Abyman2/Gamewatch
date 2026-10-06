import cv2


CAMERA_INDEX = 0


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
        "GAMEWATCH PHONE SCREEN TEST"
    )

    print(
        "========================================"
    )

    print(
        "\nPoint the camera at your phone."
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


        # Show the camera

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