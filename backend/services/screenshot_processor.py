import base64
import io
import re
from typing import Optional, Tuple
try:
    from PIL import Image
except ImportError:
    Image = None

class ScreenshotProcessor:
    @staticmethod
    def clean_base64(raw_image_str: str) -> Tuple[str, str]:
        """
        Extracts clean base64 string and mime type from data URI or raw base64.
        """
        if not raw_image_str:
            return "", "image/png"

        # Check for data URI prefix e.g. data:image/png;base64,...
        match = re.match(r"data:(image/\w+);base64,(.+)", raw_image_str)
        if match:
            mime_type = match.group(1)
            b64_data = match.group(2)
            return b64_data, mime_type

        return raw_image_str, "image/png"

    @staticmethod
    def validate_and_inspect(b64_str: str) -> Tuple[bool, Optional[Tuple[int, int]]]:
        """
        Validates Base64 image payload and returns dimensions (width, height).
        """
        try:
            clean_data, _ = ScreenshotProcessor.clean_base64(b64_str)
            if not clean_data:
                return False, None
                
            img_bytes = base64.b64decode(clean_data)
            if Image is not None:
                img = Image.open(io.BytesIO(img_bytes))
                return True, img.size
            return True, None
        except Exception:
            return False, None

screenshot_processor = ScreenshotProcessor()
