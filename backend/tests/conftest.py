import os
import tempfile

# Tests hammer POST endpoints from one client; don't let the per-IP limiter interfere.
os.environ.setdefault("RATE_LIMIT_PER_MIN", "100000")
# Keep test analyses out of the app's real storage/analyses.db.
os.environ.setdefault("ANALYSES_DB", os.path.join(tempfile.mkdtemp(prefix="dpdp-test-"), "analyses.db"))
# The API tests exercise endpoints directly; accounts are tested on their own in test_auth.py.
os.environ.setdefault("AUTH_REQUIRED", "false")
os.environ.setdefault("DOCUMENTS_DB", os.path.join(tempfile.mkdtemp(prefix="dpdp-test-"), "documents.db"))
os.environ.setdefault("AUTH_DB", os.path.join(tempfile.mkdtemp(prefix="dpdp-test-"), "accounts.db"))
