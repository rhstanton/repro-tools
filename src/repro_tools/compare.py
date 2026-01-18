"""Output comparison utilities."""

from __future__ import annotations

import difflib
import hashlib
import subprocess
from pathlib import Path
from typing import Optional, Union, Dict, List


def sha256_file(filepath: Path) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def compare_pdfs(file1: Path, file2: Path) -> Union[str, Dict]:
    """Compare two PDF files."""
    if not file1.exists() or not file2.exists():
        return None
    
    hash1 = sha256_file(file1)
    hash2 = sha256_file(file2)
    
    if hash1 == hash2:
        return "identical"
    
    # Try to get metadata
    try:
        result1 = subprocess.run(
            ["pdfinfo", str(file1)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        result2 = subprocess.run(
            ["pdfinfo", str(file2)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        
        if result1.returncode == 0 and result2.returncode == 0:
            pages1 = [line for line in result1.stdout.split('\n') if 'Pages:' in line]
            pages2 = [line for line in result2.stdout.split('\n') if 'Pages:' in line]
            
            return {
                "status": "different",
                "hash1": hash1[:8],
                "hash2": hash2[:8],
                "metadata1": pages1[0] if pages1 else "N/A",
                "metadata2": pages2[0] if pages2 else "N/A",
            }
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    return {
        "status": "different",
        "hash1": hash1[:8],
        "hash2": hash2[:8],
    }


def compare_text_files(file1: Path, file2: Path) -> Union[str, Dict]:
    """Compare two text files and show diff."""
    if not file1.exists() or not file2.exists():
        return None
    
    with open(file1) as f:
        lines1 = f.readlines()
    
    with open(file2) as f:
        lines2 = f.readlines()
    
    if lines1 == lines2:
        return "identical"
    
    # Generate unified diff
    diff = list(difflib.unified_diff(
        lines1,
        lines2,
        fromfile=str(file1),
        tofile=str(file2),
        lineterm='',
    ))
    
    return {
        "status": "different",
        "lines_changed": len([line for line in diff if line.startswith('+') or line.startswith('-')]),
        "diff_preview": '\n'.join(diff[:20]),
    }


def compare_outputs(
    current_dir: Path,
    reference_dir: Path,
    artifacts: Optional[List[str]] = None,
    verbose: bool = False
) -> tuple[bool, str]:
    """
    Compare current outputs with reference outputs.
    
    Returns:
        (all_identical, report_text)
    """
    output_lines = []
    
    if not current_dir.exists():
        return False, f"❌ Current directory not found: {current_dir}"
    
    if not reference_dir.exists():
        return False, f"❌ Reference directory not found: {reference_dir}"
    
    # Auto-detect artifacts if not specified
    if not artifacts:
        fig_dir = current_dir / "figures"
        if fig_dir.exists():
            artifacts = [p.stem for p in fig_dir.glob("*.pdf")]
        else:
            return False, f"❌ No figures found in {fig_dir}"
    
    output_lines.append(f"Comparing outputs: {current_dir} vs {reference_dir}")
    output_lines.append(f"Artifacts: {', '.join(artifacts)}")
    output_lines.append("")
    
    all_identical = True
    
    for artifact in artifacts:
        output_lines.append(f"{'='*60}")
        output_lines.append(f"Artifact: {artifact}")
        output_lines.append(f"{'='*60}")
        
        # Compare figure
        current_fig = current_dir / "figures" / f"{artifact}.pdf"
        ref_fig = reference_dir / "figures" / f"{artifact}.pdf"
        
        output_lines.append(f"\n📊 Figure: {artifact}.pdf")
        if not current_fig.exists():
            output_lines.append(f"   ⚠️  Current version not found")
        elif not ref_fig.exists():
            output_lines.append(f"   ⚠️  Reference version not found (new artifact?)")
        else:
            result = compare_pdfs(current_fig, ref_fig)
            if result == "identical":
                output_lines.append(f"   ✅ Identical")
            elif isinstance(result, dict):
                output_lines.append(f"   ❌ Different")
                output_lines.append(f"      Current hash:   {result['hash1']}...")
                output_lines.append(f"      Reference hash: {result['hash2']}...")
                if 'metadata1' in result:
                    output_lines.append(f"      Current:   {result['metadata1']}")
                    output_lines.append(f"      Reference: {result['metadata2']}")
                all_identical = False
        
        # Compare table
        current_tbl = current_dir / "tables" / f"{artifact}.tex"
        ref_tbl = reference_dir / "tables" / f"{artifact}.tex"
        
        output_lines.append(f"\n📋 Table: {artifact}.tex")
        if not current_tbl.exists():
            output_lines.append(f"   ⚠️  Current version not found")
        elif not ref_tbl.exists():
            output_lines.append(f"   ⚠️  Reference version not found (new artifact?)")
        else:
            result = compare_text_files(current_tbl, ref_tbl)
            if result == "identical":
                output_lines.append(f"   ✅ Identical")
            elif isinstance(result, dict):
                output_lines.append(f"   ❌ Different ({result['lines_changed']} lines changed)")
                all_identical = False
                
                if verbose and result['diff_preview']:
                    output_lines.append(f"\n   Diff preview:")
                    for line in result['diff_preview'].split('\n'):
                        output_lines.append(f"   {line}")
        
        output_lines.append("")
    
    output_lines.append(f"{'='*60}")
    if all_identical:
        output_lines.append("✅ All outputs identical to reference")
    else:
        output_lines.append("⚠️  Some outputs differ from reference")
        output_lines.append("\nTo see detailed diffs for tables:")
        output_lines.append(f"  diff {current_dir}/tables/<artifact>.tex {reference_dir}/tables/<artifact>.tex")
        output_lines.append("\nTo visually compare PDFs:")
        output_lines.append(f"  diff-pdf {current_dir}/figures/<artifact>.pdf {reference_dir}/figures/<artifact>.pdf")
    
    return all_identical, '\n'.join(output_lines)
