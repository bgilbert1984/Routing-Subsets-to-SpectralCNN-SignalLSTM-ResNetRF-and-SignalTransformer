#!/usr/bin/env python3
"""
Generate specialization gain vs generalist figures and TeX artifacts.

Reads logs/metrics_*.jsonl entries with:
    {"study": "specialization_per_modulation_family", "data": {...}}

Expected per-entry fields inside "data":
    - family       : str  (e.g. "psk", "qam", "analog")
    - model_role   : str  ("generalist" or "specialist")
    - routing_mode : str  (e.g. "oracle", "predicted") [optional]
    - correct      : bool (1 if prediction correct, else 0)

Outputs:
    figs/specialization_gain_vs_generalist.pdf
    figs/family_confusion_deltas.pdf   (delta accuracy per family)
    data/specialization_callouts.tex
    data/specialization_table.tex
"""

import argparse
import json
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate specialization vs generalist figures and TeX."
    )
    p.add_argument(
        "--logdir",
        type=Path,
        default=Path("../logs"),
        help="Directory containing metrics_*.jsonl (default: ../logs)",
    )
    p.add_argument(
        "--pattern",
        type=str,
        default="metrics_*.jsonl",
        help="Glob pattern for metrics files (default: metrics_*.jsonl)",
    )
    p.add_argument(
        "--outdir",
        type=Path,
        default=Path("figs"),
        help="Output directory for figures (default: figs)",
    )
    p.add_argument(
        "--datadir",
        type=Path,
        default=Path("data"),
        help="Output directory for TeX data files (default: data)",
    )
    p.add_argument(
        "--study",
        type=str,
        default="specialization_per_modulation_family",
        help='Study name to filter on in JSON ("study" field).',
    )
    p.add_argument(
        "--routing-mode",
        type=str,
        default="oracle",
        help='Routing mode to focus on (e.g. "oracle" or "predicted"). '
             "If empty, all routing modes are aggregated.",
    )
    return p.parse_args()


def load_metrics(logdir: Path, pattern: str, study: str) -> pd.DataFrame:
    paths: List[Path] = sorted(logdir.glob(pattern))
    if not paths:
        raise SystemExit(f"No metric files found in {logdir} matching {pattern}")

    records = []
    for path in paths:
        with path.open("r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if obj.get("study") != study:
                    continue

                data = obj.get("data", {})
                family = data.get("family") or data.get("true_family")
                role = data.get("model_role") or data.get("role")
                routing = data.get("routing_mode") or data.get("routing") or "none"
                correct = data.get("correct")

                if family is None or role is None or correct is None:
                    # Skip incomplete entries
                    continue

                records.append(
                    {
                        "family": str(family).lower(),
                        "model_role": str(role).lower(),
                        "routing_mode": str(routing).lower(),
                        "correct": bool(correct),
                    }
                )

    if not records:
        raise SystemExit(
            f"No records found for study='{study}' in {logdir} "
            f"(pattern: {pattern})"
        )

    df = pd.DataFrame.from_records(records)
    return df


def summarize(df: pd.DataFrame, routing_mode: str | None) -> pd.DataFrame:
    df = df.copy()

    if routing_mode:
        routing_mode = routing_mode.lower()
        if "routing_mode" in df.columns:
            mask = df["routing_mode"].str.lower() == routing_mode
            if mask.any():
                df = df[mask]
            else:
                print(
                    f"[!] No entries found for routing_mode={routing_mode}; "
                    "using all routing modes."
                )

    # Aggregate accuracy per (family, model_role, routing_mode)
    summary = (
        df.groupby(["family", "model_role", "routing_mode"])
        .agg(
            n=("correct", "size"),
            accuracy=("correct", "mean"),
        )
        .reset_index()
    )

    # Sort for nicer tables/plots
    summary = summary.sort_values(["family", "model_role"]).reset_index(drop=True)
    return summary


def write_callouts_tex(summary: pd.DataFrame, datadir: Path) -> None:
    datadir.mkdir(parents=True, exist_ok=True)
    callouts_path = datadir / "specialization_callouts.tex"

    # Map canonical family names to macro prefixes
    family_to_macro = {
        "psk": "PSK",
        "qam": "QAM",
        "analog": "Analog",
    }

    lines: List[str] = []

    for fam, macro_prefix in family_to_macro.items():
        sub = summary[summary["family"] == fam]
        if sub.empty:
            continue

        gen = sub[sub["model_role"] == "generalist"]
        spec = sub[sub["model_role"] == "specialist"]

        if gen.empty or spec.empty:
            continue

        gen_acc = float(gen["accuracy"].iloc[0])
        spec_acc = float(spec["accuracy"].iloc[0])
        gain = (spec_acc - gen_acc) * 100.0  # absolute percentage points

        lines.append(
            f"\\newcommand{{\\{macro_prefix}GeneralistAcc}}"
            "{{{:.1f}}}".format(gen_acc * 100.0)
        )
        lines.append(
            f"\\newcommand{{\\{macro_prefix}SpecialistAcc}}"
            "{{{:.1f}}}".format(spec_acc * 100.0)
        )
        lines.append(
            f"\\newcommand{{\\{macro_prefix}Gain}}"
            "{{{:.1f}}}".format(gain)
        )

    if not lines:
        lines.append("% No specialization callouts available; generated empty file.")

    callouts_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[+] Wrote {callouts_path}")


def write_table_tex(summary: pd.DataFrame, datadir: Path) -> None:
    datadir.mkdir(parents=True, exist_ok=True)
    table_path = datadir / "specialization_table.tex"

    lines: List[str] = []
    lines.append("\\begin{table}[t]")
    lines.append("  \\centering")
    lines.append("  \\caption{Generalist vs specialist accuracy per modulation family.}")
    lines.append("  \\label{tab:specialization-results}")
    lines.append("  \\begin{tabular}{llllr}")
    lines.append("    \\toprule")
    lines.append("    Family & Role & Routing & Acc (\\%) & $N$ \\\\")
    lines.append("    \\midrule")

    for _, row in summary.iterrows():
        family = str(row["family"])
        role = str(row["model_role"])
        routing = str(row["routing_mode"])
        n = int(row["n"])
        acc = float(row["accuracy"]) * 100.0

        line = f"    {family} & {role} & {routing} & {acc:.1f} & {n} \\\\"
        lines.append(line)

    lines.append("    \\bottomrule")
    lines.append("  \\end{tabular}")
    lines.append("\\end{table}")
    lines.append("")

    table_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[+] Wrote {table_path}")


def plot_specialization_gain(summary: pd.DataFrame, outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    fig_path = outdir / "specialization_gain_vs_generalist.pdf"

    families = sorted(summary["family"].unique())
    roles = ["generalist", "specialist"]

    # Build accuracy matrix [family, role]
    acc_matrix = np.zeros((len(families), len(roles))) * np.nan
    for i, fam in enumerate(families):
        for j, role in enumerate(roles):
            sub = summary[(summary["family"] == fam) &
                          (summary["model_role"] == role)]
            if sub.empty:
                continue
            acc_matrix[i, j] = float(sub["accuracy"].iloc[0]) * 100.0

    x = np.arange(len(families))
    width = 0.35

    fig, ax = plt.subplots()
    for j, role in enumerate(roles):
        accs = acc_matrix[:, j]
        ax.bar(
            x + (j - 0.5) * width,
            accs,
            width,
            label=role.capitalize(),
        )

    ax.set_xticks(x)
    ax.set_xticklabels(families)
    ax.set_ylabel("Accuracy (\\%)")
    ax.set_title("Generalist vs specialist accuracy per modulation family")
    ax.legend()
    ax.grid(axis="y", linestyle=":", linewidth=0.5)

    fig.tight_layout()
    fig.savefig(fig_path)
    plt.close(fig)
    print(f"[+] Wrote {fig_path}")


def plot_family_delta(summary: pd.DataFrame, outdir: Path) -> None:
    """
    Plot delta accuracy (specialist - generalist) per family.

    This is saved as family_confusion_deltas.pdf to match the TeX filename,
    but the Y-axis is actually specialization gain (percentage points).
    """
    outdir.mkdir(parents=True, exist_ok=True)
    fig_path = outdir / "family_confusion_deltas.pdf"

    families = sorted(summary["family"].unique())
    deltas = []

    for fam in families:
        sub = summary[summary["family"] == fam]
        gen = sub[sub["model_role"] == "generalist"]
        spec = sub[sub["model_role"] == "specialist"]
        if gen.empty or spec.empty:
            deltas.append(np.nan)
            continue
        gen_acc = float(gen["accuracy"].iloc[0])
        spec_acc = float(spec["accuracy"].iloc[0])
        deltas.append((spec_acc - gen_acc) * 100.0)

    x = np.arange(len(families))
    fig, ax = plt.subplots()
    ax.bar(x, deltas)
    ax.set_xticks(x)
    ax.set_xticklabels(families)
    ax.set_ylabel("Specialist gain (pp)")
    ax.set_title("Accuracy delta (specialist - generalist) per family")
    ax.axhline(0.0, color="black", linewidth=0.8)
    ax.grid(axis="y", linestyle=":", linewidth=0.5)

    fig.tight_layout()
    fig.savefig(fig_path)
    plt.close(fig)
    print(f"[+] Wrote {fig_path}")


def main() -> None:
    args = parse_args()

    df = load_metrics(args.logdir, args.pattern, args.study)
    print(f"[+] Loaded {len(df)} records from {args.logdir}")

    summary = summarize(df, args.routing_mode)
    print("[+] Aggregated summary:")
    print(summary)

    args.outdir.mkdir(parents=True, exist_ok=True)
    args.datadir.mkdir(parents=True, exist_ok=True)

    # Figures
    plot_specialization_gain(summary, args.outdir)
    plot_family_delta(summary, args.outdir)

    # TeX artifacts
    write_callouts_tex(summary, args.datadir)
    write_table_tex(summary, args.datadir)


if __name__ == "__main__":
    main()