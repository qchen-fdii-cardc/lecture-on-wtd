import os
import re
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

# --- Configuration ---
HTML_DIR = Path('modules/_build/html')
LOCAL_SCRIPTS_DIR = HTML_DIR / '_static' / 'scripts'
SOURCE_CDN = "cdn.jsdelivr.net"
DOWNLOAD_CDN = "s4.zstatic.net"
MATHJAX_BASE_PATH = "/npm/mathjax@3/es5/"
FONT_DIR_PATH = "output/chtml/fonts/woff-v2/"
MATHJAX_FONTS = [
    "MathJax_AMS-Regular.woff", "MathJax_Calligraphic-Bold.woff",
    "MathJax_Calligraphic-Regular.woff", "MathJax_Fraktur-Bold.woff",
    "MathJax_Fraktur-Regular.woff", "MathJax_Main-Bold.woff",
    "MathJax_Main-Italic.woff", "MathJax_Main-Regular.woff",
    "MathJax_Math-BoldItalic.woff", "MathJax_Math-Italic.woff",
    "MathJax_Math-Regular.woff", "MathJax_Mono-Regular.woff",
    "MathJax_SansSerif-Bold.woff", "MathJax_SansSerif-Italic.woff",
    "MathJax_SansSerif-Regular.woff", "MathJax_Script-Regular.woff",
    "MathJax_Size1-Regular.woff", "MathJax_Size2-Regular.woff",
    "MathJax_Size3-Regular.woff", "MathJax_Size4-Regular.woff",
    "MathJax_Vector-Bold.woff", "MathJax_Vector-Regular.woff",
]

# --- Helper Functions ---


def download_text_file(url, local_path):
    """Downloads a text file (like .js) from a URL to a local path."""
    try:
        download_url = url.replace(SOURCE_CDN, DOWNLOAD_CDN)
        print(f"正在下载脚本: {download_url} -> {local_path}")
        response = requests.get(download_url, timeout=15)
        response.raise_for_status()
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_text(response.text, encoding='utf-8')
    except requests.RequestException as e:
        print(f"  下载失败: {download_url}, 错误: {e}")


def download_binary_file(url, local_path):
    """Downloads a binary file (like .woff) from a URL to a local path."""
    try:
        print(f"正在下载字体: {url} -> {local_path}")
        response = requests.get(url, timeout=15, stream=True)
        response.raise_for_status()
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    except requests.RequestException as e:
        print(f"  下载失败: {url}, 错误: {e}")


def download_mathjax_fonts():
    """Downloads all required MathJax font files."""
    print("\n--- 开始下载 MathJax 字体文件 ---")
    font_base_url = f"https://{DOWNLOAD_CDN}{MATHJAX_BASE_PATH}{FONT_DIR_PATH}"
    for font_file in MATHJAX_FONTS:
        font_url = urljoin(font_base_url, font_file)
        local_font_path = LOCAL_SCRIPTS_DIR / \
            Path(urlparse(font_url).path).relative_to('/')
        if local_font_path.exists():
            print(f"字体已存在，跳过: {local_font_path.name}")
            continue
        download_binary_file(font_url, local_font_path)


def find_and_download_scripts(html_files):
    """Finds all unique MathJax scripts, downloads them, and returns a URL map."""
    print("\n--- 开始扫描并下载 MathJax 脚本 ---")
    all_remote_urls = set()
    for html_file in html_files:
        with open(html_file, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
        scripts = soup.find_all('script', src=re.compile(
            rf"{SOURCE_CDN}/npm/mathjax@3"))
        for script in scripts:
            all_remote_urls.add(script['src'])

    if not all_remote_urls:
        print("未找到任何远程 MathJax 脚本链接。")
        return {}

    url_map = {}
    for url in all_remote_urls:
        path_part = Path(urlparse(url).path).relative_to('/')
        local_path = LOCAL_SCRIPTS_DIR / path_part
        url_map[url] = local_path
        if local_path.exists():
            print(f"脚本已存在，跳过: {local_path.name}")
            continue
        download_text_file(url, local_path)
    return url_map


def update_html_files(html_files, url_map):
    """Updates all HTML files to point to local scripts."""
    print("\n--- 开始更新 HTML 文件 ---")
    for html_file in html_files:
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()

        soup = BeautifulSoup(content, 'html.parser')
        modified = False
        for remote_url, local_path in url_map.items():
            scripts = soup.find_all('script', src=remote_url)
            for script in scripts:
                relative_path = os.path.relpath(
                    local_path, start=html_file.parent)
                relative_path = relative_path.replace('\\', '/')
                if script['src'] != relative_path:
                    print(
                        f"  更新 {html_file.name}: {script['src']} -> {relative_path}")
                    script['src'] = relative_path
                    modified = True

        if modified:
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(str(soup))


def main():
    """Main function to run the localization process."""
    if not HTML_DIR.exists():
        print(f"错误: 目录不存在 -> {HTML_DIR}")
        return

    html_files = list(HTML_DIR.rglob("*.html"))
    if not html_files:
        print(f"在 {HTML_DIR} 中未找到任何 HTML 文件。")
        return

    print(f"找到 {len(html_files)} 个 HTML 文件。")

    # 1. Find, download scripts and get the mapping
    url_to_local_map = find_and_download_scripts(html_files)

    # 2. Download required fonts
    download_mathjax_fonts()

    # 3. Update HTML files with local paths
    if url_to_local_map:
        update_html_files(html_files, url_to_local_map)
    else:
        print("\n没有需要更新的脚本链接。")

    print("\n--- 所有处理完毕！ ---")


if __name__ == "__main__":
    main()
