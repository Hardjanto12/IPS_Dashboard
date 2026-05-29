# Panduan Instalasi IPS Dashboard sebagai Windows Service (Offline/Latar Belakang)

Dokumen ini berisi panduan langkah-demi-langkah untuk melakukan kompilasi (*compile*) backend dan frontend menjadi satu kesatuan, serta menginstalnya sebagai Windows Service agar berjalan secara otomatis di latar belakang tanpa GUI/Console Window.

---

## 1. Persiapan Awal (Offline)

Jika server target tidak memiliki akses internet, unduh berkas berikut terlebih dahulu dari komputer lain:
1. **NSSM (Non-Sucking Service Manager)**: 
   * Unduh dari [nssm.cc/download](https://nssm.cc/download).
   * Ekstrak file zip, lalu salin berkas `nssm.exe` (pilih versi di dalam folder `win64/`) ke folder server target.
2. Pastikan Python dan library yang dibutuhkan (seperti `pyinstaller`, `fastapi`, `uvicorn`, dll.) sudah terinstal di server.

---

## 2. Kompilasi Program (Compile to Executable)

Kita akan mengompilasi backend FastAPI menjadi berkas biner `.exe` yang akan berjalan secara *windowless* (tanpa memunculkan jendela Command Prompt) menggunakan file konfigurasi `.spec` yang sudah disediakan.

1. Buka Command Prompt (CMD) atau PowerShell di folder project backend (`D:\Source Codes\Nuctech\IPS_Dashboard\backend`).
2. Jalankan perintah kompilasi berikut:
   ```cmd
   pyinstaller BPM_API_Server.spec
   ```
3. Setelah proses selesai, file hasil kompilasi akan berada di folder:
   `D:\Source Codes\Nuctech\IPS_Dashboard\backend\dist\BPM_API_Server\BPM_API_Server.exe`

---

## 3. Struktur Folder Produksi

Agar backend FastAPI dapat melayani (*serve*) halaman frontend, folder `frontend` harus diletakkan sejajar atau sesuai dengan relatif path yang dicari oleh program (relatif terhadap file `.exe`).

Struktur direktori di server produksi sebaiknya seperti ini:
```text
D:\Nuctech_IPS_Dashboard\
├── frontend\                  <-- Salin folder "frontend" lengkap ke sini
│   ├── index.html
│   ├── inspection.js
│   └── ...
└── backend\
    └── dist\
        └── BPM_API_Server\
            ├── BPM_API_Server.exe   <-- File executable utama
            └── ...
```

---

## 4. Instalasi Windows Service Menggunakan NSSM

Langkah ini akan mendaftarkan berkas executable kita ke dalam Windows Services.

1. Jalankan Command Prompt (CMD) sebagai **Administrator**.
2. Masuk ke folder tempat Anda meletakkan `nssm.exe` (misalnya di folder backend):
   ```cmd
   d:
   cd "D:\Source Codes\Nuctech\IPS_Dashboard\backend"
   ```
3. Jalankan perintah instalasi service (kita beri nama service ini `IPS_Dashboard`):
   ```cmd
   nssm install IPS_Dashboard "D:\Source Codes\Nuctech\IPS_Dashboard\backend\dist\BPM_API_Server\BPM_API_Server.exe"
   ```
4. Mengonfigurasi direktori kerja (*working directory*) agar pencarian folder `frontend` relatif berjalan dengan benar:
   ```cmd
   nssm set IPS_Dashboard AppDirectory "D:\Source Codes\Nuctech\IPS_Dashboard\backend\dist\BPM_API_Server"
   ```

---

## 5. Mengelola Service di Windows (`services.msc`)

Setelah berhasil diinstal, Anda dapat mengelola jalannya server langsung melalui Windows Services Manager:

1. Tekan tombol `Windows + R` di keyboard, ketik **`services.msc`**, lalu tekan **Enter**.
2. Cari service dengan nama **`IPS_Dashboard`**.
3. **Mengatur Auto-Start**:
   * Klik kanan pada `IPS_Dashboard` -> **Properties**.
   * Pada kolom *Startup type*, ubah menjadi **Automatic**.
   * Klik **Apply** dan **OK**. (Service akan otomatis menyala setiap kali server Windows dihidupkan).
4. **Menyalakan / Mematikan**:
   * Klik kanan pada `IPS_Dashboard` -> Pilih **Start** untuk menyalakan.
   * Pilih **Stop** untuk mematikan.

---

## 6. Cara Menghapus Service (Uninstall)

Jika di kemudian hari Anda ingin menghapus service ini dari sistem Windows:
1. Buka CMD sebagai **Administrator**.
2. Hentikan service terlebih dahulu:
   ```cmd
   nssm stop IPS_Dashboard
   ```
3. Hapus service dengan perintah:
   ```cmd
   nssm remove IPS_Dashboard confirm
   ```
