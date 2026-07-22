import os
import tempfile
from pathlib import Path


def repository_temporary_root():
    configured = os.environ.get("VIDEO_TOOLKIT_TMP_ROOT")
    if configured:
        root = Path(configured).expanduser().resolve()
    else:
        root = None
        for candidate in (Path.cwd(), *Path.cwd().parents):
            if (candidate / "pyproject.toml").is_file():
                root = candidate / ".tmp"
                break
        if root is None:
            raise RuntimeError(
                "No se pudo resolver .tmp. Ejecuta el flujo desde el repositorio o define VIDEO_TOOLKIT_TMP_ROOT."
            )
    root.mkdir(parents=True, exist_ok=True)
    return root


def managed_temporary_directory(prefix, category=None):
    category = category or os.environ.get("VIDEO_TOOLKIT_TEMP_CATEGORY", "runtime")
    if not category.replace("-", "").replace("_", "").isalnum():
        raise ValueError(f"Categoria temporal insegura: {category}")
    category_root = repository_temporary_root() / category
    category_root.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(prefix=prefix, dir=category_root)
