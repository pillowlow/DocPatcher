from app.core.settings import Settings
from app.models.block import Block
from app.models.candidate import CandidateBuffer
from app.models.change_table import ChangeRow
from app.models.requirement import Requirement
from app.services.llm.base import LLMProvider
from app.services.llm.mock_provider import MockProvider
from app.services.llm.openai_provider import OpenAIProvider


def build_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "openai" and settings.openai_api_key:
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model_name=settings.model_name,
            temperature=settings.llm_temperature,
        )
    return MockProvider()


def propose_changes(
    requirement: Requirement,
    blocks_by_id: dict[str, Block],
    candidate_buffer: CandidateBuffer,
    provider: LLMProvider,
) -> list[ChangeRow]:
    rows: list[ChangeRow] = []
    for idx, candidate in enumerate(candidate_buffer.candidates, start=1):
        block = blocks_by_id[candidate.block_id]
        proposal = provider.propose(requirement=requirement, block=block)
        if not proposal.should_change:
            continue
        rows.append(
            ChangeRow(
                change_id=f"C{idx:04d}",
                doc_id=block.doc_id,
                block_id=block.block_id,
                original_text=block.text,
                proposed_text=proposal.proposed_text,
                status="pending",
            )
        )
    return rows
