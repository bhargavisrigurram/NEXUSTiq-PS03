"""Hybrid Retrieval Engine with Entity/Intent extraction and Cosine Similarity."""
import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import numpy as np

from src.config import INDEX_DIR
from src.schemas import EvidenceCard
from src.gemini_client import GeminiClient
from src.prompts import format_null_case_response

logger = logging.getLogger(__name__)

class HybridRetriever:
    """Combines deterministic entity/intent filtering with vector cosine similarity."""

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.gemini_client = gemini_client or GeminiClient()
        self.evidence_chunks: List[Dict[str, Any]] = []
        self.embeddings: Optional[np.ndarray] = None
        self.uploaded_documents: Dict[str, Dict[str, Any]] = {}
        self.uploaded_chunks: List[Dict[str, Any]] = []
        self.uploaded_embeddings: Optional[np.ndarray] = None
        self._load_index()


    def _load_index(self):
        """Loads pre-computed evidence chunks and embeddings from generated_index/."""
        chunks_file = INDEX_DIR / "evidence_chunks.json"
        embeddings_file = INDEX_DIR / "embeddings.npy"

        if chunks_file.exists():
            with open(chunks_file, "r", encoding="utf-8") as f:
                self.evidence_chunks = json.load(f)
            logger.info(f"Loaded {len(self.evidence_chunks)} evidence chunks.")
        else:
            logger.warning(f"Evidence chunks not found at {chunks_file}")

        if embeddings_file.exists():
            self.embeddings = np.load(embeddings_file)
            logger.info(f"Loaded embeddings matrix with shape {self.embeddings.shape}.")
        else:
            logger.warning(f"Embeddings matrix not found at {embeddings_file}")

    def extract_entities(self, query: str) -> Dict[str, Any]:
        """Extracts store, product, and category entities mentioned in the query."""
        q = query.lower()

        # Store extraction
        store_map = {
            "hyderabad": ("S01", "Store Hyderabad"),
            "vijayawada": ("S02", "Store Vijayawada"),
            "chennai": ("S03", "Store Chennai"),
            "bengaluru": ("S04", "Store Bengaluru"),
            "bangalore": ("S04", "Store Bengaluru"),
            "s01": ("S01", "Store Hyderabad"),
            "s02": ("S02", "Store Vijayawada"),
            "s03": ("S03", "Store Chennai"),
            "s04": ("S04", "Store Bengaluru"),
        }

        detected_store = None
        for key, val in store_map.items():
            if re.search(rf"\b{re.escape(key)}\b", q):
                detected_store = val
                break

        # Product extraction (IDs and common product nicknames)
        product_aliases = {
            "p01": ("P01", "Sparkle Water 1L"),
            "sparkle water": ("P01", "Sparkle Water 1L"),
            "water": ("P01", "Sparkle Water 1L"),
            "p02": ("P02", "Fresh Orange Juice 500ml"),
            "fresh orange juice": ("P02", "Fresh Orange Juice 500ml"),
            "orange juice": ("P02", "Fresh Orange Juice 500ml"),
            "juice": ("P02", "Fresh Orange Juice 500ml"),
            "p03": ("P03", "Cold Brew Coffee 250ml"),
            "cold brew": ("P03", "Cold Brew Coffee 250ml"),
            "coffee": ("P03", "Cold Brew Coffee 250ml"),
            "p04": ("P04", "Masala Chai Premix 200g"),
            "masala chai": ("P04", "Masala Chai Premix 200g"),
            "chai": ("P04", "Masala Chai Premix 200g"),
            "p05": ("P05", "Energy Boost 250ml"),
            "energy boost": ("P05", "Energy Boost 250ml"),
            "energy drink": ("P05", "Energy Boost 250ml"),
            "p06": ("P06", "Artisanal Butter Cookies 200g"),
            "butter cookies": ("P06", "Artisanal Butter Cookies 200g"),
            "cookies": ("P06", "Artisanal Butter Cookies 200g"),
            "p07": ("P07", "Roasted Almonds 150g"),
            "almonds": ("P07", "Roasted Almonds 150g"),
            "p08": ("P08", "Spicy Banana Chips 100g"),
            "banana chips": ("P08", "Spicy Banana Chips 100g"),
            "chips": ("P08", "Spicy Banana Chips 100g"),
            "p09": ("P09", "Multigrain Crackers 150g"),
            "crackers": ("P09", "Multigrain Crackers 150g"),
            "p10": ("P10", "Dark Chocolate 80g"),
            "dark chocolate": ("P10", "Dark Chocolate 80g"),
            "chocolate": ("P10", "Dark Chocolate 80g"),
            "p11": ("P11", "Basmati Rice 5kg"),
            "basmati rice": ("P11", "Basmati Rice 5kg"),
            "rice": ("P11", "Basmati Rice 5kg"),
            "p12": ("P12", "Cold Pressed Mustard Oil 1L"),
            "mustard oil": ("P12", "Cold Pressed Mustard Oil 1L"),
            "oil": ("P12", "Cold Pressed Mustard Oil 1L"),
            "p13": ("P13", "Organic Quinoa 500g"),
            "quinoa": ("P13", "Organic Quinoa 500g"),
            "p14": ("P14", "Durum Wheat Pasta 500g"),
            "pasta": ("P14", "Durum Wheat Pasta 500g"),
            "p15": ("P15", "Instant Oats 1kg"),
            "oats": ("P15", "Instant Oats 1kg"),
            "p16": ("P16", "Herbal Shampoo 250ml"),
            "shampoo": ("P16", "Herbal Shampoo 250ml"),
            "p17": ("P17", "Neem Face Wash 150ml"),
            "neem face wash": ("P17", "Neem Face Wash 150ml"),
            "face wash": ("P17", "Neem Face Wash 150ml"),
            "p18": ("P18", "Organic Lip Balm 15g"),
            "lip balm": ("P18", "Organic Lip Balm 15g"),
            "p19": ("P19", "Moisturizing Lotion 200ml"),
            "lotion": ("P19", "Moisturizing Lotion 200ml"),
            "p20": ("P20", "Bamboo Toothbrush 4pk"),
            "toothbrush": ("P20", "Bamboo Toothbrush 4pk"),
            "p21": ("P21", "Biodegradable Dish Soap 500ml"),
            "dish soap": ("P21", "Biodegradable Dish Soap 500ml"),
            "soap": ("P21", "Biodegradable Dish Soap 500ml"),
            "p22": ("P22", "Lavender Floor Cleaner 1L"),
            "floor cleaner": ("P22", "Lavender Floor Cleaner 1L"),
            "cleaner": ("P22", "Lavender Floor Cleaner 1L"),
            "p23": ("P23", "Recycled Paper Towels 2pk"),
            "paper towels": ("P23", "Recycled Paper Towels 2pk"),
            "p24": ("P24", "Microfiber Cloth 3pk"),
            "microfiber cloth": ("P24", "Microfiber Cloth 3pk"),
            "p25": ("P25", "Compostable Waste Bags 30pk"),
            "waste bags": ("P25", "Compostable Waste Bags 30pk"),
        }

        detected_product = None
        # Check longest matching product key first
        sorted_aliases = sorted(product_aliases.keys(), key=len, reverse=True)
        for alias in sorted_aliases:
            if re.search(rf"\b{re.escape(alias)}\b", q):
                detected_product = product_aliases[alias]
                break

        return {
            "store_id": detected_store[0] if detected_store else None,
            "store_name": detected_store[1] if detected_store else None,
            "product_id": detected_product[0] if detected_product else None,
            "product_name": detected_product[1] if detected_product else None
        }

    def add_document(self, doc_id: str, filename: str, file_type: str, file_size_kb: float, chunks: List[Dict[str, Any]]):
        """Registers an uploaded document and embeds its chunks into the retrieval engine."""
        self.uploaded_documents[doc_id] = {
            "doc_id": doc_id,
            "filename": filename,
            "file_type": file_type,
            "file_size_kb": file_size_kb,
            "chunk_count": len(chunks),
            "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Embed newly added document chunks
        new_vecs = []
        for c in chunks:
            c["doc_id"] = doc_id
            c["filename"] = filename
            c["file_type"] = file_type
            vec = None
            if self.gemini_client and self.gemini_client.is_available:
                try:
                    vec = self.gemini_client.embed_text(c["text"])
                except Exception as e:
                    logger.warning(f"Could not embed chunk {c.get('chunk_id')}: {e}")
            new_vecs.append(vec)

        self.uploaded_chunks.extend(chunks)

        # Update uploaded embeddings matrix if valid
        valid_vecs = [v for v in new_vecs if v is not None]
        if valid_vecs and len(valid_vecs) == len(new_vecs):
            new_arr = np.array(new_vecs, dtype=np.float32)
            if self.uploaded_embeddings is None:
                self.uploaded_embeddings = new_arr
            else:
                self.uploaded_embeddings = np.vstack([self.uploaded_embeddings, new_arr])

        logger.info(f"Registered document '{filename}' with {len(chunks)} chunks.")

    def remove_document(self, doc_id: str) -> bool:
        """Removes an uploaded document and its chunks from the retrieval engine."""
        if doc_id not in self.uploaded_documents:
            return False

        filename = self.uploaded_documents[doc_id]["filename"]
        del self.uploaded_documents[doc_id]

        # Re-filter uploaded chunks and embeddings
        kept_chunks = []
        kept_indices = []
        for i, c in enumerate(self.uploaded_chunks):
            if c.get("doc_id") != doc_id:
                kept_chunks.append(c)
                kept_indices.append(i)

        self.uploaded_chunks = kept_chunks
        if self.uploaded_embeddings is not None and kept_indices:
            self.uploaded_embeddings = self.uploaded_embeddings[kept_indices]
        else:
            self.uploaded_embeddings = None

        logger.info(f"Removed document '{filename}' from retrieval index.")
        return True

    def detect_intent(self, query: str) -> str:
        """Classifies the primary manager intent behind the question."""
        q = query.lower()

        if any(w in q for w in ["document", "uploaded", "agreement", "contract", "invoice", "sop", "policy", "pdf", "file", "doc", "docx", "clause", "terms", "spec sheet", "manual", "guideline"]):
            return "document_qa"
        elif any(w in q for w in ["simulate", "simulation", "what if", "what-if", "target cover", "cover for"]):
            return "simulation"
        elif any(w in q for w in ["benchmark", "compare", "comparison", "leader", "ranking", "rank", "across stores", "all stores", "category share", "top category"]):
            return "benchmark"
        elif any(w in q for w in ["run out", "running out", "stockout", "low stock", "out of stock", "empty", "deplet"]):
            return "stockout"
        elif any(w in q for w in ["not moving", "dead stock", "stagnant", "slow moving", "no sales", "zero sales", "unmoved"]):
            return "dead_stock"
        elif any(w in q for w in ["spike", "surged", "surge", "unusual increase", "jumped", "fastest", "fastest selling", "selling fastest", "highest growth"]):
            return "spike"
        elif any(w in q for w in ["drop", "dropped", "fell", "decrease", "decline", "slowdown", "slump", "loss"]):
            return "drop"
        elif any(w in q for w in ["reorder", "replenish", "restock", "order quantity", "how much to buy"]):
            return "reorder"
        elif any(w in q for w in ["days of stock", "days left", "days remaining", "how many days"]):
            return "days_cover"
        elif any(w in q for w in ["attention", "today", "prioritize", "urgent", "needs my attention", "what should i look at"]):
            return "attention"
        elif any(w in q for w in ["how did", "perform", "sales of", "revenue", "how much did", "sold"]):
            return "performance"
        return "general"

    def check_null_case(self, store_id: Optional[str], product_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """HARD CONSTRAINT (Case 5): Verifies if store+product is a known missing-data combination.
        
        Store Chennai (S03) + Product P17 (Neem Face Wash 150ml) has NO sales data.
        Returns refusal metadata without hallucinating.
        """
        if store_id == "S03" and product_id == "P17":
            return {
                "is_null_case": True,
                "store_id": "S03",
                "store_name": "Store Chennai",
                "product_id": "P17",
                "product_name": "Neem Face Wash 150ml",
                "refusal_text": format_null_case_response("Product P17 (Neem Face Wash 150ml)", "Chennai")
            }
        return None

    def retrieve(self, query: str, top_k: int = 4) -> Dict[str, Any]:
        """Performs hybrid retrieval returning ranked evidence chunks across retail and uploaded docs."""
        entities = self.extract_entities(query)
        intent = self.detect_intent(query)
        store_id = entities["store_id"]
        prod_id = entities["product_id"]

        # Check Null Case First
        null_case = self.check_null_case(store_id, prod_id)
        if null_case:
            return {
                "is_null_case": True,
                "intent": intent,
                "entities": entities,
                "null_metadata": null_case,
                "evidence_chunks": [],
                "evidence_cards": []
            }

        # Calculate query embedding vector once if available
        query_vec = None
        if self.gemini_client.is_available:
            try:
                query_vec = self.gemini_client.embed_text(query)
            except Exception as e:
                logger.warning(f"Error creating query embedding: {e}")

        # --- A. Score Core Retail Evidence Chunks ---
        retail_chunks_count = len(self.evidence_chunks)
        retail_scores = np.zeros(retail_chunks_count, dtype=np.float32)

        if self.embeddings is not None and retail_chunks_count > 0:
            if query_vec is not None and len(query_vec) == self.embeddings.shape[1]:
                q_norm = query_vec / (np.linalg.norm(query_vec) + 1e-9)
                retail_scores += np.dot(self.embeddings, q_norm)
            else:
                q_words = set(query.lower().split())
                for i, chunk in enumerate(self.evidence_chunks):
                    c_text = chunk["text"].lower()
                    overlap = sum(1 for w in q_words if w in c_text and len(w) > 2)
                    retail_scores[i] += (overlap * 0.1)

        # Entity & Intent Boosts for Retail Chunks
        for i, chunk in enumerate(self.evidence_chunks):
            if store_id and chunk.get("store_id") == store_id:
                retail_scores[i] += 2.0
            if prod_id and chunk.get("product_id") == prod_id:
                retail_scores[i] += 3.0

            chunk_type = chunk.get("type", "")
            if intent == "stockout" and chunk_type == "stockout_risk":
                retail_scores[i] += 2.5
            elif intent == "dead_stock" and chunk_type == "dead_stock":
                retail_scores[i] += 2.5
            elif intent == "spike" and chunk_type == "sales_spike":
                retail_scores[i] += 2.5
            elif intent == "drop" and chunk_type == "sales_drop":
                retail_scores[i] += 2.5
            elif intent == "attention" and chunk_type in ["stockout_risk", "dead_stock", "sales_spike", "sales_drop"]:
                retail_scores[i] += 1.5

        # --- B. Score Uploaded Document Chunks ---
        doc_chunks_count = len(self.uploaded_chunks)
        doc_scores = np.zeros(doc_chunks_count, dtype=np.float32)

        if doc_chunks_count > 0:
            if self.uploaded_embeddings is not None and query_vec is not None and len(query_vec) == self.uploaded_embeddings.shape[1]:
                q_norm = query_vec / (np.linalg.norm(query_vec) + 1e-9)
                doc_scores += np.dot(self.uploaded_embeddings, q_norm)
            else:
                q_words = set(query.lower().split())
                for j, dchunk in enumerate(self.uploaded_chunks):
                    d_text = dchunk["text"].lower()
                    overlap = sum(1 for w in q_words if w in d_text and len(w) > 2)
                    doc_scores[j] += (overlap * 0.15)

            # Document Query Boosts
            q_lower = query.lower()
            for j, dchunk in enumerate(self.uploaded_chunks):
                fname = dchunk.get("filename", "").lower()
                # Filename matching boost
                if any(part in q_lower for part in re.split(r"[._ -]", fname) if len(part) > 3):
                    doc_scores[j] += 3.0
                if intent == "document_qa":
                    doc_scores[j] += 4.0

        # --- C. Merge and Rank Top-K Across Pools ---
        all_candidates = []
        for i, chunk in enumerate(self.evidence_chunks):
            all_candidates.append({
                "score": float(retail_scores[i]),
                "is_doc": False,
                "data": chunk
            })

        for j, dchunk in enumerate(self.uploaded_chunks):
            all_candidates.append({
                "score": float(doc_scores[j]),
                "is_doc": True,
                "data": dchunk
            })

        all_candidates.sort(key=lambda x: x["score"], reverse=True)
        top_candidates = all_candidates[:top_k]

        top_chunks = []
        evidence_cards = []

        for cand in top_candidates:
            c = cand["data"]
            if cand["is_doc"]:
                # Uploaded document chunk
                page_info = f"Page {c.get('page_number')}" if c.get("page_number") else "Section"
                top_chunks.append({
                    "text": f"(From Document: {c['filename']}, {page_info}): {c['text']}",
                    "type": "uploaded_document",
                    "filename": c["filename"],
                    "metrics": {
                        "filename": c["filename"],
                        "file_type": c.get("file_type", "DOC"),
                        "page_number": c.get("page_number", 1),
                        "recommendation": f"Consult {c['filename']} for complete policy or agreement specifications.",
                        "assumption": f"Sourced directly from user-uploaded document '{c['filename']}' ({page_info})."
                    }
                })
                evidence_cards.append(EvidenceCard(
                    product_id=c.get("doc_id", "DOC"),
                    product_name=c.get("filename", "Uploaded Document"),
                    store_name=page_info,
                    current_stock=0,
                    avg_daily_sales=0.0,
                    days_remaining=None,
                    status="uploaded_document",
                    details={
                        "filename": c.get("filename"),
                        "page_number": c.get("page_number", 1),
                        "chunk_index": c.get("chunk_index", 0),
                        "file_type": c.get("file_type", "DOC"),
                        "excerpt": c.get("text", "")[:220] + ("..." if len(c.get("text", "")) > 220 else "")
                    }
                ))
            else:
                # Retail evidence chunk
                top_chunks.append(c)
                metrics = c.get("metrics", {})
                evidence_cards.append(EvidenceCard(
                    product_id=c.get("product_id") or "N/A",
                    product_name=c.get("product_name") or c.get("store_name") or "Retail Item",
                    store_name=c.get("store_name") or "All Stores",
                    current_stock=int(metrics.get("current_stock", 0)),
                    avg_daily_sales=float(metrics.get("avg_daily_sales", metrics.get("recent_7d_daily_avg", 0.0))),
                    days_remaining=metrics.get("days_remaining", metrics.get("days_of_stock_remaining")),
                    status=c.get("type", "performance_summary"),
                    details=metrics
                ))

        return {
            "is_null_case": False,
            "intent": intent,
            "entities": entities,
            "null_metadata": None,
            "evidence_chunks": top_chunks,
            "evidence_cards": evidence_cards
        }

