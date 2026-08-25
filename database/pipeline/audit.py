import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from models import TblPipelineLog, EnumPipelineStatus

logger = logging.getLogger("PipelineAudit")

def start_pipeline_log(session: Session, source_id: str) -> TblPipelineLog:
    """Create a new run entry in tbl_pipeline_log."""
    log_entry = TblPipelineLog(
        source_id=source_id,
        run_started_at=datetime.utcnow(),
        status=EnumPipelineStatus.PARTIAL,
        record_extracted=0,
        record_loaded=0
    )
    session.add(log_entry)
    session.commit()
    session.refresh(log_entry)
    return log_entry

def finish_pipeline_log(
    session: Session,
    log_id: int,
    status: EnumPipelineStatus,
    record_extracted: int,
    record_loaded: int,
    error_message: Optional[str] = None
):
    """Mark a pipeline run as finished."""
    log_entry = session.query(TblPipelineLog).filter_by(id=log_id).first()
    if log_entry:
        log_entry.run_finished_at = datetime.utcnow()
        log_entry.status = status
        log_entry.record_extracted = record_extracted
        log_entry.record_loaded = record_loaded
        log_entry.error_message = error_message
        session.commit()
        logger.info(f"[Audit Log] Finished run {log_id} ({log_entry.source_id}) with status {status.value}")
