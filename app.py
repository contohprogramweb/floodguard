from flask import Flask, redirect, url_for, session, flash, request, render_template
import config
from utils import hash_password, verify_password
from models import SensorBoxModel
from functools import wraps  # tambahkan ini

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

    return app

# Untuk WSGI (production)
application = create_app()

# Untuk development lokal
if __name__ == '__main__':
    application.run(debug=True, port=5050)   # gunakan application, bukan app