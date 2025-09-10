import sys
from pathlib import Path

# Ensure the project root is on the Python path for src imports
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

