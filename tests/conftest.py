import os
import tempfile

# railflow.config creates its output folders on import; keep tests away from real outputs
os.environ.setdefault("RAILFLOW_OUTPUT_DIR", tempfile.mkdtemp(prefix="railflow-test-"))
