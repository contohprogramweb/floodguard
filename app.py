from flask import Flask, redirect, url_for, session, flash, request, render_template, jsonify
import config
from utils import hash_password, verify_password
from models import SensorBoxModel, DataSensorModel, HasilKlasifikasiModel, NotifikasiModel
from functools import wraps  # tambahkan ini
from database import init_connection_pool
import numpy as np
import joblib
import requests as http_requests
import os
from typing import Optional, Tuple

# Load model klasifikasi
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'flood_model.pkl')

try:
    flood_model = joblib.load(MODEL_PATH)
    print(f"[API] flood_model.pkl berhasil dimuat dari {MODEL_PATH}")
except Exception as e:
    print(f"[API] Gagal memuat flood_model.pkl: {e}")
    flood_model = None

FONNTE_TOKEN = os.environ.get('FONNTE_TOKEN', 'zA76a357fxvFxAzbg9yY')


def get_last_status(id_sensorbox: int) -> Optional[str]:
    """Mengambil status terakhir dari sensor box tertentu"""
    from database import get_db_connection
    conn = get_db_connection()
    if conn is None:
        return None
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT hk.status_air
            FROM hasil_klasifikasi hk
            JOIN data_sensor ds ON hk.id_data_sensor = ds.id_data_sensor
            WHERE ds.id_sensorbox = %s
            ORDER BY ds.waktu DESC, hk.id_hasil_klasifikasi DESC
            LIMIT 1
        """, (id_sensorbox,))
        result = cursor.fetchone()
        return result['status_air'] if result else None
    finally:
        conn.close()


def should_send_notification(current_status: str, last_status: Optional[str]) -> Tuple[bool, str]:
    """
    Menentukan apakah notifikasi harus dikirim berdasarkan aturan bisnis:
    - Bahaya: selalu dikirim setiap kali terdeteksi
    - Waspada: dikirim hanya saat perubahan status ke Waspada (dari status lain)
    - Normal: dikirim hanya saat perubahan dari Waspada atau Bahaya ke Normal
    
    Returns: (should_send, reason)
    """
    current_lower = current_status.lower()
    last_lower = last_status.lower() if last_status else None
    
    # Aturan 1: Notifikasi Bahaya wajib dikirim setiap kali terdeteksi
    if current_lower in ['bahaya', 'tinggi']:
        return True, "Status Bahaya terdeteksi"
    
    # Aturan 2: Notifikasi Waspada dikirim sekali saat perubahan ke Waspada
    if current_lower in ['waspada', 'siaga', 'sedang']:
        if last_lower is None or last_lower not in ['waspada', 'siaga', 'sedang']:
            return True, "Perubahan status ke Waspada"
        return False, "Status masih Waspada (tidak perlu notif ulang)"
    
    # Aturan 3: Notifikasi Normal dikirim hanya saat perubahan dari Waspada/Bahaya ke Normal
    if current_lower in ['normal', 'aman']:
        if last_lower in ['waspada', 'siaga', 'sedang', 'bahaya', 'tinggi']:
            return True, f"Perubahan status dari {last_status} ke Normal"
        return False, "Status masih Normal (tidak perlu notif)"
    
    # Default: kirim untuk status yang tidak dikenali
    return True, "Status tidak dikenali"


def kirim_whatsapp(nomor, pesan):
    """Mengirim pesan WhatsApp melalui Fonnte API ke satu atau lebih nomor (dipisahkan koma)"""
    try:
        # Jika nomor adalah string dengan beberapa nomor terpisah koma, biarkan seperti itu
        # Fonnte API mendukung multiple targets dengan format: "6281234567890,6289876543210"
        response = http_requests.post(
            'https://api.fonnte.com/send',
            headers={'Authorization': 'zA76a357fxvFxAzbg9yY'},
            data={
                'target': nomor,
                'message': pesan,
                'countryCode': '62'
            },
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        print(f"[WhatsApp] Gagal kirim pesan: {e}")
        return False


def klasifikasi_status(tinggi_air, suhu, kelembaban, curah_hujan):
    """Melakukan klasifikasi status banjir menggunakan model ML"""
    if flood_model is None:
        return "Tidak Diketahui", 0
    try:
        fitur = np.array([[
            float(tinggi_air),
            float(suhu),
            float(kelembaban),
            float(curah_hujan)
        ]])
        prediksi = flood_model.predict(fitur)[0]
        probabilitas_arr = flood_model.predict_proba(fitur)[0]
        probabilitas = int(max(probabilitas_arr) * 100)
        return str(prediksi), probabilitas
    except Exception as e:
        print(f"[Klasifikasi] Error: {e}")
        return "Error", 0

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
        from datetime import datetime
        
        id_sb = session['sensorbox_id']
        page = request.args.get('page', 1, type=int)
        
        # Set default values to current month and year
        now = datetime.now()
        bulan = request.args.get('bulan', str(now.month), type=str)
        tahun = request.args.get('tahun', str(now.year), type=str)

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
            per_page = 20
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
            
            # Get chart data - individual sensor readings (not daily averages)
            chart_sql = f"""
                SELECT ds.waktu,
                       ds.tinggi_air,
                       ds.suhu,
                       ds.kelembaban,
                       ds.curah_hujan
                FROM data_sensor ds
                {where_clause}
                ORDER BY ds.waktu ASC
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
            chart_labels = [row['waktu'].strftime('%d/%m %H:%M') if row['waktu'] else '' for row in chart_data]
            chart_tinggi = [round(float(row['tinggi_air']), 2) if row['tinggi_air'] is not None else 0 for row in chart_data]
            chart_suhu = [round(float(row['suhu']), 2) if row['suhu'] is not None else 0 for row in chart_data]
            chart_kelembaban = [round(float(row['kelembaban']), 2) if row['kelembaban'] is not None else 0 for row in chart_data]
            chart_hujan = [round(float(row['curah_hujan']), 2) if row['curah_hujan'] is not None else 0 for row in chart_data]

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
        from datetime import datetime
        id_sb = session['sensorbox_id']
        page = request.args.get('page', 1, type=int)
        
        # Set default values to current month and year
        now = datetime.now()
        bulan = request.args.get('bulan', str(now.month), type=str)
        tahun = request.args.get('tahun', str(now.year), type=str)

        # Buka koneksi database secara eksplisit di route
        conn = get_db_connection()
        if conn is None:
            flash('Gagal terhubung ke database.', 'danger')
            return render_template('klasifikasi/index.html', data=[], total=0, total_pages=0, page=page, bulan=bulan, tahun=tahun, chart_labels=[], chart_normal=[], chart_waspada=[], chart_bahaya=[])

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
            per_page = 20
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
            
            # Get chart data - Individual classification data (not daily averages)
            # Data follows what's displayed in the table (filtered by month/year)
            chart_sql = f"""
                SELECT ds.waktu,
                       hk.status_air,
                       hk.probabilitas
                FROM hasil_klasifikasi hk
                JOIN data_sensor ds ON hk.id_data_sensor = ds.id_data_sensor
                {where_clause}
                ORDER BY ds.waktu ASC, hk.id_hasil_klasifikasi ASC
            """
            # Reset params for chart query (hanya id_sb, bulan, tahun)
            chart_params = [id_sb]
            if bulan:
                chart_params.append(int(bulan))
            if tahun:
                chart_params.append(int(tahun))
            cursor.execute(chart_sql, chart_params)
            chart_data = cursor.fetchall()
            
            # Prepare chart labels and data - individual classification items
            chart_labels = [row['waktu'].strftime('%d/%m %H:%M') if row['waktu'] else '' for row in chart_data]
            
            # Count status per data point for the chart
            chart_normal = []
            chart_waspada = []
            chart_bahaya = []
            
            for row in chart_data:
                status = row['status_air'].lower() if row['status_air'] else ''
                normal_count = 0
                waspada_count = 0
                bahaya_count = 0
                
                if 'normal' in status or 'aman' in status:
                    normal_count = 1
                elif 'waspada' in status or 'siaga' in status or 'sedang' in status:
                    waspada_count = 1 
                elif 'bahaya' in status or 'tinggi' in status:
                    bahaya_count = 1
                
                chart_normal.append(normal_count)
                chart_waspada.append(waspada_count)
                chart_bahaya.append(bahaya_count)

            return render_template('klasifikasi/index.html',
                                   data=data,
                                   total=total,
                                   total_pages=total_pages,
                                   page=page,
                                   bulan=bulan,
                                   tahun=tahun,
                                   chart_labels=chart_labels,
                                   chart_normal=chart_normal,
                                   chart_waspada=chart_waspada,
                                   chart_bahaya=chart_bahaya)
        except Exception as e:
            flash(f'Gagal mengambil data klasifikasi: {str(e)}', 'danger')
            return render_template('klasifikasi/index.html', data=[], total=0, total_pages=0, page=page, bulan=bulan, tahun=tahun, chart_labels=[], chart_normal=[], chart_waspada=[], chart_bahaya=[])
        finally:
            if conn:
                conn.close()

    # ==================== ROUTE NOTIFIKASI ====================
    @app.route('/notifikasi')
    @login_required
    def notifikasi():
        from database import get_db_connection
        from datetime import datetime
        id_sb = session['sensorbox_id']
        page = request.args.get('page', 1, type=int)
        
        # Set default values to current month and year
        now = datetime.now()
        bulan = request.args.get('bulan', str(now.month), type=str)
        tahun = request.args.get('tahun', str(now.year), type=str)

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
            per_page = 20
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

    # ==================== ROUTE API SENSOR ====================
    @app.route('/api/sensor-data', methods=['POST'])
    def receive_sensor_data():
        """API endpoint untuk menerima data sensor dari IoT device"""
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form

        kode_sensorbox = data.get('kode_sensorbox')
        tinggi_air     = data.get('tinggi_air')
        suhu           = data.get('suhu')
        kelembaban     = data.get('kelembaban')
        curah_hujan    = data.get('curah_hujan')

        if not all([kode_sensorbox, tinggi_air, suhu, kelembaban, curah_hujan]):
            return jsonify({
                'status': 'error',
                'message': 'Field tidak lengkap.'
            }), 400

        sensor_box = SensorBoxModel.find_by_kode(kode_sensorbox)
        if not sensor_box:
            return jsonify({
                'status': 'ignored',
                'message': f'kode_sensorbox "{kode_sensorbox}" tidak ditemukan.'
            }), 200

        id_sensorbox   = sensor_box['id_sensorbox']
        nomor_whatsapp = sensor_box['nomor_whatsapp']
        nama_pemilik   = sensor_box['nama_pemilik']

        # Simpan data sensor
        id_data_sensor = DataSensorModel.insert(
            id_sensorbox, tinggi_air, suhu, kelembaban, curah_hujan
        )

        # Klasifikasi status banjir
        status_air, probabilitas = klasifikasi_status(tinggi_air, suhu, kelembaban, curah_hujan)

        # Simpan hasil klasifikasi
        id_hasil = HasilKlasifikasiModel.insert(id_data_sensor, status_air, probabilitas)

        # Ambil status terakhir dari sensor box ini untuk menentukan apakah notifikasi perlu dikirim
        last_status = get_last_status(id_sensorbox)

        # Tentukan apakah notifikasi harus dikirim berdasarkan aturan bisnis
        should_send, reason = should_send_notification(status_air, last_status)

        print(f"[Notifikasi] Status saat ini: {status_air}, Status terakhir: {last_status}, Kirim: {should_send}, Alasan: {reason}")

        # Buat pesan notifikasi berdasarkan status klasifikasi
        from datetime import datetime
        waktu_sekarang = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        status_lower = status_air.lower()
        
        if status_lower in ['waspada', 'siaga', 'sedang']:
            # Format pesan untuk status WASPADA
            pesan = (
                f"⚠️ *WASPADA BANJIR*\n\n"
                f"Tinggi Air: {tinggi_air} cm\n"
                f"Suhu: {suhu}°C | Kelembaban: {kelembaban}%\n"
                f"Curah Hujan: {curah_hujan}mm\n"
                f"Waktu: {waktu_sekarang}\n\n"
                f"Harap tingkatkan kewaspadaan!"
            )
        elif status_lower in ['bahaya', 'tinggi']:
            # Format pesan untuk status BAHAYA
            pesan = (
                f"🚨 *BAHAYA BANJIR*\n\n"
                f"Status: BAHAYA\n"
                f"Tinggi Air: {tinggi_air} cm\n"
                f"Suhu: {suhu}°C | Kelembaban: {kelembaban}%\n"
                f"Curah Hujan: {curah_hujan}mm\n"
                f"Waktu: {waktu_sekarang}\n\n"
                f"SEGERA LAKUKAN EVAKUASI!"
            )
        else:
            # Format pesan untuk status NORMAL
            pesan = (
                f"✅ *STATUS NORMAL*\n\n"
                f"Kondisi air telah kembali normal.\n"
                f"Tinggi Air: {tinggi_air} cm\n"
                f"Waktu: {waktu_sekarang}\n\n"
                f"Sistem terus memantau."
            )

        # Kirim WhatsApp hanya jika sesuai dengan aturan bisnis
        terkirim = False
        if should_send:
            terkirim = kirim_whatsapp(nomor_whatsapp, pesan)
            print(f"[WhatsApp] Notifikasi {'berhasil' if terkirim else 'gagal'} dikirim ke {nomor_whatsapp}")
        else:
            print(f"[WhatsApp] Notifikasi tidak dikirim: {reason}")

        # Simpan notifikasi ke database (tetap simpan untuk logging, terlepas dari apakah dikirim atau tidak)
        NotifikasiModel.insert(id_hasil, pesan)
        
        return jsonify({
            'status': 'success',
            'data': {
                'id_data_sensor': id_data_sensor,
                'id_hasil_klasifikasi': id_hasil,
                'status_air': status_air,
                'probabilitas': probabilitas,
                'notifikasi_terkirim': terkirim
            }
        }), 201

    return app




# Untuk WSGI (production)
application = create_app()

# Untuk development lokal
if __name__ == '__main__':
    application.run(debug=True, port=5050)   # gunakan application, bukan app