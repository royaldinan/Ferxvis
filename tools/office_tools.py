"""
Office tools - Word dan Excel
"""

import os
from pathlib import Path
from config import HOME_DIR


def _resolve(path: str) -> Path:
    rp = (path or "").strip()
    if os.path.isabs(rp):
        return Path(rp).resolve()
    return (Path(HOME_DIR) / rp).resolve()


def create_word_document(relative_path: str, title: str, paragraphs: list) -> str:
    try:
        from docx import Document
        from docx.shared import Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        target = _resolve(relative_path)
        if not target.suffix:
            target = target.with_suffix(".docx")
        target.parent.mkdir(parents=True, exist_ok=True)

        doc = Document()
        h = doc.add_heading(title, 0)
        h.alignment = WD_ALIGN_PARAGRAPH.CENTER

        for para in paragraphs:
            doc.add_paragraph(para)

        doc.save(str(target))
        return f"Dokumen Word '{target.name}' berhasil dibuat di {target.parent}."
    except ImportError:
        return "ERROR: python-docx belum terinstall. Jalankan: pip install python-docx"
    except Exception as e:
        return f"ERROR: {e}"


def read_word_document(relative_path: str) -> str:
    try:
        from docx import Document

        target = _resolve(relative_path)
        if not target.exists():
            return f"File '{relative_path}' tidak ditemukan."

        doc = Document(str(target))
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        return text if text else "(Dokumen kosong)"
    except ImportError:
        return "ERROR: python-docx belum terinstall."
    except Exception as e:
        return f"ERROR: {e}"


def create_excel_sheet(relative_path: str, headers: list, rows: list) -> str:
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment

        target = _resolve(relative_path)
        if not target.suffix:
            target = target.with_suffix(".xlsx")
        target.parent.mkdir(parents=True, exist_ok=True)

        wb = openpyxl.Workbook()
        ws = wb.active

        # Header styling
        header_fill = PatternFill("solid", fgColor="2563EB")
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=h)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
            ws.column_dimensions[cell.column_letter].width = max(len(str(h)) + 4, 12)

        for r_idx, row in enumerate(rows, 2):
            for c_idx, val in enumerate(row, 1):
                ws.cell(row=r_idx, column=c_idx, value=val)

        wb.save(str(target))
        return f"File Excel '{target.name}' berhasil dibuat di {target.parent}."
    except ImportError:
        return "ERROR: openpyxl belum terinstall. Jalankan: pip install openpyxl"
    except Exception as e:
        return f"ERROR: {e}"


def read_excel_sheet(relative_path: str) -> str:
    try:
        import openpyxl

        target = _resolve(relative_path)
        if not target.exists():
            return f"File '{relative_path}' tidak ditemukan."

        wb = openpyxl.load_workbook(str(target))
        ws = wb.active
        lines = []
        for row in ws.iter_rows(values_only=True):
            lines.append("\t".join(str(c) if c is not None else "" for c in row))
        return "\n".join(lines) if lines else "(Sheet kosong)"
    except ImportError:
        return "ERROR: openpyxl belum terinstall."
    except Exception as e:
        return f"ERROR: {e}"
