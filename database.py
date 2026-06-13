import mysql.connector
import config

DB_CONFIG = {
    'host': config.MYSQL_HOST,
    'user': config.MYSQL_USER,
    'password': config.MYSQL_PASSWORD,
    'database': config.MYSQL_DB
}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)
