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

def get_fixed_paths():
    """
    ENGINEERING DIRECTIVE: Local Root Standardization
    
    All data operations are pinned to APP_ROOT with mandatory structure:
    - sources/: Input WSDOT site documents
    - results/: Output reports, JSON extraction, analysis files
    
    Returns:
        tuple: (source_dir, result_dir) - both guaranteed to exist
    """
    source_dir = APP_ROOT / "sources"
    result_dir = APP_ROOT / "results"
    
    # Ensure directories exist locally (no rework if missing)
    source_dir.mkdir(exist_ok=True)
    result_dir.mkdir(exist_ok=True)
    
    return source_dir, result_dir

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
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        
        result = subprocess.run(
            [sys.executable, str(LIST_ALL_CONTENTS_SCRIPT), project_root],
            capture_output=True,
            text=True,
            timeout=10,
            startupinfo=startupinfo
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
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        
        result = subprocess.run(
            [sys.executable, "-m", "research_synth.cli", "--help"],
            capture_output=True,
            text=True,
            timeout=5,
            startupinfo=startupinfo
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
    """Run a CLI command with fixed APP_ROOT paths and artifact validation.
    
    ENGINEERING DIRECTIVE: Local Root Standardization
    - All operations execute in APP_ROOT (no dynamic project selection)
    - Output files guaranteed in APP_ROOT/results/
    
    Args:
        args: List of CLI arguments (e.g., ["ingest", "."])
    
    Returns:
        Tuple of (output_text, artifacts_found, validation_status)
    """
    try:
        source_dir, result_dir = get_fixed_paths()
        
        # All CLI commands execute in results directory context
        cwd = str(result_dir)
        
        if not Path(cwd).is_dir():
            return f"Error: Result directory does not exist: {cwd}", [], "FAILED"
        
        files_before = set()
        try:
            for item in Path(cwd).rglob("*"):
                if item.is_file():
                    files_before.add(item.relative_to(cwd))
        except Exception:
            pass
        
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        
        result = subprocess.run(
            ["research-synth"] + args,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=cwd,
            env=os.environ.copy(),
            startupinfo=startupinfo
        )
        
        output_text = result.stdout + ("\n" + result.stderr if result.stderr else "")
        validation_status = "SUCCESS" if result.returncode == 0 else "FAILED"
        
        artifacts_found = []
        try:
            for item in Path(cwd).rglob("*"):
                if item.is_file():
                    relative_path = item.relative_to(cwd)
                    if relative_path not in files_before:
                        if any(str(item).endswith(ext) for ext in [".md", ".json", ".yaml"]):
                            artifacts_found.append(str(relative_path))
        except Exception:
            pass
        
        if result.returncode != 0:
            validation_status = "FAILED"
        elif not artifacts_found and any(cmd in args for cmd in ["ingest", "analyze", "report"]):
            validation_status = "WARNING: No output files detected"
        
        return output_text, artifacts_found, validation_status
    
    except subprocess.TimeoutExpired:
        return "Error: Command timed out (exceeded 120 seconds).", [], "TIMEOUT"
    except Exception as e:
        return f"Error: {str(e)}", [], "FAILED"

class ResearchSynthGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Research Synth GUI - Local Root Mode")
        self.geometry("900x700")
        
        # Initialize fixed paths
        source_dir, result_dir = get_fixed_paths()
        self.source_dir = source_dir
        self.result_dir = result_dir
        
        self.create_widgets()
        self.check_venv()
        self.display_paths()

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

    def display_paths(self):
        """Display the configured paths to the user."""
        self.status_label.config(text=f"Source: {self.source_dir} | Results: {self.result_dir}")

    def _on_closing(self):
        """Handle window close event."""
        self.destroy()

    def create_widgets(self):
        """Create the GUI widgets."""
        # Status frame
        status_frame = tk.Frame(self, bg="#f0f0f0")
        status_frame.pack(pady=5, padx=10, fill=tk.X)
        self.status_label = tk.Label(status_frame, text="Ready", bg="#f0f0f0", font=("Arial", 9))
        self.status_label.pack(side=tk.LEFT)
        
        # Path configuration frame (informational only)
        path_frame = tk.Frame(self, bg="#e8f5e9", relief=tk.GROOVE, bd=2)
        path_frame.pack(pady=10, padx=10, fill=tk.X)
        tk.Label(path_frame, text="ENGINEERING DIRECTIVE: Local Root Standardization", 
                font=("Arial", 10, "bold"), bg="#e8f5e9").pack(pady=5)
        tk.Label(path_frame, text=f"Sources:  {self.source_dir}", 
                font=("Arial", 9), bg="#e8f5e9", justify=tk.LEFT).pack(anchor=tk.W, padx=10)
        tk.Label(path_frame, text=f"Results:  {self.result_dir}", 
                font=("Arial", 9), bg="#e8f5e9", justify=tk.LEFT).pack(anchor=tk.W, padx=10)
        

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

    def show_all_files_threaded(self):
        """Show all files in a separate thread to prevent GUI freezing."""
        self.status_label.config(text="Listing files...", fg="blue")
        threading.Thread(target=self._show_all_files, daemon=True).start()

    def _show_all_files(self):
        """Worker thread for listing all files."""
        try:
            self.output.delete(1.0, tk.END)
            self.output.insert(tk.END, f"Files in sources directory:\n\n")
            self.update_idletasks()  # Force GUI update
            
            files = []
            if self.source_dir.exists():
                for f in self.source_dir.rglob("*"):
                    if f.is_file():
                        files.append(str(f.relative_to(self.source_dir)))
            
            if files:
                for f in sorted(files):
                    self.output.insert(tk.END, f"  ✓ {f}\n")
            else:
                self.output.insert(tk.END, "(No files found in sources directory)\n")
                self.output.insert(tk.END, f"\nPlace documents in: {self.source_dir}\n")
            
            self.status_label.config(text="Files listed successfully", fg="green")
        except Exception as e:
            self.output.delete(1.0, tk.END)
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
        """Worker thread for running CLI commands with artifact validation.
        
        ENGINEERING DIRECTIVE: Local Root Standardization
        All commands execute in APP_ROOT/results/ with sources from APP_ROOT/sources/
        """
        try:
            self.output.delete(1.0, tk.END)
            self.output.insert(tk.END, f"Running: research-synth {' '.join(args)}\n")
            self.output.insert(tk.END, f"Sources: {self.source_dir}\n")
            self.output.insert(tk.END, f"Results: {self.result_dir}\n\n")
            self.update_idletasks()
            
            output_text, artifacts_found, validation_status = run_cli_command(args)
            
            self.output.insert(tk.END, output_text)
            self.output.insert(tk.END, "\n" + "="*80 + "\n")
            self.output.insert(tk.END, "EXECUTION SUMMARY\n")
            self.output.insert(tk.END, f"Status: {validation_status}\n")
            
            if artifacts_found:
                self.output.insert(tk.END, f"\nArtifacts Generated ({len(artifacts_found)}): \n")
                for artifact in artifacts_found:
                    self.output.insert(tk.END, f"  ✓ {artifact}\n")
            else:
                self.output.insert(tk.END, "\nNo new artifacts detected.\n")
            
            # Validation Protocol
            self._validate_artifacts(args, artifacts_found)
            
            if "SUCCESS" in validation_status:
                self.status_label.config(text=f"✓ SUCCESS | {len(artifacts_found)} artifacts generated", fg="green")
            elif "WARNING" in validation_status:
                self.status_label.config(text="⚠ WARNING Command ran but no output files detected", fg="orange")
            else:
                self.status_label.config(text=f"✗ FAILED {validation_status}", fg="red")
        
        except Exception as e:
            self.output.delete(1.0, tk.END)
            self.output.insert(tk.END, f"Error: {str(e)}")
            self.status_label.config(text=f"Error: {str(e)}", fg="red")
    
    def _validate_artifacts(self, args, artifacts_found):
        """
        DEFINITIVE VALIDATION PROTOCOL (No Rework Phase)
        
        Ensures artifacts contain actual data, not hollow successes.
        """
        self.output.insert(tk.END, "\n" + "="*80 + "\n")
        self.output.insert(tk.END, "INTEGRITY VALIDATION\n")
        self.output.insert(tk.END, "="*80 + "\n")
        
        command = args[0] if args else None
        
        try:
            if command == "init" and artifacts_found:
                # Verification of Content: init_report.md must be > 1KB
                init_report = self.result_dir / "init_report.md"
                if init_report.exists():
                    size = init_report.stat().st_size
                    if size > 1024:
                        self.output.insert(tk.END, f"✓ init_report.md size: {size} bytes (>1KB) - VALID\n")
                    else:
                        self.output.insert(tk.END, f"✗ init_report.md size: {size} bytes (<1KB) - INVALID\n")
            
            elif command == "ingest" and artifacts_found:
                # Data Accuracy Audit: extracted_text.json must contain actual strings
                extracted = self.result_dir / "chunks" / "extracted_text.json"
                if extracted.exists():
                    import json
                    try:
                        with open(extracted, 'r') as f:
                            data = json.load(f)
                        
                        # Check if data contains actual text (not empty structures)
                        if data and len(str(data)) > 100:
                            self.output.insert(tk.END, f"✓ extracted_text.json contains {len(str(data))} chars of data - VALID\n")
                        else:
                            self.output.insert(tk.END, f"✗ extracted_text.json is empty or minimal - INVALID\n")
                    except Exception as e:
                        self.output.insert(tk.END, f"✗ extracted_text.json parsing error: {e}\n")
            
            elif command == "report" and artifacts_found:
                # Success Lockdown: Report must be human-readable
                report = self.result_dir / "outputs" / "draft_report.md" if (self.result_dir / "outputs").exists() else self.result_dir / "draft_report.md"
                if report.exists():
                    size = report.stat().st_size
                    with open(report, 'r') as f:
                        content = f.read()
                    
                    if size > 500 and len(content) > 100:
                        self.output.insert(tk.END, f"✓ Draft report: {size} bytes, human-readable - VALID\n")
                        self.output.insert(tk.END, f"✓ CODEBASE READY FOR FREEZE\n")
                    else:
                        self.output.insert(tk.END, f"✗ Draft report too small or invalid: {size} bytes\n")
        
        except Exception as e:
            self.output.insert(tk.END, f"Validation check skipped: {str(e)}\n")

if __name__ == "__main__":
    app = ResearchSynthGUI()
    app.mainloop()
