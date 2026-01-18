# Migration Guide: project_template → repro-tools

This guide shows how to migrate `project_template` to use the new `repro-tools` package.

## What Changes

**Before**: Provenance/publishing code lives in `project_template/scripts/`

**After**: Import from centralized `repro-tools` package

## Benefits

1. **Single source of truth**: All projects use same package
2. **Easy updates**: Fix bug once, all projects get fix
3. **Teaching-friendly**: Students just `pip install repro-tools`
4. **No duplication**: Remove ~500 lines of copied code per project
5. **Professional**: Proper package structure, versioning, tests

## Migration Steps

### 1. Install Package

Add to `env/python.yml`:

```yaml
dependencies:
  - pandas
  - matplotlib
  - pyyaml
  - pip:
    - juliacall>=0.9.14
    - -e /home/stanton/01_work/infrastructure/40_lib/python/repro-tools  # NEW
```

Then reinstall environment:
```bash
make -C env python-env
```

### 2. Update Build Scripts

**Old** (`build_price_base.py`):
```python
from scripts.provenance import auto_build_record

auto_build_record(
    out_meta=args.out_meta,
    inputs=[args.data],
    outputs=[args.out_fig, args.out_table],
)
```

**New**:
```python
from repro_tools import auto_build_record

auto_build_record(
    out_meta=args.out_meta,
    inputs=[args.data],
    outputs=[args.out_fig, args.out_table],
)
```

### 3. Update Makefile Publishing

**Option A**: Use command-line tools

```makefile
publish-figures:
	repro-publish analyses \
		--project-root . \
		--paper-root $(PAPER_DIR) \
		--names "$(PUBLISH_ANALYSES)" \
		--kinds figures \
		$(if $(filter 1,$(REQUIRE_CURRENT_HEAD)),--require-current-head)
```

**Option B**: Keep Python wrappers

```python
# scripts/publish_artifacts.py (simplified wrapper)
from repro_tools import publish_analyses

# Just call the package function
publish_analyses(...)
```

### 4. Remove Old Scripts (Optional)

After migration, can remove:
- `scripts/provenance.py` (replaced by repro_tools.core)
- `scripts/publish_artifacts.py` (replaced by repro_tools.publish)
- `scripts/publish_specific_files.py` (replaced by repro_tools.publish)

**Keep**:
- `scripts/check_git_state.py` (project-specific wrapper)
- `scripts/record_provenance.py` (project-specific wrapper)
- `config.py` (project-specific configuration)

### 5. Test Migration

```bash
# Clean rebuild
make clean
make all

# Test publishing
make publish PUBLISH_ANALYSES="price_base"

# Verify provenance
cat paper/provenance.yml
```

## Backwards Compatibility

The package API is designed to match existing usage:

```python
# These imports work identically
from scripts.provenance import auto_build_record  # OLD
from repro_tools import auto_build_record         # NEW

# Function signatures unchanged
auto_build_record(
    out_meta=Path("..."),
    inputs=[...],
    outputs=[...],
)
```

## Gradual Migration

Can migrate incrementally:

1. **Phase 1**: Install package, update 1 build script
2. **Phase 2**: Update all build scripts
3. **Phase 3**: Update Makefile publishing
4. **Phase 4**: Remove old scripts/

## Future Projects

For new projects:

1. Copy `project_template/` as base
2. Already uses `repro-tools` (no migration needed)
3. All projects share same infrastructure
4. Bug fixes propagate automatically

## Testing Strategy

```bash
# Build with old code (baseline)
git checkout <pre-migration-commit>
make clean && make all
cp -r output output.old

# Build with new code
git checkout <post-migration-commit>
make -C env python-env  # Install repro-tools
make clean && make all

# Compare outputs
diff -r output.old/figures output/figures
diff -r output.old/tables output/tables
```

Provenance files will differ (different git commits) but outputs should be identical.

## Troubleshooting

**ImportError: No module named 'repro_tools'**
```bash
# Check installation
pip list | grep repro-tools
# Should show: repro-tools @ file:///home/stanton/01_work/infrastructure/...

# Reinstall if needed
make -C env python-env
```

**Different provenance format**
- Package uses same YAML format
- Only difference: cleaner code, same output

**Publishing fails**
- Check git safety checks are configured correctly
- Package uses same safety logic as before

## Documentation

- Package README: `/home/stanton/01_work/infrastructure/40_lib/python/repro-tools/README.md`
- Quick start: `/home/stanton/01_work/infrastructure/40_lib/python/repro-tools/QUICKSTART.md`
- Examples: `/home/stanton/01_work/infrastructure/40_lib/python/repro-tools/examples/`

## Questions?

The package is local to your disk, so you can:
- Read the source code directly
- Modify if needed (editable install)
- Add project-specific wrappers if desired

**Location**: `/home/stanton/01_work/infrastructure/40_lib/python/repro-tools/`
