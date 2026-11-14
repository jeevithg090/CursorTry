from pathlib import Path

import pytest

from fintechagent import AllCustomers, DataError, Products
from fintechagent.product import parse_product_filename


def test_fetch_customers_from_migrated_db(db_path):
    customers = AllCustomers.fetch_from_db(db_path)
    assert [c.name for c in customers.customers] == ["Akhil", "Bhushan"]
    assert customers.customers[0].segment == "travel"
    assert customers.customers[0].mobile.startswith("+91")


def test_find_customer_case_insensitive(db_path):
    customers = AllCustomers.fetch_from_db(db_path)
    found = customers.find("  bhushan ")
    assert found is not None and found.segment == "movies"
    assert customers.find("nobody") is None


def test_missing_db_is_helpful_and_not_created(tmp_path):
    missing = tmp_path / "nope.sqlite"
    with pytest.raises(DataError, match="yoyo apply"):
        AllCustomers.fetch_from_db(missing)
    assert not missing.exists()


def test_unmigrated_db(tmp_path):
    empty = tmp_path / "empty.sqlite"
    empty.write_bytes(b"")
    with pytest.raises(DataError, match="migrations"):
        AllCustomers.fetch_from_db(empty)


def test_real_product_catalogue(products_dir):
    products = Products.fetch_from_folder(products_dir)
    segments = {p.segment for p in products.products}
    assert segments == {"fuel", "generic", "movies", "train", "travel"}
    assert products.default_product.title == "Platinum ValuePlus Credit Card"
    assert all(p.content for p in products.products)


@pytest.mark.parametrize(
    ("segment", "title"),
    [
        ("travel", "World Safari Credit Card"),
        ("MOVIES", "Movies and More Credit Card"),
        ("unknown", "Platinum ValuePlus Credit Card"),
    ],
)
def test_for_segment(products_dir, segment, title):
    assert Products.fetch_from_folder(products_dir).for_segment(segment).title == title


def test_filename_with_extra_dashes():
    assert parse_product_filename("travel - Co-branded Card - Plus") == (
        "travel",
        "Co-branded Card - Plus",
    )


@pytest.mark.parametrize("name", ["nodash", "- Title", "travel -  "])
def test_bad_filenames(name):
    with pytest.raises(DataError):
        parse_product_filename(name)


def _write(folder: Path, name: str, content: str = "info") -> None:
    (folder / name).write_text(content)


def test_hidden_files_ignored_and_generic_required(tmp_path):
    _write(tmp_path, ".DS_Store", "junk")
    _write(tmp_path, "travel - Card")
    with pytest.raises(DataError, match="generic"):
        Products.fetch_from_folder(tmp_path)
    _write(tmp_path, "generic - Basic")
    assert len(Products.fetch_from_folder(tmp_path).products) == 2


def test_empty_product_file_rejected(tmp_path):
    _write(tmp_path, "generic - Basic", "  ")
    with pytest.raises(DataError, match="empty"):
        Products.fetch_from_folder(tmp_path)


def test_missing_products_folder(tmp_path):
    with pytest.raises(DataError, match="not found"):
        Products.fetch_from_folder(tmp_path / "missing")
