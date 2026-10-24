from pipeline.text import fold, is_word, similarity, tokenize


def test_tokenize_matches_frequency_lists():
    # English keeps the apostrophe on the right, French/Italian on the left.
    assert tokenize("Don't stop!", "right") == ["don", "'t", "stop"]
    assert tokenize("C’est l'homme", "left") == ["c'", "est", "l'", "homme"]
    assert tokenize("¿Qué hora es? 3 horas.") == ["qué", "hora", "es", "horas"]


def test_is_word_rejects_digits_and_punctuation():
    assert is_word("estoy") and is_word("c'") and is_word("straße")
    assert not is_word("3d") and not is_word("--") and not is_word("'")


def test_fold_and_similarity():
    assert fold("Información") == "informacion"
    assert fold("Straße") == "strasse"
    assert similarity("casa", "casa") == 1
    assert similarity("noche", "noite") == 0.6
