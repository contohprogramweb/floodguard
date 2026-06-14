from flask import request, jsonify
import numpy as np
import joblib
import requests as http_requests
import os

from models import SensorBoxModel, DataSensorModel, HasilKlasifikasiModel, NotifikasiModel

# Gunakan path absolut agar tidak bergantung pada working directory server
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_PATH = os.path.join(BASE_DIR, 'flood_model.pkl')

try:
    model = joblib.load(MODEL_PATH)
    print(f"[API] flood_model.pkl berhasil dimuat dari {MODEL_PATH}")
except Exception as e:
    print(f"[API] Gagal memuat flood_model.pkl: {e}")
    model = None

FONNTE_TOKEN = os.environ.get('FONNTE_TOKEN', 'ISI_TOKEN_FONNTE_ANDA')


def kirim_whatsapp(nomor, pesan):
    try:
        response = http_requests.post(
            'https://api.fonnte.com/send',
            headers={'Authorization': FONNTE_TOKEN},
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
    if model is None:
        return "Tidak Diketahui", 0
    try:
        fitur = np.array([[
            float(tinggi_air),
            float(suhu),
            float(kelembaban),
            float(curah_hujan)
        ]])
        prediksi = model.predict(fitur)[0]
        probabilitas_arr = model.predict_proba(fitur)[0]
        probabilitas = int(max(probabilitas_arr) * 100)
        return str(prediksi), probabilitas
    except Exception as e:
        print(f"[Klasifikasi] Error: {e}")
        return "Error", 0


def receive_sensor_data():
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

    id_data_sensor = DataSensorModel.insert(
        id_sensorbox, tinggi_air, suhu, kelembaban, curah_hujan
    )

    status_air, probabilitas = klasifikasi_status(tinggi_air, suhu, kelembaban, curah_hujan)
    id_hasil = HasilKlasifikasiModel.insert(id_data_sensor, status_air, probabilitas)

    pesan = (
        f"🌊 *NOTIFIKASI BANJIR*\n"
        f"Halo {nama_pemilik},\n"
        f"Status: *{status_air}* ({probabilitas}%)\n"
        f"Tinggi Air : {tinggi_air} cm\n"
        f"Suhu       : {suhu} °C\n"
        f"Kelembaban : {kelembaban} %\n"
        f"Curah Hujan: {curah_hujan} mm\n"
        f"Harap waspada dan pantau kondisi sekitar."
    )

    terkirim = False
    if status_air.lower() not in ['normal', 'aman']:
        terkirim = kirim_whatsapp(nomor_whatsapp, pesan)

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
