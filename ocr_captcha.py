# Required: pip install opencv-python pillow pytesseract
import cv2
import numpy as np
from PIL import Image
import pytesseract


def load_image_pil(path: str) -> np.ndarray:
    """Load an image using PIL to handle Unicode paths, and convert to OpenCV BGR format."""
    img_pil = Image.open(path)
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)


def preprocess_image(img: np.ndarray) -> np.ndarray:
    """Apply preprocessing: grayscale, resize, morph close, blur, and threshold."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Resize to improve OCR recognition
    h, w = gray.shape[:2]
    resized = cv2.resize(gray, (w * 2, h * 2))

    # Morphological closing to fill small gaps
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    closed = cv2.morphologyEx(resized, cv2.MORPH_CLOSE, kernel)

    # Blur to smooth noise
    blurred = cv2.GaussianBlur(closed, (5, 5), sigmaX=1)

    # Threshold using Otsu's method
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

    return binary


def extract_text(img: np.ndarray) -> str:
    """Extract text using pytesseract with a character whitelist."""
    config = r'-c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 --psm 8'
    return pytesseract.image_to_string(img, config=config).strip()


def get_captcha_text(image_path):
    img = load_image_pil(image_path)
    processed = preprocess_image(img)
    return extract_text(processed)

def main():
    image_path = "无标题.png"  # Or any filename with non-ASCII chars
    img = load_image_pil(image_path)
    processed = preprocess_image(img)
    result = extract_text(processed)

    print("CAPTCHA result:", result)


if __name__ == "__main__":
    main()
