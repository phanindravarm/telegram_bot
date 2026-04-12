import json
import math
import re
import time
import requests

from bot import send_message, get_file_url
from db import _connect
from commands.summarize import fetch_page_text
from commands.document_utils import extract_text_from_file
from commands.ask_config import MODEL, OLLAMA_BASE_URL
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi


model = SentenceTransformer('all-MiniLM-L6-v2')

def call_local_embedding(text):
    """Generate embedding using sentence_transformers (384-dim vector)."""
    embedding = model.encode(text)
    return embedding.tolist() 


def chunk_text(text, chunk_size=500, overlap=50):
    """Split text into chunks with overlap. Returns list of strings."""
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
        if start >= len(text):
            break
    return chunks


def cosine_similarity(a, b):
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _ingest_text(chat_id, text, source):
    """Chunk, embed, and store text in SQLite. Returns chunk count."""
    chunks = chunk_text(text)
    if not chunks:
        return 0

    ingested_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    conn = _connect()
    for i, chunk in enumerate(chunks):
        embedding =  call_local_embedding(chunk)
        conn.execute(
            "INSERT INTO rag_chunks (chat_id, source, chunk_index, content, embedding, ingested_at) VALUES (?, ?, ?, ?, ?, ?)",
            (chat_id, source, i, chunk, json.dumps(embedding), ingested_at),
        )
    conn.commit()
    conn.close()
    return len(chunks)


def tokenize(text):
    """Lowercase + simple regex word tokenization."""
    return re.findall(r"\w+", (text or "").lower())


def _search_hybrid(chat_id, question, query_embedding, top_k=5, candidate_k=20, rrf_k=60):
    """Retrieve top-k chunks using hybrid BM25 + semantic search fused with RRF."""
    conn = _connect()
    rows = conn.execute(
        "SELECT content, embedding FROM rag_chunks WHERE chat_id = ?",
        (chat_id,),
    ).fetchall()
    conn.close()

    if not rows:
        return []

    contents = [content for content, _ in rows]

    # Semantic ranking
    sem_scored = []
    for i, (_, emb_json) in enumerate(rows):
        emb = json.loads(emb_json)
        sem_scored.append((i, cosine_similarity(query_embedding, emb)))
    sem_scored.sort(key=lambda x: x[1], reverse=True)
    sem_ranks = {idx: rank for rank, (idx, _) in enumerate(sem_scored[:candidate_k])}

    # BM25 ranking
    corpus = [tokenize(c) for c in contents]
    bm25 = BM25Okapi(corpus)
    bm25_scores = bm25.get_scores(tokenize(question))
    bm25_scored = sorted(enumerate(bm25_scores), key=lambda x: x[1], reverse=True)
    bm25_ranks = {idx: rank for rank, (idx, _) in enumerate(bm25_scored[:candidate_k])}

    # Reciprocal Rank Fusion
    fused = {}
    for idx, rank in sem_ranks.items():
        fused[idx] = fused.get(idx, 0.0) + 1.0 / (rrf_k + rank)
    for idx, rank in bm25_ranks.items():
        fused[idx] = fused.get(idx, 0.0) + 1.0 / (rrf_k + rank)

    ordered = sorted(fused.items(), key=lambda x: x[1], reverse=True)
    return [contents[idx] for idx, _ in ordered[:top_k]]


def _count_chunks(chat_id):
    """Count total chunks for a user."""
    conn = _connect()
    count = conn.execute(
        "SELECT COUNT(*) FROM rag_chunks WHERE chat_id = ?", (chat_id,)
    ).fetchone()[0]
    conn.close()
    return count


def handle_ingest(chat_id, args):
    """Fetch URL, chunk, embed, and store in SQLite."""
    url = args.strip()
    if not url:
        send_message(chat_id, "Usage: /ingest <url>")
        return

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        text = fetch_page_text(url)
    except Exception:
        send_message(chat_id, "Could not fetch that URL. Please check and try again.")
        return

    if text.startswith("Error fetching page:") or len(text) < 50:
        send_message(chat_id, "Could not extract enough text from that page.")
        return

    try:
        count = _ingest_text(chat_id, text, url)
        send_message(chat_id, f"Indexed {count} chunks from {url}")
    except Exception as e:
        print(f"Ingest error: {e}")
        send_message(chat_id, "Failed to index the page. Try again later.")


def handle_upload_document(chat_id, file_id, file_name, mime_type):
    """Extract text from uploaded document, chunk, embed, and store."""
    try:
        file_url = get_file_url(file_id)
        resp = requests.get(file_url, timeout=30)
        resp.raise_for_status()
        file_bytes = resp.content
    except Exception:
        send_message(chat_id, "Could not download the file. Please try again.")
        return

    text, error = extract_text_from_file(file_bytes, mime_type, file_name)
    if error:
        send_message(chat_id, error)
        return

    source = file_name or "uploaded_document"
    try:
        count = _ingest_text(chat_id, text, source)
        send_message(chat_id, f"Indexed {count} chunks from {source}")
    except Exception as e:
        print(f"Upload ingest error: {e}")
        send_message(chat_id, "Failed to index the document. Try again later.")


def handle_query(chat_id, args, silent=False):
    """Embed question, retrieve top-5 chunks, call Ollama with context."""
    question = args.strip()
    if not question:
        msg = "Usage: /query <question>"
        if silent:
            return msg
        send_message(chat_id, msg)
        return

    if _count_chunks(chat_id) == 0:
        msg = "No documents indexed yet. Use /ingest <url> or /upload a document first."
        if silent:
            return msg
        send_message(chat_id, msg)
        return

    try:
        query_embedding =  call_local_embedding(question)
        chunks = _search_hybrid(chat_id, question, query_embedding, top_k=5)
    except Exception as e:
        print(f"Query embedding/search error: {e}")
        msg = "Failed to search the knowledge base. Try again later."
        if silent:
            return msg
        send_message(chat_id, msg)
        return

    if not chunks:
        msg = "No relevant content found in your knowledge base."
        if silent:
            return msg
        send_message(chat_id, msg)
        return

    context = "\n\n---\n\n".join(chunks)
    prompt = (
        "Answer the following question using ONLY the provided context. "
        "If the context doesn't contain enough information to answer, say so.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}"
    )

    try:
        payload = {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        r = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload,
            timeout=60,
        )
        r.raise_for_status()
        answer = r.json()["message"]["content"]
        if silent:
            return answer
        send_message(chat_id, answer)
    except Exception as e:
        print(f"Query generation error: {e}")
        msg = "Could not generate an answer. Try again later."
        if silent:
            return msg
        send_message(chat_id, msg)


def handle_sources(chat_id, args, silent=False):
    """List unique sources with chunk counts."""
    conn = _connect()
    rows = conn.execute(
        "SELECT source, COUNT(*) FROM rag_chunks WHERE chat_id = ? GROUP BY source ORDER BY source",
        (chat_id,),
    ).fetchall()
    conn.close()

    if not rows:
        msg = "No documents indexed yet."
        if silent:
            return msg
        send_message(chat_id, msg)
        return

    lines = ["Your indexed sources:\n"]
    for source, count in rows:
        lines.append(f"- {source} ({count} chunks)")

    result = "\n".join(lines)
    if silent:
        return result
    send_message(chat_id, result)


def handle_forget(chat_id, args):
    """Delete all chunks matching a source name."""
    source = args.strip()
    if not source:
        send_message(chat_id, "Usage: /forget <source>")
        return

    conn = _connect()
    cursor = conn.execute(
        "DELETE FROM rag_chunks WHERE chat_id = ? AND source = ?",
        (chat_id, source),
    )
    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    if deleted == 0:
        send_message(chat_id, f"No chunks found for source: {source}")
    else:
        send_message(chat_id, f"Deleted {deleted} chunks from {source}")
