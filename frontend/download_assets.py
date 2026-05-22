import os
import re
import urllib.request
import urllib.parse

def download_file(url, filepath, headers=None):
    print(f"Downloading {url} to {filepath}")
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req) as response:
        with open(filepath, 'wb') as f:
            f.write(response.read())

def download_google_fonts(css_url, css_filename, assets_dir):
    # Spoof modern browser to get WOFF2
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    req = urllib.request.Request(css_url, headers=headers)
    with urllib.request.urlopen(req) as response:
        css_content = response.read().decode('utf-8')
    
    # Find all url(...) in CSS
    urls = re.findall(r'url\((https?://[^)]+)\)', css_content)
    urls = list(set(urls)) # unique
    
    for url in urls:
        filename = url.split('/')[-1]
        filepath = os.path.join(assets_dir, filename)
        download_file(url, filepath)
        
        # Replace URL in CSS
        css_content = css_content.replace(url, f"./{filename}")
    
    with open(os.path.join(assets_dir, css_filename), 'w', encoding='utf-8') as f:
        f.write(css_content)

def main():
    frontend_dir = r"d:\Source Codes\Nuctech\IPS_Dashboard\frontend"
    assets_dir = os.path.join(frontend_dir, "assets")
    
    if not os.path.exists(assets_dir):
        os.makedirs(assets_dir)
        
    # 1. SweetAlert2
    swal_url = "https://cdn.jsdelivr.net/npm/sweetalert2@11.10.8/dist/sweetalert2.all.min.js"
    download_file(swal_url, os.path.join(assets_dir, "sweetalert2.min.js"))
    
    # 2. Plus Jakarta Sans
    jakarta_url = "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap"
    download_google_fonts(jakarta_url, "plus_jakarta_sans.css", assets_dir)
    
    # 3. Material Symbols Outlined
    material_url = "https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined"
    download_google_fonts(material_url, "material_symbols.css", assets_dir)
    
    print("All assets downloaded successfully.")

if __name__ == "__main__":
    main()
