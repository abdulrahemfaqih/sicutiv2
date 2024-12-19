from flask import (
    Flask,
    jsonify,
    request,
    render_template,
    redirect,
    current_app,
    send_from_directory,
)
from models import db, PengajuanCuti
import redis
from rq import Queue
from rq.job import Job
from flask_bcrypt import Bcrypt
import jwt
from functools import wraps
import os
from flask_mail import Mail, Message

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+mysqlconnector://root:password@db/sicuti"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "your_secret_key"


app.config["MAIL_SERVER"] = "smtp.gmail.com"  # Server SMTP Gmail
app.config["MAIL_PORT"] = 465  # Port untuk TLS
app.config["MAIL_USE_TLS"] = False # Menggunakan TLS
app.config['MAIL_USE_SSL'] = True
app.config["MAIL_USERNAME"] = "faqih3935@gmail.com"  # Alamat email pengirim
app.config["MAIL_PASSWORD"] = "qgwgwghmsmwaahtx"  # Password email pengirim
app.config["MAIL_DEFAULT_SENDER"] = "faqih3935@gmail.com"  # Email pengirim default


mail = Mail(app)


db.init_app(app)

redis_conn = redis.StrictRedis(host="redis", port=6379, db=0)
queue = Queue(connection=redis_conn)


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


@app.route("/toggle_system", methods=["POST"])
def toggle_system():
    data = request.get_json()
    action = data.get("action")

    if action == "open":
        redis_conn.set("admin_service_status", "active", ex=60)
        message = "Sistem pengajuan cuti dibuka!"
    elif action == "close":
        redis_conn.set("admin_service_status", "inactive", ex=60)
        message = "Sistem pengajuan cuti ditutup!"
    else:
        message = "Tindakan tidak valid"

    return jsonify({"message": message})


@app.route("/check_status", methods=["GET"])
def check_status():
    try:
        redis_conn.ping()
        admin_status = redis_conn.get("admin_service_status")

        if admin_status:
            redis_status = admin_status.decode("utf-8")
        else:
            redis_status = "inactive"

        return jsonify({"status": redis_status}), 200
    except redis.ConnectionError:
        return jsonify({"status": "inactive"}), 500


def send_approval_email(user_email, user_name, action):
    if action == "approve":
        subject = "Persetujuan Pengajuan Cuti Anda"
        body = f"Hello {user_name},\n\nPengajuan cuti Anda telah diterima dan disetujui. Terima kasih telah mengajukan cuti.\n\nSalam,\nSistem Pengajuan Cuti"
    elif action == "reject":
        subject = "Penolakan Pengajuan Cuti Anda"
        body = f"Hello {user_name},\n\nPengajuan cuti Anda telah ditolak. Silakan hubungi kami untuk informasi lebih lanjut.\n\nSalam,\nSistem Pengajuan Cuti"
    else:
        return  # Jika aksi tidak valid, jangan mengirim email

    # Membuat dan mengirimkan email
    msg = Message(subject=subject, recipients=[user_email], body=body)

    try:
        mail.send(msg)
        print(f"Email berhasil dikirim ke {user_email}")
    except Exception as e:
        print(f"Terjadi kesalahan saat mengirim email: {e}")


@app.route("/", methods=["GET", "POST"])
@token_required
def get_leave_requests():
    try:
        redis_conn.ping()
        redis_status = "active"  # Redis aktif
    except redis.ConnectionError:
        redis_status = "inactive"  # Redis tidak aktif

    if request.method == "POST":
        data = request.get_json()

        pengajuan_id = data.get("id")
        action = data.get("action")
        pengajuan = PengajuanCuti.query.get_or_404(pengajuan_id)
        user = pengajuan.user

        if action == "approve":
            pengajuan.status = "Disetujui"
            message = "Leave request approved!"
            send_approval_email(user.email, user.nama, "approve")
        elif action == "reject":
            pengajuan.status = "Ditolak"
            message = "Leave request rejected!"
            send_approval_email(user.email, user.nama, "reject")
        else:
            message = "Invalid action"

        db.session.commit()
        return jsonify({"message": message})

    data_cuti = PengajuanCuti.query.all()
    return render_template(
        "home.html",
        data=[
            {
                "id": cuti.id,
                "nama": (
                    cuti.user.nama if cuti.user else "Tidak Diketahui"
                ),  # Pastikan nama user diambil dari relasi
                "alasan": cuti.alasan,
                "status": cuti.status,
                "status": cuti.status,
                "tahun_ajaran": cuti.tahun_ajaran.tahun,
                "semester": cuti.semester.semester.value,
            }
            for cuti in data_cuti
        ],
        redis_status=redis_status,
    )


@app.route("/detail_pengajuan/<int:pengajuan_id>", methods=["GET"])
@token_required
def detail_pengajuan(pengajuan_id):
    try:
        pengajuan = PengajuanCuti.query.get_or_404(pengajuan_id)
        dokumen_pendukung = pengajuan.dokumen_pendukungs

        data = {
            "id": pengajuan.id,
            "nama": (
                pengajuan.user.nama if pengajuan.user else "Tidak Diketahui"
            ),  # Relasi ke tabel user
            "alasan": pengajuan.alasan,
            "status": pengajuan.status,
            "dokumen": [
                {
                    "nama_file": dokumen.nama_file,
                    "path": f"../pengajuan_service/uploads/{dokumen.path}",  # Path untuk akses file
                }
                for dokumen in dokumen_pendukung
            ],
        }

        return render_template("detail_pengajuan.html", pengajuan=data)

    except Exception as e:
        print(f"Error: {e}")
        return (
            jsonify({"message": "Terjadi kesalahan saat mengambil detail pengajuan"}),
            500,
        )


PENGAJUAN_SERVICE_URL = "http://localhost:5000/var/uploads/"


@app.route("/uploads/<filename>")
def get_uploaded_file(filename):
    # Path lengkap ke folder uploads
    upload_folder = os.path.join(current_app.root_path, "var", "uploads")
    try:
        # Mengirim file dari folder uploads
        return send_from_directory(upload_folder, filename)
    except FileNotFoundError:
        return jsonify({"message": "File not found"}), 404


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
