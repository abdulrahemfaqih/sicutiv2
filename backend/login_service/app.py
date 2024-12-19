from flask import Flask, jsonify, request, render_template, url_for
from models import db, User, UserRole, TahunAjaran, Semester, SemesterStatus, Prodi
from flask_bcrypt import Bcrypt
import jwt
from models import UserRole
import datetime
from flask_cors import CORS


app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+mysqlconnector://root:password@db/sicuti"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "your_secret_key"
bcrypt = Bcrypt(app)
db.init_app(app)

CORS(app)


@app.route("/", methods=["GET"])
def index():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    # try:
    data = request.get_json()  # Mengambil data JSON dari body request
    print(f"Received Data: {data}")  # Debug log

    if not data:
        print("No data received")
        return jsonify({"message": "No data provided"}), 400

    username = data.get("username")
    password = data.get("password")

    # Cari pengguna berdasarkan username
    user = User.query.filter_by(username=username).first()
    if not user:
        print("User not found")
        return jsonify({"message": "Invalid username"}), 401

    # Verifikasi password
    if not bcrypt.check_password_hash(user.password, password):
        print("Invalid password")
        return jsonify({"message": "Invalid password"}), 401

    # Pastikan role_value adalah string
    role_value = str(user.role.value)  # Convert to string explicitly
    print(f"Role Value: {role_value} (Type: {type(role_value)})")

    # Buat JWT token
    payload = {
        "user_id": user.id,
        "role": role_value,
        "exp": (
            datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        ).timestamp(),  # Convert to timestamp
    }

    print(f"Payload: {payload}")  # Debug print untuk payload

    # Generate token
    token = jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")

    # Tentukan URL layanan berdasarkan role
    if user.role == UserRole.mahasiswa:
        service_url = "http://localhost:5001"
    elif user.role == UserRole.admin:
        service_url = "http://localhost:5002"
    else:
        print(f"Role {user.role} is not recognized.")
        return jsonify({"message": "Role not recognized"}), 403

    print(f"Token generated: {token}")
    return jsonify(
        {"message": "Login successful", "redirect_url": service_url, "token": token}
    )


# except Exception as e:
#     print(f"Error during login: {e}")
#     return jsonify({"message": "Internal server error", "error": str(e)}), 500


@app.route("/logout", methods=["POST"])
def logout():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"message": "Token is missing"}), 400
    try:
        token = token.split(" ")[1]  # Hapus "Bearer" dari token
        decoded_token = jwt.decode(
            token, app.config["SECRET_KEY"], algorithms=["HS256"]
        )
        blacklist.add(token)  # Tambahkan token ke blacklist
        return jsonify({"message": "Logged out successfully"}), 200
    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token has expired"}), 403
    except jwt.InvalidTokenError:
        return jsonify({"message": "Invalid token"}), 403


def token_required(f):
    def decorator(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"message": "Token is missing"}), 403
        try:
            token = token.split(" ")[1]
            if token in blacklist:
                return jsonify({"message": "Token has been logged out"}), 403
            decoded_token = jwt.decode(
                token, app.config["SECRET_KEY"], algorithms=["HS256"]
            )
            request.user_id = decoded_token["user_id"]
            request.role = decoded_token["role"]
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token has expired"}), 403
        except jwt.InvalidTokenError:
            return jsonify({"message": "Invalid token"}), 403
        return f(*args, **kwargs)

    return decorator


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")