import cv2
import json
import time
import os
import numpy as np


# ----------------------------------------
# SETTINGS
# ----------------------------------------

CAMERA_INDEX = 0

CHANGE_THRESHOLD = 18

ANALYSIS_SECONDS = 3

COOLDOWN_SECONDS = 10

MIN_STABLE_SECONDS = 2

MIN_EVENT_PEAK = 30


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
# CALCULATE FRAME DIFFERENCE
# ----------------------------------------

def calculate_difference(
    frame1,
    frame2
):

    difference = cv2.absdiff(
        frame1,
        frame2
    )

    gray = cv2.cvtColor(
        difference,
        cv2.COLOR_BGR2GRAY
    )

    return np.mean(gray)


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

        print("ERROR: Could not open camera.")
        return


    print(
        "\n========================================"
    )

    print(
        "GAMEWATCH GAME STATE DETECTOR"
    )

    print(
        "========================================"
    )

    print(
        "\nPress Q to quit."
    )


    tv_states = {}


    # ------------------------------------
    # SET UP EACH TV
    # ------------------------------------

    for tv in tv_regions:

        tv_id = tv["tv_id"]

        tv_states[tv_id] = {

            "previous_frame": None,

            "status": "STABLE",

            "change_start": None,

            "last_confirmed_change": 0,

            "stable_start": None,

            "game_count": 0,
            
            "peak_difference": 0

        }


    while True:

        success, frame = camera.read()


        if not success:

            print(
                "ERROR: Camera frame not received."
            )

            break


        current_time = time.time()


        for tv in tv_regions:

            tv_id = tv["tv_id"]

            x = tv["x"]
            y = tv["y"]

            width = tv["width"]
            height = tv["height"]


            # --------------------------------
            # CROP TV REGION
            # --------------------------------

            tv_frame = frame[
                y:y + height,
                x:x + width
            ]


            if tv_frame.size == 0:

                continue


            # Resize for more stable comparison

            tv_frame = cv2.resize(
                tv_frame,
                (160, 90)
            )


            state = tv_states[tv_id]


            # --------------------------------
            # FIRST FRAME
            # --------------------------------

            if state["previous_frame"] is None:

                state[
                    "previous_frame"
                ] = tv_frame.copy()

                continue


            # --------------------------------
            # CALCULATE CHANGE
            # --------------------------------

            difference = calculate_difference(

                state[
                    "previous_frame"
                ],

                tv_frame

            )


            # --------------------------------
            # STATUS LOGIC
            # --------------------------------

            if difference > CHANGE_THRESHOLD:


                # New movement/change detected

                if state["status"] == "STABLE":

                    state[
                        "status"
                    ] = "ANALYZING"
                    
                    state["peak_difference"] = difference


                    state[
                        "change_start"
                    ] = current_time


                    state[
                        "stable_start"
                    ] = None


                    print(

                        f"\nTV {tv_id}: "
                        f"POSSIBLE SCREEN CHANGE"

                    )


                # Still changing

                elif state["status"] == "ANALYZING":

                    state[
                        "stable_start"
                    ] = None
                    
                    state["peak_difference"] = max(
                        state["peak_difference"],
                        difference 
                    )

            else:


                # Screen has become stable

                if state["status"] == "ANALYZING":


                    if state[
                        "stable_start"
                    ] is None:


                        state[
                            "stable_start"
                        ] = current_time


                    stable_duration = (

                        current_time -

                        state[
                            "stable_start"
                        ]

                    )


                    change_duration = (

                        current_time -

                        state[
                            "change_start"
                        ]

                    )


                    # --------------------------------
                    # CONFIRM CHANGE
                    # --------------------------------

                    if (

                        change_duration >=
                        ANALYSIS_SECONDS

                        and

                        stable_duration >=
                        MIN_STABLE_SECONDS

                    ):
                        print(
                            f"\nTV {tv_id} EVENT ANALYSIS:"
                        )
                        print(
                            f"Peak Difference: "
                            f"{state['peak_difference']:.1f}"
                        )
                        print(
                            f"Change Duration: "
                            f"{change_duration:.1f} seconds"
                        )
                        print(
                            f"Stable Duration: "
                            f"{stable_duration:.1f} seconds"
                        )
                        



                        # Check cooldown

                        time_since_last_change = (

                            current_time -

                            state[
                                "last_confirmed_change"
                            ]

                        )


                        if (

                            time_since_last_change >=
                            COOLDOWN_SECONDS

                        ):


                            state[
                                "game_count"
                            ] += 1


                            state[
                                "last_confirmed_change"
                            ] = current_time


                            print(

                                f"\n🎮 TV {tv_id}: "
                                f"NEW GAME EVENT CONFIRMED"

                            )


                            print(

                                f"Game Events: "

                                f"{state['game_count']}"

                            )


                        else:

                            print(

                                f"\nTV {tv_id}: "
                                f"Change ignored "

                                f"(cooldown)"

                            )


                        # Reset state

                        state[
                            "status"
                        ] = "STABLE"


                        state[
                            "change_start"
                        ] = None
                        
                        state["peak_difference"] = 0


                        state[
                            "stable_start"
                        ] = None


            # Save current frame

            state[
                "previous_frame"
            ] = tv_frame.copy()


            # --------------------------------
            # DRAW TV BOX
            # --------------------------------

            status = state["status"]

            label = (

                f"TV {tv_id} | "

                f"{status} | "
                
                f"Diff: {difference:.1f}/{CHANGE_THRESHOLD} | "

                f"Peak: {state['peak_difference']:.1f} | "

                f"Events: {state['game_count']}"

            )


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

                label,

                (
                    x,
                    max(20, y - 10)
                ),

                cv2.FONT_HERSHEY_SIMPLEX,

                0.5,

                (0, 255, 0),

                2

            )


        # ------------------------------------
        # SHOW CAMERA
        # ------------------------------------

        cv2.imshow(
            "GameWatch Detector",
            frame
        )


        key = cv2.waitKey(1) & 0xFF


        if key == ord("q"):

            break


    camera.release()

    cv2.destroyAllWindows()


if __name__ == "__main__":

    main()
