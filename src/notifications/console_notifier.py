"""Console channel for the Intelligence Agent.

Prints rich-formatted summaries to the terminal. The logic is unchanged from
the original monolithic Notifier — it was only relocated into this module.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.storage.models import Trend

console = Console()


class ConsoleNotifier:
    """Prints rich-formatted report and digest summaries to the terminal."""

    @staticmethod
    def console_output(alert_trends: list[Trend], report_path: Optional[Path]) -> None:
        """Print a rich-formatted summary to the terminal."""
        console.print()

        if alert_trends:
            table = Table(
                title="🚨 ALERTS – Immediate Attention Required",
                box=box.ROUNDED,
                style="bold red",
                header_style="bold white on red",
            )
            table.add_column("Trend", style="bold white")
            table.add_column("Category", style="cyan")
            table.add_column("Momentum", style="yellow", justify="right")
            table.add_column("Articles", justify="right")
            for trend in alert_trends:
                table.add_row(
                    trend.name,
                    trend.category,
                    f"{trend.momentum_score:.1f}",
                    str(trend.article_count),
                )
            console.print(table)
        else:
            console.print(Panel(
                "[green]✓ No critical alerts this cycle[/green]",
                title="Alert Status",
                border_style="green",
            ))

        if report_path:
            console.print(Panel(
                f"[bold blue]Report:[/bold blue] {report_path}",
                title="📄 Report Generated",
                border_style="blue",
            ))
        console.print()

    @staticmethod
    def console_digest_output(stats, alert_trends, report_path) -> None:
        """Print digest summary to terminal."""
        from rich.table import Table
        table = Table(title=f"📋 Daily Digest – {stats.date_str}", box=box.ROUNDED,
                      header_style="bold white on #0f3460")
        table.add_column("Metric")
        table.add_column("Value", justify="right", style="bold")
        table.add_row("Articles collected", str(stats.total_articles))
        table.add_row("Average score", str(stats.avg_relevance))
        table.add_row("Alert trends", str(stats.alert_count))
        table.add_row("Categories", str(len(stats.category_counts)))
        console.print(table)
        if report_path:
            console.print(Panel(f"[bold blue]Digest saved:[/bold blue] {report_path}",
                                border_style="blue"))
