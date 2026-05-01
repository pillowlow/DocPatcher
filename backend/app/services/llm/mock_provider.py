from app.models.block import Block
from app.models.proposal import ProposalItem
from app.models.requirement import Requirement
from app.services.llm.base import LLMProvider


class MockProvider(LLMProvider):
    def propose(self, requirement: Requirement, block: Block) -> ProposalItem:
        lower_req = requirement.text.lower()
        should_change = any(token in block.text.lower() for token in lower_req.split())
        proposed_text = (
            f"{block.text} [draft suggestion: {requirement.text}]"
            if should_change
            else block.text
        )
        return ProposalItem(
            block_id=block.block_id,
            should_change=should_change,
            reason="Mock proposal based on lexical overlap",
            proposed_text=proposed_text,
            risk_level="low",
        )
