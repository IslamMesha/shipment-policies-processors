# Building the Windows executable

Build the executable on Windows; PyInstaller does not cross-compile Windows
executables from Ubuntu.

1. Copy or clone this project onto a Windows machine.
2. Install Python 3 and ensure the Python launcher (`py`) is available.
3. Run `build_windows.bat` from File Explorer or Command Prompt.

The script creates an isolated `.venv-build`, installs the application and
PyInstaller dependencies, bundles the app icon from `assets\shipment_policy_processor.ico`, and produces:

```text
dist\ShipmentPolicyProcessor.exe
```

This is a single-file, windowed executable that includes Python and the
application's Python/Qt dependencies. The target Windows machine does not need
Python or these packages installed. The first launch may take a little longer
because PyInstaller extracts the bundled files.
