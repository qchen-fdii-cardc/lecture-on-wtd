import os
import re
import requests
from pathlib import Path
from urllib.parse import urlparse

# --- Configuration ---
HTML_DIR = Path('modules/_build/html')
LOCAL_SCRIPTS_DIR = HTML_DIR / '_static' / 'scripts'
SOURCE_CDN = "cdn.jsdelivr.net"
DOWNLOAD_CDN = "cdn.jsdelivr.net"  # "s4.zstatic.net"

# --- Helper Functions ---


def download_text_file(url, local_path):
    """Downloads a text file (like .js) from a URL to a local path."""
    try:
        # Handle protocol-relative URLs just in case, though the target is specific
        download_url = url
        if download_url.startswith('//'):
            download_url = 'https:' + download_url

        # Use the specified download mirror
        download_url = download_url.replace(SOURCE_CDN, DOWNLOAD_CDN)

        print(f"正在下载脚本: {download_url} -> {local_path}")
        response = requests.get(download_url, timeout=15)
        response.raise_for_status()
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_text(response.text, encoding='utf-8')
        return True
    except requests.RequestException as e:
        print(f"  下载失败: {download_url}, 错误: {e}")
        return False


def process_html_files(html_files):
    """
    Scans HTML files for a specific Mermaid CDN URL string, downloads it,
    and replaces the string with a local relative path.
    """
    print("\n--- 开始扫描并替换 Mermaid URL 字符串 ---")

    # The specific URL string we are looking for inside JavaScript code
    # This pattern will match http://, https://, or //
    target_url_pattern = re.compile(
        r"(?:https?:)?//cdn\.jsdelivr\.net/npm/mermaid/dist/mermaid\.min\.js"
    )

    # Cache for downloaded URLs to avoid re-downloading: {remote_url: local_path}
    downloaded_url_map = {}

    total_files_modified = 0

    for html_file in html_files:
        content = html_file.read_text(encoding='utf-8')

        match = target_url_pattern.search(content)
        if not match:
            continue

        remote_url = match.group(0)
        local_path = None

        if remote_url in downloaded_url_map:
            local_path = downloaded_url_map[remote_url]
        else:
            # URL found for the first time, attempt to download it
            # Reconstruct a full URL for parsing, assuming https if protocol is missing
            full_url_for_parse = remote_url if remote_url.startswith(
                'http') else 'https:' + remote_url
            path_part = Path(
                urlparse(full_url_for_parse).path).relative_to('/')

            potential_local_path = LOCAL_SCRIPTS_DIR / path_part

            if potential_local_path.exists():
                print(f"脚本已存在，跳过下载: {potential_local_path.name}")
                local_path = potential_local_path
            elif download_text_file(remote_url, potential_local_path):
                local_path = potential_local_path

            # Cache the result (even if download failed, represented by None)
            downloaded_url_map[remote_url] = local_path

        # If the file was downloaded and a local path is available, perform replacement
        if local_path:
            # Calculate relative path from the current HTML file to the local script
            relative_path = os.path.relpath(
                local_path, start=html_file.parent).replace('\\', '/')

            # Replace the remote URL string with the calculated relative path
            if remote_url in content:
                new_content = content.replace(remote_url, relative_path)
                if new_content != content:
                    print(
                        f"  更新 {html_file.name}: 替换 {remote_url} -> {relative_path}")
                    html_file.write_text(new_content, encoding='utf-8')
                    total_files_modified += 1


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

    # Process all HTML files using the text-based search and replace method
    process_html_files(html_files)

    print("\n--- 所有处理完毕！ ---")


if __name__ == "__main__":
    main()
