from pipeline.freq import parse


def test_parse_keeps_words_and_merges_duplicates():
    text = "de 100\nque 90\n3 50\n-- 40\nque 10\nc' 5\n"
    df = parse(text)
    assert df.rows() == [("de", 100), ("que", 100), ("c'", 5)]
