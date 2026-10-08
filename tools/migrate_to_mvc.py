"""One-shot MVC folder migration. Safe to re-run only on the pre-MVC tree."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_APP = ROOT / "backend" / "app"
FRONTEND_SRC = ROOT / "frontend" / "src"
API_V1 = BACKEND_APP / "api" / "v1"
CONTROLLERS = BACKEND_APP / "controllers"
MODELS = BACKEND_APP / "models"
FRONT_API = FRONTEND_SRC / "api"
FRONT_MODELS = FRONTEND_SRC / "models"
FRONT_CONTROLLERS = FRONTEND_SRC / "controllers"
FRONT_VIEWS = FRONTEND_SRC / "views"


def balanced(text: str) -> bool:
    return text.count("(") == text.count(")") and text.count("{") == text.count("}") and text.count("[") == text.count("]")


def rewrite_text(path: Path, replacements: list[tuple[str, str]]) -> None:
    text = path.read_text(encoding="utf-8")
    original = text
    for old, new in replacements:
        text = text.replace(old, new)
    if text != original:
        path.write_text(text, encoding="utf-8")


def copy_backend_controllers() -> None:
    CONTROLLERS.mkdir(parents=True, exist_ok=True)
    for src in API_V1.glob("*.py"):
        dest = CONTROLLERS / src.name
        text = src.read_text(encoding="utf-8")
        text = text.replace("from backend.app.db.models", "from backend.app.models")
        dest.write_text(text, encoding="utf-8")
    (CONTROLLERS / "__init__.py").write_text("", encoding="utf-8")
    MODELS.mkdir(parents=True, exist_ok=True)
    (MODELS / "__init__.py").write_text(
        "from backend.app.db.models import *\nfrom backend.app.db.models import __all__\n",
        encoding="utf-8",
    )
    for src in API_V1.glob("*.py"):
        module = src.stem
        src.write_text(
            f"from backend.app.controllers.{module} import *\nfrom backend.app.controllers.{module} import router\n",
            encoding="utf-8",
        )


def update_python_imports() -> None:
    skip = {MODELS / "__init__.py", BACKEND_APP / "db" / "models" / "__init__.py"}
    for path in ROOT.rglob("*.py"):
        if "node_modules" in path.parts or "__pycache__" in path.parts:
            continue
        if path in skip or path.parent == BACKEND_APP / "db" / "models":
            continue
        if path.name == "migrate_to_mvc.py":
            continue
        rewrite_text(
            path,
            [
                ("from backend.app.api.v1", "from backend.app.controllers"),
                ("from backend.app.db.models import", "from backend.app.models import"),
                ("from backend.app.db.models.", "from backend.app.models."),
            ],
        )
    rewrite_text(
        BACKEND_APP / "main.py",
        [("from backend.app.api.v1 import (", "from backend.app.controllers import (")],
    )


def copy_frontend_models() -> None:
    if FRONT_MODELS.exists():
        shutil.rmtree(FRONT_MODELS)
    shutil.copytree(FRONT_API, FRONT_MODELS)
    for src in FRONT_API.glob("*.ts"):
        src.write_text(f"export * from '../models/{src.stem}'\n", encoding="utf-8")


def extract_import_blocks(script: str) -> tuple[list[str], str]:
    lines = script.split("\n")
    imports: list[str] = []
    body: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("import ") or line.startswith("from "):
            chunk = [line]
            while not balanced("\n".join(chunk)):
                i += 1
                if i >= len(lines):
                    break
                chunk.append(lines[i])
            imports.append("\n".join(chunk))
        else:
            body.append(line)
        i += 1
    return imports, "\n".join(body).strip() + "\n"


def exported_names(body: str) -> list[str]:
    names: list[str] = []
    for match in re.finditer(
        r"^(?:export )?(?:async )?function ([A-Za-z_][\w]*)|^(?:export )?const ([A-Za-z_][\w]*)\s*=",
        body,
        re.M,
    ):
        names.append(match.group(1) or match.group(2))
    seen: set[str] = set()
    unique: list[str] = []
    for name in names:
        if name not in seen:
            seen.add(name)
            unique.append(name)
    return unique


def to_controller_name(view_path: Path) -> tuple[str, str]:
    base = view_path.stem  # LoginView
    stem = re.sub(r"View$", "", base)
    hook = f"use{stem}Controller" if stem[0].isupper() else f"use{stem[0].upper() + stem[1:]}Controller"
    file_stem = stem[0].lower() + stem[1:] + "Controller"
    return hook, file_stem


def extract_view_controllers() -> None:
    FRONT_CONTROLLERS.mkdir(parents=True, exist_ok=True)
    for view in sorted(FRONT_VIEWS.glob("*View.vue")):
        text = view.read_text(encoding="utf-8")
        match = re.search(r"<script setup lang=\"ts\">\n(.*)\n</script>", text, re.S)
        if not match:
            continue
        script = match.group(1)
        imports, body = extract_import_blocks(script)
        view_imports: list[str] = []
        controller_imports: list[str] = []
        for block in imports:
            rewritten = (
                block.replace("../api/", "../models/")
                .replace("'../api/", "'../models/")
                .replace('"../api/', '"../models/')
            )
            if ".vue" in block:
                view_imports.append(block)
            else:
                controller_imports.append(rewritten)
        names = exported_names(body)
        hook, file_stem = to_controller_name(view)
        controller = (
            "\n".join(controller_imports)
            + ("\n\n" if controller_imports else "")
            + f"export function {hook}() {{\n"
            + "".join(f"  {line}\n" if line else "\n" for line in body.strip().split("\n"))
            + "\n  return {\n    "
            + ",\n    ".join(names)
            + ",\n  }\n}\n"
        )
        (FRONT_CONTROLLERS / f"{file_stem}.ts").write_text(controller, encoding="utf-8")
        view_script = (
            "\n".join(view_imports)
            + ("\n" if view_imports else "")
            + f"import {{ {hook} }} from '../controllers/{file_stem}'\n\n"
            + f"const {{\n  {',\n  '.join(names)}\n}} = {hook}()\n"
        )
        text = text[: match.start(1)] + view_script + text[match.end(1) :]
        view.write_text(text, encoding="utf-8")


def update_frontend_imports() -> None:
    for path in FRONTEND_SRC.rglob("*.{ts,vue}"):
        pass
    for path in list(FRONTEND_SRC.rglob("*.ts")) + list(FRONTEND_SRC.rglob("*.vue")):
        if "controllers" in path.parts:
            continue
        rewrite_text(
            path,
            [
                ("from '../api/", "from '../models/"),
                ('from "../api/', 'from "../models/'),
                ("from '../../api/", "from '../../models/"),
            ],
        )
    tests = ROOT / "frontend" / "tests"
    for path in tests.glob("*.ts"):
        rewrite_text(path, [("'../src/api/", "'../src/models/")])
    rewrite_text(
        FRONTEND_SRC / "stores" / "app.ts",
        [
            ("from '../api/client'", "from '../models/client'"),
            ("from '../api/auth'", "from '../models/auth'"),
        ],
    )


def main() -> None:
    copy_backend_controllers()
    update_python_imports()
    copy_frontend_models()
    extract_view_controllers()
    update_frontend_imports()
    print("MVC migration complete")


if __name__ == "__main__":
    main()
