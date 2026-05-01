"""Schema for workspace layout: relative subfolders under each project root."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, computed_field


class WorkspaceLayout(BaseModel):
    """Fixed subdirectory names relative to one project folder (instructions, prompts, …)."""

    model_config = ConfigDict(frozen=True)

    instructions: str = "instructions"
    prompts: str = "prompts"
    input_docs: str = "input_docs"
    intermediate: str = "intermediate"
    change_tables: str = "change_tables"
    reports: str = "reports"
    output_docs: str = "output_docs"


DEFAULT_WORKSPACE_LAYOUT = WorkspaceLayout()


class ResolvedProjectPaths(BaseModel):
    """Concrete absolute paths for the active DocPatcher project."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    root: Path
    subdirs: WorkspaceLayout = DEFAULT_WORKSPACE_LAYOUT

    @computed_field
    @property
    def instructions_dir(self) -> Path:
        return self.root / self.subdirs.instructions

    @computed_field
    @property
    def prompts_dir(self) -> Path:
        return self.root / self.subdirs.prompts

    @computed_field
    @property
    def input_docs_dir(self) -> Path:
        return self.root / self.subdirs.input_docs

    @computed_field
    @property
    def intermediate_dir(self) -> Path:
        return self.root / self.subdirs.intermediate

    @computed_field
    @property
    def change_tables_dir(self) -> Path:
        return self.root / self.subdirs.change_tables

    @computed_field
    @property
    def reports_dir(self) -> Path:
        return self.root / self.subdirs.reports

    @computed_field
    @property
    def output_docs_dir(self) -> Path:
        return self.root / self.subdirs.output_docs
