"""Unit tests do not open Postgres. The public caps are covered with fakes."""

from __future__ import annotations

import os

# Set before the app imports settings. An explicit shell value still wins.
os.environ.setdefault("USAGE_LIMITS_ENABLED", "false")
