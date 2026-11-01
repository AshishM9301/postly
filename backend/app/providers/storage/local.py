"""Local-disk storage behind the ``StorageProvider`` interface."""

from __future__ import annotations

import hashlib
import hmac
import os
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from app.core.config import get_settings

DEFAULT_ROOT = Path("media")


class LocalStorageProvider:
    def __init__(self, root: Path | str = DEFAULT_ROOT) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, path: str) -> Path:
        root = self.root.resolve()
        target = (root / path).resolve()
        if target != root and root not in target.parents:
            raise FileNotFoundError(path)
        return target

    def save(self, stream: BinaryIO, ext: str) -> str:
        """Copy to ``yyyy/mm/<uuid>.<ext>`` via a ``.part`` file, then rename."""
        now = datetime.now(UTC)
        relative = Path(f"{now:%Y/%m}/{uuid4().hex}.{ext}")
        final = self._resolve(relative.as_posix())
        final.parent.mkdir(parents=True, exist_ok=True)
        partial = final.with_name(f".{final.name}.part")

        try:
            with partial.open("wb") as output:
                shutil.copyfileobj(stream, output)
                output.flush()
                os.fsync(output.fileno())
            partial.replace(final)
        except Exception:
            partial.unlink(missing_ok=True)
            raise

        return relative.as_posix()

    def delete(self, path: str) -> None:
        self._resolve(path).unlink(missing_ok=True)

    def open(self, path: str) -> BinaryIO:
        return self._resolve(path).open("rb")

    def _secret(self) -> bytes:
        return get_settings().secret_key.encode("utf-8")

    def _signature(self, resource_key: str, expires: int) -> str:
        message = f"{resource_key}:{expires}".encode()
        return hmac.new(self._secret(), message, hashlib.sha256).hexdigest()

    def signed_url(self, resource_key: str, ttl: int) -> str:
        expires = int(time.time()) + ttl
        signature = self._signature(resource_key, expires)
        prefix = get_settings().api_prefix
        return f"{prefix}/media/{resource_key}/file?expires={expires}&sig={signature}"

    def verify_signed_url(self, resource_key: str, expires: int, signature: str) -> bool:
        if expires < int(time.time()):
            return False
        expected = self._signature(resource_key, expires)
        return hmac.compare_digest(expected, signature)
