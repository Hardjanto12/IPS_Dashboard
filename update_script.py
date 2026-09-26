import re

with open('frontend/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

old_pattern = r"\} else if \(task\.model === 'container' && task\.task_id && task\.task_id\.length === 21\) \{[\s\S]*?thumbHtml = imgTags \+ '<span class=\"fallback-dash\">-</span>';\n\s*\}"

new_fallback = r"""} else if (task.model === 'container' && task.task_id && task.task_id.length === 21) {
                const tId = task.task_id;
                const scannerId = tId.substring(0, 9);
                const year = tId.substring(9, 13);
                const md = tId.substring(13, 17);
                const seq = parseInt(tId.substring(17), 10);
                
                let imgTags = '';
                for (let offset = 0; offset <= 15; offset++) {
                    const folderSeq = String(seq + offset).padStart(4, '0');
                    const imgUrlGray = `${GLOBAL_CONFIG.mdst_base_url}/${scannerId}/${year}/${md}/${folderSeq}/${tId}_gray.jpg`;
                    const imgUrlIcon = `${GLOBAL_CONFIG.mdst_base_url}/${scannerId}/${year}/${md}/${folderSeq}/${tId}_icon.jpg`;
                    const fullImgUrl = `${GLOBAL_CONFIG.mdst_base_url}/${scannerId}/${year}/${md}/${folderSeq}/${tId}.jpg`;
                    
                    imgTags += `<img src="${imgUrlGray}" data-fallback="${imgUrlIcon}" data-full="${fullImgUrl}" style="height: 30px; border-radius: 2px; cursor: pointer; background: #2a2a2a; object-fit: cover; width: 60px; display: none;" onload="this.style.display='inline'; Array.from(this.parentElement.children).forEach(c => { if(c !== this && (c.tagName === 'IMG' || c.className === 'fallback-dash')) c.style.display='none'; });" onclick="window.open(this.getAttribute('data-full'), '_blank')" onerror="if(this.src.includes('_gray.jpg')) { this.src = this.getAttribute('data-fallback'); } else { this.remove(); }">`;
                }
                thumbHtml = imgTags + '<span class="fallback-dash">-</span>';
            }"""

new_content = re.sub(old_pattern, new_fallback, content, flags=re.DOTALL)

with open('frontend/app.js', 'w', encoding='utf-8') as f:
    f.write(new_content)
