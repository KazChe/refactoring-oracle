from cleaner import normalize_header, clean_headers


def test_normalize_header():
    assert normalize_header("  Order ID ") == "order_id"
    assert normalize_header("Price (USD)") == "price_usd"
    assert normalize_header("***") == "column"


def test_duplicates_get_suffixes():
    assert clean_headers(["Name", "name", "NAME", "Total"]) == ["name", "name_1", "name_2", "total"]
