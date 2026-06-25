from database import get_db_connection

class SensorModel:
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
