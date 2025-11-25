import os
from pathlib import Path
from langchain.tools import tool
from rich.console import Console

console = Console()

QUARANTINE_SUFFIX = ".__quarantined__"
REMEDIATION_PREFIX = "REMEDIATION_"

@tool
def quarantine_file(file_path: str):
    """
    Moves a file to quarantine status by renaming it and updating .gitignore.
    Use this immediately when a threat is detected.
    """
    path = Path(file_path)
    if not path.exists():
        return "File not found."

    # 1. Rename the file (The "Lock")
    quarantined_path = path.with_name(f"{path.name}{QUARANTINE_SUFFIX}")
    try:
        os.rename(path, quarantined_path)
        console.print(f"[bold red]🛡️  TOOL EXECUTION: File quarantined to {quarantined_path.name}[/bold red]")
    except OSError as e:
        return f"Failed to move file: {e}"

    # 2. Patch .gitignore (The "Seal")
    # We walk up to find the root .gitignore
    gitignore_path = path.parent / ".gitignore"
    
    rules = [f"*{QUARANTINE_SUFFIX}", f"{REMEDIATION_PREFIX}*.md"]
    current_content = ""
    
    if gitignore_path.exists():
        current_content = gitignore_path.read_text()
    
    missing_rules = [r for r in rules if r not in current_content]
    
    if missing_rules:
        with open(gitignore_path, "a") as f:
            f.write("\n\n# --- SECURITY SENTINEL RULES ---\n")
            for rule in missing_rules:
                f.write(f"{rule}\n")
        console.print("[bold yellow]🛠️  TOOL EXECUTION: .gitignore patched to hide quarantined files.[/bold yellow]")

    return f"File quarantined and .gitignore updated."

@tool
def write_remediation_report(file_path: str, threat_type: str, advice: str):
    """
    Writes a Markdown report explaining the security violation and how to fix it.
    """
    path = Path(file_path)
    report_path = path.parent / f"{REMEDIATION_PREFIX}{path.name}.md"
    
    content = f"""# 🚨 Security Intervention: {threat_type}

**File:** `{path.name}`  
**Status:** Quarantined (Renamed to `*{QUARANTINE_SUFFIX}`)

## Why was this blocked?
{advice}

## How to fix
1. View the file: `cat "{path.name}{QUARANTINE_SUFFIX}"`
2. Remove the sensitive data (Secrets/PII).
3. Rename it back: `mv "{path.name}{QUARANTINE_SUFFIX}" "{path.name}"`
"""
    report_path.write_text(content)
    console.print(f"[bold green]✅ TOOL SUCCESS: Remediation report generated at {report_path.name}[/bold green]")
    return "Report generated."