from app.rag.chunking import RAGChunker


def test_chunker_preserves_overlap():
    chunker = RAGChunker(chunk_size=5, overlap=2)

    chunks = chunker.chunk(
        "one two three four five six seven eight"
    )

    assert [chunk.text for chunk in chunks] == [
        "one two three four five",
        "four five six seven eight",
    ]


def test_chunker_preserves_metadata():
    chunker = RAGChunker(chunk_size=5, overlap=2)

    chunks = chunker.chunk(
        "one two three four five",
        source_file_id="doc1",
        source_filename="manual.pdf",
        page_number=3,
        section="maintenance",
        ocr_used=True,
    )

    assert len(chunks) == 1

    chunk = chunks[0]

    assert chunk.chunk_id == "chunk_00001"
    assert chunk.source_file_id == "doc1"
    assert chunk.source_filename == "manual.pdf"
    assert chunk.page_number == 3
    assert chunk.section == "maintenance"
    assert chunk.ocr_used is True


def test_chunker_empty_text():
    assert RAGChunker().chunk("   ") == []


def test_chunker_rejects_invalid_configuration():
    for chunk_size, overlap in [
        (0, 0),
        (-1, 0),
        (10, -1),
        (10, 10),
        (10, 11),
    ]:
        try:
            RAGChunker(
                chunk_size=chunk_size,
                overlap=overlap,
            )
        except ValueError:
            pass
        else:
            raise AssertionError(
                f"Expected ValueError for "
                f"chunk_size={chunk_size}, overlap={overlap}"
            )


def test_chunk_ids_are_deterministic():
    chunker = RAGChunker(chunk_size=3, overlap=1)

    first = chunker.chunk("one two three four five")
    second = chunker.chunk("one two three four five")

    assert [chunk.chunk_id for chunk in first] == [
        chunk.chunk_id for chunk in second
    ]
