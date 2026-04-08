from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
APP_DIR = PROJECT_ROOT / "app"
PROCESSED_DATA_DIR = APP_DIR / "finalData"
NEW_DATA_DIR = PROJECT_ROOT / "NEW_DATA"
MODEL_CHECKPOINT_DIR = PROJECT_ROOT / "model" / "checkpoints" / "tourism_model_checkpoint_2240"


def project_path(*parts: str) -> Path:
    return PROJECT_ROOT.joinpath(*parts)