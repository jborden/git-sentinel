#!/usr/bin/env python3
import time
import re
import typer
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from rich.console import Console
from rich.panel import Panel

# Assuming this import exists in your project structure
from sentinel_agent import process_threat_event

app = typer.Typer()
console = Console()

# --- CONFIGURATION ---
SAFE_EXTENSIONS = {'.py', '.js', '.ts', '.txt', '.md', '.json', '.csv', '.env', '.sh', '.yml', '.yaml', '.pem', '.key'}
IGNORE_SUFFIX = ".__quarantined__"

# --- THREAT SIGNATURES ---
PATTERNS = {
    "AWS Access Key": r'(?<![A-Z0-9])[A-Z0-9]{20}(?![A-Z0-9])',
    "OpenAI Secret Key": r'sk-[a-zA-Z0-9]{32,}',
    "Private Key": r'-----BEGIN PRIVATE KEY-----',
    "Mass PII (Emails)": r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
}

class SentinelHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            # Convert string to Path immediately
            self.scan_file(Path(event.src_path))

    def on_modified(self, event):
        if not event.is_directory:
            self.scan_file(Path(event.src_path))

    def scan_file(self, file_path: Path):
        """
        Robust file scanner using Path objects.
        """
        # 1. Quick Filters
        if file_path.name.endswith(IGNORE_SUFFIX): return
        if "REMEDIATION_" in file_path.name: return
        if ".git" in file_path.parts: return

        # 2. Existence Check (Race condition protection)
        if not file_path.exists():
            return

        # 3. Extension Check
        # We allow files with no suffix (like 'Dockerfile' or binaries) to pass
        # only if they are text, but for safety, we stick to allowlist for now.
        if file_path.suffix not in SAFE_EXTENSIONS:
            return

        # 4. Content Scan
        try:
            # Read only first 20KB to save CPU on large files
            # errors='replace' prevents crashing on unexpected binary characters
            content = file_path.read_text(encoding='utf-8', errors='replace')[:20000]

            detected_threat = None

            for threat_name, pattern in PATTERNS.items():
                matches = re.findall(pattern, content)

                # Context aware checks
                if threat_name == "Mass PII (Emails)" and len(matches) < 3:
                    continue

                if matches:
                    detected_threat = threat_name
                    break

            if detected_threat:
                self.trigger_agent(file_path, detected_threat)

        except PermissionError:
            # Common in system directories or locked files
            return
        except UnicodeDecodeError:
            # It was likely a binary file disguised as code
            return
        except Exception as e:
            console.print(f"[dim red]Error reading {file_path.name}: {e}[/dim red]")

    def trigger_agent(self, file_path: Path, threat_type: str):
        console.print("\n")
        console.rule(f"[bold red]🚨 SECURITY ALERT: {threat_type}[/bold red]")
        console.print(f"[yellow]File:[/yellow] {file_path}")

        console.print("[bold cyan]🤖 ACTIVATING SENTINEL AGENT...[/bold cyan]")

        try:
            # Pass str(file_path) if your agent expects a string
            result = process_threat_event(str(file_path), threat_type)
            console.print(f"[dim]{result.get('analysis', 'No analysis returned')}[/dim]")
            console.print("[bold green]✓ Threat Neutralized[/bold green]\n")
        except Exception as e:
            console.print(f"[bold red]Agent Failure:[/bold red] {e}")


@app.command()
def guard(
    path: Path = typer.Argument(".", help="Folder to watch"),
):
    """
    Starts the Zero-Trust Sentinel.
    Watches for secrets and PII. Triggers LLM remediation on detection.
    """
    console.print(f"path {path}")
    target_path = path.resolve()

    if not target_path.exists():
        console.print(f"[bold red]Error:[/bold red] Path '{target_path}' does not exist.")
        raise typer.Exit(code=1)

    console.clear()
    console.print(Panel.fit(
        "[bold cyan]🛡️ ZERO-TRUST SENTINEL[/bold cyan]\n"
        f"Watching: {target_path}\n"
        f"Signatures: {', '.join(PATTERNS.keys())}",
        subtitle="Active Pre-Commit Protection"
    ))

    observer = Observer()
    handler = SentinelHandler()

    # Watchdog expects a string for the path argument
    observer.schedule(handler, str(target_path), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        console.print("\n[yellow]Sentinel Stopped.[/yellow]")
    observer.join()

if __name__ == "__main__":
    app()
