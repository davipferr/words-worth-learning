from pipeline.cedict import choose, parse, pinyin


def test_pinyin_tone_marks():
    assert pinyin("dian4 hua4") == "diànhuà"
    assert pinyin("lu:4 se4") == "lǜsè"
    assert pinyin("de5") == "de"
    assert pinyin("shou3") == "shǒu"


def test_parse_and_choose_the_treebank_reading():
    text = "\n".join(
        [
            "# comment",
            "的 的 [de5] /of; ~'s (possessive particle)/",
            "的 的 [di4] /(bound form) bull's-eye; target/",
            "也 也 [Ye3] /surname Ye/",
            "也 也 [ye3] /also; too/",
        ]
    )
    df = parse(text)
    readings = {}
    for r in df.iter_rows(named=True):
        readings.setdefault(r["palavra"], []).append(r)
    assert choose(readings["的"], "de")["pinyin"] == "de"
    assert choose(readings["的"], None)["pinyin"] == "de"  # most real definitions
    # Same syllables, but the lower-case reading is the word; the capitalised one a surname.
    assert choose(readings["也"], "yě")["glosas"] == ["also", "too"] or choose(readings["也"], "yě")["glosas"] == ["also; too"]
