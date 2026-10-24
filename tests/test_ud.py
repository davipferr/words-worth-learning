from pipeline.ud import parse


def test_parse_counts_form_lemma_pairs_and_skips_ranges():
    conllu = [
        "# sent_id = 1\n",
        "1-2\tdel\t_\t_\t_\t_\t_\t_\t_\t_\n",
        "1\tde\tde\tADP\t_\t_\t_\t_\t_\t_\n",
        "2\tel\tel\tDET\t_\t_\t_\t_\t_\t_\n",
        "3\tAnda\tandar\tVERB\t_\t_\t_\t_\t_\t_\n",
        "3.1\tx\tx\tX\t_\t_\t_\t_\t_\t_\n",
        "4\t.\t.\tPUNCT\t_\t_\t_\t_\t_\t_\n",
        "\n",
    ]
    counts = parse(conllu)
    assert counts == {("de", "de", "ADP"): 1, ("el", "el", "DET"): 1, ("anda", "andar", "VERB"): 1}
