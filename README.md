# 🖥️ Nuctech IPS Integration Dashboard

![Light Mode Dashboard](https://img.shields.io/badge/Theme-Enterprise_Light_Mode-blue?style=flat-square)
![Backend](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi)
![Frontend](https://img.shields.io/badge/Frontend-Vanilla_JS-F7DF1E?style=flat-square&logo=javascript)

**Nuctech IPS Integration Dashboard** adalah aplikasi *middleware* dan *operational dashboard* yang dirancang untuk memantau, menginspeksi, dan mengelola tugas (*tasks*) pemindaian X-Ray Kontainer dari sistem Nuctech. 

Aplikasi ini bertindak sebagai jembatan yang mencegat (intercept) komunikasi SOAP API antara layar operator IPS dan server utama Nuctech, memberikan kebebasan kepada pengguna untuk memeriksa gambar, mengedit data manifes, dan memberikan keputusan secara manual maupun massal sebelum dikirim kembali ke server.

---

## 🌟 Fitur Utama

- **Real-time Task Polling:** Mengambil daftar antrean kontainer secara otomatis (*auto-refresh*) dari database Nuctech.
- **Deep Inspection Page:** Layar khusus bergaya SaaS modern dengan tata letak *side-by-side* yang memisahkan Form Edit Data dan Galeri Gambar Kontainer.
- **Multi-Image Carousel:** Mampu menampilkan dan membandingkan gambar dari X-Ray, CCR (Container Code Recognition), dan Kamera eksternal secara interaktif tanpa membuka jendela baru.
- **API Proxy & Data Manipulation:** Mengekstrak XML dari SOAP Nuctech (`GetSiinfo`), memanipulasinya (seperti mengubah *Container No*), dan mengirimkannya kembali (`SetSiinfo`) dengan aman.
- **Mass Auto-Submit:** Fitur untuk memilih puluhan kontainer sekaligus dan menyelesaikannya dengan status *"No Suspect"* hanya dengan satu klik.
- **Enterprise UI/UX:** Antarmuka *Light Mode* yang bersih dan profesional, ditenagai tipografi *Plus Jakarta Sans* dan notifikasi animasi dari *SweetAlert2*.
- **Desktop GUI Server:** *Backend* dibungkus dengan GUI *executable* (BPM Server GUI) yang memiliki kemampuan *Auto-Start* sehingga ramah bagi operator non-teknis.

---

## 📂 Struktur Direktori

```text
IPS_Dashboard/
├── backend/
│   ├── main.py                     # Inti server FastAPI (API Routes, XML/SOAP Logic)
│   ├── server_gui.py               # GUI Control Panel untuk menjalankan/mematikan server
│   └── BPM_API_Server_Visible.spec # File konfigurasi PyInstaller untuk kompilasi .exe
└── frontend/
    ├── index.html                  # Halaman utama (Tabel Daftar Antrean)
    ├── app.js                      # Logika utama (Polling, Tabel, Mass Submit)
    ├── style.css                   # Sistem desain utama (Token Warna Light Mode)
    ├── inspection.html             # Halaman khusus Deep Inspection (Form & Carousel)
    └── inspection.js               # Logika halaman inspeksi (Viewer Gambar & Submit Data)
```

---

## 🚀 Cara Menjalankan Aplikasi

### 1. Menjalankan Server Backend (FastAPI)

#### Opsi A: Menggunakan Executable (GUI)
Jika Anda sudah mengompilasi aplikasi:
1. Buka file `BPM_Server_GUI.exe`.
2. Server akan otomatis menyala di latar belakang pada `http://192.111.111.80:8000`.

#### Opsi B: Menjalankan via Python (Development)
1. Pastikan Python 3.8+ sudah terinstal.
2. Instal dependensi:
   ```bash
   pip install fastapi uvicorn requests pydantic
   ```
3. Pindah ke direktori backend dan jalankan server:
   ```bash
   cd backend
   python main.py
   ```
   *Atau jalankan GUI server:* `python server_gui.py`

### 2. Mengakses Frontend (Dashboard)
Karena frontend disajikan secara *statis* oleh FastAPI (ter-mount di `/`), Anda cukup membuka peramban web (*browser*) dan menuju ke:
👉 **`http://192.111.111.80:8000`** atau **`http://localhost:8000`**

*(Atau Anda bisa langsung mengklik dua kali `frontend/index.html` jika hanya ingin melihat antarmuka murni secara lokal, namun beberapa fitur API mungkin akan terblokir oleh CORS jika tidak disajikan lewat server).*

**🖥️ Cara Mengakses dari PC Lain (Client):**
Anda **tidak perlu menginstal** apapun di PC lain. Cukup pastikan PC lain tersebut terhubung dalam satu jaringan (LAN/Network) dengan PC Server, lalu buka peramban (*browser*) seperti Chrome/Edge dan ketikkan alamat IP dari PC Server:
👉 **`http://192.111.111.80:8000`**

Jika Anda *benar-benar* ingin memisahkan *frontend* dan menjalankannya tanpa *browser* dari server, Anda cukup **menyalin folder `frontend/`** ke PC lain dan membuka `index.html`. Karena semua fungsi koneksi di dalam Javascript sudah menunjuk ke IP server `192.111.111.80:8000`, maka *dashboard* akan tetap berfungsi mencari server Nuctech selama jaringan terhubung!

### 3. Kompilasi Executable (PyInstaller)
Jika Anda melakukan perubahan pada *backend* (Python) dan ingin mengemas ulang aplikasi menjadi file `.exe` yang mandiri:

1. Buka terminal/Command Prompt dan arahkan ke folder `backend`:
   ```bash
   cd backend
   ```
2. Pastikan `pyinstaller` sudah terinstal:
   ```bash
   pip install pyinstaller
   ```
3. Jalankan perintah kompilasi menggunakan file `.spec` yang telah disediakan:
   ```bash
   pyinstaller BPM_API_Server_Visible.spec
   ```
   *(Atau gunakan file `.spec` lain jika ada konfigurasi khusus, seperti `BPM_Server_GUI.spec`)*
4. File `.exe` yang baru akan dihasilkan di dalam folder `backend/dist/`.

---

## 🛠️ Stack Teknologi & Desain

- **Backend:** Python, FastAPI, Uvicorn, Requests (SOAP XML Parser).
- **Frontend:** HTML5, CSS3, Vanilla JS.
- **Font Utama:** [Plus Jakarta Sans](https://fonts.google.com/specimen/Plus+Jakarta+Sans)
- **Library Tambahan:** [SweetAlert2](https://sweetalert2.github.io/) (Untuk notifikasi modern).
- **Skema Warna (Light Mode):**
  - Background: `#E8EFF9`
  - Card/Panel: `#FFFFFF`
  - Aksent Primer (Biru): `#2563EB`
  - Sukses (Hijau): `#059669`

---

## 📝 Catatan Rilis Terakhir
- **Migrasi ke Light Mode:** Membuang tema gelap lama (Cyberpunk) sepenuhnya dan beralih ke desain Enterprise SaaS.
- **Perbaikan Carousel:** Mengubah galeri statis menjadi interaktif *side-by-side* untuk kenyamanan *Deep Inspection*.
- **Integrasi SweetAlert:** Mengganti semua peringatan bawaan *browser* (`alert()` / `confirm()`) dengan jendela *popup* yang halus dan interaktif.
