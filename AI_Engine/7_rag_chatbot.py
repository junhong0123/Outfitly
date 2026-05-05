"""Gemini RAG chatbot for Outfitly product and policy questions."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
POLICY_PATH = DATA_DIR / "store_policies.md"
DEFAULT_CHAT_MODEL = "gemini-2.5-flash"


@dataclass
class ChatSource:
    """Small source object returned to the website UI."""

    type: str
    id: int | None
    title: str

    def to_dict(self) -> dict[str, Any]:
        """Convert the source into JSON-safe values."""
        return {"type": self.type, "id": self.id, "title": self.title}


@dataclass
class RagDocument:
    """Small document object used by the local retriever."""

    page_content: str
    metadata: dict[str, Any]


class OutfitlyRagChatbot:
    """Load Outfitly product/policy documents and answer questions with Gemini."""

    def __init__(self) -> None:
        self._documents: list[Any] = []
        self._source_lookup: dict[str, ChatSource] = {}
        self._vectorizer = None
        self._doc_matrix = None

    def answer(self, message: str, user_id: str | None = None, top_k: int = 5) -> dict[str, Any]:
        """Answer one user message using retrieved product and policy context."""
        message = message.strip()
        if self._is_greeting(message):
            return {
                "answer": "Hi! I can help you find products, check sizes, explain shipping and returns, or suggest outfit ideas.",
                "sources": [],
                "is_fallback": False,
            }

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return self._fallback(
                "Gemini API key is not configured. Set GEMINI_API_KEY before using the AI assistant."
            )

        try:
            self._ensure_retriever()
            docs = self._retrieve_documents(message, max(1, min(top_k, 8)))
            answer = self._generate_answer(api_key, message, docs, user_id)
            return {
                "answer": answer,
                "sources": self._sources_from_docs(docs),
                "is_fallback": False,
            }
        except Exception as exc:
            return {
                "answer": self._friendly_error(exc),
                "sources": self._sources_from_docs(getattr(self, "_last_docs", [])),
                "is_fallback": True,
            }

    def _ensure_retriever(self) -> None:
        """Build a local TF-IDF retriever once without spending Gemini embedding quota."""
        if self._vectorizer is not None and self._doc_matrix is not None:
            return

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
        except Exception as exc:
            raise RuntimeError("scikit-learn is required for local RAG retrieval.") from exc

        self._documents = self._load_documents()
        if not self._documents:
            raise RuntimeError("No product or policy documents were available for RAG.")

        self._vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=20000)
        self._doc_matrix = self._vectorizer.fit_transform(doc.page_content for doc in self._documents)

    def _retrieve_documents(self, message: str, top_k: int) -> list[Any]:
        """Find relevant documents locally, avoiding Gemini embedding rate limits."""
        from sklearn.metrics.pairwise import cosine_similarity

        query_vector = self._vectorizer.transform([message])
        scores = cosine_similarity(query_vector, self._doc_matrix).ravel()
        ranked_indices = scores.argsort()[::-1]
        docs = [self._documents[index] for index in ranked_indices[:top_k] if scores[index] > 0]
        if not docs:
            docs = self._documents[:top_k]
        self._last_docs = docs
        return docs

    def _load_documents(self) -> list[Any]:
        """Create local retriever documents from SQL Server products and policy text."""
        documents: list[Any] = []
        product_load_error: str | None = None
        try:
            products = self._load_product_rows()
        except Exception as exc:
            products = []
            product_load_error = str(exc)

        for row in products:
            source = ChatSource(type="product", id=int(row["id"]), title=str(row["name"]))
            source_key = f"product:{source.id}"
            self._source_lookup[source_key] = source
            documents.append(
                RagDocument(
                    page_content=(
                        f"Product ID: {row['id']}\n"
                        f"Name: {row['name']}\n"
                        f"Category: {row['category']}\n"
                        f"Price: ${row['price']:.2f}\n"
                        f"Stock and sizes: {row['sizes']}\n"
                        f"Description: {row['description']}"
                    ),
                    metadata={"source_key": source_key},
                )
            )

        if product_load_error:
            source_key = "policy:product-database-status"
            self._source_lookup[source_key] = ChatSource(
                type="policy",
                id=None,
                title="Product database status",
            )
            documents.append(
                RagDocument(
                    page_content=(
                        "Product database status\n"
                        "The Outfitly product database could not be loaded by the AI assistant. "
                        "For exact product, stock, or size questions, ask the customer to browse the shop."
                    ),
                    metadata={"source_key": source_key},
                )
            )

        for index, section in enumerate(self._load_policy_sections(), start=1):
            title = section["title"]
            source_key = f"policy:{index}"
            self._source_lookup[source_key] = ChatSource(type="policy", id=None, title=title)
            documents.append(
                RagDocument(
                    page_content=f"{title}\n{section['content']}",
                    metadata={"source_key": source_key},
                )
            )

        return documents

    def _load_product_rows(self) -> list[dict[str, Any]]:
        """Read Products and ProductSizes from SQL Server for product-aware answers."""
        try:
            import pyodbc
        except Exception as exc:
            raise RuntimeError("pyodbc is required to load Outfitly products from SQL Server.") from exc

        connection_string = os.getenv("OUTFITLY_DB_CONNECTION") or self._default_sql_connection_string(pyodbc)
        products_query = "SELECT Id, Name, Price, Description, Category FROM Products"
        sizes_query = "SELECT ProductId, Size, Quantity FROM ProductSizes"

        with pyodbc.connect(connection_string) as connection:
            products = pd.read_sql(products_query, connection)
            sizes = pd.read_sql(sizes_query, connection)

        if products.empty:
            return []

        size_lookup: dict[int, str] = {}
        if not sizes.empty:
            for product_id, group in sizes.groupby("ProductId"):
                size_lookup[int(product_id)] = ", ".join(
                    f"{row.Size}: {int(row.Quantity)}"
                    for row in group.itertuples(index=False)
                    if int(row.Quantity) > 0
                ) or "Out of stock"

        rows: list[dict[str, Any]] = []
        for row in products.itertuples(index=False):
            rows.append(
                {
                    "id": int(row.Id),
                    "name": str(row.Name),
                    "price": float(row.Price),
                    "description": str(row.Description or "No description available."),
                    "category": str(row.Category or "Uncategorized"),
                    "sizes": size_lookup.get(int(row.Id), "Stock information unavailable"),
                }
            )
        return rows

    def _default_sql_connection_string(self, pyodbc_module: Any) -> str:
        """Create a local SQL Server connection string that works on most Windows setups."""
        drivers = list(pyodbc_module.drivers())
        # Driver 18 defaults to encrypted localdb connections, which can fail on
        # student Windows setups. Prefer Driver 17 when it is installed.
        preferred_drivers = ["ODBC Driver 17 for SQL Server", "SQL Server", "ODBC Driver 18 for SQL Server"]
        driver = next((candidate for candidate in preferred_drivers if candidate in drivers), preferred_drivers[0])
        return (
            f"DRIVER={{{driver}}};"
            "SERVER=(localdb)\\mssqllocaldb;"
            "DATABASE=Outfitly;"
            "Trusted_Connection=yes;"
            "Encrypt=no;"
            "TrustServerCertificate=yes;"
        )

    def _load_policy_sections(self) -> list[dict[str, str]]:
        """Split the store policy markdown into retrievable sections."""
        if not POLICY_PATH.exists():
            return []

        sections: list[dict[str, str]] = []
        current_title = "Outfitly Store Policies"
        current_lines: list[str] = []

        for raw_line in POLICY_PATH.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if line.startswith("## "):
                if current_lines:
                    sections.append({"title": current_title, "content": "\n".join(current_lines).strip()})
                current_title = line.removeprefix("## ").strip()
                current_lines = []
            elif line and not line.startswith("# "):
                current_lines.append(line)

        if current_lines:
            sections.append({"title": current_title, "content": "\n".join(current_lines).strip()})

        return sections

    def _generate_answer(self, api_key: str, message: str, docs: list[Any], user_id: str | None) -> str:
        """Ask Gemini to answer only from the retrieved Outfitly context."""
        from langchain_google_genai import ChatGoogleGenerativeAI

        context = "\n\n---\n\n".join(doc.page_content for doc in docs)
        model_name = os.getenv("GEMINI_MODEL", DEFAULT_CHAT_MODEL)
        llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key, temperature=0.2)
        prompt = (
            "You are Outfitly's AI shopping assistant. Answer using only the context below. "
            "Help with products, stock, sizes, prices, shipping, returns, and payment policy. "
            "If the question asks for order/account support, say this assistant cannot access personal orders yet. "
            "If the answer is not in context, say you do not have enough information and suggest browsing the shop.\n\n"
            f"User ID: {user_id or 'guest'}\n\n"
            f"Context:\n{context}\n\n"
            f"Customer question: {message}\n\n"
            "Answer in a concise, friendly style."
        )
        response = llm.invoke(prompt)
        content = getattr(response, "content", response)
        if isinstance(content, list):
            return " ".join(str(part) for part in content).strip()
        return str(content).strip()

    def _is_greeting(self, message: str) -> bool:
        """Handle short greetings without calling any external AI service."""
        normalized = message.lower().strip(" .,!?\t\r\n")
        return normalized in {"hi", "hello", "hey", "yo", "你好", "嗨"}

    def _friendly_error(self, exc: Exception) -> str:
        """Hide provider stack traces and return a customer-safe message."""
        text = str(exc).lower()
        if "429" in text or "quota" in text or "resource_exhausted" in text:
            return (
                "The AI service quota is busy right now. Please wait a short moment and try again. "
                "I have already switched product search to local retrieval, so this is only from Gemini answer generation."
            )
        return "The AI assistant is temporarily unavailable. Please try again after the AI service is running."

    def _sources_from_docs(self, docs: list[Any]) -> list[dict[str, Any]]:
        """Return unique sources used by the answer."""
        seen: set[str] = set()
        sources: list[dict[str, Any]] = []
        for doc in docs:
            source_key = doc.metadata.get("source_key", "")
            if not source_key or source_key in seen:
                continue
            seen.add(source_key)
            source = self._source_lookup.get(source_key)
            if source:
                sources.append(source.to_dict())
        return sources

    def _fallback(self, message: str) -> dict[str, Any]:
        """Return a graceful chatbot fallback response."""
        return {"answer": message, "sources": [], "is_fallback": True}


_chatbot: OutfitlyRagChatbot | None = None


def answer_chat(message: str, user_id: str | None = None, top_k: int = 5) -> dict[str, Any]:
    """Module-level helper used by the FastAPI service."""
    global _chatbot
    if _chatbot is None:
        _chatbot = OutfitlyRagChatbot()
    return _chatbot.answer(message, user_id=user_id, top_k=top_k)
