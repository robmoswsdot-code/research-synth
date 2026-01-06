import os
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from pathlib import Path
import threading
import io
from contextlib import redirect_stdout, redirect_stderr
import yaml

# Get the root directory of the application
APP_ROOT = Path(__file__).parent
LIST_ALL_CONTENTS_SCRIPT = APP_ROOT / "src" / "research_synth" / "list_all_contents.py"
STATE_FILE = APP_ROOT / ".research_synth_state"

def is_venv_active():
    """Check if .venv is activated."""
    return os.environ.get("VIRTUAL_ENV") is not None

def activate_venv():
    """Activate .venv if it exists."""
    venv_activate = APP_ROOT / ".venv" / "Scripts" / "Activate.ps1"
    if venv_activate.exists():
        try:
            subprocess.call(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(venv_activate)])
            return True
        except Exception as e:
            print(f"Error activating .venv: {e}")
            return False
    return False

def get_diagnostics():
    """Get system and environment diagnostics."""
    diag = f"""
=== SYSTEM DIAGNOSTICS ===
Python Executable: {sys.executable}
Python Version: {sys.version}
Virtual Environment Active: {is_venv_active()}
Virtual Env Path: {os.environ.get('VIRTUAL_ENV', 'Not set')}
APP Root: {APP_ROOT}
Current Working Directory: {os.getcwd()}

=== CHECKING RESEARCH-SYNTH INSTALLATION ===
"""
    try:
        import research_synth
        diag += f"✓ research_synth module found at: {research_synth.__file__}\n"
    except ImportError:
        diag += "✗ research_synth module NOT found. Run: pip install -e .\n"
    
    try:
        from research_synth.cli import app
        diag += "✓ research_synth.cli.app imported successfully\n"
    except ImportError as e:
        diag += f"✗ Could not import research_synth.cli.app: {e}\n"
    
    return diag

def get_cli_options_direct():
    """Get CLI options by importing the module directly instead of subprocess."""
    try:
        from research_synth.cli import app
        # Use Typer's built-in help
        import io
        from contextlib import redirect_stdout, redirect_stderr
        
        # Capture output
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            try:
                app(["--help"])
            except SystemExit:
                pass
        
        result = output.getvalue()
        if result:
            return result
        else:
            # Fallback: return the docstring
            return str(app.get_docs_for_click()) if hasattr(app, 'get_docs_for_click') else "CLI help not available"
    except Exception as e:
        return f"Error loading CLI options: {str(e)}\n\nTry running diagnostics to check your installation."

def list_all_files(project_root):
    """List all files in project root using list_all_contents.py."""
    try:
        result = subprocess.run(
            [sys.executable, str(LIST_ALL_CONTENTS_SCRIPT), project_root],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        if result.returncode == 0:
            return result.stdout if result.stdout else "(No files found)"
        else:
            return f"Error: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out."
    except Exception as e:
        return f"Error: {str(e)}"

def get_cli_options():
    """Get CLI options with timeout and error handling."""
    try:
        # Try direct import first
        result = get_cli_options_direct()
        if result and "Error loading CLI options" not in result:
            return result
        
        # Fallback to subprocess
        result = subprocess.run(
            [sys.executable, "-m", "research_synth.cli", "--help"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        if result.returncode == 0:
            return result.stdout if result.stdout else "CLI help not available"
        else:
            return f"Error: {result.stderr}\n\nMake sure .venv is activated and research-synth is installed (pip install -e .)"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out.\n\nTry running diagnostics to check your installation."
    except Exception as e:
        return f"Error: {str(e)}\n\nTry running diagnostics to check your installation."

def run_cli_command(args):
    """Run a CLI command with timeout and error handling."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "research_synth.cli"] + args,
            capture_output=True,
            text=True,
            timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        return result.stdout + ("\n" + result.stderr if result.stderr else "")
    except subprocess.TimeoutExpired:
        return "Error: Command timed out (exceeded 60 seconds)."
    except Exception as e:
        return f"Error: {str(e)}"

class ResearchSynthGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Research Synth GUI")
        self.geometry("900x700")
        self.project_root = tk.StringVar()
        
        # Load persistent session state
        self._load_project_context()
        
        self.create_widgets()
        self.check_venv()
        
        # Hook window close event to save state
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def check_venv(self):
        """Check if .venv is activated."""
        if not is_venv_active():
            result = messagebox.askyesno(
                ".venv Not Active",
                ".venv is not activated. Would you like to activate it now?"
            )
            if result:
                if activate_venv():
                    messagebox.showinfo(".venv Activated", ".venv was activated successfully.")
                else:
                    messagebox.showwarning(
                        ".venv Not Found",
                        "Could not activate .venv. Please activate manually by running:\n.venv\\Scripts\\Activate.ps1"
                    )

    def _load_project_context(self):
        """Load the last used project root from persistent state file."""
        try:
            if STATE_FILE.exists():
                with open(STATE_FILE, "r") as f:
                    state = yaml.safe_load(f)
                    if state and "last_project_root" in state:
                        last_root = state["last_project_root"]
                        # Verify the directory still exists
                        if last_root and Path(last_root).is_dir():
                            self.project_root.set(last_root)
        except Exception as e:
            # Silently fail if state file cannot be loaded
            pass

    def _save_project_context(self):
        """Save the current project root to persistent state file."""
        try:
            state = {"last_project_root": self.project_root.get()}
            with open(STATE_FILE, "w") as f:
                yaml.dump(state, f)
        except Exception as e:
            # Silently fail if state file cannot be saved
            pass

    def _on_closing(self):
        """Handle window close event: save state and exit."""
        self._save_project_context()
        self.destroy()

    def create_widgets(self):
        """Create the GUI widgets."""
        # Status frame
        status_frame = tk.Frame(self, bg="#f0f0f0")
        status_frame.pack(pady=5, padx=10, fill=tk.X)
        self.status_label = tk.Label(status_frame, text="Ready", bg="#f0f0f0", font=("Arial", 9))
        self.status_label.pack(side=tk.LEFT)
        
        # Project root selection frame
        frame = tk.Frame(self)
        frame.pack(pady=10, padx=10, fill=tk.X)
        tk.Label(frame, text="Project Root Directory:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        tk.Entry(frame, textvariable=self.project_root, width=50).pack(side=tk.LEFT, padx=5)
        tk.Button(frame, text="Browse", command=self.browse_folder, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=2)
        
        # Action buttons frame
        button_frame = tk.Frame(self)
        button_frame.pack(pady=10, padx=10, fill=tk.X)
        tk.Button(button_frame, text="List All Files", command=self.show_all_files_threaded, bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=2)
        tk.Button(button_frame, text="Show CLI Options", command=self.show_cli_options_threaded, bg="#FF9800", fg="white").pack(side=tk.LEFT, padx=2)
        tk.Button(button_frame, text="Run Diagnostics", command=self.show_diagnostics, bg="#009688", fg="white").pack(side=tk.LEFT, padx=2)
        tk.Button(button_frame, text="Clear Output", command=self.clear_output, bg="#f44336", fg="white").pack(side=tk.LEFT, padx=2)
        
        # Output area
        self.output = scrolledtext.ScrolledText(self, wrap=tk.WORD, width=120, height=25, font=("Courier", 9))
        self.output.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # CLI command frame
        cli_frame = tk.Frame(self)
        cli_frame.pack(pady=10, padx=10, fill=tk.X)
        tk.Label(cli_frame, text="Run research-synth command:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        self.cli_args = tk.Entry(cli_frame, width=60)
        self.cli_args.pack(side=tk.LEFT, padx=5)
        tk.Button(cli_frame, text="Run", command=self.run_cli_threaded, bg="#9C27B0", fg="white").pack(side=tk.LEFT, padx=2)
        tk.Label(cli_frame, text="(e.g., ingest /path/to/project or analyze /path/to/project)", font=("Arial", 8, "italic")).pack(side=tk.LEFT, padx=5)

    def browse_folder(self):
        """Browse for a project folder."""
        folder = filedialog.askdirectory(title="Select Project Root Directory")
        if folder:
            self.project_root.set(folder)

    def show_all_files_threaded(self):
        """Show all files in a separate thread to prevent GUI freezing."""
        root = self.project_root.get()
        if not root:
            messagebox.showerror("Error", "Please select a project root directory.")
            return
        self.status_label.config(text="Listing files...", fg="blue")
        threading.Thread(target=self._show_all_files, daemon=True).start()

    def _show_all_files(self):
        """Worker thread for listing all files."""
        try:
            root = self.project_root.get()
            self.output.delete(1.0, tk.END)
            self.output.insert(tk.END, f"Listing all files in {root}...\n\n")
            files = list_all_files(root)
            self.output.insert(tk.END, files)
            self.status_label.config(text="Files listed successfully", fg="green")
        except Exception as e:
            self.output.insert(tk.END, f"Error: {str(e)}")
            self.status_label.config(text=f"Error: {str(e)}", fg="red")

    def show_cli_options_threaded(self):
        """Show CLI options in a separate thread to prevent GUI freezing."""
        self.status_label.config(text="Loading CLI options...", fg="blue")
        threading.Thread(target=self._show_cli_options, daemon=True).start()

    def _show_cli_options(self):
        """Worker thread for showing CLI options."""
        try:
            self.output.delete(1.0, tk.END)
            self.output.insert(tk.END, "Fetching CLI options...\n\n")
            options = get_cli_options()
            self.output.delete(1.0, tk.END)
            self.output.insert(tk.END, options)
            self.status_label.config(text="CLI options loaded successfully", fg="green")
        except Exception as e:
            self.output.insert(tk.END, f"Error: {str(e)}")
            self.status_label.config(text=f"Error: {str(e)}", fg="red")

    def clear_output(self):
        """Clear the output area."""
        self.output.delete(1.0, tk.END)
        self.status_label.config(text="Output cleared", fg="black")

    def show_diagnostics(self):
        """Show system diagnostics."""
        self.status_label.config(text="Running diagnostics...", fg="blue")
        threading.Thread(target=self._show_diagnostics, daemon=True).start()

    def _show_diagnostics(self):
        """Worker thread for showing diagnostics."""
        try:
            self.output.delete(1.0, tk.END)
            diag = get_diagnostics()
            self.output.insert(tk.END, diag)
            self.status_label.config(text="Diagnostics completed", fg="green")
        except Exception as e:
            self.output.insert(tk.END, f"Error running diagnostics: {str(e)}")
            self.status_label.config(text=f"Diagnostics error: {str(e)}", fg="red")

    def run_cli_threaded(self):
        """Run CLI command in a separate thread to prevent GUI freezing."""
        args = self.cli_args.get().strip().split()
        if not args:
            messagebox.showerror("Error", "Please enter CLI arguments.")
            return
        self.status_label.config(text="Running command...", fg="blue")
        threading.Thread(target=self._run_cli, args=(args,), daemon=True).start()

    def _run_cli(self, args):
        """Worker thread for running CLI commands."""
        try:
            self.output.delete(1.0, tk.END)
            self.output.insert(tk.END, f"Running: research-synth {' '.join(args)}\n\n")
            result = run_cli_command(args)
            self.output.insert(tk.END, result)
            self.status_label.config(text="Command completed successfully", fg="green")
        except Exception as e:
            self.output.insert(tk.END, f"Error: {str(e)}")
            self.status_label.config(text=f"Command error: {str(e)}", fg="red")

if __name__ == "__main__":
    app = ResearchSynthGUI()
    app.mainloop()
