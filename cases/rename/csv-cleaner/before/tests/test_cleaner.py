from cleaner import clean_hdr, clean_headers


def test_clean_hdr():
    assert clean_hdr("  Order ID ") == "order_id"
    assert clean_hdr("Price (USD)") == "price_usd"
    assert clean_hdr("***") == "column"


def test_duplicates_get_suffixes():
    assert clean_headers(["Name", "name", "NAME", "Total"]) == ["name", "name_1", "name_2", "total"]
