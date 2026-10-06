import cv2
import numpy as np
import os


# ----------------------------------------
# CONFIGURATION
# ----------------------------------------

TEMPLATE_DIR = "scoreboard_templates"
OUTPUT_DIR = "preprocessed_results"
ENLARGE_SCALE = 3  # Scale factor for enlarging tiny crops


# ----------------------------------------
# SCOREBOARD PREPROCESSOR
# ----------------------------------------

class ScoreboardPreprocessor:
    """
    Modular preprocessing pipeline for GameWatch scoreboard crops.
    Enhances low-resolution, blurry camera crops before OCR recognition.
    """

    @staticmethod
    def to_grayscale(image):
        """Convert BGR image to single-channel grayscale."""
        if len(image.shape) == 2:
            return image
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    @staticmethod
    def enlarge(image, scale=ENLARGE_SCALE):
        """Enlarge image using cubic interpolation for smoother edges."""
        height, width = image.shape[:2]
        new_width = int(width * scale)
        new_height = int(height * scale)
        return cv2.resize(
            image,
            (new_width, new_height),
            interpolation=cv2.INTER_CUBIC
        )

    @staticmethod
    def enhance_contrast(gray_image, clip_limit=2.5, tile_grid_size=(4, 4)):
        """
        Enhance local contrast using CLAHE
        (Contrast Limited Adaptive Histogram Equalization).
        Prevents over-amplifying noise while making digits pop.
        """
        clahe = cv2.createCLAHE(
            clipLimit=clip_limit,
            tileGridSize=tile_grid_size
        )
        return clahe.apply(gray_image)

    @staticmethod
    def sharpen(image):
        """
        Sharpen edges using an unsharp Laplacian kernel.
        Helps recover digit boundaries from out-of-focus TV captures.
        """
        kernel = np.array([
            [0, -1, 0],
            [-1, 5, -1],
            [0, -1, 0]
        ], dtype=np.float32)
        return cv2.filter2D(image, -1, kernel)

    @staticmethod
    def threshold(gray_image):
        """
        Binarize the image using Otsu's thresholding after a light Gaussian blur.
        Separates text/numbers from the scoreboard background.
        """
        blurred = cv2.GaussianBlur(gray_image, (3, 3), 0)
        _, thresh = cv2.threshold(
            blurred,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        return thresh

    @staticmethod
    def order_quad_points(pts):
        """
        Orders 4 quadrilateral coordinates into standard order:
        [Top-Left, Top-Right, Bottom-Right, Bottom-Left].
        Handles clockwise, counter-clockwise, or arbitrary user clicks.
        """
        pts = np.array(pts, dtype="float32")
        rect = np.zeros((4, 2), dtype="float32")
        
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]  # TL has smallest sum (x+y)
        rect[2] = pts[np.argmax(s)]  # BR has largest sum (x+y)
        
        diff = np.diff(pts, axis=1)  # (y - x)
        rect[1] = pts[np.argmin(diff)]  # TR has smallest difference
        rect[3] = pts[np.argmax(diff)]  # BL has largest difference
        
        return rect

    @classmethod
    def rectify_perspective(cls, image, corners, target_size=(960, 540)):
        """
        Warps an angled camera quadrilateral TV screen into a canonical 16:9 rectangle.
        Returns:
            rectified (np.ndarray): Perspective-corrected image (target_size)
            M (np.ndarray): 3x3 homography matrix
        """
        ordered = cls.order_quad_points(corners)
        tw, th = target_size
        dst = np.array([
            [0, 0],
            [tw - 1, 0],
            [tw - 1, th - 1],
            [0, th - 1]
        ], dtype="float32")
        
        M = cv2.getPerspectiveTransform(ordered, dst)
        rectified = cv2.warpPerspective(image, M, (tw, th), flags=cv2.INTER_LINEAR)
        return rectified, M

    @staticmethod
    def suppress_glare(image, clip_limit=2.8, tile_grid=(8, 8)):
        """
        Suppresses specular reflection and glare hotspots from ceiling fluorescent tubes
        or window daylight across glossy TV screens.
        Uses CLAHE on the Lightness channel of LAB color space to equalize dynamic range
        without distorting game colors.
        """
        if len(image.shape) == 2:
            clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid)
            return clahe.apply(image)
            
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid)
        l_norm = clahe.apply(l)
        merged = cv2.merge((l_norm, a, b))
        return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

    @classmethod
    def estimate_keystone_angles(cls, corners):
        """
        Computes the perspective keystone tilt angles (pitch, yaw, and keystone severity)
        for an angled security camera or phone mount.
        """
        ordered = cls.order_quad_points(corners)
        tl, tr, br, bl = ordered
        
        top_w = float(np.linalg.norm(tr - tl))
        bot_w = float(np.linalg.norm(br - bl))
        left_h = float(np.linalg.norm(bl - tl))
        right_h = float(np.linalg.norm(br - tr))
        
        horizontal_skew = abs(top_w - bot_w) / max(1.0, max(top_w, bot_w))
        vertical_skew = abs(left_h - right_h) / max(1.0, max(left_h, right_h))
        
        pitch_deg = float(np.degrees(np.arctan(vertical_skew * 1.5)))
        yaw_deg = float(np.degrees(np.arctan(horizontal_skew * 1.5)))
        composite_tilt = float(np.sqrt(pitch_deg**2 + yaw_deg**2))
        
        return {
            "pitch_angle": round(pitch_deg, 1),
            "yaw_angle": round(yaw_deg, 1),
            "composite_tilt": round(composite_tilt, 1),
            "is_angled": bool(composite_tilt > 4.0),
            "top_width": round(top_w, 1),
            "bottom_width": round(bot_w, 1),
            "left_height": round(left_h, 1),
            "right_height": round(right_h, 1)
        }

    @staticmethod
    def extract_clock_region(image):
        """
        Crop the clock banner from the scoreboard.
        Clock is located in the bottom ~38% of the scoreboard strip.
        """
        h, w = image.shape[:2]
        clock_crop = image[int(h * 0.60):h, int(w * 0.20):int(w * 0.85)]
        return clock_crop

    @classmethod
    def process_clock_for_ocr(cls, bgr_image):
        """
        End-to-end pipeline specifically tuned for digital clock extraction:
        Crop clock -> Grayscale -> 4x Bicubic Resize -> CLAHE -> Threshold -> Invert.
        Outputs sharp black digits on white background ready for OCR.
        """
        clock = cls.extract_clock_region(bgr_image)
        gray = cls.to_grayscale(clock)
        enlarged = cv2.resize(gray, (0, 0), fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4)).apply(enlarged)
        _, thresh = cv2.threshold(clahe, 175, 255, cv2.THRESH_BINARY)
        inverted = cv2.bitwise_not(thresh)
        return inverted

    @classmethod
    def generate_all_variants(cls, original_bgr):
        """
        Generate all 6 versions of the scoreboard crop for visual inspection:
        1. Original
        2. Grayscale
        3. Enlarged
        4. Contrast Enhanced
        5. Sharpened
        6. Thresholded
        """
        # 1. Original
        original = original_bgr.copy()

        # 2. Grayscale
        gray = cls.to_grayscale(original)

        # 3. Enlarged (on grayscale for OCR readiness)
        enlarged = cls.enlarge(gray, scale=ENLARGE_SCALE)

        # 4. Contrast Enhanced (applied to enlarged)
        contrast = cls.enhance_contrast(enlarged)

        # 5. Sharpened (applied to contrast-enhanced)
        sharpened = cls.sharpen(contrast)

        # 6. Thresholded (applied to sharpened)
        thresholded = cls.threshold(sharpened)

        return {
            "1_original": original,
            "2_grayscale": gray,
            "3_enlarged": enlarged,
            "4_contrast_enhanced": contrast,
            "5_sharpened": sharpened,
            "6_thresholded": thresholded
        }


# ----------------------------------------
# VISUAL COMPARISON HELPER
# ----------------------------------------

def create_comparison_grid(variants):
    """
    Build a side-by-side or stacked grid with text labels
    so all versions can be easily compared in a single image.
    """
    target_height = 120
    labeled_images = []

    for name, img in variants.items():
        # Ensure 3-channel BGR for drawing colored text
        if len(img.shape) == 2:
            display_img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        else:
            display_img = img.copy()

        # Normalize height for clean grid layout
        h, w = display_img.shape[:2]
        aspect = w / float(h)
        new_w = int(target_height * aspect)
        resized = cv2.resize(
            display_img,
            (new_w, target_height),
            interpolation=cv2.INTER_NEAREST
        )

        # Add top border banner for the label
        banner_height = 28
        banner = np.zeros((banner_height, new_w, 3), dtype=np.uint8)
        banner[:] = (35, 35, 35)

        clean_label = name.replace("_", " ").upper()
        cv2.putText(
            banner,
            clean_label,
            (8, 19),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 255, 200),
            1,
            cv2.LINE_AA
        )

        card = np.vstack([banner, resized])
        card = cv2.copyMakeBorder(
            card, 1, 1, 1, 1,
            cv2.BORDER_CONSTANT,
            value=(70, 70, 70)
        )
        labeled_images.append(card)

    # Split into 2 rows of 3 images
    row1 = np.hstack(labeled_images[:3])
    row2 = np.hstack(labeled_images[3:])

    # Equalize row widths
    max_width = max(row1.shape[1], row2.shape[1])
    if row1.shape[1] < max_width:
        pad = max_width - row1.shape[1]
        row1 = cv2.copyMakeBorder(row1, 0, 0, 0, pad, cv2.BORDER_CONSTANT, value=(20, 20, 20))
    elif row2.shape[1] < max_width:
        pad = max_width - row2.shape[1]
        row2 = cv2.copyMakeBorder(row2, 0, 0, 0, pad, cv2.BORDER_CONSTANT, value=(20, 20, 20))

    grid = np.vstack([row1, row2])
    return grid


# ----------------------------------------
# MAIN EXECUTION
# ----------------------------------------

def main():
    print("\n========================================")
    print("   GAMEWATCH SCOREBOARD PREPROCESSOR    ")
    print("========================================")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Check template directory
    if not os.path.exists(TEMPLATE_DIR):
        print(f"[!] Error: Template directory '{TEMPLATE_DIR}' not found!")
        return

    templates = [
        f for f in os.listdir(TEMPLATE_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]

    if not templates:
        print(f"[!] Error: No image templates found in '{TEMPLATE_DIR}'!")
        return

    print(f"[+] Found {len(templates)} template(s) in '{TEMPLATE_DIR}':")
    for t in templates:
        print(f"   - {t}")

    # Process all available templates
    for template_name in templates:
        template_path = os.path.join(TEMPLATE_DIR, template_name)
        img = cv2.imread(template_path)

        if img is None:
            print(f"\n[!] Could not read: {template_path}")
            continue

        base_name = os.path.splitext(template_name)[0]
        subfolder = os.path.join(OUTPUT_DIR, base_name)
        os.makedirs(subfolder, exist_ok=True)

        print(f"\nProcessing '{template_name}' ({img.shape[1]}x{img.shape[0]} px)...")

        # 1. Generate the 6 standard variants
        variants = ScoreboardPreprocessor.generate_all_variants(img)

        # Save individual variant images
        for var_name, var_img in variants.items():
            save_path = os.path.join(subfolder, f"{var_name}.png")
            cv2.imwrite(save_path, var_img)

        # 2. Generate isolated OCR-ready clock crop
        clock_ocr = ScoreboardPreprocessor.process_clock_for_ocr(img)
        clock_save_path = os.path.join(subfolder, "7_clock_ocr_ready.png")
        cv2.imwrite(clock_save_path, clock_ocr)

        # 3. Create visual comparison montage
        comparison_grid = create_comparison_grid(variants)
        grid_path = os.path.join(subfolder, f"{base_name}_comparison_grid.png")
        cv2.imwrite(grid_path, comparison_grid)

        # Also save in root output directory for quick inspection
        quick_grid_path = os.path.join(OUTPUT_DIR, f"{base_name}_comparison.png")
        cv2.imwrite(quick_grid_path, comparison_grid)

        print(f"   [OK] Generated 6 variants + OCR clock in: {subfolder}")
        print(f"   [OK] Comparison Grid saved:  {quick_grid_path}")

    print("\n========================================")
    print("[OK] PREPROCESSING COMPLETE!")
    print(f"All results saved to '{OUTPUT_DIR}/'")
    print("Inspect the generated comparison grids to choose the best OCR pipeline.")
    print("========================================\n")


# Module-level aliases for direct imports
order_quad_points = ScoreboardPreprocessor.order_quad_points
rectify_perspective = ScoreboardPreprocessor.rectify_perspective
suppress_glare = ScoreboardPreprocessor.suppress_glare
estimate_keystone_angles = ScoreboardPreprocessor.estimate_keystone_angles

if __name__ == "__main__":
    main()
