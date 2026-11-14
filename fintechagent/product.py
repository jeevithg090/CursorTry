"""Credit-card product catalogue loaded from plain-text files.

Each file in the products folder is named ``"<segment> - <title>"`` and contains
the product description used as context for the LLM.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .errors import DataError

DEFAULT_SEGMENT = "generic"


@dataclass(frozen=True)
class Product:
    title: str
    content: str
    segment: str


def parse_product_filename(filename: str) -> tuple[str, str]:
    """Split ``"segment - Title-with-dashes"`` into ``(segment, title)``."""
    segment, sep, title = filename.partition("-")
    segment, title = segment.strip().lower(), title.strip()
    if not sep or not segment or not title:
        raise DataError(f"Invalid product file name '{filename}'. Expected '<segment> - <title>'.")
    return segment, title


class Products:
    def __init__(self, products: list[Product]):
        self.products = products
        default = next((p for p in products if p.segment == DEFAULT_SEGMENT), None)
        if default is None:
            raise DataError(f"No '{DEFAULT_SEGMENT}' product found; one is required as a fallback.")
        self.default_product: Product = default

    def __repr__(self) -> str:
        return f"Products({self.products!r})"

    def for_segment(self, segment: str) -> Product:
        """Return the product matching ``segment`` or the generic fallback."""
        wanted = segment.strip().lower()
        return next((p for p in self.products if p.segment == wanted), self.default_product)

    @classmethod
    def fetch_from_folder(cls, folder_path: str | Path) -> Products:
        folder = Path(folder_path)
        if not folder.is_dir():
            raise DataError(f"Products folder not found at '{folder}'.")
        products = []
        # Sorted for deterministic ordering; hidden files (.DS_Store etc.) skipped.
        for file in sorted(folder.iterdir()):
            if not file.is_file() or file.name.startswith("."):
                continue
            segment, title = parse_product_filename(file.name)
            content = file.read_text(encoding="utf-8").strip()
            if not content:
                raise DataError(f"Product file '{file.name}' is empty.")
            products.append(Product(title=title, content=content, segment=segment))
        return cls(products)
