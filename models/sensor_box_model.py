from database import get_db_connection

class SensorBoxModel:

    @staticmethod
    def find_by_kode(kode_sensorbox):
        conn = get_db_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM sensor_box WHERE kode_sensorbox = %s",
                (kode_sensorbox,)
            )
            return cursor.fetchone()
        finally:
            conn.close()

    @staticmethod
    def find_by_id(id_sensorbox):
        conn = get_db_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM sensor_box WHERE id_sensorbox = %s",
                (id_sensorbox,)
            )
            return cursor.fetchone()
        finally:
            conn.close()

    @staticmethod
    def create(kode_sensorbox, nama_pemilik, alamat_pemilik, nomor_whatsapp, password):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO sensor_box 
                   (kode_sensorbox, nama_pemilik, alamat_pemilik, nomor_whatsapp, password)
                   VALUES (%s, %s, %s, %s, %s)""",
                (kode_sensorbox, nama_pemilik, alamat_pemilik, nomor_whatsapp, password)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    @staticmethod
    def update(id_sensorbox, nama_pemilik, alamat_pemilik, nomor_whatsapp):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE sensor_box SET
                   nama_pemilik=%s, alamat_pemilik=%s, nomor_whatsapp=%s
                   WHERE id_sensorbox=%s""",
                (nama_pemilik, alamat_pemilik, nomor_whatsapp, id_sensorbox)
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def update_password(id_sensorbox, password):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE sensor_box SET password=%s WHERE id_sensorbox=%s",
                (password, id_sensorbox)
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def kode_exists(kode_sensorbox):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id_sensorbox FROM sensor_box WHERE kode_sensorbox = %s",
                (kode_sensorbox,)
            )
            return cursor.fetchone() is not None
        finally:
            conn.close()
