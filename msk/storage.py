"""K-node storage
- SQLite backend for structured queries
- Qdrant for semantic vector search
- sentence-transformers for embeddings (all-MiniLM-L6-v2)
"""

import json
import sqlite3
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer, util

from qdrant_client import QdrantClient
from qdrant_client.models import (Distance, VectorParams, PointStruct, 
                                  Filter, FieldCondition, Condition, 
                                  Range, MatchValue)

from .models import KNode, KNodeType


class KNodeStore:

    def __init__(self, db_path: str = ":memory:", qdrant_path: str = ":memory:"):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._qdrant = QdrantClient(path=qdrant_path)  # local file-based
        self._model = SentenceTransformer("all-MiniLM-L6-v2")
        self._create_schema()
        self._create_collection()

    def _embed(self, text: str) -> list[float]:
        return self._model.encode(text).tolist()
    
    def _create_collection(self) -> None:
        collections = [c.name for c in self._qdrant.get_collections().collections]
        if "k_nodes" not in collections:
            self._qdrant.create_collection(
                collection_name="k_nodes",
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )

    def _create_schema(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS k_nodes (
                id          TEXT PRIMARY KEY,
                type        TEXT NOT NULL,
                level       INTEGER NOT NULL DEFAULT 2,
                strength    REAL NOT NULL DEFAULT 0.7,
                active      INTEGER NOT NULL DEFAULT 1,
                data        TEXT NOT NULL 
            )
        """)
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_type ON k_nodes(type)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_active ON k_nodes(active)"
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def save(self, node: KNode) -> None:
        embedding = self._embed(node.content.text)

        # SQLite for structured data
        self._conn.execute(
            "INSERT OR REPLACE INTO k_nodes (id, type, level, strength, active, data) VALUES (?,?,?,?,?,?)",
            (node.id, node.type.value, node.activation.level,
             node.lifecycle.strength, 1 if node.is_active() else 0,
             node.model_dump_json()),
        )
        self._conn.commit()

        # Qdrant for vector search
        self._qdrant.upsert(
            collection_name="k_nodes",
            points=[PointStruct(
                id=node.id,  # use K-node UUID as point ID
                vector=embedding,
                payload={
                    "level": node.activation.level,
                    "type": node.type.value,
                    "strength": node.lifecycle.strength,
                    "active": node.is_active(),
                },
            )],
        )

    def update(self, node: KNode) -> None:
        self.save(node)

    def delete(self, node_id: str) -> None:
        self._conn.execute("DELETE FROM k_nodes WHERE id = ?", (node_id,))
        self._conn.commit()

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get(self, node_id: str) -> Optional[KNode]:
        row = self._conn.execute(
            "SELECT data FROM k_nodes WHERE id = ?", (node_id,)
        ).fetchone()
        return KNode.model_validate_json(row[0]) if row else None

    def all_active(self) -> list[KNode]:
        rows = self._conn.execute(
            "SELECT data FROM k_nodes WHERE active = 1"
        ).fetchall()
        return [KNode.model_validate_json(r[0]) for r in rows]

    def by_type(self, ktype: KNodeType) -> list[KNode]:
        rows = self._conn.execute(
            "SELECT data FROM k_nodes WHERE type = ? AND active = 1",
            (ktype.value,),
        ).fetchall()
        return [KNode.model_validate_json(r[0]) for r in rows]

    def by_level_band(self, low: int, high: int) -> list[KNode]:
        rows = self._conn.execute(
            "SELECT data FROM k_nodes WHERE level BETWEEN ? AND ? AND active = 1",
            (low, high),
        ).fetchall()
        return [KNode.model_validate_json(r[0]) for r in rows]

    # ------------------------------------------------------------------
    # Semantic search
    # ------------------------------------------------------------------

    def search(self, task: str, top_k: int = 10,
               level_band: Optional[tuple[int, int]] = None) -> list[KNode]:
        task_embedding = self._embed(task)

        # build filter for level_band
        must_conditions: list[Condition] = [
            FieldCondition(key="active", match=MatchValue(value=True)),
        ]

        if level_band is not None:
            lo, hi = level_band
            must_conditions.append(
                FieldCondition(key="level", range=Range(gte=lo, lte=hi))
            )

        qdrant_filter = Filter(must=must_conditions)

        # semantic search
        hits = self._qdrant.query_points(
            collection_name="k_nodes",
            query=task_embedding,
            query_filter=qdrant_filter,
            limit=top_k,
        ).points

        # fetch full K-nodes from SQLite by ID
        results: list[KNode] = []
        for hit in hits:
            node = self.get(str(hit.id))
            if node and node.is_active():
                results.append(node)
        return results

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        total = self._conn.execute("SELECT COUNT(*) FROM k_nodes").fetchone()[0]
        active = self._conn.execute(
            "SELECT COUNT(*) FROM k_nodes WHERE active = 1"
        ).fetchone()[0]
        by_type = self._conn.execute(
            "SELECT type, COUNT(*) FROM k_nodes WHERE active = 1 GROUP BY type"
        ).fetchall()
        return {
            "total": total,
            "active": active,
            "by_type": dict(by_type),
        }