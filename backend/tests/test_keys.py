def test_mask_key_standard():
    from keys import mask_key
    key = "gsk_1234567890abcdef"
    masked = mask_key(key)
    assert masked.startswith("gsk_")
    assert "1234567890abcdef" not in masked
    assert masked.endswith("••••••••")


def test_mask_key_empty():
    from keys import mask_key
    assert mask_key("") == ""
    assert mask_key(None) == ""


def test_mask_key_short():
    from keys import mask_key
    assert mask_key("abc") == "••••••••"
    assert mask_key("1234") == "••••••••"
    assert "abc" not in mask_key("abc")


if __name__ == "__main__":
    test_mask_key_standard()
    test_mask_key_empty()
    test_mask_key_short()
    print("All unit tests passed successfully.")
