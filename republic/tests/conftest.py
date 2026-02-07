import pytest
import sys
import os
from pathlib import Path

# Add project root to path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

@pytest.fixture
def db_path(tmp_path):
    """Create a temporary database for testing."""
    d = tmp_path / "data"
    d.mkdir()
    return d / "test_republic.db"
