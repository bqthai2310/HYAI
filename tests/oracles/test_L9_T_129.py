"""Oracle test for L9-REQ-DAT-006 / L9-T-129."""
from hyai.workflow.data_governance import TombstonePropagationManager
from ._support import oracle

def _good() -> bool:
    mgr = TombstonePropagationManager()
    mgr.register_item("search_index", "item_user_profile_42")
    mgr.register_item("vector_store", "item_user_profile_42")
    mgr.register_item("read_cache", "item_user_profile_42")
    assert not mgr.is_purged_everywhere("item_user_profile_42")
    # Propagate tombstone across projections
    mgr.propagate_tombstone("item_user_profile_42")
    return mgr.is_purged_everywhere("item_user_profile_42")

def _bad() -> bool:
    return False

def test_l9_t_129():
    oracle("L9-REQ-DAT-006", "L9-T-129", _good, _bad)
