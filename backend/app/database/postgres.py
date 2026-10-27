import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

class Document(Base):
    """Document tracking for DPDP uploads and processing."""
    __tablename__ = "documents"
    
    document_id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_hash = Column(String(64), unique=True, index=True)
    file_size = Column(Integer)
    source_type = Column(String, default="DPDP_LEGAL")
    status = Column(String, default="UPLOADED")  # UPLOADED, PROCESSING, PARSED, READY, FAILED
    
    # Processing metadata
    chunks = Column(Integer, default=0)
    triplets = Column(Integer, default=0)
    vector_count = Column(Integer, default=0)
    processing_time_ms = Column(Integer)
    
    # Evidence hierarchy tracking
    authority_level = Column(String, default="PRIMARY")  # PRIMARY, REFERENCE, INDUSTRY
    legal_source = Column(Boolean, default=True)
    company_policy = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Error handling
    error_message = Column(Text)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "file_hash": self.file_hash,
            "file_size": self.file_size,
            "source_type": self.source_type,
            "status": self.status,
            "chunks": self.chunks,
            "triplets": self.triplets,
            "vector_count": self.vector_count,
            "processing_time_ms": self.processing_time_ms,
            "authority_level": self.authority_level,
            "legal_source": self.legal_source,
            "company_policy": self.company_policy,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "error_message": self.error_message
        }

class Analysis(Base):
    """Compliance analysis results."""
    __tablename__ = "analyses"
    
    analysis_id = Column(String, primary_key=True, index=True)
    document_id = Column(String, index=True)
    policy_id = Column(String)  # Backward compatibility
    
    status = Column(String, default="PROCESSING")  # PROCESSING, COMPLETED, FAILED
    overall_score = Column(Integer, default=0)
    
    # Evidence counts
    findings = Column(JSON)
    severity_counts = Column(JSON)
    status_counts = Column(JSON)
    
    # Provenance and traceability
    agent_trace = Column(JSON)
    guardrail_results = Column(JSON)
    citations = Column(JSON)
    risks = Column(JSON)
    
    # Retrieval evidence
    evidence_legal = Column(JSON)
    evidence_policy = Column(JSON)
    
    # Model and provider info for reproducibility
    model_used = Column(String)
    provider = Column(String)
    embedding_model = Column(String)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "document_id": self.document_id,
            "policy_id": self.policy_id,
            "status": self.status,
            "overall_score": self.overall_score,
            "findings": self.findings,
            "severity_counts": self.severity_counts,
            "status_counts": self.status_counts,
            "agent_trace": self.agent_trace,
            "guardrail_results": self.guardrail_results,
            "citations": self.citations,
            "risks": self.risks,
            "evidence_legal": self.evidence_legal,
            "evidence_policy": self.evidence_policy,
            "model_used": self.model_used,
            "provider": self.provider,
            "embedding_model": self.embedding_model,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }

# Database setup
engine = create_engine(settings.postgres_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize database with required tables."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

def get_db_session():
    """Get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Service functions
async def store_document_metadata(
    document_id: str,
    filename: str,
    hash: str,
    size: int,
    source_type: str = "DPDP_LEGAL",
    status: str = "PROCESSING",
    chunks: int = 0,
    triplets: int = 0,
    vector_count: int = 0,
    processing_time_ms: int = 0
) -> Document:
    """Store document metadata in database."""
    db = SessionLocal()
    try:
        # Check if document already exists
        existing_doc = db.query(Document).filter(Document.file_hash == hash).first()
        if existing_doc:
            logger.info(f"Document already exists: {existing_doc.document_id}")
            return existing_doc
        
        document = Document(
            document_id=document_id,
            filename=filename,
            file_hash=hash,
            file_size=size,
            source_type=source_type,
            status=status,
            chunks=chunks,
            triplets=triplets,
            vector_count=vector_count,
            processing_time_ms=processing_time_ms,
            authority_level="PRIMARY" if source_type == "DPDP_LEGAL" else "REFERENCE",
            legal_source=(source_type == "DPDP_LEGAL")
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        logger.info(f"Document metadata stored: {document_id}")
        return document
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to store document metadata: {e}")
        raise
    finally:
        db.close()

async def get_document_status(document_id: str) -> Optional[Dict[str, Any]]:
    """Get document status by ID."""
    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.document_id == document_id).first()
        if not document:
            return None
        
        return document.to_dict()
    finally:
        db.close()

async def is_document_ready(document_id: str) -> bool:
    """Check if document is ready for analysis."""
    db = SessionLocal()
    try:
        document = db.query(Document).filter(
            Document.document_id == document_id,
            Document.status == "READY"
        ).first()
        return document is not None
    finally:
        db.close()

async def list_documents() -> list:
    """List all documents."""
    db = SessionLocal()
    try:
        documents = db.query(Document).order_by(Document.created_at.desc()).all()
        return [doc.to_dict() for doc in documents]
    finally:
        db.close()

async def store_failed_document(
    document_id: str,
    filename: str,
    hash: str,
    error: str,
    status: str = "FAILED"
):
    """Store failed document record."""
    db = SessionLocal()
    try:
        document = Document(
            document_id=document_id,
            filename=filename,
            file_hash=hash,
            source_type="DPDP_LEGAL",
            status=status,
            error_message=error
        )
        
        db.add(document)
        db.commit()
        logger.info(f"Failed document stored: {document_id} - {error}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to store failed document: {e}")
        raise
    finally:
        db.close()

async def store_analysis_result(
    analysis_id: str,
    document_id: str,
    status: str,
    overall_score: int,
    findings: list,
    severity_counts: dict,
    status_counts: dict,
    agent_trace: list,
    guardrail_results: list,
    citations: list,
    risks: list,
    evidence_legal: list,
    evidence_policy: list,
    model_used: str,
    provider: str,
    embedding_model: str
):
    """Store analysis result."""
    db = SessionLocal()
    try:
        analysis = Analysis(
            analysis_id=analysis_id,
            document_id=document_id,
            policy_id=document_id,  # For backward compatibility
            status=status,
            overall_score=overall_score,
            findings=findings,
            severity_counts=severity_counts,
            status_counts=status_counts,
            agent_trace=agent_trace,
            guardrail_results=guardrail_results,
            citations=citations,
            risks=risks,
            evidence_legal=evidence_legal,
            evidence_policy=evidence_policy,
            model_used=model_used,
            provider=provider,
            embedding_model=embedding_model
        )
        
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        
        # Update document status if completed
        if status == "COMPLETED":
            document = db.query(Document).filter(Document.document_id == document_id).first()
            if document:
                document.status = "ANALYZED"
                db.commit()
        
        logger.info(f"Analysis result stored: {analysis_id}")
        return analysis.to_dict()
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to store analysis result: {e}")
        raise
    finally:
        db.close()

async def get_analysis(analysis_id: str) -> Optional[Dict[str, Any]]:
    """Get analysis by ID."""
    db = SessionLocal()
    try:
        analysis = db.query(Analysis).filter(Analysis.analysis_id == analysis_id).first()
        if not analysis:
            return None
        
        return analysis.to_dict()
    finally:
        db.close()

# Initialize database on import
if __name__ != "__main__":
    init_db()