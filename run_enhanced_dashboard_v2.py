# --- START OF FILE run_enhanced_dashboard_v2.py ---

#!/usr/bin/env python3
"""
Enhanced Options Dashboard Runner Script
(Version: 2.2 - Improved Import Handling and Clarity)

This script serves as a robust launcher for the Enhanced Options Dashboard application.
It performs pre-flight checks for dependencies, environment configurations, and
directory structures, and loads key settings from a central configuration file
(defaulting to config_v2.json) before attempting to start the Dash server.
"""

# Standard Library Imports
import os
import sys
import argparse
import logging
import traceback # For detailed exception logging
import importlib
import json
from typing import Optional, List, Dict, Any, Tuple, Callable
from datetime import datetime, timedelta # timedelta is used
import time # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< MAKE SURE THIS IS PRESENT AND NOT COMMENTED OUT

# Third-Party Imports
# requests is not directly used by the runner but might be a common project dependency.
# import requests # Can be removed if not used by runner itself

# --- Add the project root to sys.path ---
# This allows a consistent way to import modules from the main package.
try:
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        # Log this addition for debugging import issues
        # logging.getLogger("DashboardRunner").debug(f"Project root '{project_root}' added to sys.path.")
except NameError: # __file__ is not defined (e.g. in some interactive environments)
    project_root = os.getcwd()
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        # logging.getLogger("DashboardRunner").debug(f"Project root (cwd) '{project_root}' added to sys.path.")


# --- Initial Logging Configuration (basic, can be overridden by app's config later if needed) ---
# Place this before any local module imports that might also configure logging.
if not logging.getLogger().hasHandlers(): # Configure root logger only if not already configured
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] (%(name)s:%(lineno)d) %(asctime)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
logger = logging.getLogger("DashboardRunnerV2.2") # Specific logger for this runner script

DEFAULT_CONFIG_FILENAME_RUNNER = "config_v2.json"

# List of essential Python packages. `psycopg2-binary` is for PostgreSQL.
PYTHON_PACKAGES_RUNNER = [
    "dash", "pandas", "numpy", "plotly", "requests",
    "dotenv", "dateutil", "convexlib", "psycopg2-binary"
]

# --- Helper Functions ---

def load_configuration_runner(config_path: str) -> Optional[Dict[str, Any]]:
    """Loads the JSON configuration file for the runner."""
    logger.info(f"RUNNER: Attempting to load configuration from: {config_path}")
    try:
        # Ensure the path is absolute for reliable file opening
        abs_config_path = config_path
        if not os.path.isabs(config_path):
            # Try resolving relative to the runner script's location first
            runner_dir = os.path.dirname(os.path.abspath(__file__))
            path_rel_runner = os.path.join(runner_dir, config_path)
            if os.path.exists(path_rel_runner):
                abs_config_path = path_rel_runner
            elif os.path.exists(config_path): # Then try as a direct path (e.g., if CWD is project root)
                abs_config_path = os.path.abspath(config_path)
            else: # Fallback if common relative paths don't work
                abs_config_path = os.path.abspath(config_path)


        with open(abs_config_path, 'r', encoding='utf-8') as f_cfg_runner:
            config = json.load(f_cfg_runner)
        config["_config_file_path"] = abs_config_path # Store the path used for loading
        logger.info(f"RUNNER: Successfully loaded configuration from {abs_config_path}.")
        return config
    except FileNotFoundError:
        logger.error(f"RUNNER FATAL: Configuration file not found at resolved path for '{config_path}'.")
        return None
    except json.JSONDecodeError as e_json_runner:
        logger.error(f"RUNNER FATAL: Could not parse JSON configuration file '{config_path}': {e_json_runner}")
        return None
    except Exception as e_load_runner:
        logger.error(f"RUNNER FATAL: An unexpected error occurred while loading '{config_path}': {e_load_runner}", exc_info=True)
        return None

def get_required_directories_from_config_runner(config: Dict[str, Any]) -> List[str]:
    """
    Extracts and resolves required directory paths from the configuration.
    Paths are resolved relative to the loaded config file's location if not absolute.
    """
    config_file_location = config.get("_config_file_path")
    if not config_file_location:
        logger.warning("RUNNER: '_config_file_path' not found in config. Using runner's CWD as base for relative paths.")
        base_path_for_dirs = os.getcwd()
    else:
        base_path_for_dirs = os.path.dirname(config_file_location)
    
    logger.debug(f"RUNNER: Base path for resolving relative directories: {base_path_for_dirs}")
    dirs_to_check_set = set()

    def _resolve_path_helper(keys: List[str], default_rel: Optional[str] = None) -> Optional[str]:
        current = config
        try:
            for key in keys: current = current[key]
            path_val = str(current) if isinstance(current, str) else None
        except (KeyError, TypeError): path_val = default_rel
        
        if path_val:
            return os.path.normpath(os.path.join(base_path_for_dirs, path_val) if not os.path.isabs(path_val) else path_val)
        return None

    # System base data directory
    sys_base_data_dir = _resolve_path_helper(["system_settings", "data_directory_base"], "eots_data_v2_5_runner_default")
    if sys_base_data_dir:
        processed_subdir = config.get("system_settings", {}).get("processed_data_subdirectory", "market_snapshots")
        dirs_to_check_set.add(os.path.join(sys_base_data_dir, processed_subdir))
        
        viz_output_subdir = config.get("system_settings", {}).get("visualizer_output_subdirectory", "charts_output")
        dirs_to_check_set.add(os.path.join(sys_base_data_dir, viz_output_subdir))

    # MSPIVisualizerV2 specific output (might be redundant if covered by system_settings)
    mspi_viz_dir = _resolve_path_helper(["visualization_settings", "mspi_visualizer", "output_dir"])
    if mspi_viz_dir: dirs_to_check_set.add(mspi_viz_dir)

    # Dashboard assets directory (convention: 'assets' subdir within the dashboard module package)
    app_module_path_str = config.get("runner_settings", {}).get("dashboard_module_path", "dashboard_v2.enhanced_dashboard_v2")
    try:
        dashboard_pkg_name = app_module_path_str.split('.')[0] # e.g., "dashboard_v2"
        # Try to find dashboard package relative to project root (where runner script is)
        # This assumes runner is in project root, and dashboard_v2 is a subdir.
        pkg_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), dashboard_pkg_name)
        if not os.path.isdir(pkg_dir): # Fallback: try relative to config base if different
             pkg_dir = os.path.join(base_path_for_dirs, dashboard_pkg_name)
        
        assets_dir = os.path.normpath(os.path.join(pkg_dir, "assets"))
        dirs_to_check_set.add(assets_dir)
        logger.debug(f"RUNNER: Derived assets directory for '{app_module_path_str}': {assets_dir}")
    except Exception as e_asset_path:
        logger.warning(f"RUNNER: Could not robustly derive assets path for '{app_module_path_str}': {e_asset_path}. Using default convention.")
        dirs_to_check_set.add(os.path.normpath(os.path.join(base_path_for_dirs, "dashboard_v2", "assets"))) # Common fallback

    final_dirs = [d for d in list(dirs_to_check_set) if d is not None]
    logger.info(f"RUNNER: Required directories identified: {final_dirs}")
    return final_dirs

def check_python_packages_runner(packages: List[str]) -> bool:
    logger.info("RUNNER: Checking required Python package imports..."); missing_pkgs = []
    for pkg in packages:
        try:
            pkg_to_import = pkg.split('==')[0].split('>')[0].split('<')[0].split('[')[0].replace("-", "_")
            if pkg_to_import == "python_dotenv": importlib.import_module("dotenv")
            elif pkg_to_import == "psycopg2_binary": importlib.import_module("psycopg2")
            else: importlib.import_module(pkg_to_import)
            logger.debug(f"  - RUNNER: Package '{pkg}' found (imported as '{pkg_to_import}').")
        except ImportError:
            logger.error(f"  - RUNNER: Required package '{pkg}' (module '{pkg_to_import}') NOT installed.")
            missing_pkgs.append(pkg)
    if missing_pkgs:
        logger.error(f"RUNNER FATAL: Missing packages: {missing_pkgs}. Please install them (e.g., via pip).")
        return False
    logger.info("RUNNER: All required Python packages appear to be installed."); return True

def check_environment_variables_runner(config: Dict[str, Any]) -> bool:
    logger.info("RUNNER: Checking API credentials (ENV VARs or direct config)...");
    try:
        from dotenv import load_dotenv
        # .env should ideally be in the project root (where this runner script is)
        env_path_runner = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
        load_dotenv(dotenv_path=env_path_runner, verbose=True)
        logger.info(f"RUNNER: Attempted to load .env from: {env_path_runner}")
    except ImportError: logger.warning("RUNNER: 'python-dotenv' not found. Cannot load .env file.")
    
    api_cfg = config.get("api_credentials", {})
    all_found = True

    for api_name, cred_details in api_cfg.items():
        if not isinstance(cred_details, dict): continue
        for key_type, env_var_key in cred_details.items():
            if "_env_var" in key_type.lower(): # e.g., "email_env_var", "access_token_env_var"
                cred_name = key_type.replace("_env_var", "")
                env_var_name = str(env_var_key)
                direct_config_key = cred_details.get(f"{cred_name}_direct")
                placeholder_val = f"YOUR_{api_name.upper()}_{cred_name.upper()}_PLACEHOLDER" # Construct typical placeholder

                if os.getenv(env_var_name):
                    logger.info(f"  - RUNNER: {api_name.capitalize()} '{cred_name}' found in ENV VAR '{env_var_name}'.")
                elif direct_config_key and direct_config_key != placeholder_val and direct_config_key != DEFAULT_CONFIG_FILENAME_RUNNER.get("api_credentials",{}).get(api_name,{}).get(f"{cred_name}_direct"): # Check against default placeholder
                    logger.warning(f"  - RUNNER: Using {api_name.capitalize()} '{cred_name}' from direct config (less secure).")
                else:
                    logger.error(f"  - RUNNER FATAL: {api_name.capitalize()} '{cred_name}' NOT FOUND (ENV VAR '{env_var_name}' or valid direct config).")
                    all_found = False
    if all_found: logger.info("RUNNER: All configured API credentials appear to be accessible."); return True
    logger.error("RUNNER: One or more API credentials missing. System functionality will be impaired."); return False

def ensure_directories_runner(dir_list: List[str]) -> bool:
    if not dir_list: logger.info("RUNNER: No specific directories configured for creation."); return True
    logger.info(f"RUNNER: Ensuring directories: {dir_list}"); all_ok_runner = True
    for d in dir_list:
        if not d: continue # Skip if path resolved to None
        try:
            os.makedirs(d, exist_ok=True)
            logger.debug(f"  - RUNNER: Directory '{d}' ensured.")
        except Exception as e:
            logger.error(f"  - RUNNER FAILED creating directory '{d}': {e}", exc_info=True)
            all_ok_runner = False
    if not all_ok_runner: logger.error("RUNNER FATAL: Failed to create one or more required directories."); return False
    logger.info("RUNNER: All required directories verified/created."); return True

def attempt_app_import_runner(app_module_path_str: str) -> Optional[Tuple[Any, Any, Optional[Dict[str, Any]], Optional[Callable[[], None]]]]:
    """
    Attempts to import the main Dash app and server from the specified module path.
    Also tries to get backend instances and a cleanup function if defined in the app module.
    """
    logger.info(f"RUNNER: Attempting to import Dash app module: '{app_module_path_str}'...")
    try:
        # Ensure the dashboard_v2 package is discoverable.
        # The sys.path.insert(0, project_root) at the top of this script should handle this
        # if the runner is in the project root and 'dashboard_v2' is a subdirectory.
        # Example: app_module_path_str might be "dashboard_v2.enhanced_dashboard_v2"
        
        dashboard_module = importlib.import_module(app_module_path_str)
        logger.debug(f"RUNNER: Successfully imported module object: {dashboard_module}")
        
        dash_app_obj = getattr(dashboard_module, 'app', None)
        flask_server_obj = getattr(dashboard_module, 'server', None)
        
        if dash_app_obj is None:
            logger.critical(f"RUNNER FATAL: 'app' (Dash instance) not found in Dash app module '{app_module_path_str}'.")
            raise ImportError(f"'app' (Dash instance) not found in Dash app module '{app_module_path_str}'.")
        if flask_server_obj is None:
            logger.critical(f"RUNNER FATAL: 'server' (Flask instance) not found in Dash app module '{app_module_path_str}'.")
            raise ImportError(f"'server' (Flask instance) not found in Dash app module '{app_module_path_str}'.")

        logger.debug(f"RUNNER: Found 'app' (type: {type(dash_app_obj)}) and 'server' (type: {type(flask_server_obj)}) in module.")

        # Retrieve instantiated backend services from the app module
        # These names ('cv_fetcher_instance_app', etc.) must match what's defined in enhanced_dashboard_v2.py
        backend_services_from_module: Dict[str, Any] = {
            "cv_fetcher": getattr(dashboard_module, 'cv_fetcher_instance_app', None),
            "tradier_fetcher": getattr(dashboard_module, 'tradier_fetcher_instance_app', None),
            "processor": getattr(dashboard_module, 'processor_instance_app', None),
            "its": getattr(dashboard_module, 'its_instance_app', None),
            "visualizer": getattr(dashboard_module, 'visualizer_instance_app', None)
        }
        
        # Log the types of retrieved backend services for verification
        for service_name, service_instance in backend_services_from_module.items():
            if service_instance is not None:
                logger.debug(f"RUNNER: Retrieved backend service '{service_name}': Type {type(service_instance).__name__}")
            else:
                logger.warning(f"RUNNER: Backend service '{service_name}' was not found or is None in the app module.")
        
        # Get the cleanup function (corrected name from previous step)
        app_cleanup_func = getattr(dashboard_module, 'cleanup_application_resources', None)
        if app_cleanup_func and callable(app_cleanup_func):
            logger.debug(f"RUNNER: Found callable cleanup function 'cleanup_application_resources'.")
        elif app_cleanup_func:
            logger.warning(f"RUNNER: Found 'cleanup_application_resources' but it is not callable (type: {type(app_cleanup_func)}).")
        else:
            logger.debug(f"RUNNER: Cleanup function 'cleanup_application_resources' not found in app module.")
            
        logger.info(f"RUNNER: Successfully imported 'app', 'server' from '{app_module_path_str}'. Backend service instances and cleanup function reference retrieved.")
        return dash_app_obj, flask_server_obj, backend_services_from_module, app_cleanup_func
        
    except ImportError as e_imp_app: # Catch specific ImportError from the app module itself
        logger.critical(f"RUNNER FATAL: ImportError when trying to load Dash app module '{app_module_path_str}': {e_imp_app}", exc_info=True)
        return None # Indicate failure
    except AttributeError as e_attr_app: # Catch if expected attributes like 'app' or 'server' are missing
        logger.critical(f"RUNNER FATAL: AttributeError accessing required components in Dash app module '{app_module_path_str}': {e_attr_app}", exc_info=True)
        return None
    except Exception as e_gen_imp_app: # Catch other errors during import or getattr
        logger.critical(f"RUNNER FATAL: Unexpected error during Dash app module import or attribute access from '{app_module_path_str}': {e_gen_imp_app}", exc_info=True)
        return None

def main():
    """Main execution function for the dashboard runner."""
    runner_start_time = time.monotonic()
    logger.info("=" * 80)
    logger.info(f"=== Enhanced Options Dashboard Runner (V2.2) Starting at {datetime.now()} ===")
    logger.info("=" * 80)

    parser = argparse.ArgumentParser(description="Run Enhanced Options Dashboard V2.2")
    parser.add_argument("--config-path", type=str, default=DEFAULT_CONFIG_FILENAME_RUNNER, help=f"Config file path (default: {DEFAULT_CONFIG_FILENAME_RUNNER})")
    parser.add_argument("--production", action="store_true", help="Run in production mode (disables Dash debug mode)")
    parser.add_argument("--host", type=str, default=None, help="Server host IP (overrides config if set)")
    parser.add_argument("--port", type=int, default=None, help="Server port (overrides config if set)")
    parser.add_argument("--skip-api-check", action="store_true", help="Skip API credential validation during startup")
    cli_args = parser.parse_args()

    main_config = load_configuration_runner(cli_args.config_path)
    if main_config is None:
        logger.critical("RUNNER: Exiting due to configuration load failure.")
        sys.exit(1)

    # Determine host, port, and debug mode
    server_host = cli_args.host or main_config.get("system_settings", {}).get("dashboard_host", "0.0.0.0")
    server_port = cli_args.port or main_config.get("system_settings", {}).get("dashboard_port", 8050)
    dash_debug_mode = not cli_args.production # Debug mode is ON if --production is NOT set

    logger.info(f"RUNNER Settings: Config='{cli_args.config_path}', ProductionMode={cli_args.production} (DashDebug={dash_debug_mode}), Host='{server_host}', Port={server_port}, SkipAPICheck={cli_args.skip_api_check}")

    # --- Pre-flight Checks ---
    if not check_python_packages_runner(PYTHON_PACKAGES_RUNNER): sys.exit(1)
    if not cli_args.skip_api_check and not check_environment_variables_runner(main_config): sys.exit(1)
    
    required_dirs_runner = get_required_directories_from_config_runner(main_config)
    if not ensure_directories_runner(required_dirs_runner): sys.exit(1)

    # --- Import and Initialize the Dash Application ---
    dashboard_module_name = main_config.get("runner_settings", {}).get("dashboard_module_path", "dashboard_v2.enhanced_dashboard_v2")
    import_attempt_result = attempt_app_import_runner(dashboard_module_name)
    
    if import_attempt_result is None:
        logger.critical(f"RUNNER: Failed to import or setup the Dash application module '{dashboard_module_name}'. Cannot start server. Exiting.")
        sys.exit(1)
    
    dash_app_instance, flask_server_instance, _, app_cleanup_function = import_attempt_result
    # backend_instances_dict is retrieved but not directly used by the runner's app.run() call.
    # It's more for awareness or potential future direct interaction by the runner.

    logger.info(f"RUNNER: Starting Dash server... Debug Mode: {dash_debug_mode}")
    print("-" * 70 + f"\n🚀🚀🚀🚀Dashboard is launching!🚀🚀🚀🚀at: http://{server_host}:{server_port}" +
          (f" (or http://127.0.0.1:{server_port})" if server_host == '0.0.0.0' else "") +
          "\n" + "-" * 70 + "\nPress CTRL+C to stop the server.", flush=True)

    try:
        # Use dash_app_instance.run_server for Dash 2.0+ style, or app.run for older versions
        # For Dash 2.x, app.run is an alias for app.run_server.
        # Dash app.run() is the current standard method.
        # use_reloader=False is important for stability when not using `if __name__ == '__main__':` in the app file itself.
        dash_app_instance.run( # <--- CORRECTED LINE
            debug=dash_debug_mode,
            host=server_host,
            port=server_port,
            use_reloader=False # Typically False when run via a script like this
        )
    except KeyboardInterrupt:
        logger.info("RUNNER: KeyboardInterrupt received. Shutting down Dash server...")
    except SystemExit:
        logger.info("RUNNER: SystemExit received. Dash server likely shut down by other means.")
    except Exception as e_run_server:
        logger.critical(f"RUNNER FATAL: Dash server encountered an error: {e_run_server}", exc_info=True)
        sys.exit(1) # Exit with error status
    finally:
        logger.info("RUNNER: Dash server stopped. Attempting application cleanup...")
        if app_cleanup_function and callable(app_cleanup_function):
            try:
                app_cleanup_function()
                logger.info("RUNNER: Application cleanup function executed successfully.")
            except Exception as e_app_cleanup:
                logger.warning(f"RUNNER: Error during application cleanup: {e_app_cleanup}", exc_info=True)
        else:
            logger.info("RUNNER: No specific application cleanup function was found or callable.")
        
        shutdown_duration = time.monotonic() - runner_start_time
        logger.info(f"=== Enhanced Options Dashboard Runner Shutdown Complete (Total uptime: {timedelta(seconds=shutdown_duration)}) ===")

if __name__ == '__main__':
    # This structure ensures that if this script is run directly, main() is executed.
    # If it were imported, main() would not automatically run.
    main()