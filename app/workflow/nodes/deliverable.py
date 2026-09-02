from __future__ import annotations

from app.deliverables.docx_generator import DocxGenerator


class DeliverableNode:
    def __init__(self):
        self.docx_generator = DocxGenerator()

    def generate(self, report: dict, output_path: str) -> str:
        return self.docx_generator.generate(report, output_path)
