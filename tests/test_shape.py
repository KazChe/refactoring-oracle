from pathlib import Path

from refactoring_oracle.case import ShapeAssertion
from refactoring_oracle.shape import check

SNIPPET = '''\
from dataclasses import dataclass

TAX_RATE = 0.08


@dataclass
class Item:
    price: float
    quantity: int


class Order:
    def total(self):
        return 0


def subtotal(item):
    return item.price * item.quantity


def total(item):
    if item is None:
        return 0
    return subtotal(item) * (1 + TAX_RATE)


def legacy(x):
    if x:
        if x > 1:
            return 2
        return 1
    return 0.08
'''


def a(kind: str, **kw) -> ShapeAssertion:
    return ShapeAssertion(kind=kind, in_file="m.py", **kw)


def run(tmp_path: Path, assertion: ShapeAssertion, text: str = SNIPPET):
    (tmp_path / "m.py").write_text(text, encoding="utf-8")
    return check(assertion, tmp_path)


def test_defines_function_and_params(tmp_path: Path) -> None:
    assert run(tmp_path, a("defines_function", name="subtotal", params=["item"])).ok
    assert not run(tmp_path, a("defines_function", name="subtotal", params=["a", "b"])).ok
    assert not run(tmp_path, a("defines_function", name="missing")).ok
    assert run(tmp_path, a("defines_function", name="Order.total", params=["self"])).ok


def test_not_defines(tmp_path: Path) -> None:
    assert run(tmp_path, a("not_defines", name="gone")).ok
    assert not run(tmp_path, a("not_defines", name="legacy")).ok


def test_defines_class(tmp_path: Path) -> None:
    assert run(tmp_path, a("defines_class", name="Item", dataclass=True,
                           fields=["price", "quantity"])).ok
    assert not run(tmp_path, a("defines_class", name="Item", fields=["quantity", "price"])).ok
    assert not run(tmp_path, a("defines_class", name="Order", dataclass=True)).ok
    assert not run(tmp_path, a("defines_class", name="Nope")).ok


def test_calls_and_no_call(tmp_path: Path) -> None:
    assert run(tmp_path, a("calls", callee="subtotal", inside="total")).ok
    assert not run(tmp_path, a("calls", callee="subtotal", inside="legacy")).ok
    assert run(tmp_path, a("no_call", callee="subtotal", inside="legacy")).ok
    assert not run(tmp_path, a("no_call", callee="subtotal")).ok


def test_constants_and_literals(tmp_path: Path) -> None:
    assert run(tmp_path, a("defines_constant", name="TAX_RATE", value=0.08)).ok
    assert not run(tmp_path, a("defines_constant", name="TAX_RATE", value=0.1)).ok
    assert not run(tmp_path, a("defines_constant", name="RATE", value=0.08)).ok
    assert run(tmp_path, a("no_literal", value=0.08, inside="total")).ok
    assert not run(tmp_path, a("no_literal", value=0.08, inside="legacy")).ok
    # 1 and True are different literals.
    assert run(tmp_path, a("no_literal", value=True, inside="legacy")).ok


def test_guard_and_depth(tmp_path: Path) -> None:
    assert run(tmp_path, a("starts_with_guard", inside="total")).ok
    assert not run(tmp_path, a("starts_with_guard", inside="legacy")).ok
    assert run(tmp_path, a("max_if_depth", inside="total", n=1)).ok
    assert not run(tmp_path, a("max_if_depth", inside="legacy", n=1)).ok
    assert run(tmp_path, a("max_if_depth", inside="legacy", n=2)).ok


def test_name_absent_present(tmp_path: Path) -> None:
    assert run(tmp_path, a("name_present", name="quantity")).ok
    assert run(tmp_path, a("name_absent", name="item_price")).ok
    assert not run(tmp_path, a("name_absent", name="subtotal")).ok


def test_missing_or_broken_file(tmp_path: Path) -> None:
    res = check(a("defines_function", name="f"), tmp_path)
    assert not res.ok and "missing" in res.message
    res = run(tmp_path, a("defines_function", name="f"), text="def (:\n")
    assert not res.ok and "parse" in res.message
