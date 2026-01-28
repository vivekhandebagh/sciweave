"""Vault tools for accessing experiment proposals from Obsidian vault."""

import re
from pathlib import Path
from typing import Optional

import yaml
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from sciweave_mcp.config import get_config


class ProposalSummary(BaseModel):
    """Summary of a proposal for listing."""
    name: str
    title: str
    status: str
    difficulty: str
    source_paper: Optional[str] = None
    tags: list[str] = []


class ProposalContent(BaseModel):
    """Full proposal content."""
    name: str
    title: str
    status: str
    difficulty: str
    source_paper: Optional[str] = None
    tags: list[str] = []
    sections: dict[str, str]
    raw_content: str


def _extract_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter from markdown content."""
    pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
    match = re.match(pattern, content, re.DOTALL)

    if match:
        frontmatter_text = match.group(1)
        body = match.group(2)
        try:
            frontmatter = yaml.safe_load(frontmatter_text) or {}
        except yaml.YAMLError:
            frontmatter = {}
        return frontmatter, body

    return {}, content


def _extract_sections(body: str) -> dict[str, str]:
    """Extract markdown sections by ## headers."""
    sections = {}
    header_pattern = r"^##\s+(.+?)$"
    lines = body.split("\n")

    current_section = None
    current_content = []

    for line in lines:
        header_match = re.match(header_pattern, line)
        if header_match:
            if current_section:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = header_match.group(1).strip()
            current_content = []
        else:
            current_content.append(line)

    if current_section:
        sections[current_section] = "\n".join(current_content).strip()

    return sections


def _parse_proposal(file_path: Path) -> tuple[dict, dict[str, str], str]:
    """Parse a proposal file, return (frontmatter, sections, raw_content)."""
    content = file_path.read_text(encoding="utf-8")
    frontmatter, body = _extract_frontmatter(content)
    sections = _extract_sections(body)
    return frontmatter, sections, content


def _reconstruct_file(frontmatter: dict, body: str) -> str:
    """Reconstruct markdown file with updated frontmatter."""
    frontmatter_yaml = yaml.dump(
        frontmatter,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
    return f"---\n{frontmatter_yaml}---\n{body}"


def register_vault_tools(mcp: FastMCP) -> None:
    """Register vault tools with the MCP server."""

    @mcp.tool()
    def vault_list_proposals(status: Optional[str] = None) -> list[ProposalSummary]:
        """List experiment proposals from Obsidian vault.

        Args:
            status: Filter by status (e.g., 'proposed', 'spec_ready', 'completed').
                   If not provided, returns all proposals.

        Returns:
            List of proposal summaries with name, title, status, difficulty, and tags.
        """
        config = get_config()
        vault_path = config.vault_path

        if not vault_path.exists():
            raise FileNotFoundError(f"Vault path not found: {vault_path}")

        proposals = []
        for md_file in sorted(vault_path.glob("*.md")):
            frontmatter, _, _ = _parse_proposal(md_file)

            proposal_status = frontmatter.get("status", "proposed")
            if status is not None and proposal_status != status:
                continue

            tags = frontmatter.get("tags", [])
            if not isinstance(tags, list):
                tags = [tags] if tags else []

            proposals.append(ProposalSummary(
                name=md_file.stem,
                title=frontmatter.get("title", md_file.stem),
                status=proposal_status,
                difficulty=frontmatter.get("difficulty", "medium"),
                source_paper=frontmatter.get("source_paper"),
                tags=tags,
            ))

        return proposals

    @mcp.tool()
    def vault_read_proposal(name: str) -> ProposalContent:
        """Read full proposal content from vault.

        Args:
            name: Proposal name (filename without .md extension)

        Returns:
            Full proposal content including all sections and raw markdown.
        """
        config = get_config()
        vault_path = config.vault_path
        file_path = vault_path / f"{name}.md"

        if not file_path.exists():
            raise FileNotFoundError(f"Proposal not found: {name}")

        frontmatter, sections, raw_content = _parse_proposal(file_path)

        tags = frontmatter.get("tags", [])
        if not isinstance(tags, list):
            tags = [tags] if tags else []

        return ProposalContent(
            name=name,
            title=frontmatter.get("title", name),
            status=frontmatter.get("status", "proposed"),
            difficulty=frontmatter.get("difficulty", "medium"),
            source_paper=frontmatter.get("source_paper"),
            tags=tags,
            sections=sections,
            raw_content=raw_content,
        )

    @mcp.tool()
    def vault_update_status(name: str, status: str) -> str:
        """Update the status of a proposal in the vault.

        Args:
            name: Proposal name (filename without .md extension)
            status: New status value (e.g., 'proposed', 'spec_ready', 'code_generated', 'running', 'completed')

        Returns:
            Confirmation message with old and new status.
        """
        config = get_config()
        vault_path = config.vault_path
        file_path = vault_path / f"{name}.md"

        if not file_path.exists():
            raise FileNotFoundError(f"Proposal not found: {name}")

        content = file_path.read_text(encoding="utf-8")
        frontmatter, body = _extract_frontmatter(content)

        old_status = frontmatter.get("status", "unknown")
        frontmatter["status"] = status

        new_content = _reconstruct_file(frontmatter, body)
        file_path.write_text(new_content, encoding="utf-8")

        return f"Updated {name}: {old_status} -> {status}"
