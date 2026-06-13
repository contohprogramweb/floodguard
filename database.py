import mysql.connector
from mysql.connector import pooling, OperationalError
import config
import time

DB_CONFIG = {
    'host': config.MYSQL_HOST,
    'user': config.MYSQL_USER,
    'password': config.MYSQL_PASSWORD,
    'database': config.MYSQL_DB,
    'connect_timeout': 10,      # Timeout koneksi: 10 detik
    'connection_timeout': 10,   # Timeout koneksi: 10 detik  
    'raise_on_warnings': True,
    'use_pure': True            # Gunakan pure Python implementation (lebih stabil)
}

# Connection pool untuk performa lebih baik
connection_pool = None

def init_connection_pool(pool_size=5, pool_name="iot_pool"):
    """Inisialisasi connection pool"""
    global connection_pool
    try:
        connection_pool = pooling.MySQLConnectionPool(
            pool_name=pool_name,
            pool_size=pool_size,
            **DB_CONFIG
        )
        return True
    except Exception as e:
        print(f"Error initializing connection pool: {e}")
        return False

def get_db_connection(max_retries=3, retry_delay=2):
    """
    Mendapatkan koneksi database dengan retry mechanism
    max_retries: jumlah maksimal percobaan ulang
    retry_delay: delay antar percobaan (detik)
    """
    global connection_pool
    
    # Coba gunakan pool jika sudah diinisialisasi
    if connection_pool is not None:
        try:
            return connection_pool.get_connection()
        except Exception as e:
            print(f"Pool connection failed: {e}")
            # Reset pool jika error
            connection_pool = None
    
    # Fallback: koneksi langsung dengan retry
    for attempt in range(max_retries):
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            return conn
        except OperationalError as e:
            if attempt < max_retries - 1:
                print(f"Connection attempt {attempt + 1} failed: {e}. Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                print(f"All {max_retries} connection attempts failed.")
                raise
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Connection attempt {attempt + 1} failed: {e}. Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                raise
    
    return None
