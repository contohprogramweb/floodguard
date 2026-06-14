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


class DataSensorModel:
    """Model untuk tabel data_sensor"""

    @staticmethod
    def insert(id_sensorbox, tinggi_air, suhu, kelembaban, curah_hujan):
        """Insert data sensor baru dan return id_data_sensor"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO data_sensor 
                   (id_sensorbox, tinggi_air, suhu, kelembaban, curah_hujan)
                   VALUES (%s, %s, %s, %s, %s)""",
                (id_sensorbox, tinggi_air, suhu, kelembaban, curah_hujan)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    @staticmethod
    def get_all(id_sensorbox, page=1, per_page=10, bulan=None, tahun=None):
        conn = get_db_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Build WHERE clause
            where_clause = "WHERE ds.id_sensorbox = %s"
            params = [id_sensorbox]
            
            if bulan:
                where_clause += " AND MONTH(ds.waktu) = %s"
                params.append(int(bulan))
            if tahun:
                where_clause += " AND YEAR(ds.waktu) = %s"
                params.append(int(tahun))
            
            # Get total count
            count_sql = f"SELECT COUNT(*) as cnt FROM data_sensor ds {where_clause}"
            cursor.execute(count_sql, params)
            total = cursor.fetchone()['cnt']
            total_pages = (total + per_page - 1) // per_page
            
            # Get paginated data
            offset = (page - 1) * per_page
            data_sql = f"""
                SELECT * FROM data_sensor ds 
                {where_clause}
                ORDER BY ds.waktu DESC
                LIMIT %s OFFSET %s
            """
            params.extend([per_page, offset])
            cursor.execute(data_sql, params)
            data = cursor.fetchall()
            
            return {'data': data, 'total': total, 'total_pages': total_pages}
        finally:
            conn.close()

    @staticmethod
    def get_chart_data(id_sensorbox, bulan=None, tahun=None):
        """Get aggregated daily data for chart"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            
            where_clause = "WHERE ds.id_sensorbox = %s"
            params = [id_sensorbox]
            
            if bulan:
                where_clause += " AND MONTH(ds.waktu) = %s"
                params.append(int(bulan))
            if tahun:
                where_clause += " AND YEAR(ds.waktu) = %s"
                params.append(int(tahun))
            
            sql = f"""
                SELECT DATE(ds.waktu) as tanggal,
                       AVG(ds.tinggi_air) as tinggi_air,
                       AVG(ds.suhu) as suhu,
                       AVG(ds.kelembaban) as kelembaban,
                       AVG(ds.curah_hujan) as curah_hujan
                FROM data_sensor ds
                {where_clause}
                GROUP BY DATE(ds.waktu)
                ORDER BY tanggal ASC
            """
            cursor.execute(sql, params)
            return cursor.fetchall()
        finally:
            conn.close()


class HasilKlasifikasiModel:
    """Model untuk tabel hasil_klasifikasi joined with data_sensor"""

    @staticmethod
    def insert(id_data_sensor, status_air, probabilitas):
        """Insert hasil klasifikasi baru dan return id_hasil_klasifikasi"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO hasil_klasifikasi 
                   (id_data_sensor, status_air, probabilitas)
                   VALUES (%s, %s, %s)""",
                (id_data_sensor, status_air, probabilitas)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    @staticmethod
    def get_all(id_sensorbox, page=1, per_page=10, bulan=None, tahun=None):
        conn = get_db_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            
            where_clause = "WHERE ds.id_sensorbox = %s"
            params = [id_sensorbox]
            
            if bulan:
                where_clause += " AND MONTH(ds.waktu) = %s"
                params.append(int(bulan))
            if tahun:
                where_clause += " AND YEAR(ds.waktu) = %s"
                params.append(int(tahun))
            
            # Get total count
            count_sql = f"""
                SELECT COUNT(*) as cnt 
                FROM hasil_klasifikasi hk
                JOIN data_sensor ds ON hk.id_data_sensor = ds.id_data_sensor
                {where_clause}
            """
            cursor.execute(count_sql, params)
            total = cursor.fetchone()['cnt']
            total_pages = (total + per_page - 1) // per_page
            
            # Get paginated data
            offset = (page - 1) * per_page
            data_sql = f"""
                SELECT hk.*, ds.tinggi_air, ds.suhu, ds.kelembaban, ds.curah_hujan, ds.waktu
                FROM hasil_klasifikasi hk
                JOIN data_sensor ds ON hk.id_data_sensor = ds.id_data_sensor
                {where_clause}
                ORDER BY ds.waktu DESC, hk.id_hasil_klasifikasi DESC
                LIMIT %s OFFSET %s
            """
            params.extend([per_page, offset])
            cursor.execute(data_sql, params)
            data = cursor.fetchall()
            
            return {'data': data, 'total': total, 'total_pages': total_pages}
        finally:
            conn.close()

    @staticmethod
    def get_chart_data(id_sensorbox, bulan=None, tahun=None):
        """Get status distribution for donut chart"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            
            where_clause = "WHERE ds.id_sensorbox = %s"
            params = [id_sensorbox]
            
            if bulan:
                where_clause += " AND MONTH(ds.waktu) = %s"
                params.append(int(bulan))
            if tahun:
                where_clause += " AND YEAR(ds.waktu) = %s"
                params.append(int(tahun))
            
            sql = f"""
                SELECT hk.status_air, COUNT(*) as cnt
                FROM hasil_klasifikasi hk
                JOIN data_sensor ds ON hk.id_data_sensor = ds.id_data_sensor
                {where_clause}
                GROUP BY hk.status_air
                ORDER BY cnt DESC
            """
            cursor.execute(sql, params)
            return cursor.fetchall()
        finally:
            conn.close()


class NotifikasiModel:
    """Model untuk tabel notifikasi joined with hasil_klasifikasi and data_sensor"""

    @staticmethod
    def insert(id_hasil_klasifikasi, pesan):
        """Insert notifikasi baru"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO notifikasi 
                   (id_hasil_klasifikasi, pesan)
                   VALUES (%s, %s)""",
                (id_hasil_klasifikasi, pesan)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    @staticmethod
    def get_all(id_sensorbox, page=1, per_page=10, bulan=None, tahun=None):
        conn = get_db_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            
            where_clause = "WHERE ds.id_sensorbox = %s"
            params = [id_sensorbox]
            
            if bulan:
                where_clause += " AND MONTH(n.waktu_kirim) = %s"
                params.append(int(bulan))
            if tahun:
                where_clause += " AND YEAR(n.waktu_kirim) = %s"
                params.append(int(tahun))
            
            # Get total count
            count_sql = f"""
                SELECT COUNT(*) as cnt 
                FROM notifikasi n
                JOIN hasil_klasifikasi hk ON n.id_hasil_klasifikasi = hk.id_hasil_klasifikasi
                JOIN data_sensor ds ON hk.id_data_sensor = ds.id_data_sensor
                {where_clause}
            """
            cursor.execute(count_sql, params)
            total = cursor.fetchone()['cnt']
            total_pages = (total + per_page - 1) // per_page
            
            # Get paginated data
            offset = (page - 1) * per_page
            data_sql = f"""
                SELECT n.*, hk.status_air
                FROM notifikasi n
                JOIN hasil_klasifikasi hk ON n.id_hasil_klasifikasi = hk.id_hasil_klasifikasi
                JOIN data_sensor ds ON hk.id_data_sensor = ds.id_data_sensor
                {where_clause}
                ORDER BY n.waktu_kirim DESC
                LIMIT %s OFFSET %s
            """
            params.extend([per_page, offset])
            cursor.execute(data_sql, params)
            data = cursor.fetchall()
            
            return {'data': data, 'total': total, 'total_pages': total_pages}
        finally:
            conn.close()
