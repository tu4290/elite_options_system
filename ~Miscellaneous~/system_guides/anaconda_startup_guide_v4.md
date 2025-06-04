# Anaconda Setup and System Startup Guide

This guide provides a quick summary on how to organize the files for the Elite Options Trading System and how to start it up using an Anaconda environment.

## I. Recommended File Organization

We recommend creating a main project directory to house all components of the system. Here’s a suggested structure:

/your_anaconda_projects_directory/
└── elite_options_system/
├── config_v2.json                 # Main configuration (ensure paths are correct)
├── enhanced_data_fetcher_v2.py
├── enhanced_data_processor_v2.py
├── integrated_strategies_v2.py
├── mspi_visualizer_v2.py
├── run_enhanced_dashboard_v2.py   # The robust V2 dashboard runner script

├── dashboard_v2/                  # Directory containing the actual dashboard application
│   ├── __init__.py                # Make dashboard_v2 a package
│   ├── enhanced_dashboard_v2.py   # Main dashboard logic
│   ├── layout.py
│   ├── callbacks.py
│   ├── styling.py
│   ├── utils.py
│   └── assets/
│       └── custom.css
├── data/                          # For input/output data (paths configured in config_v2.json)
│   ├── raw_data/
│   └── processed_data/
└── system_guide_visuals/          # Optional: For mspi_visualizer_v2.py charts
└── comprehensive_system_guide/    # Optional: For the main guide document
├── Comprehensive_System_Guide.md
└── images/

**Key file placements:**

**Key file placements:**

1.  **`run_enhanced_dashboard.py`**: Place this in the root of your `elite_options_system` directory.
2.  **`config_v2.json`**: Place this in the root. *Note: The `run_enhanced_dashboard.py` script's comments might mention `config.json` as a dependency for the dashboard module it tries to load; however, our system uses `config_v2.json`. Ensure your actual dashboard logic (`dashboard_v2/enhanced_dashboard_v2.py`) correctly loads `config_v2.json`.*
3.  **`enhanced_dashboard.py` (Bridge Script)**: Create this file in the root directory. This script is necessary for `run_enhanced_dashboard.py` to correctly load your dashboard from the `dashboard_v2` folder. See "System Startup Sequence" below for its content and purpose.
4.  **Core Scripts**: `enhanced_data_fetcher_v2.py`, `enhanced_data_processor_v2.py`, `integrated_strategies_v2.py`, and `mspi_visualizer_v2.py` should also be in the `elite_options_system` root directory.
5.  **`dashboard_v2` Folder**: This entire folder, containing all its Python files (including an `__init__.py` to make it a package) and the `assets` subfolder, should be placed in the `elite_options_system` root directory.
6.  **`data` Directory**: Create a `data` directory (or whatever you specify in `config_v2.json` under `data_directory` and `raw_data_path`/`processed_data_path`).

## II. Anaconda Environment Setup

1.  **Open Anaconda Prompt**.
2.  **Create a new Conda environment** (e.g., named `options_env` with Python 3.11):
```bash
conda create -n options_env python=3.11
```
3.  **Activate the environment**:
```bash
conda activate options_env
```
4.  **Install necessary packages**. The primary ones you'll need are:
```bash
pip install convexlib dash kaleido numpy pandas plotly python-dateutil python-dotenv requests
```
-   **pandas**: For data manipulation.
-   **plotly** & **dash**: For the interactive dashboard.
-   **kaleido**: For exporting static images from Plotly charts (used by `mspi_visualizer_v2.py` and potentially by the dashboard for report generation if that feature is added).
-   **requests**: If your data fetcher needs to make HTTP requests.
-   **numpy**: For numerical operations, often a dependency.
-   **python-dotenv**: For loading environment variables from a `.env` file (used by `run_enhanced_dashboard.py`). Install using `pip install python-dotenv`.
-   **python-dateutil**: For advanced date parsing. Install using `pip install python-dateutil`.
-   Ensure `convexlib` is also installed if using ConvexValue: `pip install git+https://github.com/convexvalue/convexlib.git`.
-   You might need other libraries depending on the specifics of your data sources or any custom modifications. Check the import statements in the Python scripts for a full list.

## III. System Startup Sequence

Ensure your Anaconda environment (`options_env`) is activated before running these scripts. Navigate to your `elite_options_system` directory in the Anaconda Prompt.

1.  **Configure `config_v2.json`**: Before the first run, open `config_v2.json` in a text editor and ensure all paths (like `data_directory`, `raw_data_path`, `processed_data_path`, `charts_output_directory`) are correctly set up for your system. Also, input any necessary API credentials (e.g., for ConvexValue under `api_credentials`).

2.  **Run the Data Fetcher** (if you need to fetch new data):
```bash
python enhanced_data_fetcher_v2.py
```
This script will fetch data as per its configuration and save it to the location specified in `config_v2.json` (e.g., `data/raw_data/`).

3.  **Run the Data Processor**:
```bash
python enhanced_data_processor_v2.py
```
This script will take the raw data, process it, calculate intermediate metrics, and save the processed data (e.g., to `data/processed_data/`). This processed data is then used by the `integrated_strategies_v2.py` module (which is called by the dashboard or visualizer).

4.  **Run the Dashboard OR the Standalone Visualizer**:

*   **To start the interactive Dashboard (Recommended Method)**:
    The `run_enhanced_dashboard_v2.py` script is the recommended and most robust way to start your dashboard. It handles necessary pre-flight checks, loads configurations dynamically from `config_v2.json`, and provides better error reporting.

    Navigate to your `elite_options_system` directory in the Anaconda Prompt and run:
    ```bash
    python run_enhanced_dashboard_v2.py --config-path config_v2.json
    ```
    You can also specify other command-line arguments:
    -   `--host YOUR_IP` (e.g., `--host 127.0.0.1`)
    -   `--port YOUR_PORT` (e.g., `--port 8080`)
    -   `--production` (to run in production mode, typically with debugging off)
    -   `--skip-api-check` (if you want to bypass API credential checks for local testing without live data)

    For example, to run in production mode on a specific port:
    ```bash
    python run_enhanced_dashboard_v2.py --config-path config_v2.json --production --port 8080
    ```
    The script will attempt to load the dashboard module specified in your `config_v2.json` (under `runner_settings.dashboard_module_path`, which should be `dashboard_v2.main` or `dashboard_v2.enhanced_dashboard_v2` depending on your main dashboard script name within the package).

    Open your web browser and navigate to the address shown in the terminal (e.g., `http://127.0.0.1:8050/` or your specified host/port).

*   **Alternative Method (Direct Module Execution - Advanced Users)**:
    If you have corrected all internal imports within `dashboard_v2/enhanced_dashboard_v2.py` to use absolute paths for modules in the root directory (e.g., `from enhanced_data_fetcher_v2 import ...`), you *can* still run the dashboard module directly from the `elite_options_system` directory:
    ```bash
    python -m dashboard_v2.enhanced_dashboard_v2
    ```
    However, this method bypasses the additional checks and flexibility of the `run_enhanced_dashboard_v2.py` script and is generally not recommended for regular use.

*   **To generate standalone charts using the MSPI Visualizer**:
```bash
python mspi_visualizer_v2.py
```
This will generate and save chart images to the directory specified in `config_v2.json` (e.g., `system_guide_visuals/`).

**Important Notes**:

*   The `integrated_strategies_v2.py` script is not run directly by the user. It is imported and used by `enhanced_data_processor_v2.py` (for some calculations if structured that way), `mspi_visualizer_v2.py`, and the `dashboard_v2` application to calculate final signals and metrics.
*   Ensure that the Python scripts and the `config_v2.json` file are in the same directory from which you are running the commands, or adjust paths accordingly in your scripts/config if you choose a different structure.
*   Check the console output for any error messages if scripts fail to run.

This setup should get you started with the Elite Options Trading System in your Anaconda environment.