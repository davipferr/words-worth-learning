from pipeline.cognates import classify, false_friends, gloss_heads, heads_overlap, same_origin


def w(lang, word, anc=(), cog=()):
    return lang, word, set(anc), set(cog)


def test_gloss_heads_keeps_short_translation_pieces():
    assert gloss_heads("(formal) dog, hound") == {"dog", "hound"}
    assert gloss_heads("to eat; to have lunch") == {"eat", "have lunch"}
    assert gloss_heads("A wheeled vehicle that moves independently, with at least three wheels") == set()


def test_classes():
    assert classify(w("es", "casa"), w("it", "casa")) == ("igual", 1.0)
    assert classify(w("es", "nación"), w("pt", "nação"))[0] == "parecida"
    assert classify(w("de", "Haus"), w("en", "house"))[0] == "parecida"
    assert classify(w("es", "hijo", ["la:filius"]), w("pt", "filho", ["la:filius"]))[0] == "mesma origem"
    assert classify(w("es", "perro"), w("it", "cane"))[0] == "diferente"


def test_remote_ancestors_do_not_count():
    # A shared Proto-Indo-European root says nothing useful to a learner.
    assert not same_origin(w("en", "two", ["ine-pro:dwoh1"]), w("es", "dos", ["ine-pro:dwoh1"]))
    assert same_origin(w("es", "perro", cog=["pt:cao"]), w("pt", "cão"))


def test_false_friends_rules():
    # burro: donkey (es) vs butter (it).
    assert false_friends("burro", {"donkey", "ass"}, {"butter"}, set(), set())
    # A meaning in common (also by prefix) is not a false friend.
    assert not false_friends("foto", {"photo"}, {"photograph"}, set(), set())
    assert heads_overlap({"photo"}, {"photograph"}) and not heads_overlap({"car"}, {"care"})
    # A loan glossed by itself, and inflections of look-alike verbs, are excluded.
    assert not false_friends("okay", {"okay"}, {"ok"}, set(), set())
    assert not false_friends("visto", {"seen"}, {"visa"}, {"ver"}, {"vedere"})
    # English lists itself as its meaning, so its side is left out of the loan check.
    assert false_friends("pain", {"pain"}, {"bread"}, set(), set(), loans={"bread"})
