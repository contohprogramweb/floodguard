import os
#36.50.77.116
MYSQL_HOST = os.environ.get('MYSQL_HOST', '36.50.77.116')
MYSQL_USER = os.environ.get('MYSQL_USER', 'alatdete_root')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'diehard2001OK')
MYSQL_DB = os.environ.get('MYSQL_DB', 'alatdete_iot')
SECRET_KEY = os.environ.get('SECRET_KEY', 'aplikasi_a_secret_key_change_in_production')
