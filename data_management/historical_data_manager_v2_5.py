# data_management/historical_data_manager_v2_5.py
"""
Manages the persistent storage and retrieval of historical market data
for the EOTS v2.5 system, including OHLCV and calculated aggregate metrics.

This module interacts with database_manager_v2_5.py for actual
database operations.
"""
import logging
import pandas as pd
from typing import List, Dict, Any, Optional, Union
from datetime import date, datetime, timedelta # Ensure all necessary datetime components are imported

# --- Relative import for database_manager ---
# Since database_manager.py is now in the SAME data_management/ package,
# we use a relative import.
from . import database_manager_v2_5 as db_manager
# If you prefer to import specific functions from database_manager:
# from .database_manager_v2_5 import get_db_connection, store_daily_ohlcv_batch_pg, etc.

# If psycopg2 types are used for type hinting and it's available in the db_manager context
try:
    import psycopg2.extras # For type hinting DictCursor if used in db_manager
except ImportError:
    psycopg2 = None # type: ignore

# --- Module-Specific Logger ---
logger = logging.getLogger(__name__)
# (Consider centralizing logging configuration in your main runner script,
# but a direct logger here is fine for module-specific messages)


class HistoricalDataManagerV2_5:
    """
    Handles storage and retrieval of historical data relevant for EOTS analysis,
    such as daily OHLCV and aggregated EOTS metrics.
    """
    def __init__(self, db_connection_details: Dict[str, str]):
        """
        Initializes the HistoricalDataManagerV2_5.

        Args:
            db_connection_details (Dict[str, str]): Credentials for DB connection.
        """
        self.db_connection_details = db_connection_details
        # (Your existing connection test logic can remain here)
        conn_test = None
        try:
            conn_test = db_manager.get_db_connection(self.db_connection_details)
            if conn_test:
                logger.info("HistoricalDataManagerV2_5: Database connection details validated successfully.")
            else:
                logger.error("HistoricalDataManagerV2_5: Failed to establish a test database connection with provided details.")
        except Exception as e:
            logger.error(f"HistoricalDataManagerV2_5: Error during initial DB connection test: {e}", exc_info=True)
        finally:
            if conn_test:
                conn_test.close()

    def _execute_query(self, query: str, params: Optional[tuple] = None, fetch_one: bool = False, fetch_all: bool = False, commit: bool = False) -> Any:
        """
        Helper function to execute database queries.
        Manages connection opening and closing for each operation.
        In a high-throughput application, a connection pool would be better.
        """
        conn = None
        results = None
        try:
            conn = db_manager.get_db_connection(self.db_connection_details)
            if not conn:
                logger.error("HistoricalDataManagerV2_5: Failed to get database connection for query execution.")
                return None
            
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor if hasattr(db_manager, 'psycopg2') else None) as cur: # Use DictCursor if psycopg2
                cur.execute(query, params)
                if fetch_one:
                    results = cur.fetchone()
                elif fetch_all:
                    results = cur.fetchall()
                
                if commit:
                    conn.commit()
                    logger.debug(f"Query executed and committed: {query[:100]}...")
                else:
                    logger.debug(f"Query executed: {query[:100]}...")

        except Exception as e:
            logger.error(f"HistoricalDataManagerV2_5: Database query error: {e}\nQuery: {query}\nParams: {params}", exc_info=True)
            if conn: # Rollback on error if it was a transaction
                conn.rollback()
        finally:
            if conn:
                conn.close()
        return results

    def store_daily_ohlcv_batch(self, symbol: str, ohlcv_data_list: List[Dict[str, Any]]) -> bool:
        """
        Stores a batch of daily OHLCV data for a given symbol.

        Args:
            symbol (str): The trading symbol (e.g., 'SPY').
            ohlcv_data_list (List[Dict[str, Any]]): A list of dictionaries,
                where each dictionary represents a day's OHLCV data.
                Expected keys: 'date' (YYYYMMDD int or datetime.date), 'open', 'high', 'low', 'close', 'volume'.

        Returns:
            bool: True if storage was successful (or attempted), False otherwise.
        """
        if not ohlcv_data_list:
            logger.info(f"HistoricalDataManagerV2_5: No OHLCV data provided for symbol {symbol} to store.")
            return True # No data to store is not an error in this context

        # Prepare data for the database_manager function
        # The database_manager's store_daily_ohlcv_batch_pg expects 'symbol' to be part of each dict
        data_to_store = []
        for record in ohlcv_data_list:
            if not isinstance(record, dict):
                logger.warning(f"Skipping invalid OHLCV record (not a dict): {record}")
                continue
            
            # Ensure date is in YYYYMMDD integer format if not already
            record_date = record.get('date')
            if isinstance(record_date, datetime):
                record_date = int(record_date.strftime('%Y%m%d'))
            elif isinstance(record_date, date):
                 record_date = int(record_date.strftime('%Y%m%d'))
            elif isinstance(record_date, str):
                try:
                    record_date = int(datetime.strptime(record_date, '%Y-%m-%d').strftime('%Y%m%d'))
                except ValueError:
                    try:
                        record_date = int(record_date) # Assume it's already YYYYMMDD if string
                    except ValueError:
                        logger.warning(f"Invalid date format for OHLCV record: {record.get('date')}. Skipping.")
                        continue
            elif not isinstance(record_date, int):
                 logger.warning(f"Invalid date type for OHLCV record: {type(record_date)}. Skipping.")
                 continue

            # Inside store_daily_ohlcv_batch in historical_data_manager_v2_5.py
            # ...
            data_to_store.append({
                'symbol': symbol,
                'date': record_date, # This should be an integer YYYYMMDD for the DB
                # Ensure these keys match the SQL placeholders in database_manager.py
                'open': record.get('open', record.get('open_price')), 
                'high': record.get('high', record.get('high_price')), 
                'low': record.get('low', record.get('low_price')),   
                'close': record.get('close', record.get('close_price')),
                'volume': record.get('volume')
            })
            # ...
        
        if not data_to_store:
            logger.warning(f"HistoricalDataManagerV2_5: No valid OHLCV data to store for {symbol} after processing.")
            return False

        logger.info(f"HistoricalDataManagerV2_5: Attempting to store {len(data_to_store)} OHLCV records for {symbol}.")
        # Use the existing database_manager function
        # This requires establishing a connection within this call or passing one
        conn = None
        try:
            conn = db_manager.get_db_connection(self.db_connection_details)
            if conn:
                db_manager.store_daily_ohlcv_batch_pg(conn, data_to_store)
                logger.info(f"HistoricalDataManagerV2_5: Successfully attempted to store OHLCV data for {symbol}.")
                return True
            else:
                logger.error(f"HistoricalDataManagerV2_5: Failed to get DB connection for storing OHLCV data for {symbol}.")
                return False
        except Exception as e:
            logger.error(f"HistoricalDataManagerV2_5: Error storing OHLCV data for {symbol}: {e}", exc_info=True)
            return False
        finally:
            if conn:
                conn.close()

    def store_daily_eots_metrics_batch(self, symbol: str, metrics_data_list: List[Dict[str, Any]]) -> bool:
        """
        Stores a batch of daily EOTS aggregate metrics for a given symbol.

        Args:
            symbol (str): The trading symbol.
            metrics_data_list (List[Dict[str, Any]]): A list of dictionaries,
                where each dictionary represents a day's aggregate EOTS metrics.
                Expected keys: 'date' (YYYYMMDD int or datetime.date), and various metric keys
                (e.g., 'gib_oi_based_und', 'vapi_fa_z_score_und', 'underlying_closing_price', etc.).

        Returns:
            bool: True if storage was successful (or attempted), False otherwise.
        """
        if not metrics_data_list:
            logger.info(f"HistoricalDataManagerV2_5: No EOTS metrics data provided for symbol {symbol} to store.")
            return True

        data_to_store = []
        for record in metrics_data_list:
            if not isinstance(record, dict):
                logger.warning(f"Skipping invalid EOTS metrics record (not a dict): {record}")
                continue

            record_date = record.get('date')
            if isinstance(record_date, datetime):
                record_date = int(record_date.strftime('%Y%m%d'))
            elif isinstance(record_date, date):
                 record_date = int(record_date.strftime('%Y%m%d'))
            elif isinstance(record_date, str):
                try:
                    record_date = int(datetime.strptime(record_date, '%Y-%m-%d').strftime('%Y%m%d'))
                except ValueError:
                     try:
                        record_date = int(record_date) # Assume it's already YYYYMMDD if string
                     except ValueError:
                        logger.warning(f"Invalid date format for EOTS metrics record: {record.get('date')}. Skipping.")
                        continue
            elif not isinstance(record_date, int):
                 logger.warning(f"Invalid date type for EOTS metrics record: {type(record_date)}. Skipping.")
                 continue
            
            # Add symbol and ensure date is correctly formatted
            metric_record_to_store = {'symbol': symbol, 'date': record_date}
            # Add all other keys from the input record
            for key, value in record.items():
                if key not in ['symbol', 'date']: # Avoid overwriting
                    metric_record_to_store[key] = value
            data_to_store.append(metric_record_to_store)

        if not data_to_store:
            logger.warning(f"HistoricalDataManagerV2_5: No valid EOTS metrics data to store for {symbol} after processing.")
            return False

        logger.info(f"HistoricalDataManagerV2_5: Attempting to store {len(data_to_store)} EOTS metrics records for {symbol}.")
        conn = None
        try:
            conn = db_manager.get_db_connection(self.db_connection_details)
            if conn:
                # This function expects the full structure including symbol and date per record
                db_manager.store_daily_eots_metrics_batch_pg(conn, data_to_store)
                logger.info(f"HistoricalDataManagerV2_5: Successfully attempted to store EOTS metrics for {symbol}.")
                return True
            else:
                logger.error(f"HistoricalDataManagerV2_5: Failed to get DB connection for storing EOTS metrics for {symbol}.")
                return False
        except Exception as e:
            logger.error(f"HistoricalDataManagerV2_5: Error storing EOTS metrics for {symbol}: {e}", exc_info=True)
            return False
        finally:
            if conn:
                conn.close()

    def get_ohlcv_history(self, symbol: str, start_date: Union[date, str], end_date: Union[date, str], date_format: str = '%Y%m%d') -> pd.DataFrame:
        """
        Retrieves historical OHLCV data for a symbol within a date range.

        Args:
            symbol (str): The trading symbol.
            start_date (Union[date, str]): Start date (inclusive). Can be date object or string.
            end_date (Union[date, str]): End date (inclusive). Can be date object or string.
            date_format (str): The format of start_date/end_date if they are strings.
                               Also used for converting integer dates from DB if needed.

        Returns:
            pd.DataFrame: DataFrame with OHLCV data, or empty DataFrame on error/no data.
                          Columns: ['date', 'open', 'high', 'low', 'close', 'volume']
        """
        try:
            if isinstance(start_date, str):
                start_date_obj = datetime.strptime(start_date, date_format).date()
            elif isinstance(start_date, datetime): # Handle if datetime object is passed
                start_date_obj = start_date.date()
            else: # assume date object
                start_date_obj = start_date

            if isinstance(end_date, str):
                end_date_obj = datetime.strptime(end_date, date_format).date()
            elif isinstance(end_date, datetime): # Handle if datetime object is passed
                end_date_obj = end_date.date()
            else: # assume date object
                end_date_obj = end_date
            
            start_date_int = int(start_date_obj.strftime('%Y%m%d'))
            end_date_int = int(end_date_obj.strftime('%Y%m%d'))

        except ValueError as e_date:
            logger.error(f"HistoricalDataManagerV2_5: Invalid date format for get_ohlcv_history: {e_date}")
            return pd.DataFrame()

        query = """
            SELECT date, open, high, low, close, volume 
            FROM Daily_OHLCV_Data
            WHERE symbol = %s AND date >= %s AND date <= %s
            ORDER BY date ASC;
        """
        params = (symbol, start_date_int, end_date_int)
        
        # Ensure self._execute_query is called correctly
        records = self._execute_query(query, params, fetch_all=True)
        
        if records:
            # These column names MUST match the ones selected in the SQL query
            df = pd.DataFrame(records, columns=['date_int', 'open', 'high', 'low', 'close', 'volume']) 
            try:
                # Convert integer date from DB back to datetime.date objects
                df['date'] = pd.to_datetime(df['date_int'].astype(str), format='%Y%m%d').dt.date
                df.drop(columns=['date_int'], inplace=True) # Drop the temporary integer date column
            except Exception as e_conv:
                logger.warning(f"HistoricalDataManagerV2_5: Could not convert date_int in OHLCV: {e_conv}. Keeping as int if conversion failed.")
                # If conversion fails, it might be better to rename to avoid confusion,
                # or ensure the column is still named 'date' for consistency if it's kept as int.
                if 'date_int' in df.columns and 'date' not in df.columns: # Check if 'date' was created
                    df.rename(columns={'date_int': 'date'}, inplace=True)


            logger.info(f"HistoricalDataManagerV2_5: Retrieved {len(df)} OHLCV records for {symbol} from {start_date_obj} to {end_date_obj}.")
            return df
        else:
            logger.info(f"HistoricalDataManagerV2_5: No OHLCV data found for {symbol} from {start_date_obj} to {end_date_obj}.")
            return pd.DataFrame()

    def get_historical_metric_data(self, symbol: str, metric_name: str, start_date: Union[date, str], end_date: Union[date, str], date_format: str = '%Y%m%d') -> pd.DataFrame:
        """
        Retrieves historical data for a specific EOTS aggregate metric for a symbol.

        Args:
            symbol (str): The trading symbol.
            metric_name (str): The column name of the metric to retrieve (e.g., 'gib_oi_based_und').
            start_date (Union[date, str]): Start date (inclusive).
            end_date (Union[date, str]): End date (inclusive).
            date_format (str): Format for string dates.

        Returns:
            pd.DataFrame: DataFrame with ['date', metric_name], or empty DataFrame on error/no data.
        """
        try:
            if isinstance(start_date, str):
                start_date_obj = datetime.strptime(start_date, date_format).date()
            elif isinstance(start_date, datetime):
                start_date_obj = start_date.date()
            else:
                start_date_obj = start_date

            if isinstance(end_date, str):
                end_date_obj = datetime.strptime(end_date, date_format).date()
            elif isinstance(end_date, datetime):
                end_date_obj = end_date.date()
            else:
                end_date_obj = end_date

            start_date_int = int(start_date_obj.strftime('%Y%m%d'))
            end_date_int = int(end_date_obj.strftime('%Y%m%d'))
        except ValueError as e_date:
            logger.error(f"HistoricalDataManagerV2_5: Invalid date format for get_historical_metric_data: {e_date}")
            return pd.DataFrame()

        # Need to ensure the metric_name is a valid column to prevent SQL injection.
        # Best practice: Validate metric_name against a predefined list of allowed metric columns.
        # For now, we assume metric_name is safe as it's developer-defined.
        # However, for production, add validation.
        allowed_metrics_cols = db_manager.get_eots_metrics_column_names_pg() # Get from db_manager
        if metric_name not in allowed_metrics_cols:
            logger.error(f"HistoricalDataManagerV2_5: Invalid or non-allowed metric_name '{metric_name}'. Cannot query.")
            return pd.DataFrame()

        query = f"""
            SELECT date, "{metric_name}"
            FROM Daily_EOTS_Metrics_Aggregates
            WHERE symbol = %s AND date >= %s AND date <= %s AND "{metric_name}" IS NOT NULL
            ORDER BY date ASC;
        """
        params = (symbol, start_date_int, end_date_int)
        
        records = self._execute_query(query, params, fetch_all=True)
        
        if records:
            df = pd.DataFrame(records, columns=['date_int', metric_name])
            try:
                df['date'] = pd.to_datetime(df['date_int'].astype(str), format='%Y%m%d').dt.date
                df.drop(columns=['date_int'], inplace=True)
            except Exception as e_conv:
                logger.warning(f"HistoricalDataManagerV2_5: Could not convert date_int in metric data: {e_conv}. Keeping as int.")
                df.rename(columns={'date_int': 'date'}, inplace=True)

            logger.info(f"HistoricalDataManagerV2_5: Retrieved {len(df)} records for metric '{metric_name}' for {symbol} from {start_date_obj} to {end_date_obj}.")
            return df[['date', metric_name]] # Ensure correct column order
        else:
            logger.info(f"HistoricalDataManagerV2_5: No data found for metric '{metric_name}' for {symbol} from {start_date_obj} to {end_date_obj}.")
            return pd.DataFrame()

    def get_metric_distribution_stats(self, symbol: str, metric_name: str, lookback_days: int) -> Dict[str, Optional[float]]:
        """
        Calculates distribution statistics (mean, std, percentiles) for a metric
        over a lookback period. Used for dynamic thresholding.

        Args:
            symbol (str): The trading symbol.
            metric_name (str): The column name of the metric.
            lookback_days (int): Number of past days to consider for distribution.

        Returns:
            Dict[str, Optional[float]]: Dictionary with stats like 'mean', 'std', 
                                        'p05', 'p10', 'p25', 'p50', 'p75', 'p90', 'p95', 'min', 'max', 'count'.
                                        Returns None for values if data is insufficient or error.
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=lookback_days -1) # -1 because it's inclusive

        metric_df = self.get_historical_metric_data(symbol, metric_name, start_date, end_date)

        stats: Dict[str, Optional[float]] = {
            'mean': None, 'std': None, 'min': None, 'max': None, 'count': 0,
            'p01': None, 'p05': None, 'p10': None, 'p25': None, 'p50': None, 
            'p75': None, 'p90': None, 'p95': None, 'p99': None
        }

        if metric_df.empty or metric_name not in metric_df.columns:
            logger.warning(f"HistoricalDataManagerV2_5: No data or metric column '{metric_name}' not found for {symbol} in the last {lookback_days} days to calculate distribution stats.")
            return stats
        
        metric_series = pd.to_numeric(metric_df[metric_name], errors='coerce').dropna()
        
        if metric_series.empty:
            logger.warning(f"HistoricalDataManagerV2_5: Metric series for '{metric_name}' for {symbol} is empty after dropping NaNs.")
            return stats

        stats['count'] = float(len(metric_series))
        stats['mean'] = float(metric_series.mean())
        stats['std'] = float(metric_series.std())
        stats['min'] = float(metric_series.min())
        stats['max'] = float(metric_series.max())
        
        percentiles_to_calc = [0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99]
        calculated_percentiles = metric_series.quantile(percentiles_to_calc)
        
        for p_val, p_key_suffix in zip(percentiles_to_calc, ['p01', 'p05', 'p10', 'p25', 'p50', 'p75', 'p90', 'p95', 'p99']):
            stats[p_key_suffix] = float(calculated_percentiles[p_val]) if pd.notna(calculated_percentiles[p_val]) else None
            
        logger.info(f"HistoricalDataManagerV2_5: Calculated distribution stats for '{metric_name}' on {symbol} (lookback {lookback_days} days): Mean={stats['mean']:.2f}, Std={stats['std']:.2f}, Count={stats['count']}")
        return stats


if __name__ == '__main__':
    # Example Usage (requires database_manager.py to be in the same directory or proper path setup)
    # And environment variables for DB connection set as in database_manager.py's example
    
    # --- Basic Logging Setup for Standalone Test ---
    test_logger_hdm = logging.getLogger("HDM_Standalone_Test")
    test_logger_hdm.setLevel(logging.DEBUG) # Set to DEBUG to see more logs from HDM
    handler_hdm = logging.StreamHandler()
    formatter_hdm = logging.Formatter('[%(levelname)s] (%(name)s:%(lineno)d) %(asctime)s - %(message)s')
    handler_hdm.setFormatter(formatter_hdm)
    if not test_logger_hdm.hasHandlers(): # Avoid adding multiple handlers if run multiple times
        test_logger_hdm.addHandler(handler_hdm)
    # Also configure the logger used *within* the HistoricalDataManagerV2_5 class if needed
    class_logger_hdm = logging.getLogger(__name__) # This is the logger used by the class methods
    class_logger_hdm.setLevel(logging.DEBUG)
    if not class_logger_hdm.hasHandlers():
        class_logger_hdm.addHandler(handler_hdm) # Share the same handler for this test

    test_logger_hdm.info("Running HistoricalDataManagerV2_5 standalone example...")

    # --- Database Connection Details (from environment variables as in database_manager.py) ---
    db_connection_details_hdm = {
        "host": os.environ.get("SUPABASE_DB_HOST_EOTS"), # Use distinct env vars if needed
        "dbname": os.environ.get("SUPABASE_DB_NAME_EOTS", "postgres"),
        "user": os.environ.get("SUPABASE_DB_USER_EOTS", "postgres"),
        "password": os.environ.get("SUPABASE_DB_PASSWORD_EOTS"),
        "port": os.environ.get("SUPABASE_DB_PORT_EOTS", "5432")
    }

    if not db_connection_details_hdm["password"]:
        test_logger_hdm.critical("CRITICAL: SUPABASE_DB_PASSWORD_EOTS environment variable not set. Cannot run test.")
    else:
        hdm = HistoricalDataManagerV2_5(db_connection_details_hdm)

        # 1. Test Storing OHLCV Data
        test_logger_hdm.info("\n--- Testing OHLCV Storage ---")
        sample_ohlcv_data = [
            {'date': date(2024, 1, 1), 'open': 100.0, 'high': 102.5, 'low': 99.5, 'close': 101.0, 'volume': 1000000},
            {'date': '2024-01-02', 'open': 101.0, 'high': 103.0, 'low': 100.0, 'close': 102.0, 'volume': 1200000},
            {'date': 20240103, 'open': 102.0, 'high': 102.0, 'low': 98.0, 'close': 99.0, 'volume': 1100000},
        ]
        hdm.store_daily_ohlcv_batch('TESTSYM_OHLCV', sample_ohlcv_data)

        # 2. Test Retrieving OHLCV Data
        test_logger_hdm.info("\n--- Testing OHLCV Retrieval ---")
        retrieved_ohlcv = hdm.get_ohlcv_history('TESTSYM_OHLCV', date(2024, 1, 1), '2024-01-03', date_format='%Y-%m-%d')
        if not retrieved_ohlcv.empty:
            test_logger_hdm.info(f"Retrieved TESTSYM_OHLCV OHLCV data:\n{retrieved_ohlcv.to_string()}")
        else:
            test_logger_hdm.warning("No OHLCV data retrieved for TESTSYM_OHLCV.")

        # 3. Test Storing EOTS Metrics Data
        test_logger_hdm.info("\n--- Testing EOTS Metrics Storage ---")
        sample_metrics_data = [
            {'date': 20240101, 'gib_oi_based_und': -1.5e10, 'vapi_fa_z_score_und': 1.2, 'underlying_closing_price': 101.0, 'underlying_atr_daily': 2.5, 'market_regime_v2_5_daily_summary': 'NegativeGammaTrending'},
            {'date': '2024-01-02', 'gib_oi_based_und': -1.2e10, 'vapi_fa_z_score_und': 0.5, 'underlying_closing_price': 102.0, 'underlying_atr_daily': 2.6, 'market_regime_v2_5_daily_summary': 'NegativeGammaTrending'},
            {'date': date(2024, 1, 3), 'gib_oi_based_und': 0.5e10, 'vapi_fa_z_score_und': -0.8, 'underlying_closing_price': 99.0, 'underlying_atr_daily': 2.7, 'market_regime_v2_5_daily_summary': 'PositiveGammaStable'},
        ]
        hdm.store_daily_eots_metrics_batch('TESTSYM_METRICS', sample_metrics_data)

        # 4. Test Retrieving Specific Metric Data
        test_logger_hdm.info("\n--- Testing Specific Metric Retrieval ---")
        retrieved_gib = hdm.get_historical_metric_data('TESTSYM_METRICS', 'gib_oi_based_und', date(2024, 1, 1), date(2024, 1, 3))
        if not retrieved_gib.empty:
            test_logger_hdm.info(f"Retrieved TESTSYM_METRICS GIB data:\n{retrieved_gib.to_string()}")
        else:
            test_logger_hdm.warning("No GIB data retrieved for TESTSYM_METRICS.")

        # 5. Test Metric Distribution Stats
        test_logger_hdm.info("\n--- Testing Metric Distribution Stats ---")
        # Ensure enough data for meaningful stats, might need to store more than 3 days for a real test
        # For this example, it will use the 3 days stored above.
        gib_stats = hdm.get_metric_distribution_stats('TESTSYM_METRICS', 'gib_oi_based_und', lookback_days=5) # Lookback 5, but only 3 days of data
        test_logger_hdm.info(f"GIB Distribution Stats for TESTSYM_METRICS (last 5 days, found {gib_stats.get('count')} points):")
        for stat_key, stat_val in gib_stats.items():
            test_logger_hdm.info(f"  {stat_key}: {stat_val}")
        
        test_logger_hdm.info("HistoricalDataManagerV2_5 standalone example finished.")
