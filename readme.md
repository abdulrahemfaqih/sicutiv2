# SICUTI-V2 Microservice

Aplikasi pengajuan cuti online berbasis microservice yang dibangun menggunakan Flask (Python), React.js, dan Docker.

## Deskripsi

SICUTI-V2 adalah sistem pengajuan cuti online yang dirancang dengan arsitektur microservice untuk memudahkan pengelolaan dan skalabilitas aplikasi. Sistem ini memisahkan backend dan frontend menjadi layanan terpisah yang dapat di-deploy secara independen.

## Teknologi yang Digunakan

- Backend: Flask (Python)
- Frontend: React.js
- Containerization: Docker
- Database: (sesuaikan dengan database yang digunakan)

## Persyaratan Sistem

- Python 3.8+
- Node.js 14+
- Docker & Docker Compose
- Virtual Environment (venv)

## Cara Menjalankan Aplikasi

### Menggunakan Virtual Environment (Development)

1. Clone repository ini
```bash
git clone [url-repository]
cd sicutiV2
```

2. Setup Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Setup Frontend
```bash
cd frontend
npm install
```

### Menggunakan Docker Compose (Production)

1. Pastikan Docker dan Docker Compose terinstall

2. Jalankan aplikasi
```bash
docker-compose up --build
```


## Struktur Proyek

```
sicutiV2-microservice/
├── backend/
│   ├── login_service
│   ├── validasi_service
│   └── pengajuan-service
├── frontend/
│   ├── src/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

