# database_manager.py (for PostgreSQL/Supabase)
"""
Handles PostgreSQL database interactions for the EOTS v2.5 system,
including connection, table creation, and basic CRUD operations using psycopg2.
"""
import psycopg2
import psycopg2.extras # For DictCursor
import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Union 
from datetime import datetime, timedelta # Added timedelta for example
import pandas as pd # Moved import pandas as pd to the top
import os # Added for environment variables in example

# Module-level logger
logger = logging.getLogger(__name__)

# Database connection parameters will be passed to connect_db function
# Example structure for connection_details:
# {
#     "host": "db.your-project-ref.supabase.co",
#     "dbname": "postgres",
#     "user": "postgres",
#     "password": "YOUR_DATABASE_PASSWORD",
#     "port": "5432" # or your specific port
# }

def get_db_connection(connection_details: Dict[str, str]) -> Optional[psycopg2.extensions.connection]:
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host=connection_details.get("host"),
            dbname=connection_details.get("dbname"),
            user=connection_details.get("user"),
            password=connection_details.get("password"),
            port=connection_details.get("port")
        )
        logger.info(f"Successfully connected to PostgreSQL database host: {connection_details.get('host')}")
        return conn
    except psycopg2.Error as e:
        logger.error(f"Error connecting to PostgreSQL database host '{connection_details.get('host')}': {e}", exc_info=True)
        return None

def create_tables(conn: psycopg2.extensions.connection):
    """Creates the necessary tables in the database if they don't already exist."""
    if not conn:
        logger.error("Cannot create tables: database connection is None.")
        return

    commands = (
        # --- Performance Tracking Tables ---
        """
        CREATE TABLE IF NOT EXISTS Trade_Recommendations_Log (
            recommendation_id TEXT PRIMARY KEY,
            timestamp_issued_utc BIGINT NOT NULL, -- Unix epoch timestamp (seconds)
            symbol TEXT NOT NULL,
            market_regime_at_issuance TEXT NOT NULL,
            ticker_context_at_issuance_json JSONB,
            triggering_signals_json JSONB,
            atif_situational_assessment_json JSONB,
            atif_final_conviction_score REAL,
            atif_conviction_level TEXT,
            selected_strategy_type TEXT NOT NULL,
            target_dte_min INTEGER,
            target_dte_max INTEGER,
            target_delta_long_leg_min REAL,
            target_delta_long_leg_max REAL,
            target_delta_short_leg_min REAL,
            target_delta_short_leg_max REAL,
            recommended_options_json JSONB,
            calculated_entry_price REAL,
            initial_stop_loss_price REAL,
            initial_target_1_price REAL,
            initial_target_2_price REAL,
            initial_target_3_price REAL,
            tpo_rationale TEXT,
            current_status TEXT NOT NULL,
            last_status_update_utc BIGINT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS Trade_Outcomes_Log (
            trade_log_id SERIAL PRIMARY KEY, -- Auto-incrementing integer
            recommendation_id TEXT NOT NULL REFERENCES Trade_Recommendations_Log(recommendation_id),
            entry_timestamp_utc BIGINT,
            actual_entry_price REAL,
            contracts_traded_json JSONB,
            exit_timestamp_utc BIGINT,
            actual_exit_price REAL,
            exit_reason TEXT,
            profit_loss_absolute REAL,
            profit_loss_percentage REAL,
            mae_during_trade REAL,
            mfe_during_trade REAL,
            trade_duration_seconds INTEGER,
            commissions_fees REAL,
            notes TEXT,
            metrics_at_entry_json JSONB,
            metrics_at_exit_json JSONB
        )
        """,
        # --- Historical Market & System Data Tables ---
        """
        CREATE TABLE IF NOT EXISTS Daily_OHLCV_Data (
            ohlcv_id SERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            date BIGINT NOT NULL, -- Unix epoch for start of day UTC (seconds), or YYYYMMDD int
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume BIGINT, -- Changed to BIGINT for larger volumes
            UNIQUE (symbol, date)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS Daily_EOTS_Metrics_Aggregates (
            metric_log_id SERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            date BIGINT NOT NULL, -- Unix epoch for start of day UTC (seconds), or YYYYMMDD int
            gib_oi_based_und REAL,
            td_gib_dollar_und REAL,
            hp_eod_und REAL,
            vapi_fa_z_score_und REAL,
            dwfd_z_score_und REAL,
            tw_laf_z_score_und REAL,
            a_mspi_und_avg REAL,
            a_sai_und_avg REAL,
            a_ssi_und_avg REAL,
            vri_2_0_und_aggregate REAL,
            market_regime_v2_5_daily_summary TEXT,
            underlying_closing_price REAL,
            underlying_atr_daily REAL,
            UNIQUE (symbol, date)
        )
        """
    )
    try:
        with conn.cursor() as cur:
            for command in commands:
                cur.execute(command)
                logger.debug(f"Executed: {command.strip().splitlines()[0]}...") # Log first line of command
        conn.commit()
        logger.info("All EOTS database tables checked/created successfully for PostgreSQL.")
    except psycopg2.Error as e:
        logger.error(f"Error creating EOTS tables for PostgreSQL: {e}", exc_info=True)
        conn.rollback()

# --- Functions for Performance Tracking Data ---

def log_trade_recommendation_pg(conn: psycopg2.extensions.connection, rec_data: Dict[str, Any]) -> Optional[str]:
    """Logs a new trade recommendation to PostgreSQL. Returns recommendation_id if successful."""
    if not conn: return None
    sql = """
    INSERT INTO Trade_Recommendations_Log (
        recommendation_id, timestamp_issued_utc, symbol, market_regime_at_issuance,
        ticker_context_at_issuance_json, triggering_signals_json, atif_situational_assessment_json,
        atif_final_conviction_score, atif_conviction_level, selected_strategy_type,
        target_dte_min, target_dte_max, target_delta_long_leg_min, target_delta_long_leg_max,
        target_delta_short_leg_min, target_delta_short_leg_max, recommended_options_json,
        calculated_entry_price, initial_stop_loss_price, initial_target_1_price,
        initial_target_2_price, initial_target_3_price, tpo_rationale, current_status,
        last_status_update_utc
    ) VALUES (
        %(recommendation_id)s, %(timestamp_issued_utc)s, %(symbol)s, %(market_regime_at_issuance)s,
        %(ticker_context_at_issuance_json)s, %(triggering_signals_json)s, %(atif_situational_assessment_json)s,
        %(atif_final_conviction_score)s, %(atif_conviction_level)s, %(selected_strategy_type)s,
        %(target_dte_min)s, %(target_dte_max)s, %(target_delta_long_leg_min)s, %(target_delta_long_leg_max)s,
        %(target_delta_short_leg_min)s, %(target_delta_short_leg_max)s, %(recommended_options_json)s,
        %(calculated_entry_price)s, %(initial_stop_loss_price)s, %(initial_target_1_price)s,
        %(initial_target_2_price)s, %(initial_target_3_price)s, %(tpo_rationale)s, %(current_status)s,
        %(last_status_update_utc)s
    ) ON CONFLICT (recommendation_id) DO NOTHING;
    """ # Added ON CONFLICT DO NOTHING for robustness
    try:
        # Ensure JSON fields are proper JSON strings if they are dicts/lists
        for json_field in ['ticker_context_at_issuance_json', 'triggering_signals_json', 
                           'atif_situational_assessment_json', 'recommended_options_json']:
            if json_field in rec_data and isinstance(rec_data[json_field], (dict, list)):
                rec_data[json_field] = json.dumps(rec_data[json_field])
            elif json_field in rec_data and rec_data[json_field] is None: # psycopg2 needs None for NULL, not json 'null'
                pass # Keep as None
            elif json_field in rec_data and not isinstance(rec_data[json_field], str):
                 rec_data[json_field] = str(rec_data[json_field]) # Fallback to string for safety

        with conn.cursor() as cur:
            cur.execute(sql, rec_data)
        conn.commit()
        logger.info(f"Logged/ignored trade recommendation ID: {rec_data.get('recommendation_id')}")
        return rec_data.get('recommendation_id')
    except psycopg2.Error as e:
        logger.error(f"Error logging trade recommendation to PostgreSQL: {e}", exc_info=True)
        conn.rollback()
        return None
    except Exception as e_gen: # Catch other potential errors like bad data types
        logger.error(f"Generic error logging trade recommendation: {e_gen}. Data: {rec_data}", exc_info=True)
        conn.rollback()
        return None


def log_trade_outcome_pg(conn: psycopg2.extensions.connection, outcome_data: Dict[str, Any]) -> Optional[int]:
    """Logs the outcome of a trade to PostgreSQL. Returns trade_log_id if successful."""
    if not conn: return None
    sql = """
    INSERT INTO Trade_Outcomes_Log (
        recommendation_id, entry_timestamp_utc, actual_entry_price, contracts_traded_json,
        exit_timestamp_utc, actual_exit_price, exit_reason, profit_loss_absolute,
        profit_loss_percentage, mae_during_trade, mfe_during_trade, trade_duration_seconds,
        commissions_fees, notes, metrics_at_entry_json, metrics_at_exit_json
    ) VALUES (
        %(recommendation_id)s, %(entry_timestamp_utc)s, %(actual_entry_price)s, %(contracts_traded_json)s,
        %(exit_timestamp_utc)s, %(actual_exit_price)s, %(exit_reason)s, %(profit_loss_absolute)s,
        %(profit_loss_percentage)s, %(mae_during_trade)s, %(mfe_during_trade)s, %(trade_duration_seconds)s,
        %(commissions_fees)s, %(notes)s, %(metrics_at_entry_json)s, %(metrics_at_exit_json)s
    ) RETURNING trade_log_id;
    """
    try:
        for json_field in ['contracts_traded_json', 'metrics_at_entry_json', 'metrics_at_exit_json']:
            if json_field in outcome_data and isinstance(outcome_data[json_field], (dict, list)):
                outcome_data[json_field] = json.dumps(outcome_data[json_field])
            elif json_field in outcome_data and outcome_data[json_field] is None:
                pass
            elif json_field in outcome_data and not isinstance(outcome_data[json_field], str):
                 outcome_data[json_field] = str(outcome_data[json_field])

        with conn.cursor() as cur:
            cur.execute(sql, outcome_data)
            trade_log_id = cur.fetchone()[0] if cur.rowcount > 0 else None
        conn.commit()
        if trade_log_id:
            logger.info(f"Logged trade outcome for recommendation ID: {outcome_data.get('recommendation_id')}. Trade Log ID: {trade_log_id}")
        return trade_log_id
    except psycopg2.Error as e:
        logger.error(f"Error logging trade outcome to PostgreSQL: {e}", exc_info=True)
        conn.rollback()
        return None
    except Exception as e_gen:
        logger.error(f"Generic error logging trade outcome: {e_gen}. Data: {outcome_data}", exc_info=True)
        conn.rollback()
        return None

def get_trade_outcomes_for_symbol_pg(conn: psycopg2.extensions.connection, symbol: str, limit: int = 100) -> List[Dict]:
    """Retrieves recent trade outcomes for a given symbol from PostgreSQL."""
    if not conn: return []
    sql = """
    SELECT tol.*, trl.symbol 
    FROM Trade_Outcomes_Log tol
    JOIN Trade_Recommendations_Log trl ON tol.recommendation_id = trl.recommendation_id
    WHERE trl.symbol = %s
    ORDER BY tol.exit_timestamp_utc DESC
    LIMIT %s
    """
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(sql, (symbol, limit))
            rows = cur.fetchall()
        return [dict(row) for row in rows]
    except psycopg2.Error as e:
        logger.error(f"Error fetching trade outcomes for symbol {symbol} from PostgreSQL: {e}", exc_info=True)
        return []

# --- Functions for Historical Market & System Data ---

def store_daily_ohlcv_batch_pg(conn: psycopg2.extensions.connection, ohlcv_data_list: List[Dict[str, Any]]):
    """Stores a batch of daily OHLCV data to PostgreSQL. Uses INSERT ... ON CONFLICT DO NOTHING."""
    if not conn or not ohlcv_data_list: return
    sql = """
    INSERT INTO Daily_OHLCV_Data (symbol, date, open, high, low, close, volume)
    VALUES (%(symbol)s, %(date)s, %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s)
    ON CONFLICT (symbol, date) DO NOTHING; 
    """
    try:
        with conn.cursor() as cur:
            psycopg2.extras.execute_batch(cur, sql, ohlcv_data_list)
        conn.commit()
        logger.info(f"Attempted to store {len(ohlcv_data_list)} daily OHLCV records to PostgreSQL.")
    except psycopg2.Error as e:
        logger.error(f"Error storing daily OHLCV batch to PostgreSQL: {e}", exc_info=True)
        conn.rollback()
    except Exception as e_gen:
        logger.error(f"Generic error storing daily OHLCV batch: {e_gen}", exc_info=True)
        conn.rollback()


def store_daily_eots_metrics_batch_pg(conn: psycopg2.extensions.connection, metrics_data_list: List[Dict[str, Any]]):
    """Stores a batch of daily EOTS aggregate metrics to PostgreSQL. Uses INSERT ... ON CONFLICT DO NOTHING."""
    if not conn or not metrics_data_list: return
    sql = """
    INSERT INTO Daily_EOTS_Metrics_Aggregates (
        symbol, date, gib_oi_based_und, td_gib_dollar_und, hp_eod_und,
        vapi_fa_z_score_und, dwfd_z_score_und, tw_laf_z_score_und,
        a_mspi_und_avg, a_sai_und_avg, a_ssi_und_avg, vri_2_0_und_aggregate,
        market_regime_v2_5_daily_summary, underlying_closing_price, underlying_atr_daily
    ) VALUES (
        %(symbol)s, %(date)s, %(gib_oi_based_und)s, %(td_gib_dollar_und)s, %(hp_eod_und)s,
        %(vapi_fa_z_score_und)s, %(dwfd_z_score_und)s, %(tw_laf_z_score_und)s,
        %(a_mspi_und_avg)s, %(a_sai_und_avg)s, %(a_ssi_und_avg)s, %(vri_2_0_und_aggregate)s,
        %(market_regime_v2_5_daily_summary)s, %(underlying_closing_price)s, %(underlying_atr_daily)s
    ) ON CONFLICT (symbol, date) DO NOTHING;
    """
    try:
        with conn.cursor() as cur:
            psycopg2.extras.execute_batch(cur, sql, metrics_data_list)
        conn.commit()
        logger.info(f"Attempted to store {len(metrics_data_list)} daily EOTS metrics records to PostgreSQL.")
    except psycopg2.Error as e:
        logger.error(f"Error storing daily EOTS metrics batch to PostgreSQL: {e}", exc_info=True)
        conn.rollback()
    except Exception as e_gen:
        logger.error(f"Generic error storing daily EOTS metrics batch: {e_gen}", exc_info=True)
        conn.rollback()


def get_ohlcv_for_symbol_daterange_pg(conn: psycopg2.extensions.connection, symbol: str, start_date_val: Union[int, float], end_date_val: Union[int, float]) -> List[Dict]:
    """Retrieves OHLCV data for a symbol within a date range from PostgreSQL."""
    if not conn: return []
    sql = """
    SELECT * FROM Daily_OHLCV_Data
    WHERE symbol = %s AND date >= %s AND date <= %s
    ORDER BY date ASC
    """
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(sql, (symbol, start_date_val, end_date_val))
            rows = cur.fetchall()
        return [dict(row) for row in rows]
    except psycopg2.Error as e:
        logger.error(f"Error fetching OHLCV for {symbol} ({start_date_val}-{end_date_val}) from PostgreSQL: {e}", exc_info=True)
        return []

def get_historical_metric_distribution_pg(conn: psycopg2.extensions.connection, symbol: str, metric_name: str, lookback_days: int) -> Optional[pd.Series]:
    """
    Retrieves a series of a specific EOTS aggregate metric for a symbol from PostgreSQL.
    'metric_name' must be a valid column name in Daily_EOTS_Metrics_Aggregates.
    Assumes 'date' column is stored as Unix epoch timestamp (seconds) for timedelta.
    """
    if not conn: return None
    try:
        # Import datetime, timedelta here if not globally available in this module's context when called
        # from datetime import datetime, timedelta # Already imported at module level
        current_timestamp = int(datetime.now().timestamp())
        start_timestamp = current_timestamp - (lookback_days * 24 * 60 * 60)
    except Exception:
        logger.error("Date conversion for metric distribution failed, query might be incorrect.", exc_info=True)
        return None

    valid_metric_cols = [
        "gib_oi_based_und", "td_gib_dollar_und", "hp_eod_und", "vapi_fa_z_score_und", 
        "dwfd_z_score_und", "tw_laf_z_score_und", "a_mspi_und_avg", "a_sai_und_avg", 
        "a_ssi_und_avg", "vri_2_0_und_aggregate", "underlying_closing_price", "underlying_atr_daily"
    ]
    if metric_name not in valid_metric_cols:
        logger.error(f"Invalid metric_name '{metric_name}' for get_historical_metric_distribution_pg.")
        return None

    sql = f"""
    SELECT {metric_name} FROM Daily_EOTS_Metrics_Aggregates
    WHERE symbol = %s AND date >= %s AND date <= %s 
    ORDER BY date ASC
    """
    
    try:
        with conn.cursor() as cur: 
            cur.execute(sql, (symbol, start_timestamp, current_timestamp))
            rows = cur.fetchall() 
        if not rows: return pd.Series(dtype=float)
        
        metric_series = pd.Series([row[0] for row in rows if row[0] is not None])
        return metric_series.dropna()
    except psycopg2.Error as e:
        logger.error(f"Error fetching historical metric '{metric_name}' for {symbol} from PostgreSQL: {e}", exc_info=True)
        return None
    # Removed ImportError for pd as it's now at module level


# --- Example Usage & Setup ---
if __name__ == '__main__':
    # os and timedelta are now imported at module level or within specific functions if needed
    # pandas (pd) is imported at module level

    logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] (%(name)s:%(lineno)d) %(asctime)s - %(message)s')
    dbm_logger = logging.getLogger("DBM_Standalone_Test")
    dbm_logger.info("Running database_manager.py (PostgreSQL/Supabase version) standalone example...")
    
    test_connection_details = {
        "host": os.environ.get("SUPABASE_DB_HOST", "your-db-host.supabase.co"),
        "dbname": os.environ.get("SUPABASE_DB_NAME", "postgres"),
        "user": os.environ.get("SUPABASE_DB_USER", "postgres"),
        "password": os.environ.get("SUPABASE_DB_PASSWORD", "YOUR_SECRET_PASSWORD"),
        "port": os.environ.get("SUPABASE_DB_PORT", "5432")
    }

    if "YOUR_SECRET_PASSWORD" == test_connection_details["password"] or "your-db-host" in test_connection_details["host"]:
        dbm_logger.critical("Placeholder connection details detected. Please update with your actual Supabase credentials.")
        dbm_logger.critical("Set environment variables: SUPABASE_DB_HOST, SUPABASE_DB_NAME, SUPABASE_DB_USER, SUPABASE_DB_PASSWORD, SUPABASE_DB_PORT")
        exit()

    db_connection_pg = get_db_connection(test_connection_details)
    
    if db_connection_pg:
        create_tables(db_connection_pg)
        
        ts_now_utc = int(datetime.utcnow().timestamp())
        sample_rec_pg = {
            'recommendation_id': f'TESTREC_PG_{ts_now_utc}', 'timestamp_issued_utc': ts_now_utc,
            'symbol': 'TSLA', 'market_regime_at_issuance': 'VolExpansionExpected',
            'selected_strategy_type': 'LongStraddle', 'current_status': 'ACTIVE_NEW',
            'ticker_context_at_issuance_json': json.dumps({"is_earnings_week": True}),
            'last_status_update_utc': ts_now_utc,
            'triggering_signals_json': None, 'atif_situational_assessment_json': None,
            'atif_final_conviction_score': None, 'atif_conviction_level': None,
            'target_dte_min': 7, 'target_dte_max': 14, 'target_delta_long_leg_min': None, 
            'target_delta_long_leg_max': None, 'target_delta_short_leg_min': None, 'target_delta_short_leg_max': None,
            'recommended_options_json': json.dumps([{"contract":"TSLA251219C00200000", "action":"BUY"}]),
            'calculated_entry_price': 15.50, 'initial_stop_loss_price': 10.0, 
            'initial_target_1_price': 25.0, 'initial_target_2_price': 35.0, 'initial_target_3_price': None,
            'tpo_rationale': 'Example TPO Rationale for Test PG Rec'
        }
        log_trade_recommendation_pg(db_connection_pg, sample_rec_pg)

        sample_outcome_pg = {
            'recommendation_id': sample_rec_pg['recommendation_id'], 
            'entry_timestamp_utc': ts_now_utc + 300,
            'actual_entry_price': 15.45, 
            'exit_timestamp_utc': ts_now_utc + (2 * 24 * 3600),
            'actual_exit_price': 18.50, 'exit_reason': 'TP1_Hit_Manual', 
            'profit_loss_absolute': (18.50 - 15.45) * 100,
            'contracts_traded_json': json.dumps([{"contract":"TSLA251219C00200000", "action":"BUY", "qty":1, "price":15.45}, {"contract":"TSLA251219C00200000", "action":"SELL", "qty":1, "price":18.50}])
        }
        outcome_fields = ["profit_loss_percentage", "mae_during_trade", "mfe_during_trade", 
                          "trade_duration_seconds", "commissions_fees", "notes", 
                          "metrics_at_entry_json", "metrics_at_exit_json"]
        for fld in outcome_fields:
            sample_outcome_pg.setdefault(fld, None)
        log_trade_outcome_pg(db_connection_pg, sample_outcome_pg)

        today_int_pg = int(datetime.utcnow().date().strftime("%Y%m%d")) 
        sample_ohlcv_pg = [{
            'symbol': 'TSLA', 'date': today_int_pg, 
            'open': 180.0, 'high': 182.5, 'low': 179.5, 'close': 182.0, 'volume': 75000000
        }]
        store_daily_ohlcv_batch_pg(db_connection_pg, sample_ohlcv_pg)

        sample_eots_metrics_pg = [{
            'symbol': 'TSLA', 'date': today_int_pg, 
            'gib_oi_based_und': 5e9, 'vapi_fa_z_score_und': -0.5,
            'underlying_closing_price': 182.0, 'underlying_atr_daily': 5.5,
            'td_gib_dollar_und': None, 'hp_eod_und': None, 'dwfd_z_score_und': None, 
            'tw_laf_z_score_und': None, 'a_mspi_und_avg': None, 'a_sai_und_avg': None, 
            'a_ssi_und_avg': None, 'vri_2_0_und_aggregate': None, 
            'market_regime_v2_5_daily_summary': 'Neutral'
        }]
        store_daily_eots_metrics_batch_pg(db_connection_pg, sample_eots_metrics_pg)

        tsla_outcomes_pg = get_trade_outcomes_for_symbol_pg(db_connection_pg, 'TSLA')
        dbm_logger.info(f"TSLA Trade Outcomes (PG): {tsla_outcomes_pg}")

        tsla_gib_hist_pg = get_historical_metric_distribution_pg(db_connection_pg, 'TSLA', 'gib_oi_based_und', 30)
        if tsla_gib_hist_pg is not None:
            dbm_logger.info(f"TSLA Historical GIB (PG) (last 30d, {len(tsla_gib_hist_pg)} points): Mean={tsla_gib_hist_pg.mean() if not tsla_gib_hist_pg.empty else 'N/A'}")

        db_connection_pg.close()
        dbm_logger.info("PostgreSQL Database connection closed.")
    else:
        dbm_logger.error("Failed to get PostgreSQL database connection for standalone test.")

