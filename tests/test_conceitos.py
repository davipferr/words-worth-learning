from pipeline.conceitos import Concept, Word, advantage, align, choose, false_friend_pairs, reverse_heads


def word(lang, palavra, rank, share=0.01, heads=(), first=(), pos=("noun",), **kw):
    return Word(lang=lang, palavra=palavra, rank=rank, share=share, pos=set(pos), heads=set(heads) | set(first), first_heads=set(first), first_head=next(iter(first), None), **kw)


def test_choose_prefers_first_definition_then_frequency():
    vocab = {
        "faire": word("fr", "faire", 5, heads=["go"], first=["do", "make"], pos=["verb"]),
        "aller": word("fr", "aller", 9, first=["go"], pos=["verb"]),
        "vache": word("fr", "vache", 900, first=["cow"]),
    }
    c = Concept("go", "verb", 23, ["fr:faire", "fr:aller"])
    assert choose(c, "fr", vocab, {}) == (vocab["aller"], True)
    # A table entry whose definitions never name the concept: only from the top two.
    dog = Concept("dog", "noun", 300, ["fr:chien", "fr:thon", "fr:vache"])
    assert choose(dog, "fr", vocab, {}) == (None, False)


def test_reverse_lookup_when_the_table_has_nothing():
    vocab = {"chien": word("fr", "chien", 400, first=["dog"])}
    c = Concept("dog", "noun", 300, [])
    assert choose(c, "fr", vocab, reverse_heads(vocab)) == (vocab["chien"], True)


def vocabs():
    v = {
        "en": {"house": word("en", "house", 1, heads=["house"])},
        "pt": {"casa": word("pt", "casa", 1, first=["house"])},
        "es": {"casa": word("es", "casa", 1, share=0.10, first=["house"])},
        "fr": {"maison": word("fr", "maison", 1, share=0.10, first=["house"])},
        "it": {"casa": word("it", "casa", 1, share=0.20, first=["house"])},
        "de": {"Haus": word("de", "Haus", 1, share=0.30, first=["house"])},
    }
    return v


def test_align_and_advantage():
    v = vocabs()
    rows = align([Concept("house", "noun", 1, ["pt:casa", "es:casa", "fr:maison", "it:casa", "de:Haus"])], v)
    assert [rows[0][c].palavra for c in ["pt", "es", "fr", "it", "de"]] == ["casa", "casa", "maison", "casa", "Haus"]
    adv = {(r["origem"], r["alvo"]): r for r in advantage(rows, v)}
    assert adv[("pt", "it")]["reconhecivel"] == 0.20 and adv[("pt", "it")]["igual"] == 0.20
    assert adv[("pt", "fr")]["reconhecivel"] == 0 and adv[("pt", "fr")]["alinhada"] == 0.10
    assert adv[("en", "de")]["parecida"] == 0.30  # house / Haus


def test_false_friend_pairs_skip_linked_words():
    v = {
        "es": {"burro": word("es", "burro", 900, first=["donkey"]), "casa": word("es", "casa", 1, first=["house"])},
        "it": {"burro": word("it", "burro", 2000, first=["butter"]), "casa": word("it", "casa", 1, first=["home"])},
    }
    out = false_friend_pairs(v, linked={("es", "casa", "it", "casa")})
    assert [(r["palavra_a"], r["lingua_a"], r["lingua_b"]) for r in out] == [("burro", "es", "it")]
