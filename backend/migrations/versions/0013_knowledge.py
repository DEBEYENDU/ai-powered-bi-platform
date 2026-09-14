"""Knowledge base tables for RAG

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-13
"""

from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0013"
down_revision = "0012"
branch_labels: str | tuple | None = None
depends_on: str | tuple | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "knowledge_collections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("access_policy", sa.String(50), server_default="organization"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.Column("document_count", sa.Integer(), server_default="0"),
        sa.Column("total_chunks", sa.Integer(), server_default="0"),
        sa.UniqueConstraint("organization_id", "name", name="uq_knowledge_collections_org_name"),
    )

    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False, index=True),
        sa.Column(
            "collection_id",
            sa.String(36),
            sa.ForeignKey("knowledge_collections.id"),
            nullable=True,
            index=True,
        ),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False, index=True),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(50), server_default="upload"),
        sa.Column("source_url", sa.String(1000), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending", index=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.Column("indexed_at", sa.DateTime(), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("chunk_count", sa.Integer(), server_default="0"),
        sa.Column("content_text", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_knowledge_documents_org_collection",
        "knowledge_documents",
        ["organization_id", "collection_id"],
    )

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "document_id",
            sa.String(36),
            sa.ForeignKey("knowledge_documents.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("organization_id", sa.String(36), nullable=False, index=True),
        sa.Column("collection_id", sa.String(36), nullable=True, index=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), server_default="0"),
        sa.Column("character_count", sa.Integer(), server_default="0"),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("section", sa.String(500), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("embedding", postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column("embedding_model", sa.String(100), nullable=True),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=True),
        sa.Column("embedding_status", sa.String(20), server_default="pending"),
        sa.Column("keyword_tsv", postgresql.TSVECTOR(), nullable=True),
        sa.Column("created_at", sa.DateTime(), default=datetime.utcnow),
    )
    op.create_index(
        "ix_knowledge_chunks_doc_index",
        "knowledge_chunks",
        ["document_id", "chunk_index"],
    )
    op.create_index(
        "ix_knowledge_chunks_keyword_tsv",
        "knowledge_chunks",
        ["keyword_tsv"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_chunks_keyword_tsv", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_doc_index", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")

    op.drop_index("ix_knowledge_documents_org_collection", table_name="knowledge_documents")
    op.drop_table("knowledge_documents")

    op.drop_table("knowledge_collections")
