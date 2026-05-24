import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import urllib3
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
url = "https://jwc.njupt.edu.cn/2026/0522/c1594a302493/page.htm"
resp = requests.get(url, verify=False)
resp.encoding = 'utf-8'
soup = BeautifulSoup(resp.text, 'html.parser')

for a in soup.find_all('a'):
    href = a.get('href')
    if href and href.lower().endswith('.xlsx'):
        print(f"Found: {a.get_text(strip=True)} -> {urljoin(url, href)}")
        if "17-18" in href or "17-18" in a.get_text(strip=True):
            print("Downloading this file...")
            r = requests.get(urljoin(url, href), verify=False)
            with open("test_download.xlsx", "wb") as f:
                f.write(r.content)
            print(f"Downloaded {len(r.content)} bytes.")
            import zipfile
            try:
                with zipfile.ZipFile("test_download.xlsx") as zf:
                    print("Zip test: SUCCESS")
            except Exception as e:
                print(f"Zip test: FAILED - {e}")
