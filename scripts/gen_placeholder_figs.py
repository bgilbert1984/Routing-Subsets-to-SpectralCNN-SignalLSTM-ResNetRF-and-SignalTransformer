#!/usr/bin/env python3
"""
Generate placeholder figures for specialization paper.
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


def create_placeholder_figures():
    """Create placeholder figures for the specialization paper."""
    
    # Create output directory
    fig_dir = Path("figs")
    fig_dir.mkdir(exist_ok=True)
    
    # Figure 1: Specialization gain vs generalist
    fig, ax = plt.subplots(figsize=(8, 5))
    
    families = ["PSK", "QAM", "Analog"]
    generalist_acc = [85.2, 82.1, 78.9]
    specialist_acc = [88.6, 84.2, 83.6]
    
    x = np.arange(len(families))
    width = 0.35
    
    ax.bar(x - width/2, generalist_acc, width, label='Generalist', alpha=0.8)
    ax.bar(x + width/2, specialist_acc, width, label='Specialist', alpha=0.8)
    
    ax.set_xlabel('Modulation Family')
    ax.set_ylabel('Accuracy (%)')
    ax.set_title('Generalist vs Specialist Accuracy per Modulation Family')
    ax.set_xticks(x)
    ax.set_xticklabels(families)
    ax.legend()
    ax.grid(axis='y', linestyle=':', linewidth=0.5)
    
    # Add gain annotations
    gains = [spec - gen for spec, gen in zip(specialist_acc, generalist_acc)]
    for i, gain in enumerate(gains):
        ax.annotate(f'+{gain:.1f}pp', 
                   xy=(i, specialist_acc[i]), 
                   xytext=(i, specialist_acc[i] + 1.5),
                   ha='center', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(fig_dir / "specialization_gain_vs_generalist.pdf", bbox_inches='tight', dpi=300)
    plt.close()
    
    # Figure 2: Family confusion deltas (specialization gains)
    fig, ax = plt.subplots(figsize=(8, 5))
    
    x = np.arange(len(families))
    ax.bar(x, gains, color=['#1f77b4', '#ff7f0e', '#2ca02c'], alpha=0.8)
    
    ax.set_xlabel('Modulation Family')
    ax.set_ylabel('Specialist Gain (percentage points)')
    ax.set_title('Accuracy Delta (Specialist - Generalist) per Family')
    ax.set_xticks(x)
    ax.set_xticklabels(families)
    ax.axhline(0.0, color='black', linewidth=0.8)
    ax.grid(axis='y', linestyle=':', linewidth=0.5)
    
    # Add value labels on bars
    for i, gain in enumerate(gains):
        ax.text(i, gain + 0.1, f'{gain:.1f}', ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(fig_dir / "family_confusion_deltas.pdf", bbox_inches='tight', dpi=300)
    plt.close()
    
    print("Generated placeholder figures:")
    print("- figs/specialization_gain_vs_generalist.pdf")
    print("- figs/family_confusion_deltas.pdf")


if __name__ == "__main__":
    create_placeholder_figures()