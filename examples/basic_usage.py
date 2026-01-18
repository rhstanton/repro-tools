"""Basic usage example for repro-tools."""

from pathlib import Path
import sys

# Add parent to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from repro_tools import auto_build_record

# Simulate a simple analysis
data_file = Path("data.csv")
figure_file = Path("output/figure.pdf")
table_file = Path("output/table.tex")
provenance_file = Path("output/provenance/example.yml")

# Create dummy output files (in real usage, your analysis creates these)
figure_file.parent.mkdir(parents=True, exist_ok=True)
table_file.parent.mkdir(parents=True, exist_ok=True)
provenance_file.parent.mkdir(parents=True, exist_ok=True)

figure_file.write_text("Dummy figure content")
table_file.write_text("Dummy table content")

# Record provenance
print("Recording provenance...")
auto_build_record(
    out_meta=provenance_file,
    inputs=[data_file],
    outputs=[figure_file, table_file],
    artifact_name="example",  # Optional: will auto-detect from script name
)

print(f"✓ Provenance recorded: {provenance_file}")
print(f"\nContents:")
print(provenance_file.read_text())
