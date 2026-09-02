from app.workflow.nodes.document_node import DocumentNode


node = DocumentNode()

results = node.run(
    pdf_path=r"C:\Users\ARYAN\OneDrive\Desktop\AI\GEN-AI\langchain models\data\Gaurav's_resume_AI_ML_research.pdf",
    user_query="What is the main purpose of this document?",
    file_id="test_file",
)

print(f"\nEvidence returned: {len(results)}")

for item in results:
    print("\n" + "=" * 60)
    print("PAGE:", item.page_number)
    print("CHUNK:", item.chunk_id)
    print("SCORE:", item.relevance_score)
    print("METHOD:", item.retrieval_method)
    print("TEXT:")
    print(item.text[:500])