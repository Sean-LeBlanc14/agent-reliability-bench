from pathlib import Path

REPO_ROOT = Path(__file__).parent
DATA_DIR = REPO_ROOT / "data"
DB_DIR = DATA_DIR / "database"
DEV_FILE = DATA_DIR / "validation.json"
ADAPTER_DIR = Path("/home/SeanUbuntu/Github/text2sql/adapters/qlora-r16-1ep-canonical")

