"""pytest configuration for bazaar skill tests.

Adds scripts/ to sys.path so test modules can import aggregate, report,
and bazaar_dispatch directly. This is needed because pytest runs from the
repo root, not from the tests/ directory.

scripts/ is added so 'lib' resolves as a package (enabling 'import lib.<module>'
style imports that match the production import path). lib/ is NOT added directly
to sys.path — doing so would put lib/http.py on the path ahead of stdlib's http
package, breaking urllib.request (DEC-BAZAAR-009).
"""

import sys
from pathlib import Path

# tests/ -> bazaar/ -> scripts/
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"

# scripts/ only: enables 'import lib.anthropic_chat' (package-relative imports work)
# lib/ is intentionally NOT added — lib/http.py would shadow stdlib http package
sys.path.insert(0, str(SCRIPTS_DIR))
