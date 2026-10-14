from pathlib import Path
from string import ascii_letters, ascii_lowercase, digits

"""The kernel's own constants. A module's live in that module."""

REQUEST_ID_HEADER = "X-Request-Id"
OAUTH_STATE_TTL_SECONDS = 600
OTP_DIGITS = 6

QUESTIONS = {
    "sqlite": "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
    "postgres": (
        "SELECT table_name FROM information_schema.tables WHERE table_schema = current_schema() AND table_name = $1"
    ),
    "mysql": ("SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = %s"),
}

DEFAULT_CONFIG_PATH = Path("data/config.toml")
CONFIG_ENV_VAR = "APP_CONFIG"
KERNEL_SECTIONS = frozenset({"server", "database", "session", "cors", "modules"})

APP_LABEL = "models"

ENTRY_POINTS = "dooservice_kernel.modules"

LABEL_CHARACTERS = frozenset(ascii_lowercase + digits + "-")
CODE_CHARACTERS = frozenset(ascii_letters + digits + "-_.")
HEX_CHARACTERS = frozenset(digits + "abcdef")

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s"

MIGRATIONS_TABLE = "tortoise_migrations"

TABLE = "kernel_outbox"
RELAY_EVERY_SECONDS = 1.0
BATCH = 100

SEPARATOR = "__"
FROM_FILE = "file"

PROBLEM_CONTENT_TYPE = "application/problem+json"

CHANNEL = "dooservice_kernel.events"

PREFIX = "dooservice_kernel:throttle:"
