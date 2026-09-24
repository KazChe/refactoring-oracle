"""Helpers to build a throwaway case on disk for the oracle tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from refactoring_oracle.case import Case, load_case

BEFORE_PRICING = '''\
"""Pricing helpers."""


def subtotal(item_price, item_quantity):
    return item_price * item_quantity


def total_with_tax(item_price, item_quantity):
    return subtotal(item_price, item_quantity) * 1.08


def receipt(item_price, item_quantity):
    return f"total: {total_with_tax(item_price, item_quantity):.2f}"


def format_money(amount):
    return f"${amount:.2f}"
'''

AFTER_PRICING = '''\
"""Pricing helpers."""

from dataclasses import dataclass


@dataclass
class Item:
    price: float
    quantity: int


def subtotal(item):
    return item.price * item.quantity


def total_with_tax(item):
    return subtotal(item) * 1.08


def receipt(item_price, item_quantity):
    return f"total: {total_with_tax(Item(price=item_price, quantity=item_quantity)):.2f}"


def format_money(amount):
    return f"${amount:.2f}"
'''

INIT = '"""A tiny package used only by the oracle tests."""\n'

TESTS_AFTER = '''\
from pricing import Item, subtotal, total_with_tax


def test_subtotal():
    assert subtotal(Item(price=9.99, quantity=6)) == 59.94


def test_total_with_tax():
    assert round(total_with_tax(Item(price=10.0, quantity=1)), 2) == 10.8
'''

CASE_JSON = {
    "id": "introduce-parameter-object/pricing",
    "refactoring": "introduce-parameter-object",
    "sample": "pricing",
    "instruction": "In pricing.py introduce a dataclass Item(price: float, quantity: int) ...",
    "allowed_files": ["pricing.py"],
    "protected": ["pricing.py::format_money"],
    "allowed_imports": ["dataclasses"],
    "deterministic_tool": None,
    "shape": [
        {"kind": "defines_class", "in_file": "pricing.py", "name": "Item",
         "dataclass": True, "fields": ["price", "quantity"]},
        {"kind": "defines_function", "in_file": "pricing.py", "name": "subtotal",
         "params": ["item"]},
    ],
}


def write_tree(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")


@pytest.fixture
def pricing_case(tmp_path: Path) -> Case:
    case_dir = tmp_path / "cases" / "introduce-parameter-object" / "pricing"
    write_tree(case_dir / "before", {"pricing.py": BEFORE_PRICING, "__init__.py": INIT})
    write_tree(case_dir / "after", {"pricing.py": AFTER_PRICING, "__init__.py": INIT})
    write_tree(case_dir / "tests_after", {"test_pricing.py": TESTS_AFTER})
    (case_dir / "case.json").write_text(json.dumps(CASE_JSON, indent=2), encoding="utf-8")
    return load_case(case_dir)
