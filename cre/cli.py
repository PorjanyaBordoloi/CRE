"""CRE CLI: Typer entrypoint with all v0.1 commands."""

from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from cre.config import Config
from cre.vector_store import VectorStore
from cre.memory import Memory
from cre.sidecar import get_sidecar
from cre.retriever import Retriever
from cre.ingestor import Ingestor
from cre.injector import Injector

app = typer.Typer(
    name="cre",
    help="Context Retrieval Engine - Composable context management for LLM workflows",
    pretty_exceptions_show_locals=False,
)
console = Console()


@app.command()
def init(
    path: str = typer.Argument(
        ".",
        help="Path to initialize CRE in (default: current directory)"
    ),
) -> None:
    """Initialize a CRE project in a directory.

    Creates .cre/ config, vector store, and memory database.
    """
    cre_dir = Path(path) / ".cre"
    cre_dir.mkdir(parents=True, exist_ok=True)

    # Initialize config
    config = Config(cre_dir)
    config.initialize()

    # Initialize stores
    vector_store = VectorStore(cre_dir / "vector_store")
    memory = Memory(cre_dir / "memory.db")

    console.print(
        Panel(
            f"✅ CRE initialized at [bold]{path}[/bold]\n"
            f"📁 Config: {config.config_file}\n"
            f"🗄️ Vector Store: {vector_store.persist_dir}\n"
            f"💾 Memory: {memory.db_path}",
            title="CRE Init",
            style="green",
        )
    )


@app.command()
def ingest(
    path: str = typer.Argument(..., help="Path to file or directory to ingest"),
    tier: int = typer.Option(
        1,
        "--tier",
        help="Memory tier (1=raw facts, 2=summaries, 3=themes)"
    ),
    domain: str = typer.Option(
        "",
        "--domain",
        help="Domain classification (research, academics, music, self, synthesis, aria)"
    ),
) -> None:
    """Ingest markdown files into vector store and memory.

    Reads files, chunks them, embeds into ChromaDB L1, and stores in SQLite L2.
    """
    ingest_path = Path(path)
    if not ingest_path.exists():
        console.print(f"[red]Error: {path} not found[/red]")
        raise typer.Exit(1)

    config = Config()
    vector_store = VectorStore()
    memory = Memory()
    ingestor = Ingestor(vector_store, memory)

    try:
        if ingest_path.is_file():
            chunk_ids = ingestor.ingest_file(ingest_path, domain=domain, tier=tier)
        else:
            chunk_ids = ingestor.ingest_directory(
                ingest_path, domain=domain, tier=tier
            )

        # Get stats
        vector_stats = vector_store.get_stats()
        memory_stats = memory.get_stats()

        console.print(
            Panel(
                f"✅ Ingested {len(chunk_ids)} chunks\n"
                f"📊 Vector Store: {vector_stats['total_chunks']} total chunks\n"
                f"💾 Memory: {memory_stats['total_entries']} total entries\n"
                f"  Tier breakdown: {memory_stats['by_tier']}",
                title="Ingest Complete",
                style="green",
            )
        )

    except Exception as e:
        console.print(f"[red]Error during ingestion: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def retrieve(
    query: str = typer.Argument(..., help="Query string"),
    top_k: int = typer.Option(
        5,
        "--top-k",
        help="Number of chunks to retrieve from vector store"
    ),
    budget: int = typer.Option(
        None,
        "--budget",
        help="Token budget (defaults to config value)"
    ),
) -> None:
    """Retrieve relevant context for a query.

    Searches L1 vector store, fetches L2 tiers, and optionally ranks with L3 sidecar.
    """
    config = Config()
    vector_store = VectorStore()
    memory = Memory()
    sidecar = get_sidecar(config)
    retriever = Retriever(vector_store, memory, sidecar, config)

    try:
        bundle = retriever.retrieve(query, token_budget=budget, top_k=top_k)

        # Display results
        console.print(
            Panel(
                f"Query: [bold]{query}[/bold]\n"
                f"Tokens: {bundle.token_count} used",
                title="Retrieval Results",
                style="blue",
            )
        )

        if bundle.themes:
            console.print(f"\n[bold magenta]Themes ({len(bundle.themes)})[/bold magenta]")
            for i, theme in enumerate(bundle.themes, 1):
                console.print(f"  {i}. {theme[:100]}..." if len(theme) > 100 else f"  {i}. {theme}")

        if bundle.summaries:
            console.print(f"\n[bold cyan]Summaries ({len(bundle.summaries)})[/bold cyan]")
            for i, summary in enumerate(bundle.summaries, 1):
                console.print(f"  {i}. {summary[:100]}..." if len(summary) > 100 else f"  {i}. {summary}")

        if bundle.facts:
            console.print(f"\n[bold yellow]Facts ({len(bundle.facts)})[/bold yellow]")
            for i, fact in enumerate(bundle.facts, 1):
                console.print(f"  {i}. {fact[:100]}..." if len(fact) > 100 else f"  {i}. {fact}")

    except Exception as e:
        console.print(f"[red]Error during retrieval: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def inject(
    query: str = typer.Argument(..., help="Query string"),
    budget: int = typer.Option(
        None,
        "--budget",
        help="Token budget (defaults to config value)"
    ),
    format: str = typer.Option(
        "markdown",
        "--format",
        help="Output format (markdown, plain, json)"
    ),
) -> None:
    """Retrieve and format context ready for prompt injection.

    Combines retrieval with formatting for direct paste into LLM prompt.
    """
    config = Config()
    vector_store = VectorStore()
    memory = Memory()
    sidecar = get_sidecar(config)
    retriever = Retriever(vector_store, memory, sidecar, config)
    injector = Injector()

    try:
        bundle = retriever.retrieve(query, token_budget=budget)
        formatted = injector.inject(bundle, format=format)

        console.print(formatted)

    except Exception as e:
        console.print(f"[red]Error during injection: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def compress(
    file: str = typer.Argument(..., help="Path to file to compress"),
    tier: int = typer.Option(
        2,
        "--tier",
        help="Target memory tier (2=summary, 3=theme)"
    ),
) -> None:
    """Compress a session log or document and file into memory.

    Runs sidecar LLM to extract summaries/themes from raw notes.
    """
    config = Config()
    vector_store = VectorStore()
    memory = Memory()
    sidecar = get_sidecar(config)
    retriever = Retriever(vector_store, memory, sidecar, config)

    try:
        file_path = Path(file)
        if not file_path.exists():
            console.print(f"[red]Error: {file} not found[/red]")
            raise typer.Exit(1)

        compressed = retriever.compress_document(str(file_path), tier=tier)

        console.print(
            Panel(
                f"✅ Compressed and filed to tier {tier}\n"
                f"📄 Original: {file_path.name}\n"
                f"📝 Result preview: {compressed[:200]}...",
                title="Compression Complete",
                style="green",
            )
        )

    except Exception as e:
        console.print(f"[red]Error during compression: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def status() -> None:
    """Show CRE store statistics and configuration.

    Displays chunk counts, memory tiers, and sidecar configuration.
    """
    config = Config()
    vector_store = VectorStore()
    memory = Memory()

    # Vector store stats
    vector_stats = vector_store.get_stats()
    memory_stats = memory.get_stats()

    # Build display table
    table = Table(title="CRE Status", show_header=True, header_style="bold blue")
    table.add_column("Component", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Config File", str(config.config_file))
    table.add_row("Sidecar Backend", config.sidecar_backend)
    table.add_row("Sidecar Model", config.sidecar_model)
    table.add_row("Embedding Model", config.embedding_model)
    table.add_row("Chunk Size", f"{config.chunk_size} tokens")
    table.add_row("", "")
    table.add_row("Vector Store", f"{vector_stats['total_chunks']} chunks")
    table.add_row("Vector Store Path", str(vector_stats['persist_dir']))

    # Memory stats
    table.add_row("Memory Total", f"{memory_stats['total_entries']} entries")
    for tier, count in memory_stats.get("by_tier", {}).items():
        tier_name = {1: "Raw Facts", 2: "Summaries", 3: "Themes"}.get(tier, f"Tier {tier}")
        table.add_row(f"  {tier_name}", str(count))

    # Domain stats
    if memory_stats.get("by_domain"):
        table.add_row("", "")
        for domain, count in memory_stats["by_domain"].items():
            table.add_row(f"  Domain: {domain}", str(count))

    console.print(table)


@app.command()
def tui() -> None:
    """Launch TUI viewer (v0.2 - stub).

    Interactive terminal UI for browsing context and searching live.
    """
    console.print(
        Panel(
            "🚧 TUI viewer coming in v0.2\n"
            "For now, use [bold]cre retrieve[/bold] and [bold]cre inject[/bold] commands.",
            title="TUI - v0.2 Feature",
            style="yellow",
        )
    )


@app.command()
def lint() -> None:
    """Health check: orphan chunks, stale tiers (v0.2 - stub).

    Scan for inconsistencies and missing cross-links.
    """
    console.print(
        Panel(
            "🚧 Lint checks coming in v0.2\n"
            "Will detect: orphan chunks, stale tiers, contradictions",
            title="Lint - v0.2 Feature",
            style="yellow",
        )
    )


def main() -> None:
    """CLI entrypoint."""
    app()


if __name__ == "__main__":
    main()
