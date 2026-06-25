from pathlib import Path
from typing import List, Dict
import re


class DocumentParser:
    def parse(self, path: Path) -> List[Dict]:
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return self._parse_pdf(path)
        elif suffix == ".docx":
            return self._parse_docx(path)
        elif suffix in [".txt", ".md"]:
            return self._parse_text(path)
        return []

    def _parse_pdf(self, path: Path) -> List[Dict]:
        import pdfplumber
        chunks = []
        try:
            with pdfplumber.open(path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text() or ""
                    paragraphs = self._split_paragraphs(text)
                    for par_num, par in enumerate(paragraphs, 1):
                        if par.strip():
                            chunks.extend(self._chunk_text(par.strip(), page_num, par_num))
        except Exception as e:
            print(f"Erro ao parsear PDF {path.name}: {e}")
        return chunks

    def _parse_docx(self, path: Path) -> List[Dict]:
        from docx import Document
        chunks = []
        try:
            doc = Document(path)
            par_num = 0
            char_count = 0
            for para in doc.paragraphs:
                text = para.text.strip()
                if text:
                    par_num += 1
                    char_count += len(text)
                    page_num = max(1, char_count // 3000 + 1)
                    chunks.extend(self._chunk_text(text, page_num, par_num))
        except Exception as e:
            print(f"Erro ao parsear DOCX {path.name}: {e}")
        return chunks

    def _parse_text(self, path: Path) -> List[Dict]:
        chunks = []
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
            paragraphs = self._split_paragraphs(text)
            char_count = 0
            for par_num, par in enumerate(paragraphs, 1):
                if par.strip():
                    char_count += len(par)
                    page_num = max(1, char_count // 3000 + 1)
                    chunks.extend(self._chunk_text(par.strip(), page_num, par_num))
        except Exception as e:
            print(f"Erro ao parsear texto {path.name}: {e}")
        return chunks

    def _split_paragraphs(self, text: str) -> List[str]:
        return re.split(r'\n\s*\n', text)

    def _chunk_text(self, text: str, page: int, paragraph: int,
                    max_size: int = 600, overlap: int = 80) -> List[Dict]:
        text = text.strip()
        if not text:
            return []
        if len(text) <= max_size:
            return [{"text": text, "page": page, "paragraph": paragraph}]

        chunks = []
        sentences = re.split(r'(?<=[.!?])\s+', text)
        current = ""

        for sentence in sentences:
            if len(current) + len(sentence) + 1 <= max_size:
                current = current + " " + sentence if current else sentence
            else:
                if current:
                    chunks.append({"text": current, "page": page, "paragraph": paragraph})
                    tail = current[-overlap:] if len(current) > overlap else current
                    current = tail + " " + sentence
                else:
                    current = sentence

        if current:
            chunks.append({"text": current, "page": page, "paragraph": paragraph})

        return chunks
