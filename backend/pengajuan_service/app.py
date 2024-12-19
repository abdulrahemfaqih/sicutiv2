from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    redirect,
    url_for,
    send_from_directory,
)
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import redis
from rq import Queue
from models import (
    db,
    PengajuanCuti,
    UserRole,
    TahunAjaran,
    Semester,
    SemesterStatus,
    Prodi,
    User,
    DokumenPendukung,
)
import jwt
from functools import wraps
import os
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime


app = Flask(__name__)

# Konfigurasi database MySQL
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+mysqlconnector://root:password@db/sicuti"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "your_secret_key"
UPLOAD_FOLDER = "var/uploads"

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
bcrypt = Bcrypt(app)



# Inisialisasi database
db.init_app(app)

# Inisialisasi Redis dan Queue
redis_conn = redis.StrictRedis(
    host="redis", port=6379, db=0
)  # Koneksi ke Redis service yang ada di docker-compose
queue = Queue(connection=redis_conn)  # Membuat queue untuk menambahkan task ke Redis


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get("token")  # Ambil token dari cookie
        if not token:
            return redirect("http://localhost:5003/")
        try:
            decoded_token = jwt.decode(
                token, app.config["SECRET_KEY"], algorithms=["HS256"]
            )
            request.user_id = decoded_token["user_id"]
            request.role = decoded_token["role"]
        except jwt.ExpiredSignatureError:
            return redirect(
                "http://localhost:5003/"
            )  # Redirect ke login jika token kadaluarsa
        except jwt.InvalidTokenError:
            return redirect(
                "http://localhost:5003/"
            )  # Redirect ke login jika token tidak valid
        return f(*args, **kwargs)

    return decorated


@app.route("/logout", methods=["POST"])
@token_required
def logout():
    response = jsonify({"message": "Logged out successfully!"})
    response.delete_cookie("token")
    return response


with app.app_context():
    db.create_all()


def check_admin_service_status():
    status = redis_conn.get("admin_service_status")
    if status is None or status.decode() != "active":
        return False
    return True


@app.route("/", methods=["GET"])
@token_required
def welcome():
    return render_template("home.html")


@app.route("/apply", methods=["GET"])
@token_required
def apply_form():
    return render_template("apply_form.html")


TAHUN_AJARAN_ID = 1
SEMESTER_ID = 1


@app.route("/apply", methods=["POST"])
@token_required
def apply():
    try:
        if not check_admin_service_status():
            return (
                jsonify(
                    {
                        "message": "Service validasi sedang tidak tersedia. Silakan coba beberapa saat lagi."
                    }
                ),
                503,
            )

        alasan = request.form.get("alasan")
        user_id = request.user_id

        total_pengajuan = PengajuanCuti.query.filter_by(user_id=user_id).count()

        current_cuti = PengajuanCuti.query.filter_by(
            user_id=user_id,
            tahun_ajaran_id=TAHUN_AJARAN_ID,
            semester_id=SEMESTER_ID,
            status="Disetujui",  # Hanya pengajuan dengan status 'Disetujui'
        ).first()

        if total_pengajuan >= 2:
            return jsonify({"message": "Batas pengajuan cuti sudah tercapai."}), 403

        if current_cuti is not None:
            return (
                jsonify({"message": "Anda sudah mengajukan cuti pada semester ini."}),
                403,
            )

        # Simpan pengajuan cuti ke database
        pengajuan = PengajuanCuti(
            user_id=user_id,
            alasan=alasan,
            tahun_ajaran_id=TAHUN_AJARAN_ID,
            semester_id=SEMESTER_ID,
        )
        db.session.add(pengajuan)
        db.session.commit()

        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        # Proses upload file
        files = {
            "ktm": request.files.get("ktm"),
            "surat_pengajuan": request.files.get("surat_pengajuan"),
            "surat_bebas": request.files.get("surat_bebas"),
        }

        for doc_type, file in files.items():
            if file and allowed_file(file.filename):
                # Dapatkan ekstensi file asli
                original_extension = file.filename.rsplit(".", 1)[1].lower()

                # Buat nama file unik dengan UUID dan timestamp
                unique_filename = f"{doc_type}_{uuid.uuid4()}_{int(datetime.now().timestamp())}.{original_extension}"

                # Simpan file dengan nama unik
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
                file.save(filepath)

                # Simpan info dokumen ke database dengan nama asli dan nama unik
                dokumen = DokumenPendukung(
                    nama_file=file.filename,  # Simpan nama asli file
                    path=unique_filename,  # Simpan path dengan nama unik
                    pengajuan_id=pengajuan.id,
                )
                db.session.add(dokumen)

        db.session.commit()

        # Setelah pengajuan cuti berhasil, kirimkan task ke Redis untuk validasi
        # Misalnya task ini memanggil fungsi validasi yang ada di service admin
        job = queue.enqueue("validasi_service.process_validasi", pengajuan.id)

        return (
            jsonify(
                {"message": "Pengajuan berhasil dibuat dan dokumen berhasil diupload!"}
            ),
            201,
        )
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Terdapat Kesalahan"}), 500


@app.route("/status", methods=["GET"])
@token_required
def get_status():
    try:
        user_id = request.user_id
        pengajuan_cuti = PengajuanCuti.query.filter_by(user_id=user_id).all()

        data = [
            {
                "id": pengajuan.id,
                "alasan": pengajuan.alasan,
                "tahun_ajaran": pengajuan.tahun_ajaran.tahun,
                "semester": pengajuan.semester.semester.value,  # Asumsikan SemesterStatus adalah Enum
                "status": pengajuan.status,
            }
            for pengajuan in pengajuan_cuti
        ]

        return jsonify(data), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Gagal mengambil data status pengajuan."}), 500


@app.route("/check-cuti-status", methods=["GET"])
@token_required
def check_cuti_status():
    try:
        user_id = request.user_id
        current_year = TAHUN_AJARAN_ID
        current_semester = SEMESTER_ID

        # Hitung jumlah pengajuan cuti pengguna
        total_pengajuan = PengajuanCuti.query.filter_by(user_id=user_id).count()

        # Cek apakah sudah ada pengajuan di tahun dan semester yang sama
        current_cuti = PengajuanCuti.query.filter_by(
            user_id=user_id,
            tahun_ajaran_id=TAHUN_AJARAN_ID,
            semester_id=SEMESTER_ID,
            status="Disetujui",  # Hanya pengajuan dengan status 'Disetujui'
        ).first()

        # Atur kondisi untuk tidak bisa mengajukan
        cannot_apply = total_pengajuan >= 2 or current_cuti is not None

        return jsonify({"cannotApply": cannot_apply}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Gagal memeriksa status cuti."}), 500


# Route untuk mengakses file
@app.route("/uploads/<path:filename>")
@token_required
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# bautian root untuk rollback database
@app.route("/rollback", methods=["GET"])
def rollback_data():
    db.drop_all()
    return jsonify({"message": "Database rollback successfully!"})


@app.route("/create_db", methods=["GET"])
def create_db():
    db.create_all()
    return jsonify({"message": "Database created successfully!"})


@app.route("/seeder", methods=["GET"])
def seed_data():
    with app.app_context():
        # Seed Tahun Ajaran
        if not TahunAjaran.query.first():
            tahun_ajaran1 = TahunAjaran(tahun="2023/2024", status=True)
            tahun_ajaran2 = TahunAjaran(tahun="2022/2023", status=False)
            db.session.add_all([tahun_ajaran1, tahun_ajaran2])
            db.session.commit()
            print("Seeded Tahun Ajaran!")

        # Seed Prodi
        if not Prodi.query.first():
            prodi1 = Prodi(nama="Teknik Informatika")
            prodi2 = Prodi(nama="Sistem Informasi")
            prodi3 = Prodi(nama="Teknik Elektro")
            prodi4 = Prodi(nama="Teknik Mesin")
            db.session.add_all([prodi1, prodi2, prodi3, prodi4])
            db.session.commit()
            print("Seeded Prodi!")

        # Seed Semester
        if not Semester.query.first():
            # Semester untuk tahun ajaran 2023/2024
            semester1 = Semester(
                semester=SemesterStatus.ganjil,
                tahun_ajaran_id=1,  # Referensi ke tahun ajaran 2023/2024
                status=True,
            )
            semester2 = Semester(
                semester=SemesterStatus.genap,
                tahun_ajaran_id=1,  # Referensi ke tahun ajaran 2023/2024
                status=False,
            )

            # Semester untuk tahun ajaran 2022/2023
            semester3 = Semester(
                semester=SemesterStatus.ganjil,
                tahun_ajaran_id=2,  # Referensi ke tahun ajaran 2022/2023
                status=False,
            )
            semester4 = Semester(
                semester=SemesterStatus.genap,
                tahun_ajaran_id=2,  # Referensi ke tahun ajaran 2022/2023
                status=False,
            )

            db.session.add_all([semester1, semester2, semester3, semester4])
            db.session.commit()
            print("Seeded Semester!")

        # Seed Users
        if not User.query.first():
            mahasiswa1 = User(
                nama="Ahmad Mahasiswa",
                username="mahasiswa1",
                email="220411100029@student.trunojoyo.ac.id",
                password=bcrypt.generate_password_hash("mahasiswa123"),
                role=UserRole.mahasiswa,
                nim="123456789",
                prodi_id=1,  # Teknik Informatika
            )
            mahasiswa2 = User(
                nama="Budi Mahasiswa",
                username="mahasiswa2",
                email="ilhamzakaria3024@gmail.com",
                password=bcrypt.generate_password_hash("mahasiswa123"),
                role=UserRole.mahasiswa,
                nim="987654321",
                prodi_id=2,  # Sistem Informasi
            )
            admin = User(
                nama="Admin BAK",
                username="admin",
                email="admin@gmail.com",
                password=bcrypt.generate_password_hash("admin123"),
                role=UserRole.admin,
            )
            db.session.add_all([mahasiswa1, mahasiswa2, admin])
            db.session.commit()
            return jsonify({"message": "Seeded Users!"})


# Jalankan Aplikasi
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
