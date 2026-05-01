from abc import ABC, abstractmethod

from app.models.block import Block
from app.models.proposal import ProposalItem
from app.models.requirement import Requirement


class LLMProvider(ABC):
    @abstractmethod
    def propose(self, requirement: Requirement, block: Block) -> ProposalItem:
        raise NotImplementedError
