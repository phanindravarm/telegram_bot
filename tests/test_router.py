from unittest.mock import patch, MagicMock


def test_average_vectors():
    from router import _average_vectors

    result = _average_vectors([[1.0, 2.0, 3.0], [3.0, 4.0, 5.0]])
    assert result == [2.0, 3.0, 4.0]


def test_average_vectors_empty():
    from router import _average_vectors

    assert _average_vectors([]) == []


def test_average_vectors_single():
    from router import _average_vectors

    assert _average_vectors([[1.0, 2.0]]) == [1.0, 2.0]


@patch("router.cosine_similarity")
@patch("router.call_local_embedding")
def test_classify_intent_clear_match(mock_embed, mock_cosine):
    mock_embed.return_value = [0.1, 0.2, 0.3]

    def fake_cosine(a, b):
        return scores.pop(0)

    from router import INTENT_EMBEDDINGS
    intent_keys = list(INTENT_EMBEDDINGS.keys())

    scores_map = {k: 0.2 for k in intent_keys}
    scores_map["/weather"] = 0.85

    scores = [scores_map[k] for k in intent_keys]
    mock_cosine.side_effect = fake_cosine

    from router import classify_intent
    result = classify_intent("what's the weather in London")

    assert result is not None
    intent, confidence, args = result
    assert intent == "/weather"
    assert confidence == 0.85
    assert args == "what's the weather in London"


@patch("router.cosine_similarity")
@patch("router.call_local_embedding")
def test_classify_intent_below_threshold(mock_embed, mock_cosine):
    mock_embed.return_value = [0.1, 0.2, 0.3]
    mock_cosine.return_value = 0.3

    from router import classify_intent
    result = classify_intent("asdfghjkl random gibberish")

    assert result is None


@patch("router.cosine_similarity")
@patch("router.call_local_embedding")
def test_classify_intent_ambiguous(mock_embed, mock_cosine):
    mock_embed.return_value = [0.1, 0.2, 0.3]

    from router import INTENT_EMBEDDINGS
    intent_keys = list(INTENT_EMBEDDINGS.keys())

    scores_map = {k: 0.2 for k in intent_keys}
    scores_map[intent_keys[0]] = 0.70
    scores_map[intent_keys[1]] = 0.68 

    scores = [scores_map[k] for k in intent_keys]
    mock_cosine.side_effect = lambda a, b: scores.pop(0)

    from router import classify_intent
    result = classify_intent("ambiguous query")

    assert result is None


@patch("router.cosine_similarity")
@patch("router.call_local_embedding")
def test_classify_intent_empty_text(mock_embed, mock_cosine):
    from router import classify_intent
    assert classify_intent("") is None
    assert classify_intent("   ") is None
    mock_embed.assert_not_called()


def test_meta_commands_excluded():
    from router import INTENT_EXAMPLES
    excluded = ["/start", "/help", "/clear", "/sources", "/forget"]
    for cmd in excluded:
        assert cmd not in INTENT_EXAMPLES, f"{cmd} should be excluded from INTENT_EXAMPLES"
