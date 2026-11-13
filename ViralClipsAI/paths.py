import os, sys
from pathlib import Path

def resource_path(relative):
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return root / relative

# Keep generated media and downloaded AI models outside the program folder.
APP_HOME = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "ViralClipsAI"
UPLOADS = APP_HOME / "uploads"
OUTPUTS = APP_HOME / "outputs"
MODELS = APP_HOME / "models"
for folder in (UPLOADS, OUTPUTS, MODELS):
    folder.mkdir(parents=True, exist_ok=True)
