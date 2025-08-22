import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# ------------------------------------------------------ ИМПОРТ КЛЮЧЕЙ ------------------------------------------------------

_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _ROOT / ".env"

def _manual_load_env(path: Path) -> None:
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                if "=" not in s:
                    continue
                k, v = s.split("=", 1)
                k = k.strip()
                v = v.strip()
                if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                    v = v[1:-1]
                os.environ.setdefault(k, v)
    except Exception:
        pass

if _ENV_PATH.exists():
    if load_dotenv:
        load_dotenv(str(_ENV_PATH))
    else:
        _manual_load_env(_ENV_PATH)

def _get(name: str, default: str = "") -> str:
    val = os.getenv(name)
    return val if val is not None and val != "" else default

BOT_TOKEN = _get("BOT_TOKEN")
PAYMENT_PROVIDER_TOKEN = _get("PAYMENT_PROVIDER_TOKEN")

ADMIN_USERNAME = _get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = _get("ADMIN_PASSWORD", "password")

OPENWEATHERMAP_API_KEY = _get("OPENWEATHERMAP_API_KEY")
WEATHERAPI_API_KEY = _get("WEATHERAPI_API_KEY")
LOCATIONIQ_API_KEY = _get("LOCATIONIQ_API_KEY")

PAYMASTER_MERCHANT_ID = _get("PAYMASTER_MERCHANT_ID")
PAYMASTER_SECRET_KEY = _get("PAYMASTER_SECRET_KEY")
PAYMASTER_TOKEN = _get("PAYMASTER_TOKEN")

REFERRAL_BOT_URL = _get("REFERRAL_BOT_URL")

SUBSCRIBE_CHANNEL_URL = _get("SUBSCRIBE_CHANNEL_URL")
def _get_int(name: str, default: int | None = None) -> int | None:
    val = _get(name, "")
    try:
        return int(val)
    except Exception:
        return default

CHANNEL_CHAT_ID = _get_int("CHANNEL_CHAT_ID")