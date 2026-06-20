# Hugging Face Spaces / Streamlit Cloud entrypoint.
# Spaces looks for app.py at repo root; this just runs the real app.
import runpy, os
runpy.run_path(os.path.join(os.path.dirname(__file__), "app", "streamlit_app.py"),
               run_name="__main__")
