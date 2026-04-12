from commands.rag import call_local_embedding, cosine_similarity

INTENT_EXAMPLES = {
    "/weather": [
        "what's the weather",
        "is it raining",
        "temperature in NYC",
        "how's the weather today",
        "weather forecast",
        "is it cold outside",
        "will it rain tomorrow",
    ],
    "/joke": [
        "tell me a joke",
        "make me laugh",
        "say something funny",
        "got any jokes",
        "I need a laugh",
    ],
    "/time": [
        "what time is it",
        "current time",
        "what's the time now",
        "tell me the time",
        "time right now",
    ],
    "/worldtime": [
        "time in Tokyo",
        "world clock",
        "what time is it in London",
        "current time in Paris",
        "time zone for New York",
        "time across the world",
    ],
    "/remind": [
        "remind me in 5 minutes",
        "set a reminder",
        "remind me to do something",
        "create a reminder",
        "alert me in 10 minutes",
        "don't let me forget",
    ],
    "/ask": [
        "what is quantum computing",
        "explain machine learning",
        "how does photosynthesis work",
        "tell me about black holes",
        "what does AI mean",
        "explain the theory of relativity",
    ],
    "/summarize": [
        "summarize this article",
        "tldr of this website",
        "give me a summary of this page",
        "summarize this link",
        "what does this article say",
    ],
    "/ingest": [
        "index this page",
        "save to knowledge base",
        "add this url to my knowledge base",
        "ingest this webpage",
        "store this page for later",
    ],
    "/query": [
        "search my documents",
        "find in my knowledge base",
        "query my indexed content",
        "what do my documents say about",
        "look up in my knowledge base",
    ],
}


def _average_vectors(vectors):
    """Average a list of vectors into a single vector."""
    if not vectors:
        return []
    dim = len(vectors[0])
    avg = [0.0] * dim
    for v in vectors:
        for i in range(dim):
            avg[i] += v[i]
    for i in range(dim):
        avg[i] /= len(vectors)
    return avg


INTENT_EMBEDDINGS = {}


def _build_intent_embeddings():
    for intent, examples in INTENT_EXAMPLES.items():
        vectors = [call_local_embedding(phrase) for phrase in examples]
        INTENT_EMBEDDINGS[intent] = _average_vectors(vectors)


_build_intent_embeddings()

CONFIDENCE_THRESHOLD = 0.45
AMBIGUITY_MARGIN = 0.05


def classify_intent(text):
    """Classify user text into an intent using cosine similarity.

    Returns (intent_name, confidence, args) or None.
    """
    if not text or not text.strip():
        return None

    user_embedding = call_local_embedding(text)

    scores = []
    for intent, intent_embedding in INTENT_EMBEDDINGS.items():
        score = cosine_similarity(user_embedding, intent_embedding)
        scores.append((score, intent))

    scores.sort(key=lambda x: x[0], reverse=True)

    if not scores:
        return None

    best_score, best_intent = scores[0]

    if best_score < CONFIDENCE_THRESHOLD:
        return None

    if len(scores) > 1:
        second_score = scores[1][0]
        if best_score - second_score < AMBIGUITY_MARGIN:
            return None

    return (best_intent, best_score, text)
