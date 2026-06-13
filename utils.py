import hashlib

def hash_password(password):
    """Hash password menggunakan SHA-1 (sama seperti schema.sql)"""
    return hashlib.sha1(password.encode('utf-8')).hexdigest()

def verify_password(password, hashed):
    """Verifikasi password terhadap hash"""
    return hash_password(password) == hashed
