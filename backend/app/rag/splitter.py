from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from app.config import settings


class TextSplitter:
    """Split documents into chunks suitable for embedding."""

    def __init__(self):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=["\n\n", "\n", "。", ".", "！", "!", "？", "?", " ", ""],
            length_function=len,
        )

    def split(self, documents: list[Document]) -> list[Document]:
        return self.splitter.split_documents(documents)