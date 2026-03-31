"""Streamlit Cloud entrypoint — delegates to app.py."""
from pathlib import Path

# exec() ensures app.py is fully re-executed on every Streamlit rerun.
# `from app import *` only executes app.py on the first run due to Python's
# module cache, which causes blank pages on subsequent widget interactions.
exec(compile(Path("app.py").read_text(encoding="utf-8"), "app.py", "exec"))
