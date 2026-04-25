from pathlib import Path
from dotenv import load_dotenv
import os

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

HEYGEN_API_KEY = os.environ["HEYGEN_API_KEY"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

# Legacy (kept so older code doesn't crash if imported; not used while HeyGen is active)
HIGGSFIELD_API_KEY = os.environ.get("HIGGSFIELD_API_KEY", "")
HIGGSFIELD_API_SECRET = os.environ.get("HIGGSFIELD_API_SECRET", "")

HEYGEN_BASE = "https://api.heygen.com"
HEYGEN_UPLOAD_BASE = "https://upload.heygen.com"

# Trained HeyGen avatar for Dr Aara (use this INSTEAD of talking_photo flow).
# This is the look_id (avatar_id) of the trained "Dr Aara" Instant Avatar —
# NOT the group_id. The /v2/video/generate endpoint wants the look, not the
# group. Group id for reference: c8d988b189a74b328213639d1ba0fe07.
HEYGEN_AVATAR_ID = os.environ.get(
    "HEYGEN_AVATAR_ID", "3563531037fc4c0fb06736d921ac7928"
)

# Default HeyGen voice for Dr Aara — her trained avatar's linked voice or override here.
# List voices via: GET /v2/voices
HEYGEN_VOICE_ID = os.environ.get(
    "HEYGEN_VOICE_ID", "1bd001e7e50f421d891986aad5158bc8"
)

# 10 premium podcast-studio scene variations for Dr Aara. All seated/stationary
# with cinematic lighting. Pipeline picks one at random per video for variety
# without breaking the consistent premium aesthetic.
HEYGEN_SCENE_PROMPTS = [
    "Dr Aara seated in a premium podcast studio, medium close-up, soft warm key light from the left and subtle amber rim light from behind, blurred acoustic-panel backdrop, shallow depth of field, composed and direct",
    "Dr Aara in a moody podcast set, three-quarter angle, deep black background with a soft golden backlight creating a halo effect, cinematic contrast, intimate framing",
    "Dr Aara at a minimalist podcast desk with a broadcast microphone softly out of focus in the foreground, eye-level camera, warm tungsten key and gentle cool fill, luxurious film-like grade",
    "Dr Aara in a walnut-and-leather podcast studio, medium shot, rich warm tones, soft practical lamp in the blurred background, shallow depth of field, quietly confident",
    "Dr Aara in a dark cinematic podcast room, close-up, single soft key light carving the face, subtle warm edge light, matte black backdrop, editorial magazine feel",
    "Dr Aara in a two-tone podcast studio, medium close-up, warm amber key on the face and soft teal rim from behind, blurred studio backdrop, cinematic dual colour lighting",
    "Dr Aara at an architectural podcast set with vertical wood slats softly blurred behind her, medium shot, warm daylight-balanced key, gentle fill, premium editorial tone",
    "Dr Aara in a refined library-style podcast studio, seated in a designer chair, medium shot, warm practical lamp and soft window light, bookshelves softly defocused, thoughtful and grounded",
    "Dr Aara in a modern glass-and-concrete podcast space, three-quarter angle, soft diffused daylight from a large window, subtle golden hour bounce, clean premium aesthetic",
    "Dr Aara in an intimate low-key podcast setup, close-up, single warm softbox as key, deep shadows on the opposite side, faint ambient practicals in the blurred background, documentary-film feel",
]

# Kept for backward compatibility — if set, overrides the random pick.
HEYGEN_SCENE_PROMPT = os.environ.get("HEYGEN_SCENE_PROMPT", "")

# Background strategy for photo-avatar videos.
# Photo avatars keep the face/body in the original photo's frame — so the
# avatar's original background leaks through unless we enable matting
# (cut-out) and composite our own background underneath.
#
# Three options for the composited background:
#   (1) HEYGEN_BACKGROUND_URL: a public podcast-studio image URL — best look.
#   (2) HEYGEN_BACKGROUND_COLORS: refined dark palette — clean & consistent.
#   (3) Leave both blank → default to #0A0A0A.
HEYGEN_BACKGROUND_URL = os.environ.get("HEYGEN_BACKGROUND_URL", "")

HEYGEN_BACKGROUND_COLORS = [
    "#0A0A0A",  # near black
    "#12100E",  # warm near black
    "#141414",  # neutral charcoal
    "#1A1410",  # deep espresso
    "#0E1418",  # cool midnight
]


def pick_scene_prompt() -> str:
    """Random scene + angle for Dr Aara. Env override wins if set."""
    if HEYGEN_SCENE_PROMPT:
        return HEYGEN_SCENE_PROMPT
    import random

    return random.choice(HEYGEN_SCENE_PROMPTS)


def pick_background() -> dict:
    """Returns a HeyGen `background` payload. Image URL if configured,
    otherwise a random premium dark color."""
    if HEYGEN_BACKGROUND_URL:
        return {"type": "image", "url": HEYGEN_BACKGROUND_URL, "fit": "cover"}
    import random

    return {"type": "color", "value": random.choice(HEYGEN_BACKGROUND_COLORS)}

# Target video dimensions (9:16 Instagram Reel). 1080x1920 is the full-quality
# portrait Reel size. Requires a paid HeyGen plan; free tier caps at 720p.
HEYGEN_WIDTH = 1080
HEYGEN_HEIGHT = 1920

ASSETS_DIR = ROOT / "assets"
PERSONA_FILE = ROOT / "persona" / "dr_aara.md"
OUT_DIR = ROOT / "out"
OUT_DIR.mkdir(exist_ok=True)

DEFAULT_REFERENCE_IMAGE = ASSETS_DIR / "draara.png"
TALKING_PHOTO_CACHE = ROOT / "backend" / ".talking_photo_cache.json"
