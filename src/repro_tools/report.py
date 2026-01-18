#!/usr/bin/env python3
"""
generate_replication_report.py

Generate a comprehensive replication report for journal submission.
Creates HTML/Markdown report with all provenance, system info, and outputs.

Usage:
    python scripts/generate_replication_report.py [--format html|markdown]
"""
import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone
import yaml
import hashlib


def load_yaml_safe(filepath):
    """Load YAML file safely."""
    try:
        with open(filepath) as f:
            return yaml.safe_load(f)
    except Exception as e:
        return {"error": str(e)}


def format_timestamp(ts_str):
    """Format ISO timestamp for display."""
    try:
        dt = datetime.fromisoformat(ts_str)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except:
        return ts_str


class ReplicationReportGenerator:
    """Generate replication report."""
    
    def __init__(self, repo_root, output_file, format="html"):
        self.repo_root = Path(repo_root)
        self.output_file = Path(output_file)
        self.format = format
        self.content = []
    
    def generate(self):
        """Generate complete report."""
        print(f"Generating replication report...")
        
        self.add_header()
        self.add_overview()
        self.add_system_info()
        self.add_data_info()
        self.add_artifacts_info()
        self.add_provenance_details()
        self.add_verification_commands()
        self.add_footer()
        
        self.write_report()
        print(f"✅ Report generated: {self.output_file}")
    
    def add_header(self):
        """Add report header."""
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        if self.format == "html":
            self.content.append(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Replication Package Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif; 
               max-width: 1200px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; border-bottom: 2px solid #95a5a6; padding-bottom: 5px; margin-top: 30px; }}
        h3 {{ color: #7f8c8d; }}
        .meta {{ color: #7f8c8d; font-size: 0.9em; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #3498db; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        code {{ background-color: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-family: monospace; }}
        pre {{ background-color: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }}
        .success {{ color: #27ae60; }}
        .warning {{ color: #f39c12; }}
        .error {{ color: #e74c3c; }}
        .checksum {{ font-family: monospace; font-size: 0.85em; color: #7f8c8d; }}
    </style>
</head>
<body>
    <h1>🔬 Replication Package Report</h1>
    <p class="meta">Generated: {generated_at}</p>
""")
        else:  # markdown
            self.content.append(f"""# Replication Package Report

**Generated:** {generated_at}

---

""")
    
    def add_overview(self):
        """Add overview section."""
        # Get git info
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=self.repo_root,
            )
            commit = result.stdout.strip() if result.returncode == 0 else "N/A"
            
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                cwd=self.repo_root,
            )
            branch = result.stdout.strip() if result.returncode == 0 else "N/A"
        except:
            commit = "N/A"
            branch = "N/A"
        
        if self.format == "html":
            self.content.append(f"""
    <h2>📋 Overview</h2>
    <table>
        <tr><th>Property</th><th>Value</th></tr>
        <tr><td>Repository</td><td>{self.repo_root.name}</td></tr>
        <tr><td>Git Commit</td><td><code>{commit}</code></td></tr>
        <tr><td>Git Branch</td><td><code>{branch}</code></td></tr>
    </table>
""")
        else:
            self.content.append(f"""## Overview

- **Repository:** {self.repo_root.name}
- **Git Commit:** `{commit}`
- **Git Branch:** `{branch}`

""")
    
    def add_system_info(self):
        """Add system information."""
        system_info_file = self.repo_root / "output" / "system_info.yml"
        
        if not system_info_file.exists():
            if self.format == "html":
                self.content.append(f"""
    <h2>💻 Computational Environment</h2>
    <p class="warning">⚠️ System info not available. Run: make system-info</p>
""")
            else:
                self.content.append(f"""## Computational Environment

⚠️ System info not available. Run: `make system-info`

""")
            return
        
        system_info = load_yaml_safe(system_info_file)
        
        if "error" in system_info:
            return
        
        sys_data = system_info.get("system", {})
        
        if self.format == "html":
            self.content.append(f"""
    <h2>💻 Computational Environment</h2>
    <table>
        <tr><th>Component</th><th>Version/Details</th></tr>
        <tr><td>Operating System</td><td>{sys_data.get('os', 'N/A')}</td></tr>
        <tr><td>Architecture</td><td>{sys_data.get('architecture', 'N/A')}</td></tr>
        <tr><td>Python Version</td><td>{sys_data.get('python_version', 'N/A').split()[0]}</td></tr>
    </table>
    
    <h3>Python Packages</h3>
    <details>
        <summary>View installed packages ({len(system_info.get('python_packages', {}))} packages)</summary>
        <pre>{yaml.dump(system_info.get('python_packages', {}), default_flow_style=False)}</pre>
    </details>
""")
        else:
            self.content.append(f"""## Computational Environment

- **Operating System:** {sys_data.get('os', 'N/A')}
- **Architecture:** {sys_data.get('architecture', 'N/A')}
- **Python Version:** {sys_data.get('python_version', 'N/A').split()[0]}

### Python Packages

```
{yaml.dump(system_info.get('python_packages', {}), default_flow_style=False)}
```

""")
    
    def add_data_info(self):
        """Add data information."""
        checksums_file = self.repo_root / "data" / "CHECKSUMS.txt"
        
        if not checksums_file.exists():
            return
        
        with open(checksums_file) as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        if self.format == "html":
            self.content.append(f"""
    <h2>📊 Data Files</h2>
    <table>
        <tr><th>File</th><th>SHA256 Checksum</th></tr>
""")
            for line in lines:
                parts = line.split()
                if len(parts) >= 2:
                    checksum = parts[0]
                    filename = ' '.join(parts[1:])
                    self.content.append(f"""        <tr><td><code>{filename}</code></td><td class="checksum">{checksum[:16]}...</td></tr>\n""")
            
            self.content.append("""    </table>
""")
        else:
            self.content.append(f"""## Data Files

| File | SHA256 Checksum |
|------|----------------|
""")
            for line in lines:
                parts = line.split()
                if len(parts) >= 2:
                    checksum = parts[0]
                    filename = ' '.join(parts[1:])
                    self.content.append(f"""| `{filename}` | `{checksum[:16]}...` |\n""")
            
            self.content.append("\n")
    
    def add_artifacts_info(self):
        """Add artifacts information."""
        prov_dir = self.repo_root / "output" / "provenance"
        
        if not prov_dir.exists():
            return
        
        prov_files = sorted(prov_dir.glob("*.yml"))
        
        if self.format == "html":
            self.content.append(f"""
    <h2>📦 Artifacts ({len(prov_files)} total)</h2>
    <table>
        <tr><th>Artifact</th><th>Built</th><th>Figure</th><th>Table</th></tr>
""")
            for prov_file in prov_files:
                data = load_yaml_safe(prov_file)
                artifact = prov_file.stem
                built_at = format_timestamp(data.get('built_at_utc', 'N/A'))
                
                fig_path = self.repo_root / "output" / "figures" / f"{artifact}.pdf"
                tbl_path = self.repo_root / "output" / "tables" / f"{artifact}.tex"
                
                fig_status = "✅" if fig_path.exists() else "❌"
                tbl_status = "✅" if tbl_path.exists() else "❌"
                
                self.content.append(f"""        <tr>
            <td><code>{artifact}</code></td>
            <td>{built_at}</td>
            <td>{fig_status}</td>
            <td>{tbl_status}</td>
        </tr>
""")
            
            self.content.append("""    </table>
""")
        else:
            self.content.append(f"""## Artifacts ({len(prov_files)} total)

| Artifact | Built | Figure | Table |
|----------|-------|--------|-------|
""")
            for prov_file in prov_files:
                data = load_yaml_safe(prov_file)
                artifact = prov_file.stem
                built_at = format_timestamp(data.get('built_at_utc', 'N/A'))
                
                fig_path = self.repo_root / "output" / "figures" / f"{artifact}.pdf"
                tbl_path = self.repo_root / "output" / "tables" / f"{artifact}.tex"
                
                fig_status = "✅" if fig_path.exists() else "❌"
                tbl_status = "✅" if tbl_path.exists() else "❌"
                
                self.content.append(f"""| `{artifact}` | {built_at} | {fig_status} | {tbl_status} |\n""")
            
            self.content.append("\n")
    
    def add_provenance_details(self):
        """Add detailed provenance for each artifact."""
        prov_dir = self.repo_root / "output" / "provenance"
        
        if not prov_dir.exists():
            return
        
        prov_files = sorted(prov_dir.glob("*.yml"))
        
        if self.format == "html":
            self.content.append(f"""
    <h2>📋 Detailed Provenance</h2>
""")
            for prov_file in prov_files:
                data = load_yaml_safe(prov_file)
                artifact = prov_file.stem
                
                self.content.append(f"""
    <h3>{artifact}</h3>
    <details>
        <summary>View provenance details</summary>
        <pre>{yaml.dump(data, default_flow_style=False, sort_keys=False)}</pre>
    </details>
""")
        else:
            self.content.append(f"""## Detailed Provenance

""")
            for prov_file in prov_files:
                data = load_yaml_safe(prov_file)
                artifact = prov_file.stem
                
                self.content.append(f"""### {artifact}

```yaml
{yaml.dump(data, default_flow_style=False, sort_keys=False)}
```

""")
    
    def add_verification_commands(self):
        """Add verification commands."""
        if self.format == "html":
            self.content.append(f"""
    <h2>✅ Verification Commands</h2>
    <p>Run these commands to verify the replication package:</p>
    
    <h3>1. Environment Setup</h3>
    <pre>make environment</pre>
    
    <h3>2. Verify Environment</h3>
    <pre>make verify</pre>
    
    <h3>3. Build All Artifacts</h3>
    <pre>make all</pre>
    
    <h3>4. Verify Outputs</h3>
    <pre>make test-outputs</pre>
    
    <h3>5. Run Tests</h3>
    <pre>make test</pre>
    
    <h3>6. Verify Data Checksums</h3>
    <pre>cd data && sha256sum -c CHECKSUMS.txt</pre>
""")
        else:
            self.content.append(f"""## Verification Commands

Run these commands to verify the replication package:

### 1. Environment Setup
```bash
make environment
```

### 2. Verify Environment
```bash
make verify
```

### 3. Build All Artifacts
```bash
make all
```

### 4. Verify Outputs
```bash
make test-outputs
```

### 5. Run Tests
```bash
make test
```

### 6. Verify Data Checksums
```bash
cd data && sha256sum -c CHECKSUMS.txt
```

""")
    
    def add_footer(self):
        """Add report footer."""
        if self.format == "html":
            self.content.append(f"""
    <hr>
    <p class="meta">Report generated by generate_replication_report.py</p>
</body>
</html>
""")
        else:
            self.content.append(f"""---

*Report generated by generate_replication_report.py*
""")
    
    def write_report(self):
        """Write report to file."""
        with open(self.output_file, 'w') as f:
            f.write(''.join(self.content))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--format",
        choices=["html", "markdown"],
        default="html",
        help="Output format (default: html)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file path (default: output/replication_report.{format})",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root directory",
    )
    args = parser.parse_args()
    
    if not args.output:
        ext = "html" if args.format == "html" else "md"
        args.output = args.repo_root / "output" / f"replication_report.{ext}"
    
    # Ensure output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)
    
    generator = ReplicationReportGenerator(
        args.repo_root,
        args.output,
        format=args.format,
    )
    generator.generate()
    
    print()
    print(f"View report: {args.output}")
    if args.format == "html":
        print(f"Open in browser: file://{args.output.absolute()}")


if __name__ == "__main__":
    main()
