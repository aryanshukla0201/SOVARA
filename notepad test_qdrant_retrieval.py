from app.tools.documents.retriever import DocumentRetriever
from app.tools.documents.pdf_parser import PDFParser

pdf = r"data\uploads\ocr_test_scanned.pdf"

parsed = PDFParser.extract_text(pdf)

chunks = []

for page in parsed["pages"]:
    chunks.append(
        {
            "page_number": page["page_number"],
            "chunk_id": f"page_{page['page_number']}_chunk_1",
            "text": page["text"],
            "ocr_used": page["ocr_used"],
        }
    )

retriever = DocumentRetriever()

results = retriever.retrieve(
    chunks=chunks,
    query="four stroke engine power cycle",
    file_id="ocr_test",
    filename="ocr_test_scanned.pdf",
)

print(
    [
        {
            "id": e.evidence_id,
            "score": e.relevance_score,
            "method": e.retrieval_method,
        }
        for e in results
    ]
)