import pytest

from fintechagent.text import chunk_text, is_stop_request


def test_short_text_is_single_chunk():
    assert chunk_text("Hello there.") == ["Hello there."]


def test_empty_text_has_no_chunks():
    assert chunk_text("   ") == []


@pytest.mark.parametrize("length", [499, 500, 501, 998, 1000, 1500, 2345])
def test_chunks_respect_limit_and_preserve_words(length):
    words = ("word " * length)[:length].strip()
    chunks = chunk_text(words, 500)
    assert all(0 < len(c) <= 500 for c in chunks)
    assert " ".join(chunks).split() == words.split()


def test_exact_multiple_does_not_produce_empty_chunk():
    # Regression: the original loop sent an empty string to TTS here.
    chunks = chunk_text("a" * 1000, 500)
    assert chunks == ["a" * 500, "a" * 500]


def test_prefers_sentence_boundaries():
    text = "First sentence is here. Second one follows! Third?"
    assert chunk_text(text, 30) == ["First sentence is here.", "Second one follows! Third?"]


def test_invalid_limit():
    with pytest.raises(ValueError):
        chunk_text("x", 0)


@pytest.mark.parametrize(
    "utterance", ["stop", "Stop.", "STOP please", "Okay, close it", "bye!", "Goodbye"]
)
def test_stop_requests(utterance):
    assert is_stop_request(utterance)


@pytest.mark.parametrize(
    "utterance", ["Is it unstoppable?", "Tell me about closed accounts", "", "What fees apply?"]
)
def test_non_stop_requests(utterance):
    assert not is_stop_request(utterance)
