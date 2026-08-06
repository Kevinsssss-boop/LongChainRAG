from langchain_community.document_loaders import PyPDFLoader, TextLoader, CSVLoader
from langchain_core.documents import Document
from typing import List


class DocumentLoader:
    """Load documents from various file formats."""

    def load(self, file_path: str, file_type: str) -> List[Document]:
        if file_type == "pdf":
            return self._load_pdf(file_path)
        elif file_type == "csv":
            return self._load_csv(file_path)
        else:  # txt, md
            return self._load_text(file_path)

    def _load_pdf(self, file_path: str) -> List[Document]:
        loader = PyPDFLoader(file_path)
        return loader.load()

    def _load_text(self, file_path: str) -> List[Document]:
        loader = TextLoader(file_path, encoding="utf-8")
        return loader.load()

    def _load_csv(self, file_path: str) -> List[Document]:
        loader = CSVLoader(file_path, encoding="utf-8")
        return loader.load()