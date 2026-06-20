"""
Table utility functions for DP-Bench evaluation.

This module provides helper functions for converting HTML tables to markdown,
used when building gold text from DP-Bench elements.
"""


def html_table_to_markdown(html: str) -> str:
    """
    Convert HTML table to Markdown pipe-table format.

    Args:
        html: HTML string containing <tr><td>...</td></tr> structure.

    Returns:
        Markdown table string with header separator.

    """
    # Simple HTML table parser - handles <tr><td>...</td></tr>
    rows = []
    current_row = []

    # Parse rows by splitting on <tr> tags
    i = 0
    while i < len(html):
        if html[i:i+4].lower() == "<tr>":
            i += 4
        elif html[i:i+5].lower() == "</tr>":
            if current_row:
                rows.append(current_row)
                current_row = []
            i += 5
        elif html[i:i+4].lower() == "<td>":
            i += 4
            # Find cell content until </td>
            end_idx = html.find("</td>", i)
            if end_idx != -1:
                cell_text = html[i:end_idx].strip()
                current_row.append(cell_text)
                i = end_idx + 5
            else:
                break
        else:
            i += 1

    if not rows:
        return ""

    cols = len(rows[0])
    lines = []

    for row_idx, row in enumerate(rows):
        # Pad row to consistent column count
        while len(row) < cols:
            row.append("")
        lines.append("| " + " | ".join(row) + " |")

        # Add header separator after first row
        if row_idx == 0:
            lines.append("| " + " | ".join(["---"] * cols) + " |")

    return "\n".join(lines)
