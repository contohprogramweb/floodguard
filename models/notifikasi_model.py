from database import get_db_connection

class NotifikasiModel:
    """Model untuk tabel notifikasi joined with hasil_klasifikasi and data_sensor"""

    @staticmethod
    def insert(id_hasil_klasifikasi, pesan):
        """Insert notifikasi baru dengan waktu_kirim otomatis"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO notifikasi 
                   (id_hasil_klasifikasi, pesan, waktu_kirim)
                   VALUES (%s, %s, NOW())""",
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
