"""Initial migration - create all tables

Revision ID: 001_initial
Revises: 
Create Date: 2024-03-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Create enum types (DO block for conditional creation)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE userrole AS ENUM ('admin', 'analyst', 'viewer');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE claimstatus AS ENUM ('pending', 'processing', 'analyzed', 'failed');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE documenttype AS ENUM ('discharge_summary', 'insurance_policy', 'billing_data');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE documentstatus AS ENUM ('uploaded', 'processing', 'processed', 'failed');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE approvallikelihood AS ENUM ('high', 'medium', 'low', 'very_low');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create users table if not exists
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255) NOT NULL UNIQUE,
            hashed_password VARCHAR(255) NOT NULL,
            full_name VARCHAR(255) NOT NULL,
            role userrole NOT NULL DEFAULT 'analyst',
            is_active BOOLEAN NOT NULL DEFAULT true,
            is_verified BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)
    op.execute('CREATE INDEX IF NOT EXISTS ix_users_email ON users(email)')

    # Create claims table if not exists
    op.execute("""
        CREATE TABLE IF NOT EXISTS claims (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id),
            claim_number VARCHAR(100) NOT NULL UNIQUE,
            patient_name VARCHAR(255) NOT NULL,
            status claimstatus NOT NULL DEFAULT 'pending',
            claim_metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        'CREATE INDEX IF NOT EXISTS ix_claims_claim_number ON claims(claim_number)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_claims_user_id ON claims(user_id)')

    # Create documents table if not exists
    op.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            claim_id UUID NOT NULL REFERENCES claims(id),
            document_type documenttype NOT NULL,
            filename VARCHAR(255) NOT NULL,
            s3_key VARCHAR(500) NOT NULL,
            file_size INTEGER NOT NULL,
            content_type VARCHAR(100) NOT NULL,
            status documentstatus NOT NULL DEFAULT 'uploaded',
            extracted_text TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        'CREATE INDEX IF NOT EXISTS ix_documents_claim_id ON documents(claim_id)')

    # Create embeddings table if not exists
    op.execute("""
        CREATE TABLE IF NOT EXISTS embeddings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id UUID NOT NULL REFERENCES documents(id),
            chunk_index INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            embedding vector(1536) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        'CREATE INDEX IF NOT EXISTS ix_embeddings_document_id ON embeddings(document_id)')

    # Create vector similarity index for embeddings (HNSW for better performance)
    op.execute("""
        DO $$ BEGIN
            CREATE INDEX ix_embeddings_vector ON embeddings USING hnsw (embedding vector_cosine_ops);
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create analysis_results table if not exists
    op.execute("""
        CREATE TABLE IF NOT EXISTS analysis_results (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            claim_id UUID NOT NULL REFERENCES claims(id),
            approval_score FLOAT NOT NULL,
            approval_likelihood approvallikelihood NOT NULL,
            compliance_risks JSONB DEFAULT '[]',
            clause_references JSONB DEFAULT '[]',
            missing_documentation JSONB DEFAULT '[]',
            recommendations JSONB DEFAULT '[]',
            reasoning TEXT NOT NULL,
            raw_response JSONB,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        'CREATE INDEX IF NOT EXISTS ix_analysis_results_claim_id ON analysis_results(claim_id)')


def downgrade() -> None:
    # Drop indexes
    op.execute('DROP INDEX IF EXISTS ix_embeddings_vector')
    op.execute('DROP INDEX IF EXISTS ix_analysis_results_claim_id')
    op.execute('DROP INDEX IF EXISTS ix_embeddings_document_id')
    op.execute('DROP INDEX IF EXISTS ix_documents_claim_id')
    op.execute('DROP INDEX IF EXISTS ix_claims_user_id')
    op.execute('DROP INDEX IF EXISTS ix_claims_claim_number')
    op.execute('DROP INDEX IF EXISTS ix_users_email')

    # Drop tables
    op.execute('DROP TABLE IF EXISTS analysis_results CASCADE')
    op.execute('DROP TABLE IF EXISTS embeddings CASCADE')
    op.execute('DROP TABLE IF EXISTS documents CASCADE')
    op.execute('DROP TABLE IF EXISTS claims CASCADE')
    op.execute('DROP TABLE IF EXISTS users CASCADE')

    # Drop enum types
    op.execute('DROP TYPE IF EXISTS approvallikelihood')
    op.execute('DROP TYPE IF EXISTS documentstatus')
    op.execute('DROP TYPE IF EXISTS documenttype')
    op.execute('DROP TYPE IF EXISTS claimstatus')
    op.execute('DROP TYPE IF EXISTS userrole')

    # Drop pgvector extension (optional - commented out to preserve for other uses)
    # op.execute('DROP EXTENSION IF EXISTS vector')
