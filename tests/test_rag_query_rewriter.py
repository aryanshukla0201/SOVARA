from app.rag.query_rewriter import QueryRewriter


def test_query_rewriter_normalizes_whitespace_and_case():
    rewriter = QueryRewriter()

    assert rewriter.rewrite("  What   is   Kafka?  ") == "what is kafka?"


def test_query_rewriter_returns_empty_for_blank_query():
    rewriter = QueryRewriter()

    assert rewriter.rewrite("") == ""
    assert rewriter.rewrite("   ") == ""


def test_query_rewriter_preserves_query_terms_and_punctuation():
    rewriter = QueryRewriter()

    assert rewriter.rewrite("Spring Boot, Kafka & Redis!") == (
        "spring boot, kafka & redis!"
    )


def test_query_rewriter_is_deterministic():
    rewriter = QueryRewriter()

    query = "  How   does Kafka work? "
    assert rewriter.rewrite(query) == rewriter.rewrite(query)
