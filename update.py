import sys

with open('frontend/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add toggle initialization
toggle_code = '''const autoRefreshToggle = document.getElementById('auto-refresh-toggle');
const thumbnailToggle = document.getElementById('thumbnail-toggle');
let showThumbnails = localStorage.getItem('show-thumbnails') !== 'false';
if (thumbnailToggle) {
    thumbnailToggle.checked = showThumbnails;
    thumbnailToggle.addEventListener('change', (e) => {
        showThumbnails = e.target.checked;
        localStorage.setItem('show-thumbnails', showThumbnails);
        fetchTasks();
    });
}'''
content = content.replace("const autoRefreshToggle = document.getElementById('auto-refresh-toggle');", toggle_code)

# 2. Modify thumbnail generation inside fetchTasks
old_thumb_logic = '''            let thumbHtml = '<span class="fallback-dash">-</span>';
            if (task.thumbnail_path && task.thumbnail_path !== "NOT_FOUND") {
                thumbHtml = <img src="" style="height: 30px; border-radius: 4px; cursor: pointer; background: #2a2a2a; object-fit: cover; width: 60px;" onclick="window.open('', '_blank')" onerror="this.style.display='none'; this.nextElementSibling ? this.nextElementSibling.style.display='inline' : null"><span class="fallback-dash" style="display:none">-</span>;
            } else if (task.model === 'container' && task.task_id && task.task_id.length === 21) {
                const tId = task.task_id;
                const scannerId = tId.substring(0, 9);
                const year = tId.substring(9, 13);
                const md = tId.substring(13, 17);
                const seq = parseInt(tId.substring(17), 10);
                
                let imgTags = '';
                for (let offset = 0; offset <= 15; offset++) {
                    const folderSeq = String(seq + offset).padStart(4, '0');
                    const imgUrlGray = ${GLOBAL_CONFIG.mdst_base_url}/////_gray.jpg;
                    const imgUrlIcon = ${GLOBAL_CONFIG.mdst_base_url}/////_icon.jpg;
                    const fullImgUrl = ${GLOBAL_CONFIG.mdst_base_url}/////.jpg;
                    
                    imgTags += <img src="" data-fallback="" data-full="" style="height: 30px; border-radius: 2px; cursor: pointer; background: #2a2a2a; object-fit: cover; width: 60px; display: none;" onload="this.style.display='inline'; Array.from(this.parentElement.children).forEach(c => { if(c !== this && (c.tagName === 'IMG' || c.className === 'fallback-dash')) c.style.display='none'; });" onclick="window.open(this.getAttribute('data-full'), '_blank')" onerror="if(this.src.includes('_gray.jpg')) { this.src = this.getAttribute('data-fallback'); } else { this.remove(); }">;
                }
                thumbHtml = imgTags + '<span class="fallback-dash">-</span>';
            }'''

new_thumb_logic = '''            let thumbHtml = '<span class="fallback-dash">-</span>';
            if (!showThumbnails) {
                thumbHtml = '<span class="fallback-dash" style="font-size: 0.8rem; background: var(--canvas-soft); padding: 2px 8px; border-radius: 4px;">Disabled</span>';
            } else {
                if (task.thumbnail_path && task.thumbnail_path !== "NOT_FOUND") {
                    thumbHtml = <img src="" style="height: 30px; border-radius: 4px; cursor: pointer; background: #2a2a2a; object-fit: cover; width: 60px;" onclick="window.open('', '_blank')" onerror="this.style.display='none'; this.nextElementSibling ? this.nextElementSibling.style.display='inline' : null"><span class="fallback-dash" style="display:none">-</span>;
                } else if (task.model === 'container' && task.task_id && task.task_id.length === 21) {
                    const tId = task.task_id;
                    const scannerId = tId.substring(0, 9);
                    const year = tId.substring(9, 13);
                    const md = tId.substring(13, 17);
                    const seq = parseInt(tId.substring(17), 10);
                    
                    let imgTags = '';
                    for (let offset = 0; offset <= 15; offset++) {
                        const folderSeq = String(seq + offset).padStart(4, '0');
                        const imgUrlGray = ${GLOBAL_CONFIG.mdst_base_url}/////_gray.jpg;
                        const imgUrlIcon = ${GLOBAL_CONFIG.mdst_base_url}/////_icon.jpg;
                        const fullImgUrl = ${GLOBAL_CONFIG.mdst_base_url}/////.jpg;
                        
                        imgTags += <img src="" data-fallback="" data-full="" style="height: 30px; border-radius: 2px; cursor: pointer; background: #2a2a2a; object-fit: cover; width: 60px; display: none;" onload="this.style.display='inline'; Array.from(this.parentElement.children).forEach(c => { if(c !== this && (c.tagName === 'IMG' || c.className === 'fallback-dash')) c.style.display='none'; });" onclick="window.open(this.getAttribute('data-full'), '_blank')" onerror="if(this.src.includes('_gray.jpg')) { this.src = this.getAttribute('data-fallback'); } else { this.remove(); }">;
                    }
                    thumbHtml = imgTags + '<span class="fallback-dash">-</span>';
                }
            }'''
content = content.replace(old_thumb_logic, new_thumb_logic)

# 3. Modify lazy loading thumbnails in batch fetch
old_batch_logic = '''                        if (mData.thumbnail_path) {
                            const tCell = document.getElementById(	humb-cell-);
                            if (tCell && tCell.querySelector('.fallback-dash') && tCell.querySelector('.fallback-dash').style.display !== 'none') {
                                tCell.innerHTML = <img src="" style="height: 30px; border-radius: 4px; cursor: pointer; background: #2a2a2a; object-fit: cover; width: 60px;" onclick="window.open('', '_blank')" onerror="this.style.display='none'">;
                            }
                        }'''

new_batch_logic = '''                        if (mData.thumbnail_path && showThumbnails) {
                            const tCell = document.getElementById(	humb-cell-);
                            if (tCell && tCell.querySelector('.fallback-dash') && tCell.querySelector('.fallback-dash').style.display !== 'none') {
                                tCell.innerHTML = <img src="" style="height: 30px; border-radius: 4px; cursor: pointer; background: #2a2a2a; object-fit: cover; width: 60px;" onclick="window.open('', '_blank')" onerror="this.style.display='none'">;
                            }
                        }'''
content = content.replace(old_batch_logic, new_batch_logic)

with open('frontend/app.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
