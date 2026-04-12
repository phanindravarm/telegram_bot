from unittest.mock import patch, MagicMock
import json
import sqlite3
import pytest


# --- chunk_text tests ---

def test_chunk_text_empty():
    from commands.rag import chunk_text
    assert chunk_text("") == []


def test_chunk_text_short():
    from commands.rag import chunk_text
    result = chunk_text("hello", chunk_size=500, overlap=50)
    assert result == ["hello"]


def test_chunk_text_splits_with_overlap():
    from commands.rag import chunk_text
    text = "a" * 1000
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) >= 2
    assert len(chunks[0]) == 500
    assert len(chunks[1]) == 500
    assert chunks[0][-50:] == chunks[1][:50]


def test_chunk_text_custom_params():
    from commands.rag import chunk_text
    text = "a" * 100
    chunks = chunk_text(text, chunk_size=30, overlap=10)
    assert len(chunks) >= 4
    assert all(len(c) <= 30 for c in chunks)


# --- cosine_similarity tests ---

def test_cosine_similarity_identical():
    from commands.rag import cosine_similarity
    assert cosine_similarity([1, 0, 0], [1, 0, 0]) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal():
    from commands.rag import cosine_similarity
    assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)


def test_cosine_similarity_zero_vector():
    from commands.rag import cosine_similarity
    assert cosine_similarity([0, 0], [1, 1]) == 0.0


# --- handle_ingest tests ---

@patch("commands.rag.send_message")
def test_handle_ingest_no_url(mock_send):
    from commands.rag import handle_ingest
    handle_ingest(123, "")
    mock_send.assert_called_once_with(123, "Usage: /ingest <url>")


@patch("commands.rag._ingest_text", return_value=5)
@patch("commands.rag.fetch_page_text", return_value="x" * 100)
@patch("commands.rag.send_message")
def test_handle_ingest_success(mock_send, mock_fetch, mock_ingest):
    from commands.rag import handle_ingest
    handle_ingest(123, "https://example.com")
    mock_fetch.assert_called_once_with("https://example.com")
    mock_ingest.assert_called_once()
    mock_send.assert_called_once_with(123, "Indexed 5 chunks from https://example.com")


@patch("commands.rag.fetch_page_text", return_value="short")
@patch("commands.rag.send_message")
def test_handle_ingest_too_little_text(mock_send, mock_fetch):
    from commands.rag import handle_ingest
    handle_ingest(123, "https://example.com")
    mock_send.assert_called_once_with(123, "Could not extract enough text from that page.")

@patch("commands.rag._ingest_text", return_value=3)
@patch("commands.rag.fetch_page_text", return_value="x" * 100)
@patch("commands.rag.send_message")
def test_handle_no_https(mock_send, mock_fetch, mock_ingest):
    from commands.rag import handle_ingest

    handle_ingest(123, "example.com")

    mock_fetch.assert_called_with("https://example.com")
    mock_send.assert_called_once()


@patch("commands.rag.fetch_page_text", side_effect=Exception("connection error"))
@patch("commands.rag.send_message")
def test_handle_ingest_fetch_exception(mock_send, mock_fetch):
    from commands.rag import handle_ingest
    handle_ingest(123, "https://example.com")
    mock_send.assert_called_once_with(123, "Could not fetch that URL. Please check and try again.")


@patch("commands.rag._ingest_text", side_effect=Exception("db error"))
@patch("commands.rag.fetch_page_text", return_value="x" * 100)
@patch("commands.rag.send_message")
def test_handle_ingest_ingest_text_exception(mock_send, mock_fetch, mock_ingest):
    from commands.rag import handle_ingest
    handle_ingest(123, "https://example.com")
    mock_send.assert_called_once_with(123, "Failed to index the page. Try again later.")


# --- handle_query tests ---

@patch("commands.rag.send_message")
def test_handle_query_no_question(mock_send):
    from commands.rag import handle_query
    handle_query(123, "")
    mock_send.assert_called_once_with(123, "Usage: /query <question>")


@patch("commands.rag._count_chunks", return_value=0)
@patch("commands.rag.send_message")
def test_handle_query_empty_collection(mock_send, mock_count):
    from commands.rag import handle_query
    handle_query(123, "what is this?")
    mock_send.assert_called_once_with(123, "No documents indexed yet. Use /ingest <url> or /upload a document first.")


@patch("commands.rag.requests.post")
@patch("commands.rag._search_hybrid", return_value=["chunk1 text", "chunk2 text"])
@patch("commands.rag.call_local_embedding", return_value=[0.1] * 384)
@patch("commands.rag._count_chunks", return_value=3)
@patch("commands.rag.send_message")
def test_handle_query_success(mock_send, mock_count, mock_embed, mock_search, mock_post):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "message": {"role": "assistant", "content": "The answer is 42."}
    }
    mock_resp.raise_for_status = MagicMock()
    mock_post.return_value = mock_resp

    from commands.rag import handle_query
    handle_query(123, "what is the answer?")
    mock_send.assert_called_once_with(123, "The answer is 42.")


# --- handle_sources tests ---

@patch("commands.rag._connect")
@patch("commands.rag.send_message")
def test_handle_sources_empty(mock_send, mock_conn):
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = []
    mock_conn.return_value = conn

    from commands.rag import handle_sources
    handle_sources(123, "")
    mock_send.assert_called_once_with(123, "No documents indexed yet.")


@patch("commands.rag._connect")
@patch("commands.rag.send_message")
def test_handle_sources_lists(mock_send, mock_conn):
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = [
        ("https://a.com", 2),
        ("https://b.com", 1),
    ]
    mock_conn.return_value = conn

    from commands.rag import handle_sources
    handle_sources(123, "")
    text = mock_send.call_args[0][1]
    assert "https://a.com" in text
    assert "2 chunks" in text
    assert "https://b.com" in text
    assert "1 chunks" in text


# --- handle_forget tests ---

@patch("commands.rag.send_message")
def test_handle_forget_no_source(mock_send):
    from commands.rag import handle_forget
    handle_forget(123, "")
    mock_send.assert_called_once_with(123, "Usage: /forget <source>")


@patch("commands.rag._connect")
@patch("commands.rag.send_message")
def test_handle_forget_success(mock_send, mock_conn):
    conn = MagicMock()
    cursor = MagicMock()
    cursor.rowcount = 2
    conn.execute.return_value = cursor
    mock_conn.return_value = conn

    from commands.rag import handle_forget
    handle_forget(123, "https://a.com")
    mock_send.assert_called_once_with(123, "Deleted 2 chunks from https://a.com")


@patch("commands.rag._connect")
@patch("commands.rag.send_message")
def test_handle_forget_not_found(mock_send, mock_conn):
    conn = MagicMock()
    cursor = MagicMock()
    cursor.rowcount = 0
    conn.execute.return_value = cursor
    mock_conn.return_value = conn

    from commands.rag import handle_forget
    handle_forget(123, "https://a.com")
    mock_send.assert_called_once_with(123, "No chunks found for source: https://a.com")


# --- handle_query error path tests ---

@patch("commands.rag.call_local_embedding", side_effect=Exception("embed error"))
@patch("commands.rag._count_chunks", return_value=3)
@patch("commands.rag.send_message")
def test_handle_query_embedding_failure(mock_send, mock_count, mock_embed):
    from commands.rag import handle_query
    handle_query(123, "what is this?")
    mock_send.assert_called_once_with(123, "Failed to search the knowledge base. Try again later.")


@patch("commands.rag._search_hybrid", return_value=[])
@patch("commands.rag.call_local_embedding", return_value=[0.1] * 384)
@patch("commands.rag._count_chunks", return_value=3)
@patch("commands.rag.send_message")
def test_handle_query_no_relevant_chunks(mock_send, mock_count, mock_embed, mock_search):
    from commands.rag import handle_query
    handle_query(123, "what is this?")
    mock_send.assert_called_once_with(123, "No relevant content found in your knowledge base.")


@patch("commands.rag.requests.post", side_effect=Exception("API error"))
@patch("commands.rag._search_hybrid", return_value=["chunk1 text"])
@patch("commands.rag.call_local_embedding", return_value=[0.1] * 384)
@patch("commands.rag._count_chunks", return_value=3)
@patch("commands.rag.send_message")
def test_handle_query_ollama_api_failure(mock_send, mock_count, mock_embed, mock_search, mock_post):
    from commands.rag import handle_query
    handle_query(123, "what is this?")
    mock_send.assert_called_once_with(123, "Could not generate an answer. Try again later.")


# --- handle_upload_document tests ---

@patch("commands.rag.requests.get", side_effect=Exception("download error"))
@patch("commands.rag.get_file_url", return_value="https://api.telegram.org/file/bot123/doc.pdf")
@patch("commands.rag.send_message")
def test_handle_upload_document_download_failure(mock_send, mock_file_url, mock_get):
    from commands.rag import handle_upload_document
    handle_upload_document(123, "file_id_1", "doc.pdf", "application/pdf")
    mock_send.assert_called_once_with(123, "Could not download the file. Please try again.")


@patch("commands.rag.extract_text_from_file", return_value=("", "Unsupported file type."))
@patch("commands.rag.requests.get")
@patch("commands.rag.get_file_url", return_value="https://api.telegram.org/file/bot123/doc.xyz")
@patch("commands.rag.send_message")
def test_handle_upload_document_extract_error(mock_send, mock_file_url, mock_get, mock_extract):
    mock_resp = MagicMock()
    mock_resp.content = b"file bytes"
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    from commands.rag import handle_upload_document
    handle_upload_document(123, "file_id_1", "doc.xyz", "application/octet-stream")
    mock_send.assert_called_once_with(123, "Unsupported file type.")


@patch("commands.rag._ingest_text", return_value=4)
@patch("commands.rag.extract_text_from_file", return_value=("Some long text here", None))
@patch("commands.rag.requests.get")
@patch("commands.rag.get_file_url", return_value="https://api.telegram.org/file/bot123/doc.pdf")
@patch("commands.rag.send_message")
def test_handle_upload_document_success(mock_send, mock_file_url, mock_get, mock_extract, mock_ingest):
    mock_resp = MagicMock()
    mock_resp.content = b"file bytes"
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    from commands.rag import handle_upload_document
    handle_upload_document(123, "file_id_1", "report.pdf", "application/pdf")
    mock_ingest.assert_called_once_with(123, "Some long text here", "report.pdf")
    mock_send.assert_called_once_with(123, "Indexed 4 chunks from report.pdf")


@patch("commands.rag._ingest_text", side_effect=Exception("db error"))
@patch("commands.rag.extract_text_from_file", return_value=("Some long text here", None))
@patch("commands.rag.requests.get")
@patch("commands.rag.get_file_url", return_value="https://api.telegram.org/file/bot123/doc.pdf")
@patch("commands.rag.send_message")
def test_handle_upload_document_ingest_failure(mock_send, mock_file_url, mock_get, mock_extract, mock_ingest):
    mock_resp = MagicMock()
    mock_resp.content = b"file bytes"
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    from commands.rag import handle_upload_document
    handle_upload_document(123, "file_id_1", "report.pdf", "application/pdf")
    mock_send.assert_called_once_with(123, "Failed to index the document. Try again later.")


# --- tokenize tests ---

def test_tokenize_lowercases_and_strips_punctuation():
    from commands.rag import tokenize
    assert tokenize("Hello, World! BM25?") == ["hello", "world", "bm25"]


def test_tokenize_empty():
    from commands.rag import tokenize
    assert tokenize("") == []
    assert tokenize(None) == []


# --- _search_hybrid tests ---

def _make_rows(chunks, embeddings):
    return [(c, json.dumps(e)) for c, e in zip(chunks, embeddings)]


@patch("commands.rag._connect")
def test_search_hybrid_empty_corpus(mock_conn):
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = []
    mock_conn.return_value = conn

    from commands.rag import _search_hybrid
    assert _search_hybrid(123, "anything", [0.1, 0.2, 0.3]) == []


@patch("commands.rag._connect")
def test_search_hybrid_lexical_only_win(mock_conn):
    """Chunk containing a rare exact term should rank highest by BM25,
    and survive into the top result via lexical lift even when its embedding
    is unrelated to the query."""
    chunks = [
        "the quick brown fox jumps",
        "lorem ipsum dolor sit amet",
        "a unique zxqwvb identifier appears here",
    ]
    # Constant embeddings — semantic provides zero discriminating signal.
    embeddings = [[1.0, 0.0], [1.0, 0.0], [1.0, 0.0]]
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = _make_rows(chunks, embeddings)
    mock_conn.return_value = conn

    from commands.rag import _search_hybrid
    # Without BM25, the target chunk would tie semantically with everything else.
    # The lexical signal pulls it into the top-2 results.
    result = _search_hybrid(123, "zxqwvb", [1.0, 0.0], top_k=2)
    assert "a unique zxqwvb identifier appears here" in result


@patch("commands.rag._connect")
def test_search_hybrid_semantic_only_win(mock_conn):
    """Paraphrased query whose terms don't overlap any chunk → closest embedding wins."""
    chunks = [
        "alpha beta gamma",
        "delta epsilon zeta",
        "eta theta iota",
    ]
    # Chunk 1 (delta epsilon zeta) is closest to query embedding
    embeddings = [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
    ]
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = _make_rows(chunks, embeddings)
    mock_conn.return_value = conn

    from commands.rag import _search_hybrid
    # Query has no token overlap with any chunk
    result = _search_hybrid(123, "xyz unrelated query", [0.0, 1.0, 0.0], top_k=1)
    assert result == ["delta epsilon zeta"]


@patch("commands.rag._connect")
def test_search_hybrid_fusion_beats_single_winner(mock_conn):
    """A chunk that ranks well in BOTH BM25 and semantic should beat a chunk
    that is #1 in only one of them."""
    chunks = [
        "apple",        # idx 0: BM25 #1, but semantically far
        "banana",       # idx 1: BM25 last, semantically middle
        "apple fruit",  # idx 2: BM25 #2 + semantic #1 → fusion winner
    ]
    embeddings = [
        [0.0, 0.0, 1.0],  # far from query
        [0.5, 0.5, 0.0],  # middle distance
        [1.0, 0.0, 0.0],  # exact query match
    ]
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = _make_rows(chunks, embeddings)
    mock_conn.return_value = conn

    from commands.rag import _search_hybrid
    result = _search_hybrid(123, "apple", [1.0, 0.0, 0.0], top_k=1)
    assert result == ["apple fruit"]
