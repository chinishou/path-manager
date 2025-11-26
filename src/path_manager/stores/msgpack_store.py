"""
Indexed MsgPack-based compiled schema storage.
"""
from __future__ import annotations

import mmap
from pathlib import Path
from typing import Iterator

try:
    import msgpack
except ImportError:
    raise ImportError(
        "msgpack is required for MsgPackStore. "
        "Install it with: pip install msgpack"
    )

from .base import CompiledStore


# Magic number: "PMSG" (Path Manager Schema)
MAGIC = b"PMSG"
VERSION = 1


class MsgPackStore(CompiledStore):
    """
    Indexed MsgPack storage implementation.

    File format:
        [Byte 0-3]    Magic: "PMSG"
        [Byte 4-7]    Version: uint32
        [Byte 8-15]   Index offset: uint64
        [Byte 16-23]  Index size: uint64
        [Byte 24...]  Data blocks
        [End]         Index data (msgpack encoded)
    """

    def __init__(self, file_path: str | Path):
        """
        Initialize MsgPack store.

        Args:
            file_path: Path to msgpack file
        """
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"MsgPack file not found: {file_path}")

        self.file = open(self.file_path, "rb")
        self.mmap = mmap.mmap(self.file.fileno(), 0, access=mmap.ACCESS_READ)

        # Read and validate header
        self._read_header()

        # Load index
        self._load_index()

    def _read_header(self):
        """Read and validate file header."""
        magic = self.mmap[0:4]
        if magic != MAGIC:
            raise ValueError(f"Invalid magic number: {magic}")

        version = int.from_bytes(self.mmap[4:8], "little")
        if version != VERSION:
            raise ValueError(f"Unsupported version: {version}")

        self.index_offset = int.from_bytes(self.mmap[8:16], "little")
        self.index_size = int.from_bytes(self.mmap[16:24], "little")
        self.data_start = 24

    def _load_index(self):
        """Load index from file."""
        self.mmap.seek(self.index_offset)
        index_data = self.mmap.read(self.index_size)
        self.index = msgpack.unpackb(index_data, raw=False)

    def _read_data(self, category: str, name: str) -> dict | None:
        """
        Read data block by category and name.

        Args:
            category: "kinds", "dirs", or "fields"
            name: Item name

        Returns:
            Data dict or None if not found
        """
        items = self.index.get(category, {})
        info = items.get(name)

        if info is None:
            return None

        offset = info["offset"]
        size = info["size"]

        self.mmap.seek(self.data_start + offset)
        data = self.mmap.read(size)

        return msgpack.unpackb(data, raw=False)

    def get_kind(self, name: str) -> dict | None:
        """Get kind definition by name."""
        return self._read_data("kinds", name)

    def get_dir(self, name: str) -> dict | None:
        """Get directory definition by name."""
        return self._read_data("dirs", name)

    def get_field(self, name: str) -> dict | None:
        """Get field definition by name."""
        return self._read_data("fields", name)

    def iter_all_kinds(self) -> Iterator[str]:
        """Iterate over all kind names."""
        kinds = self.index.get("kinds", {})
        for name in sorted(kinds.keys()):
            yield name

    def get_ambiguities(self) -> dict[str, list[str]]:
        """Get ambiguity mapping."""
        return self.index.get("ambiguities", {})

    def close(self):
        """Close file and mmap."""
        if self.mmap:
            self.mmap.close()
            self.mmap = None

        if self.file:
            self.file.close()
            self.file = None


class MsgPackWriter:
    """
    Writer for indexed MsgPack format.

    Usage:
        writer = MsgPackWriter(output_path)
        writer.add_kind("asset_image", {"template": "...", "fields": [...]})
        writer.add_dir("proj_root", {"template": "...", "fields": [...]})
        writer.add_field("root", {"regex": "...", "example": "..."})
        writer.set_ambiguities({"pattern": ["kind1", "kind2"]})
        writer.finalize()
    """

    def __init__(self, file_path: str | Path):
        """
        Initialize writer.

        Args:
            file_path: Output file path
        """
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        self.file = open(self.file_path, "wb")

        # Reserve space for header (24 bytes)
        self.file.write(b"\x00" * 24)

        self.kinds = {}
        self.dirs = {}
        self.fields = {}
        self.ambiguities = {}

        self.current_offset = 0

    def add_kind(self, name: str, data: dict):
        """Add kind definition."""
        self._add_item("kinds", name, data)

    def add_dir(self, name: str, data: dict):
        """Add directory definition."""
        self._add_item("dirs", name, data)

    def add_field(self, name: str, data: dict):
        """Add field definition."""
        self._add_item("fields", name, data)

    def set_ambiguities(self, ambiguities: dict[str, list[str]]):
        """Set ambiguity mapping."""
        self.ambiguities = ambiguities

    def _add_item(self, category: str, name: str, data: dict):
        """
        Add item and record its offset/size.

        Args:
            category: "kinds", "dirs", or "fields"
            name: Item name
            data: Item data
        """
        # Pack data
        packed = msgpack.packb(data, use_bin_type=True)

        # Write to file
        self.file.write(packed)

        # Record offset and size
        storage = getattr(self, category)
        storage[name] = {
            "offset": self.current_offset,
            "size": len(packed)
        }

        self.current_offset += len(packed)

    def finalize(self):
        """Write index and header, then close file."""
        # Build index
        index = {
            "kinds": self.kinds,
            "dirs": self.dirs,
            "fields": self.fields,
            "ambiguities": self.ambiguities
        }

        # Pack and write index
        index_data = msgpack.packb(index, use_bin_type=True)
        index_offset = self.file.tell()
        index_size = len(index_data)

        self.file.write(index_data)

        # Write header
        self.file.seek(0)
        self.file.write(MAGIC)
        self.file.write(VERSION.to_bytes(4, "little"))
        self.file.write(index_offset.to_bytes(8, "little"))
        self.file.write(index_size.to_bytes(8, "little"))

        # Close file
        self.file.close()

        # Set to read-only
        self.file_path.chmod(0o444)
