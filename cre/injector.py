"""Context formatting and injection: output context in various formats."""

from typing import Optional
from cre.retriever import ContextBundle


class Injector:
    """Format and output context bundles for injection into LLM prompts."""

    @staticmethod
    def format_markdown(bundle: ContextBundle) -> str:
        """Format context bundle as markdown.

        Args:
            bundle: ContextBundle from retriever

        Returns:
            Formatted markdown string
        """
        lines = []

        # Header with token info
        lines.append("---")
        lines.append("# CRE Context Injection")
        lines.append(f"**Query:** {bundle.metadata.get('query', 'N/A')}")
        lines.append(
            f"**Tokens Used:** {bundle.token_count} / {bundle.metadata.get('token_budget', 'N/A')}"
        )
        lines.append(f"**Domains:** {', '.join(bundle.metadata.get('domains', []))}")
        lines.append("---\n")

        # Themes (tier 3)
        if bundle.themes:
            lines.append("## 🎯 Key Themes\n")
            for i, theme in enumerate(bundle.themes, 1):
                lines.append(f"**Theme {i}:**\n{theme}\n")

        # Summaries (tier 2)
        if bundle.summaries:
            lines.append("## 📋 Summaries\n")
            for i, summary in enumerate(bundle.summaries, 1):
                lines.append(f"**Summary {i}:**\n{summary}\n")

        # Facts (tier 1)
        if bundle.facts:
            lines.append("## 📌 Details & Facts\n")
            for i, fact in enumerate(bundle.facts, 1):
                lines.append(f"**Fact {i}:**\n{fact}\n")

        return "\n".join(lines)

    @staticmethod
    def format_plain(bundle: ContextBundle) -> str:
        """Format context bundle as plain text.

        Args:
            bundle: ContextBundle from retriever

        Returns:
            Formatted plain text string
        """
        lines = []

        lines.append("=" * 60)
        lines.append("CRE CONTEXT INJECTION")
        lines.append("=" * 60)
        lines.append(f"Query: {bundle.metadata.get('query', 'N/A')}")
        lines.append(f"Tokens: {bundle.token_count} / {bundle.metadata.get('token_budget', 'N/A')}")
        lines.append(f"Domains: {', '.join(bundle.metadata.get('domains', []))}")
        lines.append("=" * 60 + "\n")

        if bundle.themes:
            lines.append("KEY THEMES:\n")
            for i, theme in enumerate(bundle.themes, 1):
                lines.append(f"({i}) {theme}\n")

        if bundle.summaries:
            lines.append("\nSUMMARIES:\n")
            for i, summary in enumerate(bundle.summaries, 1):
                lines.append(f"({i}) {summary}\n")

        if bundle.facts:
            lines.append("\nDETAILS & FACTS:\n")
            for i, fact in enumerate(bundle.facts, 1):
                lines.append(f"({i}) {fact}\n")

        return "\n".join(lines)

    @staticmethod
    def format_json(bundle: ContextBundle) -> str:
        """Format context bundle as JSON.

        Args:
            bundle: ContextBundle from retriever

        Returns:
            JSON string
        """
        import json

        data = {
            "metadata": bundle.metadata,
            "token_count": bundle.token_count,
            "content": {
                "themes": bundle.themes,
                "summaries": bundle.summaries,
                "facts": bundle.facts,
            },
        }
        return json.dumps(data, indent=2)

    @staticmethod
    def inject(
        bundle: ContextBundle,
        format: str = "markdown",
    ) -> str:
        """Inject formatted context bundle.

        Args:
            bundle: ContextBundle from retriever
            format: Output format (markdown, plain, json)

        Returns:
            Formatted context ready for injection
        """
        if format == "markdown":
            return Injector.format_markdown(bundle)
        elif format == "plain":
            return Injector.format_plain(bundle)
        elif format == "json":
            return Injector.format_json(bundle)
        else:
            raise ValueError(f"Unknown format: {format}")
