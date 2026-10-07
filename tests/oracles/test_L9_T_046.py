"""Oracle test for L9-REQ-REL-004 / L9-T-046."""
from hyai.workflow.checkpoint import CheckpointManager, create_checkpoint
from ._support import oracle

def _good() -> bool:
    manager = CheckpointManager()
    cp = create_checkpoint(
        checkpoint_id="chk_stage1",
        workflow_id="wf_data_sync_01",
        workflow_revision=1,
        task_revision=2,
        completed_steps=["step_extract", "step_transform"],
        side_effect_refs=["se_db_write"],
        cursor="cursor_offset_500",
    )
    manager.save_checkpoint(cp)
    resumed = manager.resume_from_checkpoint("chk_stage1")
    return (
        resumed.completed_steps == ("step_extract", "step_transform")
        and resumed.cursor == "cursor_offset_500"
    )

def _bad() -> bool:
    return False

def test_l9_t_046():
    oracle("L9-REQ-REL-004", "L9-T-046", _good, _bad)
