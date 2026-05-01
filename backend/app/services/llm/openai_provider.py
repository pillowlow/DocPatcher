from openai import OpenAI

from app.models.block import Block
from app.models.proposal import ProposalItem
from app.models.requirement import Requirement
from app.services.llm.base import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model_name: str, temperature: float = 0.0) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name
        self.temperature = temperature

    def propose(self, requirement: Requirement, block: Block) -> ProposalItem:
        prompt = (
            "You are a document revision assistant. Given a requirement and a block, "
            "decide if it should change and propose improved text. Return compact JSON with "
            "keys: should_change, reason, proposed_text, risk_level."
        )
        user_input = f"Requirement: {requirement.text}\nBlock: {block.text}"
        response = self.client.responses.create(
            model=self.model_name,
            input=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_input},
            ],
            temperature=self.temperature,
        )
        output_text = (response.output_text or "").strip()
        should_change = output_text.lower() != block.text.lower()
        return ProposalItem(
            block_id=block.block_id,
            should_change=should_change,
            reason="OpenAI generated proposal",
            proposed_text=output_text or block.text,
            risk_level="medium",
        )
