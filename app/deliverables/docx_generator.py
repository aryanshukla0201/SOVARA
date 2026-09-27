from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from docx import Document


class DocxGenerator:
    @staticmethod
    def _to_text(value: Any) -> str:
        if value is None:
            return ""

        if isinstance(value, str):
            return value

        if isinstance(value, (dict, list)):
            return json.dumps(
                value,
                indent=2,
                ensure_ascii=False,
                default=str,
            )

        return str(value)

    @classmethod
    def _add_section_content(
        cls,
        document: Document,
        content,
        level: int = 0,
    ) -> None:
        if content is None:
            return

        if isinstance(content, str):
            if content.strip():
                for paragraph in content.split("\n\n"):
                    if paragraph.strip():
                        document.add_paragraph(
                            paragraph.strip()
                        )
            return

        if isinstance(content, dict):
            for key, value in content.items():
                if value in (None, "", [], {}):
                    continue

                label = str(key).replace(
                    "_",
                    " ",
                ).title()

                if isinstance(value, (dict, list)):
                    paragraph = document.add_paragraph()
                    run = paragraph.add_run(
                        f"{label}:"
                    )
                    run.bold = True

                    cls._add_section_content(
                        document,
                        value,
                        level + 1,
                    )
                else:
                    paragraph = document.add_paragraph()
                    run = paragraph.add_run(
                        f"{label}: "
                    )
                    run.bold = True
                    paragraph.add_run(
                        cls._to_text(value)
                    )
            return

        if isinstance(content, list):
            if not content:
                return

            for item in content:
                if isinstance(item, dict):
                    lines = []

                    for key, value in item.items():
                        if value in (
                            None,
                            "",
                            [],
                            {},
                        ):
                            continue

                        label = str(key).replace(
                            "_",
                            " ",
                        ).title()

                        lines.append(
                            f"{label}: "
                            f"{cls._to_text(value)}"
                        )

                    if lines:
                        paragraph = document.add_paragraph(
                            style="List Bullet"
                        )
                        paragraph.add_run(
                            "\n".join(lines)
                        )
                elif isinstance(item, list):
                    cls._add_section_content(
                        document,
                        item,
                        level + 1,
                    )
                else:
                    document.add_paragraph(
                        f"• {cls._to_text(item)}"
                    )
            return

        document.add_paragraph(
            cls._to_text(content)
        )

    @classmethod
    def _add_section_content(
        cls,
        document,
        content,
    ) -> None:
        if content is None:
            return

        if isinstance(content, str):
            if content.strip():
                for line in content.splitlines():
                    line = line.strip()

                    if line:
                        document.add_paragraph(
                            line
                        )
            return

        if isinstance(
            content,
            (int, float, bool),
        ):
            document.add_paragraph(
                str(content)
            )
            return

        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    for key, value in item.items():
                        document.add_paragraph(
                            f"{key}:"
                        )

                        cls._add_section_content(
                            document,
                            value,
                        )
                else:
                    document.add_paragraph(
                        cls._to_text(item),
                        style="List Bullet",
                    )
            return

        if isinstance(content, dict):
            for key, value in content.items():
                # Preserve machine-readable field names exactly.
                # This is important for telemetry, evidence metadata,
                # verification fields, and other structured report data.
                document.add_heading(
                    str(key),
                    level=3,
                )

                cls._add_section_content(
                    document,
                    value,
                )
            return

        document.add_paragraph(
            cls._to_text(content)
        )

    def generate(
        self,
        report: dict,
        output_path,
    ) -> str:
        document = Document()

        document.add_heading(
            report.get(
                "title",
                "SOVARA ANALYSIS REPORT",
            ),
            level=1,
        )

        section_numbers = {
            "executive_summary":
                "1 Executive Summary",
            "key_findings":
                "2 Key Findings",
            "detailed_analysis":
                "3 Detailed Analysis",
            "supporting_evidence":
                "4 Supporting Evidence",
            "verification":
                "5 Verification",
            "conclusion":
                "6 Conclusion",
        }

        for (
            section_key,
            section_content,
        ) in report.get(
            "sections",
            {},
        ).items():

            document.add_heading(
                section_numbers.get(
                    section_key,
                    str(section_key)
                    .replace("_", " ")
                    .title(),
                ),
                level=2,
            )

            self._add_section_content(
                document,
                section_content,
            )

        appendix = report.get(
            "appendix"
        )

        if appendix:
            document.add_heading(
                "Appendix",
                level=2,
            )

            appendix_numbers = {
                "evidence_registry":
                    "A. Evidence Registry",
                "execution_telemetry":
                    "B. Execution & Sovereignty Telemetry",
                "generated_artifacts":
                    "C. Generated Artifacts",
            }

            for (
                appendix_key,
                appendix_content,
            ) in appendix.items():

                document.add_heading(
                    appendix_numbers.get(
                        appendix_key,
                        str(appendix_key)
                        .replace("_", " ")
                        .title(),
                    ),
                    level=3,
                )

                self._add_section_content(
                    document,
                    appendix_content,
                )

        out = Path(output_path)

        out.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        document.save(
            str(out)
        )

        return str(out)
