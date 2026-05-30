# Panduan Instalasi IPS Dashboard sebagai Windows Service

Dokumen ini berisi panduan untuk melakukan kompilasi (*compile*) dan menginstal IPS Dashboard sebagai Windows Service agar berjalan secara otomatis di latar belakang tanpa GUI/Console Window.

> **Semua proses di bawah ini bisa dilakukan secara offline (tanpa internet).** File `nssm.exe` sudah disertakan di dalam project.

---

## Prasyarat

Pastikan hal-hal berikut sudah terpenuhi di server target:
- **Python** dan library yang dibutuhkan (`pyinstaller`, `fastapi`, `uvicorn`, dll.) sudah terinstal *(hanya diperlukan untuk proses compile)*.
- Folder project sudah lengkap, termasuk folder `frontend/` dan `backend/`.

---

## 1. Kompilasi Program (Compile to Executable)

Kompilasi backend FastAPI menjadi file `.exe` yang berjalan tanpa jendela CMD (*windowless*).

1. Buka Command Prompt (CMD) atau PowerShell di folder project backend:
   ```cmd
   cd "D:\Source Codes\Nuctech\IPS_Dashboard\backend"
   ```
2. Jalankan perintah kompilasi:
   ```cmd
   pyinstaller BPM_API_Server.spec
   ```
3. Setelah proses selesai, file hasil kompilasi akan berada di:
   ```
   backend\dist\BPM_API_Server.exe
   ```

> **Catatan:** Jika ingin melakukan debug (melihat log di console), compile menggunakan `BPM_API_Server_Visible.spec` sebagai gantinya.

---

## 2. Struktur Folder Produksi

Pastikan folder `frontend` berada satu tingkat di atas folder tempat file `.exe` berada, sehingga backend dapat menemukannya secara otomatis.

```text
IPS_Dashboard\
├── nssm.exe                      <-- Sudah disertakan dalam project
├── install_service.bat            <-- Script install otomatis
├── uninstall_service.bat          <-- Script uninstall otomatis
├── frontend\                      <-- Halaman web dashboard
│   ├── index.html
│   ├── app.js
│   ├── inspection.html
│   ├── inspection.js
│   ├── style.css
│   └── assets\
└── backend\
    ├── main.py
    ├── BPM_API_Server.spec
    └── dist\
        └── BPM_API_Server.exe     <-- File executable hasil compile
```

---

## 3. Instalasi Windows Service (Otomatis)

Cara termudah untuk menginstal service adalah menggunakan script otomatis yang sudah disediakan.

### Langkah-langkah:
1. Buka folder project `IPS_Dashboard` di File Explorer.
2. Klik kanan pada file **`install_service.bat`** → pilih **Run as administrator**.
3. Script akan otomatis:
   - Memeriksa apakah `nssm.exe` dan `BPM_API_Server.exe` tersedia.
   - Menghapus service lama jika sudah pernah diinstal sebelumnya.
   - Mendaftarkan service baru dengan nama `IPS_Dashboard`.
   - Mengatur service agar **auto-start** saat Windows boot.
   - Mengatur **auto-restart** jika service crash (restart otomatis setelah 5 detik).
   - Langsung menjalankan service.

### Setelah berhasil:
- Dashboard dapat diakses di browser: **`http://localhost:8000/dashboard`**
- Atau dari komputer lain dalam jaringan: **`http://<IP_SERVER>:8000/dashboard`**

---

## 4. Mengelola Service di Windows (`services.msc`)

Setelah berhasil diinstal, Anda dapat mengelola service melalui Windows Services Manager:

1. Tekan `Windows + R`, ketik **`services.msc`**, lalu tekan **Enter**.
2. Cari service dengan nama **`IPS Dashboard Server`** (nama internal: `IPS_Dashboard`).
3. **Menyalakan / Mematikan**:
   - Klik kanan → **Start** untuk menyalakan.
   - Klik kanan → **Stop** untuk mematikan.
4. **Mengatur Startup**:
   - Klik kanan → **Properties** → ubah *Startup type* sesuai kebutuhan:
     - `Automatic` → Otomatis menyala saat Windows boot.
     - `Manual` → Hanya menyala jika di-start manual.
     - `Disabled` → Tidak bisa dinyalakan.

---

## 5. Menghapus Service (Uninstall)

### Cara Otomatis (Direkomendasikan):
1. Klik kanan pada file **`uninstall_service.bat`** → pilih **Run as administrator**.
2. Ketik **Y** untuk mengkonfirmasi penghapusan.
3. Service akan dihentikan dan dihapus dari sistem.

### Cara Manual (Jika diperlukan):
Buka CMD sebagai Administrator, lalu jalankan:
```cmd
nssm stop IPS_Dashboard
nssm remove IPS_Dashboard confirm
```

---

## Troubleshooting

| Masalah | Solusi |
|---------|--------|
| Dashboard tidak bisa diakses (`Not Found`) | Pastikan folder `frontend` berada satu tingkat di atas lokasi file `.exe` |
| Service gagal start | Jalankan `BPM_API_Server_Visible.exe` secara manual untuk melihat error di console |
| Port 8000 sudah dipakai | Hentikan proses lain yang menggunakan port 8000, atau ubah port di `main.py` |
| Script `.bat` minta Administrator | Klik kanan file `.bat` → **Run as administrator** |
