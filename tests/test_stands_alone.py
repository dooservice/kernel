"""The kernel imports its own dependencies and nothing else: whatever is built on it
plugs into it, never the other way round."""

import ast
from pathlib import Path
import sys

import dooservice_kernel

KERNEL = Path(dooservice_kernel.__file__).parent
ALLOWED = {
    "dooservice_kernel",
    "fastapi",
    "starlette",
    "pydantic",
    "pydantic_core",
    "email_validator",
    "msgspec",
    "tortoise",
    "itsdangerous",
    "bcrypt",
    "nacl",
    "cyclopts",
    "prometheus_client",
    "opentelemetry",
    "redis",
    "httpx",
    "pytest",
}


def test_the_kernel_imports_only_the_standard_library_and_its_dependencies() -> None:
    found = set()
    for source in KERNEL.glob("*.py"):
        for node in ast.walk(ast.parse(source.read_text())):
            names = [alias.name for alias in node.names] if isinstance(node, ast.Import) else []
            if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module]
            for name in names:
                top = name.split(".")[0]
                if top not in ALLOWED and top not in sys.stdlib_module_names and top != "__future__":
                    found.add(f"{source.name}: {name}")
    assert not found
