"""L9-REQ-EXE-008 / L9-T-155: Cross-department conflict resolves by authority/evidence, never majority vote."""
from hyai.departments.charter import ConflictResolver, MajorityVoteForbiddenError
from ._support import oracle


def test_l9_t_155_conflict_resolution_authority_not_majority_vote():
    def _pos():
        winner = ConflictResolver.resolve_conflict(
            resolution_mode="EVIDENCE_AND_AUTHORITY",
            evidence_score_a=0.95,
            evidence_score_b=0.40,
        )
        return winner == "DEPT_A"

    def _neg():
        try:
            ConflictResolver.resolve_conflict(
                resolution_mode="MAJORITY_VOTE",
                evidence_score_a=0.95,
                evidence_score_b=0.40,
                agent_votes={"agent_1": "DEPT_B", "agent_2": "DEPT_B"},
            )
            return True
        except MajorityVoteForbiddenError:
            return False

    oracle("L9-REQ-EXE-008", "L9-T-155", _pos, _neg)
