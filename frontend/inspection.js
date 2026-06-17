const urlParams = new URLSearchParams(window.location.search);
const taskId = urlParams.get('id');

if (!taskId) {
    Swal.fire('Error', 'Task ID tidak ditemukan di URL!', 'error').then(() => {
        window.close();
    });
}

document.getElementById('task-id-badge').textContent = `Memuat Task #${taskId}...`;

let allImages = [];

async function loadData() {
    try {
        const res = await fetch(`http://192.111.111.80:8000/api/tasks/${taskId}/details`);
        const data = await res.json();
        
        if (data.error) throw new Error(data.error);

        const task = data.task;
        const manifest = data.manifest_data || {};
        const ips = data.ips_data || {};
        
        document.getElementById('task-id-badge').textContent = task.task_id;
        
        // Populate Form
        document.getElementById('inp-container-no').value = manifest.container_no || '-';
        document.getElementById('inp-front-vehicle').value = manifest.vehicle_serial || '-';
        document.getElementById('inp-rear-vehicle').value = manifest.rear_vehicle_no || '-';
        document.getElementById('inp-driver').value = manifest.driver_name || '-';
        document.getElementById('inp-country').value = manifest.country_of_origin || '-';
        
        document.getElementById('inp-enter-time').value = ips.vehicle_enter_time || formatTime(task.create_time);
        document.getElementById('inp-scan-time').value = ips.scan_time ? ips.scan_time.replace(/\.\d+/, '') : '-';
        document.getElementById('inp-exit-time').value = manifest.exit_time || '-';
        
        document.getElementById('inp-weight').value = manifest.container_weight || '-';
        document.getElementById('inp-remark').value = manifest.remark || '-';
        
        // Populate Gallery
        const carousel = document.getElementById('carousel-container');
        carousel.innerHTML = '';
        allImages = [];
        
        // 1. Add CCR Images first
        if (ips.ccr_images) {
            // Find the 006 image if it exists
            const rearIndex = ips.ccr_images.findIndex(img => img.toLowerCase().includes('006.jpg') || img.includes('006.'));
            if (rearIndex > -1) {
                const rearImg = ips.ccr_images.splice(rearIndex, 1)[0];
                ips.ccr_images.unshift(rearImg);
            }
            
            ips.ccr_images.forEach(img => {
                allImages.push({url: img, type: 'CCR', badgeColor: '#DBEAFE'});
            });
        }
        
        // 2. Add X-Ray Images
        if (ips.images) {
            ips.images.forEach(img => {
                allImages.push({url: img, type: 'X-Ray', badgeColor: '#E2E8F0'});
            });
        }
        
        // 3. Add Camera Images
        if (ips.camera_images) {
            ips.camera_images.forEach(img => {
                allImages.push({url: img, type: 'Camera', badgeColor: '#FEF3C7'});
            });
        }
        
        if (allImages.length === 0) {
            carousel.innerHTML = `<div style="width: 100%; text-align: center; line-height: 100px; color: var(--text-muted);">Belum ada gambar yang tersedia.</div>`;
            document.getElementById('main-img-badge').textContent = 'No Image Found';
            return;
        }

        allImages.forEach((imgObj, idx) => {
            const thumb = document.createElement('div');
            thumb.className = `thumbnail ${idx === 0 ? 'active' : ''}`;
            thumb.style.backgroundImage = `url('${imgObj.url}')`;
            thumb.innerHTML = `<span class="thumb-badge" style="background: ${imgObj.badgeColor}; color: #000;">${imgObj.type}</span>`;
            thumb.onclick = () => selectImage(idx, thumb);
            carousel.appendChild(thumb);
        });

        // Select first image by default
        selectImage(0, carousel.firstChild);
        
    } catch (e) {
        Swal.fire('Gagal Memuat Data', e.message, 'error');
    }
}

function selectImage(index, thumbElement) {
    // Update active class
    const thumbnails = document.querySelectorAll('.thumbnail');
    thumbnails.forEach(t => t.classList.remove('active'));
    if(thumbElement) thumbElement.classList.add('active');

    const imgObj = allImages[index];
    if(!imgObj) return;

    const mainImg = document.getElementById('main-image-display');
    const mainBadge = document.getElementById('main-img-badge');
    const loading = document.getElementById('main-image-loading');

    // Show loading
    mainImg.style.display = 'none';
    loading.style.display = 'block';

    mainBadge.textContent = imgObj.type;
    mainBadge.style.background = imgObj.badgeColor;
    mainBadge.style.color = '#000';

    mainImg.onload = () => {
        loading.style.display = 'none';
        mainImg.style.display = 'block';
    };
    
    mainImg.onerror = () => {
        loading.style.display = 'none';
        mainBadge.textContent = 'Error loading image';
    };

    mainImg.src = imgObj.url;
}

function formatTime(unix) {
    if (!unix) return '-';
    return new Date(unix * 1000).toLocaleString('en-CA', { hour12: false }).replace(',', '');
}

async function submitInspection() {
    const btn = document.getElementById('btn-save-submit');
    const originalText = btn.innerHTML;
    
    // Gather data
    const payload = {
        container_no: document.getElementById('inp-container-no').value,
        front_vehicle: document.getElementById('inp-front-vehicle').value,
        rear_vehicle: document.getElementById('inp-rear-vehicle').value,
        driver: document.getElementById('inp-driver').value,
        weight: document.getElementById('inp-weight').value,
        country: document.getElementById('inp-country').value,
        remark: document.getElementById('inp-remark').value,
        conclusion: document.querySelector('input[name="conclusion"]:checked').value,
        contents: document.getElementById('inp-contents').value
    };
    
    if (!payload.container_no) {
        Swal.fire('Peringatan', 'Nomor Kontainer tidak boleh kosong!', 'warning');
        document.getElementById('inp-container-no').focus();
        return;
    }
    
    const result = await Swal.fire({
        title: 'Konfirmasi Submit',
        text: `Anda akan menyimpan perubahan dan men-submit task ini dengan status "${payload.conclusion}". Lanjutkan?`,
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#2563EB',
        confirmButtonText: 'Ya, Lanjutkan'
    });
    
    if (!result.isConfirmed) return;
    
    btn.innerHTML = `<span class="spinner" style="width:16px; height:16px; margin:0; border-width:2px; border-top-color:#000;"></span> Menyimpan...`;
    btn.disabled = true;
    
    try {
        const res = await fetch(`http://192.111.111.80:8000/api/tasks/${taskId}/update_and_submit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const data = await res.json();
        
        if (res.ok) {
            if (window.opener && !window.opener.closed) {
                window.opener.fetchTasks();
            }
            window.close();
        } else {
            Swal.fire('Error', data.detail || data.error, 'error');
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    } catch (e) {
        Swal.fire('Gagal', 'Koneksi gagal: ' + e.message, 'error');
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

// Start
loadData();

// Shortcut Keys
document.addEventListener('keydown', function(e) {
    // Ctrl + Enter to Save & Submit
    if (e.ctrlKey && e.key === 'Enter') {
        e.preventDefault();
        submitInspection();
    }
    
    // Alt + C to focus Container No. form
    if (e.altKey && e.key.toLowerCase() === 'c') {
        e.preventDefault();
        const containerInput = document.getElementById('inp-container-no');
        if (containerInput) {
            containerInput.focus();
            containerInput.select(); // Highlight existing text for quick replacement
        }
    }
});
