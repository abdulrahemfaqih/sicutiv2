import enum
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class EnumStatus(enum.Enum):
    Ditolak = 0
    Disetujui = 1
    Pending = 2


# class PengajuanCuti(db.Model):
#     __tablename__ = "transaksi"
#     id = db.Column(db.Integer, primary_key=True)
#     nama = db.Column(db.String(100), nullable=False)
#     alasan = db.Column(db.String(255), nullable=False)
#     status = db.Column(db.Enum(EnumStatus), default=EnumStatus.Pending, nullable=False)

#     def __init__(self, nama, alasan, status=EnumStatus.Pending):
#         self.nama = nama
#         self.alasan = alasan
#         self.status = status


# docker exec -it mysql_db bash
class UserRole(enum.Enum):
    mahasiswa = "mahasiswa"
    admin = "bak"


class Prodi(db.Model):
    __tablename__ = "prodi"
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    role = db.Column(db.Enum(UserRole), nullable=False)
    nim = db.Column(db.String(20), nullable=True)  # Nullable jika bukan mahasiswa
    prodi_id = db.Column(
        db.Integer, db.ForeignKey("prodi.id"), nullable=True
    )  # Nullable jika bukan mahasiswa
    prodi = db.relationship("Prodi", backref="users")  # Relasi ke Prodi


class TahunAjaran(db.Model):
    __tablename__ = "tahun_ajaran"
    id = db.Column(db.Integer, primary_key=True)
    tahun = db.Column(db.String(9), nullable=False)  # Format: 2023/2024
    status = db.Column(db.Boolean, default=True)


class SemesterStatus(enum.Enum):
    ganjil = "ganjil"
    genap = "genap"


class Semester(db.Model):
    __tablename__ = "semester"
    id = db.Column(db.Integer, primary_key=True)
    semester = db.Column(db.Enum(SemesterStatus), nullable=False)
    tahun_ajaran_id = db.Column(
        db.Integer, db.ForeignKey("tahun_ajaran.id"), nullable=False
    )
    status = db.Column(db.Boolean, default=True)  # True jika aktif
    tahun_ajaran = db.relationship("TahunAjaran", backref="semesters")


class PengajuanCuti(db.Model):
    __tablename__ = "pengajuan_cuti"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    alasan = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), default="pending")  # Ditolak, Disetujui, Pending
    tahun_ajaran_id = db.Column(
        db.Integer, db.ForeignKey("tahun_ajaran.id"), nullable=False
    )
    semester_id = db.Column(db.Integer, db.ForeignKey("semester.id"), nullable=False)
    user = db.relationship("User", backref="pengajuan_cutis")
    tahun_ajaran = db.relationship("TahunAjaran", backref="pengajuan_cutis")
    semester = db.relationship("Semester", backref="pengajuan_cutis")


class DokumenPendukung(db.Model):
    __tablename__ = "dokumen_pendukung"
    id = db.Column(db.Integer, primary_key=True)
    nama_file = db.Column(db.String(255), nullable=False)
    path = db.Column(db.String(255), nullable=False)
    pengajuan_id = db.Column(
        db.Integer, db.ForeignKey("pengajuan_cuti.id"), nullable=False
    )
    pengajuan = db.relationship("PengajuanCuti", backref="dokumen_pendukungs")


class SuratKeteranganCuti(db.Model):
    __tablename__ = "surat_keterangan_cuti"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    pengajuan_id = db.Column(
        db.Integer, db.ForeignKey("pengajuan_cuti.id"), nullable=False
    )
    nama_file = db.Column(db.String(255), nullable=False)
    path = db.Column(db.String(255), nullable=False)
    user = db.relationship("User", backref="surat_keterangan_cutis")
    pengajuan = db.relationship("PengajuanCuti", backref="surat_keterangan_cutis")