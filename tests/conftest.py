"""Shared fixtures and configuration for SwiggyIt tests."""

import sys
from pathlib import Path

import pytest

# Add src/ to import path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


@pytest.fixture
def project_root():
    return PROJECT_ROOT


@pytest.fixture
def input_food_dir(project_root):
    d = project_root / "input" / "food"
    if not d.exists():
        pytest.skip(f"No input/food/ directory at {d}")
    return d


@pytest.fixture
def input_instamart_dir(project_root):
    d = project_root / "input" / "instamart"
    if not d.exists():
        pytest.skip(f"No input/instamart/ directory at {d}")
    return d


@pytest.fixture
def tmp_detail_food(project_root):
    d = project_root / ".tmp" / "detail_food"
    if not d.exists():
        pytest.skip(f"No .tmp/detail_food/ directory at {d}")
    return d


@pytest.fixture
def tmp_detail_instamart(project_root):
    d = project_root / ".tmp" / "detail_instamart"
    if not d.exists():
        pytest.skip(f"No .tmp/detail_instamart/ directory at {d}")
    return d
