from rapidfuzz import fuzz

from app.models.block import Block
from app.models.candidate import CandidateBuffer, CandidateItem
from app.models.requirement import Requirement


def retrieve_candidates(
    requirement: Requirement, blocks: list[Block], top_k: int
) -> CandidateBuffer:
    scored = []
    for block in blocks:
        score = fuzz.token_set_ratio(requirement.text, block.text) / 100.0
        scored.append((block.block_id, score))

    scored.sort(key=lambda item: item[1], reverse=True)
    candidates = [
        CandidateItem(block_id=block_id, score=score) for block_id, score in scored[:top_k]
    ]
    return CandidateBuffer(requirement_id=requirement.requirement_id, candidates=candidates)
