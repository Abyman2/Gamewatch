import cv2
import json
import os
import numpy as np


CAMERA_INDEX = 0


# ----------------------------------------
# LOAD TV REGIONS
# ----------------------------------------

def load_tv_regions():

    if not os.path.exists("tv_regions.json"):

        print("ERROR: tv_regions.json not found.")

        return []


    with open(
        "tv_regions.json",
        "r"
    ) as file:

        return json.load(file)


# ----------------------------------------
# MAIN
# ----------------------------------------

def main():

    tv_regions = load_tv_regions()


    if not tv_regions:

        return


    camera = cv2.VideoCapture(
        CAMERA_INDEX
    )


    if not camera.isOpened():

        print(
            "ERROR: Could not open camera."
        )

        return


    print("\n" + "=" * 50)

    print(
        "GAMEWATCH TV CALIBRATION TEST"
    )

    print("=" * 50)

    print(
        "\nPress Q to quit."
    )

    print(
        "Each TV will open in its own window."
    )


    previous_frames = {}


    while True:

        success, frame = camera.read()


        if not success:

            print(
                "ERROR: Could not read camera."
            )

            break


        for tv in tv_regions:

            tv_id = tv["tv_id"]

            x = tv["x"]
            y = tv["y"]

            width = tv["width"]
            height = tv["height"]


            # --------------------------------
            # CROP TV
            # --------------------------------

            tv_crop = frame[
                y:y + height,
                x:x + width
            ]


            if tv_crop.size == 0:

                print(
                    f"TV {tv_id}: Invalid region."
                )

                continue


            # --------------------------------
            # CALCULATE LIVE DIFFERENCE
            # --------------------------------

            difference = 0


            if tv_id in previous_frames:


                previous = previous_frames[
                    tv_id
                ]


                if previous.shape == tv_crop.shape:


                    frame_difference = cv2.absdiff(
                        previous,
                        tv_crop
                    )


                    gray = cv2.cvtColor(
                        frame_difference,
                        cv2.COLOR_BGR2GRAY
                    )


                    difference = np.mean(
                        gray
                    )


            previous_frames[
                tv_id
            ] = tv_crop.copy()


            # --------------------------------
            # SHOW SIZE + DIFFERENCE
            # --------------------------------

            info = (

                f"TV {tv_id} | "

                f"{width}x{height} | "

                f"Diff: {difference:.1f}"

            )


            display_crop = tv_crop.copy()


            cv2.putText(

                display_crop,

                info,

                (10, 25),

                cv2.FONT_HERSHEY_SIMPLEX,

                0.5,

                (0, 255, 0),

                1

            )


            # --------------------------------
            # ENLARGE SMALL TV CROPS
            # --------------------------------

            display_crop = cv2.resize(

                display_crop,

                None,

                fx=3,

                fy=3,

                interpolation=cv2.INTER_NEAREST

            )


            cv2.imshow(

                f"GameWatch - TV {tv_id}",

                display_crop

            )


            # Draw region on main camera

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


        # ------------------------------------
        # SHOW MAIN CAMERA
        # ------------------------------------

        cv2.imshow(

            "GameWatch - Camera View",

            frame

        )


        key = cv2.waitKey(1) & 0xFF


        if key == ord("q"):

            break


    camera.release()

    cv2.destroyAllWindows()


if __name__ == "__main__":

    main()