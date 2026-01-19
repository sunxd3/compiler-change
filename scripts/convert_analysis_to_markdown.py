#!/usr/bin/env python3
"""Convert analysis YAML files to readable Markdown format."""

import sys
from pathlib import Path
from datetime import datetime

import yaml


def format_date(date_str):
    """Format ISO date string to readable format."""
    if not date_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except:
        return str(date_str)


def yaml_to_markdown(yaml_path):
    """Convert an analysis YAML file to markdown."""
    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)

    pr = data.get("pr", {})
    scope = data.get("scope", {})
    analysis = data.get("analysis", {})

    lines = []

    # Header
    lines.append(f"# PR #{pr.get('number')}: {pr.get('title')}")
    lines.append("")

    # Metadata
    lines.append("## Metadata")
    lines.append("")
    lines.append(f"- **Author**: {pr.get('author')}")
    lines.append(f"- **URL**: {pr.get('url')}")
    if pr.get("merged_at"):
        lines.append(f"- **Merged**: {format_date(pr.get('merged_at'))}")
    if pr.get("labels"):
        labels = ", ".join([f"`{l}`" for l in pr["labels"]])
        lines.append(f"- **Labels**: {labels}")
    if pr.get("diff_url"):
        lines.append(f"- **Diff**: {pr.get('diff_url')}")
    lines.append("")

    # Scope
    if scope:
        lines.append("## Scope")
        lines.append("")
        if scope.get("files_touched"):
            lines.append("### Files Touched")
            for f in scope["files_touched"]:
                lines.append(f"- `{f}`")
            lines.append("")
        if scope.get("components"):
            lines.append("### Components")
            for c in scope["components"]:
                lines.append(f"- {c}")
            lines.append("")
        if scope.get("pipeline_stages"):
            lines.append("### Pipeline Stages")
            for s in scope["pipeline_stages"]:
                lines.append(f"- {s}")
            lines.append("")

    # Analysis
    if analysis:
        lines.append("## Analysis")
        lines.append("")

        # Intent
        intent = analysis.get("intent", {})
        if intent:
            lines.append("### Intent")
            lines.append("")
            if intent.get("summary"):
                lines.append(intent["summary"])
                lines.append("")
            if intent.get("issue_links"):
                lines.append("**Related Issues:**")
                for link in intent["issue_links"]:
                    lines.append(f"- {link}")
                lines.append("")

        # Direct Changes
        direct_changes = analysis.get("direct_changes", [])
        if direct_changes:
            lines.append("### Direct Changes")
            lines.append("")
            for i, change in enumerate(direct_changes, 1):
                lines.append(f"#### {i}. {change.get('summary', 'Change')}")
                lines.append("")
                if change.get("component"):
                    lines.append(f"**Component**: {change['component']}")
                    lines.append("")
                if change.get("evidence"):
                    lines.append("<details>")
                    lines.append("<summary>Evidence</summary>")
                    lines.append("")
                    for ev in change["evidence"]:
                        if ev.get("path"):
                            loc = f":{ev['loc']}" if ev.get("loc") else ""
                            lines.append(f"**{ev.get('path')}{loc}**")
                            if ev.get("url"):
                                lines.append(f"[View on GitHub]({ev['url']})")
                        if ev.get("snippet"):
                            lines.append("```julia")
                            lines.append(ev["snippet"].rstrip())
                            lines.append("```")
                        lines.append("")
                    lines.append("</details>")
                    lines.append("")

        # Secondary Effects
        secondary = analysis.get("secondary_effects", [])
        if secondary:
            lines.append("### Secondary Effects")
            lines.append("")
            for effect in secondary:
                lines.append(f"#### {effect.get('effect', 'Effect')}")
                lines.append("")
                if effect.get("likelihood") or effect.get("impact"):
                    lines.append(f"**Likelihood**: {effect.get('likelihood', 'N/A')} | **Impact**: {effect.get('impact', 'N/A')}")
                    lines.append("")
                if effect.get("mechanism"):
                    lines.append("<details>")
                    lines.append("<summary>Mechanism</summary>")
                    lines.append("")
                    lines.append("```")
                    lines.append(effect["mechanism"].rstrip())
                    lines.append("```")
                    lines.append("</details>")
                    lines.append("")
                if effect.get("downstream_surfaces"):
                    lines.append("**Downstream Surfaces:**")
                    for s in effect["downstream_surfaces"]:
                        lines.append(f"- {s}")
                    lines.append("")

        # Compatibility
        compat = analysis.get("compatibility", {})
        if compat:
            lines.append("### Compatibility")
            lines.append("")
            if compat.get("internal_api"):
                lines.append("#### Internal API Changes")
                for api in compat["internal_api"]:
                    if isinstance(api, str):
                        lines.append(f"- {api}")
                    else:
                        lines.append(f"- **{api.get('field', 'Field')}**: {api.get('change', '')}")
                lines.append("")
            if compat.get("behavioral"):
                lines.append("#### Behavioral Changes")
                for b in compat["behavioral"]:
                    if isinstance(b, str):
                        lines.append(f"- {b}")
                    else:
                        change = b.get('change', str(b))
                        impact = b.get('impact', '')
                        if impact:
                            lines.append(f"- {change} *(Impact: {impact})*")
                        else:
                            lines.append(f"- {change}")
                lines.append("")

        # Performance
        perf = analysis.get("performance", {})
        if perf:
            lines.append("### Performance")
            lines.append("")
            if perf.get("compile_time"):
                lines.append("**Compile Time:**")
                for p in perf["compile_time"]:
                    if isinstance(p, str):
                        lines.append(f"- {p}")
                    else:
                        lines.append(f"- {p.get('impact', str(p))}")
                lines.append("")
            if perf.get("runtime"):
                lines.append("**Runtime:**")
                for p in perf["runtime"]:
                    if isinstance(p, str):
                        lines.append(f"- {p}")
                    else:
                        lines.append(f"- {p.get('impact', str(p))}")
                lines.append("")

        # Risk
        risk = analysis.get("risk", {})
        if risk:
            lines.append("### Risk Assessment")
            lines.append("")
            lines.append(f"**Level**: {risk.get('level', 'N/A')}")
            lines.append("")
            if risk.get("rationale"):
                lines.append("**Rationale:**")
                for r in risk["rationale"]:
                    lines.append(f"- {r}")
                lines.append("")

        # Recommendations
        recs = analysis.get("recommendations", [])
        if recs:
            lines.append("### Recommendations")
            lines.append("")
            for r in recs:
                lines.append(f"- {r}")
            lines.append("")

    return "\n".join(lines)


def convert_file(yaml_path, output_dir=None):
    """Convert a single YAML file to markdown."""
    yaml_path = Path(yaml_path)
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        md_path = output_dir / yaml_path.with_suffix(".md").name
    else:
        md_path = yaml_path.with_suffix(".md")

    markdown = yaml_to_markdown(yaml_path)
    with open(md_path, "w") as f:
        f.write(markdown)

    print(f"Converted: {yaml_path} -> {md_path}")
    return md_path


def convert_directory(input_dir, output_dir=None):
    """Convert all YAML files in a directory."""
    input_dir = Path(input_dir)
    count = 0
    skipped = 0

    for yaml_file in input_dir.rglob("*.yaml"):
        rel_path = yaml_file.relative_to(input_dir)
        if output_dir:
            out_subdir = Path(output_dir) / rel_path.parent
        else:
            out_subdir = yaml_file.parent

        try:
            convert_file(yaml_file, out_subdir)
            count += 1
        except Exception as e:
            print(f"Skipping: {yaml_file} (error: {e})")
            skipped += 1

    print(f"\nConverted {count} files, skipped {skipped}")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python convert_analysis_to_markdown.py <yaml_file>")
        print("  python convert_analysis_to_markdown.py <input_dir> [output_dir]")
        print()
        print("Examples:")
        print("  python convert_analysis_to_markdown.py analyses/pr_55601.yaml")
        print("  python convert_analysis_to_markdown.py analyses/ analyses-markdown/")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    if input_path.is_file():
        convert_file(input_path, output_dir)
    elif input_path.is_dir():
        convert_directory(input_path, output_dir)
    else:
        print(f"Error: {input_path} not found")
        sys.exit(1)


if __name__ == "__main__":
    main()
