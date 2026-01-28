"""Journal tools for tracking experiment runs and collaboration."""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from sciweave_mcp.config import get_config


class JournalContent(BaseModel):
    """Full journal content."""
    experiment_name: str
    content: str
    run_count: int


def _to_snake_case(title: str) -> str:
    """Convert title to snake_case."""
    clean = re.sub(r"[^\w\s\-]", "", title)
    words = re.split(r"[\s\-]+", clean.lower())
    return "_".join(word for word in words if word)


def _get_journal_path(name: str) -> Path:
    """Get path to journal file for experiment."""
    config = get_config()
    workspace = config.workspace_path
    exp_name = _to_snake_case(name)
    return workspace / exp_name / "journal.md"


def _count_runs(content: str) -> int:
    """Count the number of runs in a journal."""
    return len(re.findall(r"^## Run \d+", content, re.MULTILINE))


def register_journal_tools(mcp: FastMCP) -> None:
    """Register journal tools with the MCP server."""

    @mcp.tool()
    def journal_new_run(name: str, config_summary: Optional[str] = None) -> int:
        """Start a new run section in the experiment journal.

        Creates a new "## Run N" section with timestamp and optional config summary.

        Args:
            name: Experiment name
            config_summary: Optional summary of config being used for this run

        Returns:
            The run number (1-indexed)
        """
        journal_path = _get_journal_path(name)

        if not journal_path.exists():
            raise FileNotFoundError(f"Journal not found: {journal_path}")

        content = journal_path.read_text(encoding="utf-8")
        run_number = _count_runs(content) + 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        new_section = f"""## Run {run_number} - {timestamp}

### Execution
- Status: PENDING
- Duration: -
"""
        if config_summary:
            new_section += f"- Config: {config_summary}\n"

        new_section += """
### Results
| Metric | Value |
|--------|-------|
| - | - |

### Analysis
_Analysis pending..._

### Issues
_None yet_

### Next Steps
_TBD_

### Human Notes
_Your comments here..._

---

"""
        # Append new section
        new_content = content.rstrip() + "\n\n" + new_section
        journal_path.write_text(new_content, encoding="utf-8")

        return run_number

    @mcp.tool()
    def journal_append(
        name: str,
        section: str,
        content: str,
        run_number: Optional[int] = None,
    ) -> str:
        """Append content to a specific section of the journal.

        Args:
            name: Experiment name
            section: Section name - one of: 'execution', 'results', 'analysis', 'issues', 'next_steps', 'human_notes'
            content: Content to append (markdown formatted)
            run_number: Which run to append to. If not specified, appends to the latest run.

        Returns:
            Confirmation message
        """
        journal_path = _get_journal_path(name)

        if not journal_path.exists():
            raise FileNotFoundError(f"Journal not found: {journal_path}")

        journal_content = journal_path.read_text(encoding="utf-8")

        # Map section names to headers
        section_map = {
            "execution": "### Execution",
            "results": "### Results",
            "analysis": "### Analysis",
            "issues": "### Issues",
            "next_steps": "### Next Steps",
            "human_notes": "### Human Notes",
        }

        section_header = section_map.get(section.lower())
        if not section_header:
            raise ValueError(f"Unknown section: {section}. Valid sections: {list(section_map.keys())}")

        # Find the target run
        if run_number is None:
            run_number = _count_runs(journal_content)
            if run_number == 0:
                raise ValueError("No runs found in journal. Use journal_new_run first.")

        # Find the run section
        run_pattern = rf"(## Run {run_number}.*?)(?=## Run \d+|$)"
        run_match = re.search(run_pattern, journal_content, re.DOTALL)

        if not run_match:
            raise ValueError(f"Run {run_number} not found in journal")

        run_section = run_match.group(1)

        # Find the target section within the run
        # Pattern: section header followed by content until next ### or ## or ---
        section_pattern = rf"({re.escape(section_header)}\n)(.*?)(?=###|## |---|\Z)"
        section_match = re.search(section_pattern, run_section, re.DOTALL)

        if not section_match:
            raise ValueError(f"Section '{section}' not found in Run {run_number}")

        # Replace the section content
        old_section = section_match.group(0)
        section_content = section_match.group(2).rstrip()

        # Append new content
        if section_content.strip() in ("_Analysis pending..._", "_None yet_", "_TBD_", "_Your comments here..._", "| - | - |"):
            # Replace placeholder
            new_section_content = content
        else:
            # Append to existing
            new_section_content = section_content + "\n" + content

        new_section = section_match.group(1) + new_section_content + "\n\n"

        # Replace in run section
        new_run_section = run_section.replace(old_section, new_section)

        # Replace in full journal
        new_journal = journal_content.replace(run_section, new_run_section)
        journal_path.write_text(new_journal, encoding="utf-8")

        return f"Appended to {section} in Run {run_number}"

    @mcp.tool()
    def journal_update_status(
        name: str,
        status: str,
        duration: Optional[str] = None,
        run_number: Optional[int] = None,
    ) -> str:
        """Update the execution status of a run.

        Args:
            name: Experiment name
            status: New status (e.g., 'SUCCESS', 'FAILED', 'RUNNING')
            duration: Optional duration string (e.g., '45 minutes')
            run_number: Which run to update. If not specified, updates the latest run.

        Returns:
            Confirmation message
        """
        journal_path = _get_journal_path(name)

        if not journal_path.exists():
            raise FileNotFoundError(f"Journal not found: {journal_path}")

        content = journal_path.read_text(encoding="utf-8")

        if run_number is None:
            run_number = _count_runs(content)
            if run_number == 0:
                raise ValueError("No runs found in journal")

        # Update status line
        status_pattern = rf"(## Run {run_number}.*?- Status: )(\w+)"
        content = re.sub(status_pattern, rf"\g<1>{status}", content, flags=re.DOTALL)

        # Update duration if provided
        if duration:
            duration_pattern = rf"(## Run {run_number}.*?- Duration: )([^\n]+)"
            content = re.sub(duration_pattern, rf"\g<1>{duration}", content, flags=re.DOTALL)

        journal_path.write_text(content, encoding="utf-8")
        return f"Updated Run {run_number}: status={status}" + (f", duration={duration}" if duration else "")

    @mcp.tool()
    def journal_read(name: str) -> JournalContent:
        """Read the full journal for an experiment.

        Args:
            name: Experiment name

        Returns:
            JournalContent with full markdown content and run count.
        """
        journal_path = _get_journal_path(name)

        if not journal_path.exists():
            raise FileNotFoundError(f"Journal not found: {journal_path}")

        content = journal_path.read_text(encoding="utf-8")

        return JournalContent(
            experiment_name=name,
            content=content,
            run_count=_count_runs(content),
        )
