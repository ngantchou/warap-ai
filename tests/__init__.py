"""
Djobea AI Test Suite
Professional test organization for comprehensive system testing
"""

import os
import sys
from pathlib import Path

# Add the app directory to Python path for imports
app_dir = Path(__file__).parent.parent / "app"
sys.path.insert(0, str(app_dir))

# Test configuration
TEST_DATABASE_URL = "sqlite:///test_djobea.db"
TEST_ENV = "testing"

# Common test fixtures and utilities
from tests.fixtures.common import *