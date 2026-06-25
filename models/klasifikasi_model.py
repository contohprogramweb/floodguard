from database import get_db_connection

class KlasifikasiModel:
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
