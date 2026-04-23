# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2026 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import dataclasses
import pathlib
import pickle

import click
import ollama
import tqdm
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_ollama import OllamaEmbeddings
from sqlalchemy import delete, literal, select, union_all

from indico.core.db import db

from indico_ror.models.affiliation_vs_document import AffiliationVectorStoreDocument


def is_model_pulled(model_name: str) -> bool:
    models = ollama.list()
    return any(model.model.split(':')[0] == model_name for model in models.models)


def ensure_model(model_name: str):
    """Pull a model if it's not already available."""
    if not is_model_pulled(model_name):
        click.secho(f"model '{model_name}' not found locally, pulling...", fg='yellow')
        ollama.pull(model_name)
        click.echo(f"model '{model_name}' pulled successfully.")


@dataclasses.dataclass(frozen=True)
class VectorStoreMatchEntry:
    text: str
    metadata: dict


@dataclasses.dataclass(frozen=True)
class VectorStoreMatch:
    score: float
    entry: VectorStoreMatchEntry


class InMemoryVectorStoreBackedSearch:
    def __init__(self, model: str = 'jina/jina-embeddings-v2-small-en', batch_size: int = 256) -> None:
        ensure_model(model)
        self.model = model
        self.embeddings = OllamaEmbeddings(
            model=model,
        )
        self.vectorstore = InMemoryVectorStore(self.embeddings)
        self.batch_size = batch_size

    def save(self, file: str | pathlib.Path) -> None:
        path = pathlib.Path(file)
        path.parent.mkdir(exist_ok=True, parents=True)

        with path.open('wb') as f:
            pickle.dump({
                'model': self.model,
                'batch_size': self.batch_size,
                'store': self.vectorstore.store,
            }, f)

    @staticmethod
    def load(file: str) -> 'InMemoryVectorStoreBackedSearch':
        path = pathlib.Path(file)

        with path.open('rb') as f:
            saved_data = pickle.load(f)  # noqa: S301

        new = InMemoryVectorStoreBackedSearch(saved_data['model'], saved_data.get('batch_size', 256))
        new.vectorstore.store = saved_data['store']
        return new

    def init(self, texts: list[str], metadatas: list[dict]) -> list[str]:
        return self.add(texts, metadatas)

    def add(self, texts: list[str], metadatas: list[dict], vsids: list[str] | None = None) -> list[str]:
        new_ids = []
        for i in tqdm.trange(0, len(texts), self.batch_size, desc='Embedding', unit_scale=self.batch_size):
            new_ids.extend(self.vectorstore.add_texts(
                texts[i:i+self.batch_size],
                metadatas=metadatas[i:i+self.batch_size],
                ids=vsids[i:i+self.batch_size] if vsids is not None else None
            ))
        return new_ids

    def update(self, texts: list[str], metadatas: list[dict], old_ids: list[str]) -> list[str]:
        old_vsids = self.delete(old_ids)
        return self.add(texts, metadatas, old_vsids)

    def delete(self, ror_ids: list) -> list[str]:
        set_ids = set(ror_ids)
        vsids = [key for key, value in self.vectorstore.store.items() if value.get('metadata', {}).get('id') in set_ids]
        self.vectorstore.delete(vsids)
        return vsids

    def match(self, text: str, k: int = 4) -> list[VectorStoreMatch]:
        return [
            VectorStoreMatch(
                (document[1] + 1) / 2,
                VectorStoreMatchEntry(
                    document[0].page_content, document[0].metadata
                )
            )
            for document in self.vectorstore.similarity_search_with_score(text, k)
        ]


class PGVectorStoreBackedSearch:
    def __init__(self, model: str = 'jina/jina-embeddings-v2-small-en', batch_size: int = 512) -> None:
        ensure_model(model)
        self.model = model
        self.embeddings = OllamaEmbeddings(
            model=model,
        )
        self.batch_size = batch_size

    def init(self, texts: list[str], affiliation_ids: list[int]) -> list[str]:
        return self.add(texts, affiliation_ids)

    def add(self, texts: list[str], affiliation_ids: list[int]) -> None:
        if len(texts) == 0:
            return
        for i in tqdm.trange(0, len(texts), self.batch_size, desc='Embedding', unit_scale=self.batch_size):
            embeddings = self.embeddings.embed_documents(texts[i:i+self.batch_size])
            for j in range(len(embeddings)):
                db.session.add(AffiliationVectorStoreDocument(
                    content=texts[i+j],
                    embedding=embeddings[j],
                    affiliation_id=affiliation_ids[i+j],
                ))
            db.session.flush()
        db.session.flush()

    def update(self, texts: list[str], affiliation_ids: list[int], changed_affiliations: list[int]) -> None:
        if len(texts) == 0:
            return
        self.delete(changed_affiliations)
        return self.add(texts, affiliation_ids)

    def delete(self, affiliation_ids: list[int]) -> None:
        if len(affiliation_ids) == 0:
            return
        db.session.execute(
            delete(AffiliationVectorStoreDocument)
            .where(AffiliationVectorStoreDocument.affiliation_id.in_(affiliation_ids))
        )

    def match_embeddings(
        self, embeddings: list[list[float]], k: int = 4, threshold: float = 0.3
    ) -> list[list[tuple[AffiliationVectorStoreDocument, float]]]:
        subqueries = []
        for i, embedding in enumerate(embeddings):
            distance = AffiliationVectorStoreDocument.embedding.cosine_distance(embedding).label('distance')
            subqueries.append(
                select(
                    literal(i).label('embedding_index'),
                    AffiliationVectorStoreDocument.id.label('id'),
                    distance
                ).where(distance < threshold)
                .order_by(distance)
                .limit(k)
            )
        combined = union_all(*subqueries).subquery()

        results = db.session.execute(
            select(
                combined.c.embedding_index,
                AffiliationVectorStoreDocument,
                combined.c.distance
            )
            .join(AffiliationVectorStoreDocument, AffiliationVectorStoreDocument.id == combined.c.id)
            .order_by(combined.c.embedding_index, combined.c.distance)
        ).all()

        grouped: dict[int, list] = {i: [] for i in range(len(embeddings))}
        for embedding_index, doc, dist in results:
            grouped[embedding_index].append((doc, 1 - dist))

        return [grouped[i] for i in sorted(grouped.keys())]

    def match_embedding(
        self, embedding: list[float], k: int = 4, threshold: float = 0.3
    ) -> list[tuple[AffiliationVectorStoreDocument, float]]:
        distance = AffiliationVectorStoreDocument.embedding.cosine_distance(embedding).label('distance')
        return [(doc, 1 - dist) for doc, dist in db.session.execute(
            select(AffiliationVectorStoreDocument, distance)
            .where(distance < threshold)
            .order_by(distance)
            .limit(k)
        ).all()]

    def match_many(
        self, texts: list[str], k: int = 4, threshold: float = 0.3
    ) -> list[list[tuple[AffiliationVectorStoreDocument, float]]]:
        return self.match_embeddings([self.embeddings.embed_query(text) for text in texts], k, threshold)

    def match(
        self, text: str, k: int = 4, threshold: float = 0.3
    ) -> list[tuple[AffiliationVectorStoreDocument, float]]:
        return self.match_embedding(self.embeddings.embed_query(text), k, threshold)
