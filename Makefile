# Makefile for Specialized Models per Modulation Family paper

MAIN = main_specialized_models
PDF = $(MAIN).pdf

# LaTeX build commands
LATEX = pdflatex
BIBTEX = bibtex
LATEX_FLAGS = -interaction=nonstopmode

.PHONY: all clean figs data

all: $(PDF)

$(PDF): $(MAIN).tex refs.bib data/specialization_callouts.tex data/specialization_table.tex figs/specialization_gain_vs_generalist.pdf figs/family_confusion_deltas.pdf
	$(LATEX) $(LATEX_FLAGS) $(MAIN).tex
	$(BIBTEX) $(MAIN)
	$(LATEX) $(LATEX_FLAGS) $(MAIN).tex
	$(LATEX) $(LATEX_FLAGS) $(MAIN).tex
	@echo "✅ Generated $(PDF)"
	@ls -lh $(PDF)

# Generate figures from real data (if logs exist)
figs: scripts/gen_figs_specialization_gain.py
	@echo "Generating figures from log data..."
	cd scripts && python3 gen_figs_specialization_gain.py --logdir ../../logs --study specialization_per_modulation_family

# Generate placeholder figures
figs-placeholder: scripts/gen_placeholder_figs.py
	@echo "Generating placeholder figures..."
	python3 scripts/gen_placeholder_figs.py

# Generate placeholder data files
data: data/specialization_callouts.tex data/specialization_table.tex

data/specialization_callouts.tex data/specialization_table.tex: scripts/gen_figs_specialization_gain.py
	@echo "Generating TeX data files..."
	@mkdir -p data
	cd scripts && python3 gen_figs_specialization_gain.py --logdir ../../logs --study specialization_per_modulation_family || echo "No real data found, using placeholders"

# Clean build artifacts
clean:
	rm -f *.aux *.bbl *.blg *.log *.out *.toc *.lof *.lot *.fdb_latexmk *.fls *.synctex.gz
	rm -f $(PDF)

# Clean everything including generated files
distclean: clean
	rm -f figs/*.pdf
	rm -f data/specialization_*.tex

# Help target
help:
	@echo "Available targets:"
	@echo "  all                - Build the paper (default)"
	@echo "  figs               - Generate figures from real log data"
	@echo "  figs-placeholder   - Generate placeholder figures"
	@echo "  data               - Generate TeX data files from logs"
	@echo "  clean              - Remove LaTeX build artifacts"
	@echo "  distclean          - Remove all generated files"
	@echo "  help               - Show this help message"