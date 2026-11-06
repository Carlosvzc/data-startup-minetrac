import sys
from pathlib import Path
R = Path(__file__).resolve().parents[1]
for p in ['services/worker', 'services/ingesta']:
    sys.path.insert(0, str(R / p))
