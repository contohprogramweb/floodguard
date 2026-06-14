from flask import Flask, redirect, url_for, session, flash, request, render_template
import config
from utils import hash_password, verify_password
from models import SensorBoxModel, DataSensorModel, HasilKlasifikasiModel, NotifikasiModel
from functools import wraps  # tambahkan ini
from database import init_connection_pool

def login_required(f):
    @wraps(f)                 # gunakan wraps agar nama fungsi tetap
    def decorated(*args, **kwargs):
        if 'sensorbox_id' not in session:
            flash('Silakan login terlebih dahulu.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def create_app():
    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY
    app.debug = False          # ganti True jika ingin melihat error detail (development)
    
    # Inisialisasi connection pool saat aplikasi start
    with app.app_context():
        init_connection_pool(pool_size=5, pool_name="iot_pool")

    @app.route('/')
    @login_required
    def dashboard():
        from database import get_db_connection
        id_sb = session['sensorbox_id']

        conn = get_db_connection()
        if conn is None:
            flash('Gagal terhubung ke database.', 'danger')
            return redirect(url_for('login'))

        try:
            cursor = conn.cursor(dictionary=True)

            # Ambil info sensor box
            cursor.execute("SELECT * FROM sensor_box WHERE id_sensorbox = %s", (id_sb,))
            sensor_box = cursor.fetchone()

            # Jika tidak ditemukan (mungkin dihapus), paksa logout
            if sensor_box is None:
                session.clear()
                flash('Akun tidak ditemukan.', 'danger')
                return redirect(url_for('login'))

            # Total data sensor
            cursor.execute("SELECT COUNT(*) as cnt FROM data_sensor WHERE id_sensorbox = %s", (id_sb,))
            total_sensor = cursor.fetchone()['cnt']

            # Total klasifikasi
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM hasil_klasifikasi hk
                JOIN data_sensor ds ON hk.id_data_sensor = ds.id_data_sensor
                WHERE ds.id_sensorbox = %s
            """, (id_sb,))
            total_klasifikasi = cursor.fetchone()['cnt']

            # Total notifikasi
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM notifikasi n
                JOIN hasil_klasifikasi hk ON n.id_hasil_klasifikasi = hk.id_hasil_klasifikasi
                JOIN data_sensor ds ON hk.id_data_sensor = ds.id_data_sensor
                WHERE ds.id_sensorbox = %s
            """, (id_sb,))
            total_notifikasi = cursor.fetchone()['cnt']

            # Status terbaru
            cursor.execute("""
                SELECT hk.status_air, hk.probabilitas
                FROM hasil_klasifikasi hk
                JOIN data_sensor ds ON hk.id_data_sensor = ds.id_data_sensor
                WHERE ds.id_sensorbox = %s
                ORDER BY ds.waktu DESC, hk.id_hasil_klasifikasi DESC
                LIMIT 1
            """, (id_sb,))
            latest_status = cursor.fetchone()

            return render_template('dashboard/index.html',
                                   sensor_box=sensor_box,
                                   total_sensor=total_sensor,
                                   total_klasifikasi=total_klasifikasi,
                                   total_notifikasi=total_notifikasi,
                                   latest_status=latest_status)
        except Exception as e:
            # Tampilkan error untuk debugging (hapus di production)
            return f"Dashboard error: {e}", 500
        finally:
            if conn:
                conn.close()

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if 'sensorbox_id' in session:
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            kode_sensorbox = request.form.get('kode_sensorbox', '').strip().upper()
            password = request.form.get('password', '')

            sensor_box = SensorBoxModel.find_by_kode(kode_sensorbox)
            if sensor_box and verify_password(password, sensor_box['password']):
                session['sensorbox_id'] = sensor_box['id_sensorbox']
                session['kode_sensorbox'] = sensor_box['kode_sensorbox']
                session['nama_pemilik'] = sensor_box['nama_pemilik']
                flash('Login berhasil!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Kode sensor box atau password salah.', 'danger')

        return render_template('auth/login.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            kode_sensorbox = request.form.get('kode_sensorbox', '').strip().upper()
            nama_pemilik = request.form.get('nama_pemilik', '').strip()
            alamat_pemilik = request.form.get('alamat_pemilik', '').strip()
            nomor_whatsapp = request.form.get('nomor_whatsapp', '').strip()
            password = request.form.get('password', '')
            confirm_pass = request.form.get('confirm_password', '')

            if not all([kode_sensorbox, nama_pemilik, alamat_pemilik, nomor_whatsapp, password]):
                flash('Semua field wajib diisi.', 'danger')
                return render_template('auth/register.html')

            if not kode_sensorbox.isalnum() or len(kode_sensorbox) > 5:
                flash('Kode sensor box harus berupa huruf/angka, maksimal 5 karakter.', 'danger')
                return render_template('auth/register.html')

            if SensorBoxModel.kode_exists(kode_sensorbox):
                flash(f'Kode sensor box "{kode_sensorbox}" sudah digunakan.', 'danger')
                return render_template('auth/register.html')

            if password != confirm_pass:
                flash('Password dan konfirmasi tidak sama.', 'danger')
                return render_template('auth/register.html')

            hashed = hash_password(password)
            SensorBoxModel.create(kode_sensorbox, nama_pemilik, alamat_pemilik,
                                  nomor_whatsapp, hashed)

            flash(f'Registrasi berhasil! Gunakan kode "{kode_sensorbox}" untuk login.', 'success')
            return redirect(url_for('login'))

        return render_template('auth/register.html')

    @app.route('/logout')
    def logout():
        session.clear()
        flash('Anda telah logout.', 'info')
        return redirect(url_for('login'))

    @app.route('/dashboard/edit', methods=['GET', 'POST'])
    @login_required
    def edit_sensorbox():
        id_sb = session['sensorbox_id']
        sensor_box = SensorBoxModel.find_by_id(id_sb)

        if sensor_box is None:
            session.clear()
            flash('Akun tidak ditemukan.', 'danger')
            return redirect(url_for('login'))

        if request.method == 'POST':
            nama_pemilik = request.form.get('nama_pemilik', '').strip()
            alamat_pemilik = request.form.get('alamat_pemilik', '').strip()
            nomor_whatsapp = request.form.get('nomor_whatsapp', '').strip()
            new_password = request.form.get('new_password', '')
            confirm_pass = request.form.get('confirm_password', '')

            if not all([nama_pemilik, alamat_pemilik, nomor_whatsapp]):
                flash('Field nama, alamat, dan nomor WhatsApp wajib diisi.', 'danger')
                return render_template('dashboard/edit.html', sensor_box=sensor_box)

            SensorBoxModel.update(id_sb, nama_pemilik, alamat_pemilik, nomor_whatsapp)
            session['nama_pemilik'] = nama_pemilik

            if new_password:
                if new_password != confirm_pass:
                    flash('Password baru dan konfirmasi tidak cocok.', 'danger')
                    return render_template('dashboard/edit.html', sensor_box=sensor_box)
                hashed = hash_password(new_password)
                SensorBoxModel.update_password(id_sb, hashed)

            flash('Data berhasil diperbarui.', 'success')
            return redirect(url_for('dashboard'))

        return render_template('dashboard/edit.html', sensor_box=sensor_box)

    # ==================== ROUTE SENSOR ====================
    @app.route('/sensor')
    @login_required
    def sensor():
        from database import get_db_connection
        id_sb = session['sensorbox_id']
        page = request.args.get('page', 1, type=int)
        bulan = request.args.get('bulan', '', type=str)
        tahun = request.args.get('tahun', '', type=str)

        # Buka koneksi database secara eksplisit di route
        conn = get_db_connection()
        if conn is None:
            flash('Gagal terhubung ke database.', 'danger')
            return render_template('sensor/index.html', data=[], total=0, total_pages=0, page=page, bulan=bulan, tahun=tahun, chart_labels=[], chart_tinggi=[], chart_suhu=[], chart_kelembaban=[], chart_hujan=[])

        try:
            # Gunakan koneksi yang sudah dibuka untuk mengambil data
            cursor = conn.cursor(dictionary=True)
            
            # Build WHERE clause
            where_clause = "WHERE ds.id_sensorbox = %s"
            params = [id_sb]
            
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
            per_page = 10
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
            
            # Get chart data
            chart_sql = f"""
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
            # Reset params for chart query (hanya id_sb, bulan, tahun)
            chart_params = [id_sb]
            if bulan:
                chart_params.append(int(bulan))
            if tahun:
                chart_params.append(int(tahun))
            cursor.execute(chart_sql, chart_params)
            chart_data = cursor.fetchall()
            
            # Prepare chart labels and data
            chart_labels = [row['tanggal'].strftime('%d/%m') if row['tanggal'] else '' for row in chart_data]
            chart_tinggi = [round(row['tinggi_air'], 2) if row['tinggi_air'] else 0 for row in chart_data]
            chart_suhu = [round(row['suhu'], 2) if row['suhu'] else 0 for row in chart_data]
            chart_kelembaban = [round(row['kelembaban'], 2) if row['kelembaban'] else 0 for row in chart_data]
            chart_hujan = [round(row['curah_hujan'], 2) if row['curah_hujan'] else 0 for row in chart_data]

            return render_template('sensor/index.html',
                                   data=data,
                                   total=total,
                                   total_pages=total_pages,
                                   page=page,
                                   bulan=bulan,
                                   tahun=tahun,
                                   chart_labels=chart_labels,
                                   chart_tinggi=chart_tinggi,
                                   chart_suhu=chart_suhu,
                                   chart_kelembaban=chart_kelembaban,
                                   chart_hujan=chart_hujan)
        except Exception as e:
            flash(f'Gagal mengambil data sensor: {str(e)}', 'danger')
            return render_template('sensor/index.html', data=[], total=0, total_pages=0, page=page, bulan=bulan, tahun=tahun, chart_labels=[], chart_tinggi=[], chart_suhu=[], chart_kelembaban=[], chart_hujan=[])
        finally:
            if conn:
                conn.close()

    # ==================== ROUTE KLASIFIKASI ====================
    @app.route('/klasifikasi')
    @login_required
    def klasifikasi():
        from database import get_db_connection
        id_sb = session['sensorbox_id']
        page = request.args.get('page', 1, type=int)
        bulan = request.args.get('bulan', '', type=str)
        tahun = request.args.get('tahun', '', type=str)

        # Buka koneksi database secara eksplisit di route
        conn = get_db_connection()
        if conn is None:
            flash('Gagal terhubung ke database.', 'danger')
            return render_template('klasifikasi/index.html', data=[], total=0, total_pages=0, page=page, bulan=bulan, tahun=tahun, chart_labels=[], chart_values=[])

        try:
            cursor = conn.cursor(dictionary=True)
            
            # Build WHERE clause
            where_clause = "WHERE ds.id_sensorbox = %s"
            params = [id_sb]
            
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
            per_page = 10
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
            
            # Get chart data - Timeseries per bulan
            chart_sql = f"""
                SELECT DATE_FORMAT(ds.waktu, '%%Y-%%m') as periode, 
                       SUM(CASE WHEN LOWER(hk.status_air) LIKE '%%normal%%' OR LOWER(hk.status_air) LIKE '%%aman%%' THEN 1 ELSE 0 END) as normal,
                       SUM(CASE WHEN LOWER(hk.status_air) LIKE '%%siaga%%' OR LOWER(hk.status_air) LIKE '%%waspada%%' OR LOWER(hk.status_air) LIKE '%%sedang%%' THEN 1 ELSE 0 END) as siaga,
                       SUM(CASE WHEN LOWER(hk.status_air) LIKE '%%bahaya%%' OR LOWER(hk.status_air) LIKE '%%tinggi%%' THEN 1 ELSE 0 END) as bahaya
                FROM hasil_klasifikasi hk
                JOIN data_sensor ds ON hk.id_data_sensor = ds.id_data_sensor
                {where_clause}
                GROUP BY DATE_FORMAT(ds.waktu, '%%Y-%%m')
                ORDER BY periode ASC
            """
            # Reset params for chart query (hanya id_sb, bulan, tahun)
            chart_params = [id_sb]
            if bulan:
                chart_params.append(int(bulan))
            if tahun:
                chart_params.append(int(tahun))
            cursor.execute(chart_sql, chart_params)
            chart_data = cursor.fetchall()
            
            # Prepare chart labels and values for timeseries
            chart_labels = [row['periode'] for row in chart_data]
            chart_normal = [row['normal'] or 0 for row in chart_data]
            chart_siaga = [row['siaga'] or 0 for row in chart_data]
            chart_bahaya = [row['bahaya'] or 0 for row in chart_data]

            return render_template('klasifikasi/index.html',
                                   data=data,
                                   total=total,
                                   total_pages=total_pages,
                                   page=page,
                                   bulan=bulan,
                                   tahun=tahun,
                                   chart_labels=chart_labels,
                                   chart_normal=chart_normal,
                                   chart_siaga=chart_siaga,
                                   chart_bahaya=chart_bahaya)
        except Exception as e:
            flash(f'Gagal mengambil data klasifikasi: {str(e)}', 'danger')
            return render_template('klasifikasi/index.html', data=[], total=0, total_pages=0, page=page, bulan=bulan, tahun=tahun, chart_labels=[], chart_normal=[], chart_siaga=[], chart_bahaya=[])
        finally:
            if conn:
                conn.close()

    # ==================== ROUTE NOTIFIKASI ====================
    @app.route('/notifikasi')
    @login_required
    def notifikasi():
        from database import get_db_connection
        id_sb = session['sensorbox_id']
        page = request.args.get('page', 1, type=int)
        bulan = request.args.get('bulan', '', type=str)
        tahun = request.args.get('tahun', '', type=str)

        # Buka koneksi database secara eksplisit di route
        conn = get_db_connection()
        if conn is None:
            flash('Gagal terhubung ke database.', 'danger')
            return render_template('notifikasi/index.html', data=[], total=0, total_pages=0, page=page, bulan=bulan, tahun=tahun)

        try:
            cursor = conn.cursor(dictionary=True)
            
            # Build WHERE clause
            where_clause = "WHERE ds.id_sensorbox = %s"
            params = [id_sb]
            
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
            per_page = 10
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

            return render_template('notifikasi/index.html',
                                   data=data,
                                   total=total,
                                   total_pages=total_pages,
                                   page=page,
                                   bulan=bulan,
                                   tahun=tahun)
        except Exception as e:
            flash(f'Gagal mengambil data notifikasi: {str(e)}', 'danger')
            return render_template('notifikasi/index.html', data=[], total=0, total_pages=0, page=page, bulan=bulan, tahun=tahun)
        finally:
            if conn:
                conn.close()

    return app

# Untuk WSGI (production)
application = create_app()

# Untuk development lokal
if __name__ == '__main__':
    application.run(debug=True, port=5050)   # gunakan application, bukan app
