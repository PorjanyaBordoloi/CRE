"""TUI: Terminal UI for CRE (v0.2 stub)."""

from textual.app import ComposeResult, Screen
from textual.widgets import Header, Footer


class CREScreen(Screen):
    """Main CRE TUI screen (v0.2 stub)."""

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Compose TUI layout."""
        yield Header(show_clock=True)
        yield Footer()

    def on_mount(self) -> None:
        """Placeholder on mount."""
        pass


def launch_tui():
    """Launch CRE TUI (v0.2 stub - not yet implemented)."""
    from textual.app import App

    class CRETUI(App):
        """CRE Terminal UI."""

        BINDINGS = [("q", "quit", "Quit")]

        def compose(self) -> ComposeResult:
            """Compose layout."""
            yield Header(show_clock=True)
            yield Footer()

    app = CRETUI()
    app.run()
