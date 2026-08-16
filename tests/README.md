# repro-tools Test Suite

Comprehensive test suite for the repro-tools package.

## Test Organization

### Unit Tests
- **test_core.py**: Core provenance tracking functions
- **test_publishing.py**: Publishing workflow and safety checks
- **test_auto_provenance.py**: Automatic provenance system
- **test_error_handling.py**: Error handling and validation

## Running Tests

### All Tests
```bash
make test
```

### Specific Test File
```bash
pytest tests/test_core.py -v
```

### Specific Test Class or Function
```bash
pytest tests/test_publishing.py::TestPublishAnalyses::test_publish_clean_repo -v
```

### With Coverage
```bash
make coverage
```

## Test Markers

- **@pytest.mark.integration**: Integration tests (vs unit tests)
- **@pytest.mark.slow**: Slow tests requiring Julia installation (~5-10 min)

## Test Categories

### Fast Tests (Seconds)
- Unit tests for all modules
- Python-only project generation
- Python environment setup
- Python example execution

### Slow Tests (Minutes)
- Julia environment installation (~5-10 min)
- Julia example execution
- Multi-language project setup

## CI/CD Recommendations

**Pull Request CI** (fast feedback):
```bash
pytest -v -m "not slow"
```

**Nightly/Weekly CI** (comprehensive):
```bash
pytest -v
```

## Test Fixtures

### temp_output_dir
Creates temporary directory for test project output. Automatically cleaned up after test.

Usage:
```python
def test_something(temp_output_dir):
    create_project(
        name="Test Project",
        slug="test-proj",
        output_dir=temp_output_dir,
        languages=["python"],
    )
    project_dir = temp_output_dir / "test-proj"
    assert project_dir.exists()
```

## Debugging Failed Tests

### Verbose Output
```bash
pytest -vv tests/test_integration.py::TestPythonEnvironment::test_python_environment_setup
```

### Print Statements
```bash
pytest -s tests/test_integration.py
```

### Keep Test Directories
Modify test to not use tempfile, or add breakpoint:
```python
import pdb

pdb.set_trace()
```

### Check Test Logs
Integration tests create projects in temporary directories. If test fails, check:
- output/logs/*.log files in test project
- stderr from make commands (captured in test assertions)

## Writing New Tests

### Unit Test Template
```python
def test_something():
    """Test description."""
    # Setup
    ...
    
    # Execute
    result = function_under_test()
    
    # Assert
    assert result == expected
```

### Integration Test Template (Fast)
```python
@pytest.mark.integration
def test_python_workflow(temp_output_dir):
    """Test Python-only workflow (fast)."""
    create_project(
        name="Test",
        slug="test",
        output_dir=temp_output_dir,
        languages=["python"],
    )
    
    project_dir = temp_output_dir / "test"
    
    # Run make command
    result = subprocess.run(
        ["make", "environment"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        timeout=600,
    )
    
    assert result.returncode == 0
    assert (project_dir / ".env" / "bin" / "python").exists()
```

### Integration Test Template (Slow)
```python
@pytest.mark.integration
@pytest.mark.slow
def test_julia_workflow(temp_output_dir):
    """Test Julia workflow (slow - ~10 min)."""
    create_project(
        name="Test",
        slug="test",
        output_dir=temp_output_dir,
        languages=["python", "julia"],
    )
    
    project_dir = temp_output_dir / "test"
    
    # Setup environment (installs Julia)
    result = subprocess.run(
        ["make", "environment"],
        cwd=project_dir,
        capture_output=True,
        timeout=900,  # 15 minutes
    )
    
    assert result.returncode == 0
    julia_bin = project_dir / ".julia" / "pyjuliapkg" / "install" / "bin" / "julia"
    assert julia_bin.exists()
```

## Performance Notes

- **Python environment**: ~5 minutes (conda install)
- **Julia installation**: ~5-10 minutes (download + precompilation)
- **Python examples**: <10 seconds
- **Julia examples**: ~30 seconds (first run with precompilation)

## Current Status

Total tests: 100+ (83 unit + ~20 integration)
- Unit tests: All passing ✅
- Integration tests (fast): All passing ✅
- Integration tests (slow): Run separately due to time

