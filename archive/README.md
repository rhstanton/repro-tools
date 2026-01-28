# Archived: Project Scaffolding

**Status**: Archived (January 28, 2026)

This directory contains the original project scaffolding functionality that has been **replaced by direct cloning of project_template**.

## What's Archived

- `scaffold.py` - Project generation script
- `templates/` - Template files with placeholder substitution
- `test_integration.py` - Integration tests for scaffolding

## Why Archived

The scaffolding approach was designed to generate new projects from templates. However, this created maintenance overhead:

1. **Duplication**: Template files duplicated actual project_template files
2. **Sync issues**: Templates could drift out of sync with project_template
3. **Complexity**: Placeholder substitution system was complex for minimal benefit

## New Approach

Instead of generating projects from templates, users now:

1. **Clone project_template directly**: `git clone https://github.com/rhstanton/project_template.git my-project`
2. **Customize via bootstrap.py**: `python bootstrap.py --remove-julia --rename "My Project"`

Benefits:
- ✅ No template sync issues (project_template IS the template)
- ✅ Simpler workflow (clone + customize vs generate)
- ✅ Better separation of concerns (repro-tools = library, project_template = reference)

## If You Need the Old Scaffolding

To restore the scaffolding functionality:

```bash
# In repro-tools repo
git mv archive/scaffold.py src/repro_tools/
git mv archive/templates src/repro_tools/
git mv archive/test_integration.py tests/
```

Then update:
- `pyproject.toml`: Add `repro-new-project` CLI entry point
- `src/repro_tools/cli.py`: Add `new_project()` function

## Archive Date

Archived: January 28, 2026  
Last working version: v0.3.3  
Replacement: project_template/bootstrap.py

## See Also

- [project_template](https://github.com/rhstanton/project_template) - Direct clone approach
- [project_template/bootstrap.py](https://github.com/rhstanton/project_template/blob/main/bootstrap.py) - Post-clone customization
