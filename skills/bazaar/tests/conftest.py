"""pytest configuration for bazaar skill tests.

Adds scripts/ to sys.path so test modules can import aggregate, report,
and bazaar_dispatch directly. This is needed because pytest runs from the
repo root, not from the tests/ directory.

scripts/ is added so 'lib' resolves as a package (enabling relative imports
within provider wrappers). lib/ is also added as a fallback for bare imports.
"""

import sys
from pathlib import Path

# tests/ -> bazaar/ -> scripts/
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
LIB_DIR = SCRIPTS_DIR / "lib"

# scripts/ first: enables 'import lib.anthropic_chat' (package-relative imports work)
sys.path.insert(0, str(SCRIPTS_DIR))
# lib/ second: fallback for bare 'import anthropic_chat' style
sys.path.insert(0, str(LIB_DIR))
