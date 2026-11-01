"""Storage provider interface.

Local disk is the MVP. S3/R2 (T-063) implements the same handful of methods and
swaps in without touching the media service or routes.
"""

from __future__ import annotations

from typing import BinaryIO, Protocol, runtime_checkable


@runtime_checkable
class StorageProvider(Protocol):
    def save(self, stream: BinaryIO, ext: str) -> str:
        """Persist the stream and return a relative storage path."""
        ...

    def delete(self, path: str) -> None:
        """Remove one stored object; missing objects are ignored."""
        ...

    def open(self, path: str) -> BinaryIO:
        """Open a stored object for reading, or raise ``FileNotFoundError``."""
        ...

    def signed_url(self, resource_key: str, ttl: int) -> str:
        """Build a short-lived, signed URL for a resource."""
        ...

    def verify_signed_url(self, resource_key: str, expires: int, signature: str) -> bool:
        """True only for an unexpired signature produced by this provider."""
        ...
