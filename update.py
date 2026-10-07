import re

with open('frontend/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# 1
content = re.sub(
    r'if\s*\(task\.thumbnail_path\s*&&\s*task\.thumbnail_path\s*!==\s*"NOT_FOUND"\)\s*\{\s*thumbHtml\s*=\s*<img src="\$\{task\.thumbnail_path\}"[^>]+><span class="fallback-dash"[^>]*>-</span>;\s*\}',
    '''if (task.thumbnail_path && task.thumbnail_path !== "NOT_FOUND") {
                const fixedPath = task.thumbnail_path.replace('_gray.jpg', '_icon.jpg');
                thumbHtml = <img src="" style="height: 30px; border-radius: 4px; cursor: pointer; background: #2a2a2a; object-fit: cover; width: 60px;" onclick="window.open('', '_blank')" onerror="this.style.display='none'; this.nextElementSibling ? this.nextElementSibling.style.display='inline' : null"><span class="fallback-dash" style="display:none">-</span>;
            }''',
    content
)

# 2
content = re.sub(
    r'const\s+imgUrlGray\s*=\s*\$\{GLOBAL_CONFIG\.mdst_base_url\}/[^\n]+_gray\.jpg;\s*const\s+imgUrlIcon\s*=\s*\$\{GLOBAL_CONFIG\.mdst_base_url\}/[^\n]+_icon\.jpg;\s*const\s+fullImgUrl\s*=\s*\$\{GLOBAL_CONFIG\.mdst_base_url\}/[^\n]+\.jpg;\s*imgTags\s*\+=\s*<img src="\$\{imgUrlGray\}" data-fallback="\$\{imgUrlIcon\}"[^\n]+;',
    '''const imgUrlIcon = ${GLOBAL_CONFIG.mdst_base_url}/////_icon.jpg;
                    const fullImgUrl = ${GLOBAL_CONFIG.mdst_base_url}/////.jpg;
                    imgTags += <img src="" data-full="" style="height: 30px; border-radius: 2px; cursor: pointer; background: #2a2a2a; object-fit: cover; width: 60px; display: none;" onload="this.style.display='inline'; Array.from(this.parentElement.children).forEach(c => { if(c !== this && (c.tagName === 'IMG' || c.className === 'fallback-dash')) c.style.display='none'; });" onclick="window.open(this.getAttribute('data-full'), '_blank')" onerror="this.remove();">;''',
    content
)

# 3
content = re.sub(
    r'if\s*\(mData\.thumbnail_path\s*&&\s*window\.showThumbnails\)\s*\{\s*const\s+tCell\s*=\s*document\.getElementById\(	humb-cell-\$\{task\.id\}\);\s*if\s*\(tCell[^\{]+\{\s*tCell\.innerHTML\s*=\s*<img src="\$\{mData\.thumbnail_path\}"[^>]+>;\s*\}\s*\}',
    '''if (mData.thumbnail_path && window.showThumbnails) {
                            const fixedPath = mData.thumbnail_path.replace('_gray.jpg', '_icon.jpg');
                            const tCell = document.getElementById(	humb-cell-);
                            if (tCell && tCell.querySelector('.fallback-dash') && tCell.querySelector('.fallback-dash').style.display !== 'none') {
                                tCell.innerHTML = <img src="" style="height: 30px; border-radius: 4px; cursor: pointer; background: #2a2a2a; object-fit: cover; width: 60px;" onclick="window.open('', '_blank')" onerror="this.style.display='none'">;
                            }
                        }''',
    content
)

with open('frontend/app.js', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done regex patching")
