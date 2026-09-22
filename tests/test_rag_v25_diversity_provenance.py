from app.rag.diversity import EvidenceDiversity
from app.rag.compression import ContextCompressor
from app.rag.citations import CitationBuilder
from app.state.evidence import EvidenceRecord


def test_diversity_removes_duplicate_chunk_and_text():
    selector = EvidenceDiversity()
    candidates = [
        {
            "evidence_id": "a",
            "source_file_id": "f",
            "chunk_id": "c1",
            "content": "same text",
            "rerank_score": 0.9,
        },
        {
            "evidence_id": "b",
            "source_file_id": "f",
            "chunk_id": "c2",
            "content": "same text",
            "rerank_score": 0.8,
        },
        {
            "evidence_id": "c",
            "source_file_id": "f",
            "chunk_id": "c3",
            "content": "different",
            "rerank_score": 0.7,
        },
    ]
    result = selector.select(candidates, 5)
    assert [item["evidence_id"] for item in result] == ["a", "c"]


def test_compression_is_deterministic():
    compressor = ContextCompressor(chars_per_token=4)
    assert compressor.compress_text("abcdefghij", 1) == "a..."


def test_provenance_and_citation_fields_are_preserved():
    evidence = EvidenceRecord(
        evidence_id="e1",
        source_file_id="f1",
        source_filename="report.pdf",
        document_id="doc1",
        page_number=3,
        section="Results",
        chunk_id="chunk7",
        text="evidence",
        retrieval_score=0.91,
        rerank_score=0.88,
        retrieval_method="hybrid",
        citation_id="citation:e1",
        provenance={"source_file_id": "f1", "chunk_id": "chunk7"},
    )
    citations = CitationBuilder.build([evidence])
    assert citations == [
        {
            "citation_id": "citation:e1",
            "source_file_id": "f1",
            "source_filename": "report.pdf",
            "document_id": "doc1",
            "chunk_id": "chunk7",
            "page_number": 3,
            "section": "Results",
            "evidence_id": "e1",
        }
    ]
