import requests
import os
import zipfile
import subprocess
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from webdriver_manager.chrome import ChromeDriverManager

def get_latest_chromedriver_version():
    """從 Chrome for Testing 網站取得最新的 ChromeDriver 版本。"""
    url = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data["channels"]["Stable"]["version"], data["channels"]["Stable"]["downloads"]["chromedriver"]
    else:
        raise Exception("無法取得最新 ChromeDriver 版本資訊。")

def download_chromedriver(download_url, download_path="chromedriver"):
    """下載指定的 ChromeDriver。"""
    if not os.path.exists(download_path):
        os.makedirs(download_path)
    
    file_name = os.path.join(download_path, download_url.split("/")[-1])
    
    # 下載檔案
    print(f"正在下載 ChromeDriver，URL: {download_url} ...")
    response = requests.get(download_url, stream=True)
    if response.status_code == 200:
        with open(file_name, 'wb') as file:
            for chunk in response.iter_content(chunk_size=1024):
                file.write(chunk)
        print(f"ChromeDriver 下載完成，儲存於: {file_name}")
    else:
        raise Exception("下載失敗，請確認 URL 是否正確。")

    return file_name

def extract_chromedriver(file_path, extract_to="chromedriver"):
    """解壓縮下載的 ChromeDriver。"""
    if file_path.endswith(".zip"):
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        print(f"ChromeDriver 已解壓縮至: {extract_to}")
    else:
        raise Exception("僅支援 ZIP 格式的檔案解壓縮。")

def close_chrome():
    """關閉 Chrome 瀏覽器"""
    if os.name == "nt":  # Windows
        subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif os.name == "posix":  # macOS / Linux
        subprocess.run(["pkill", "chrome"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("Chrome 已關閉")

def restart_chrome():
    """重新啟動 Chrome 並恢復上次的 session"""
    time.sleep(2)  # 等待 2 秒再啟動
    print("重新啟動 Chrome...")

    if os.name == "nt":  # Windows
        subprocess.run(["start", "chrome", "--restore-last-session"], shell=True)
    elif os.name == "posix":  # macOS / Linux
        subprocess.Popen(["google-chrome", "--restore-last-session"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("Chrome 已重新啟動！")

def auto_update_chrome():
    """啟動 Chrome 並檢查更新"""
    chrome_options = Options()
    chrome_options.add_argument("--remote-allow-origins=*")  # 避免跨源問題
    chrome_options.add_argument("--start-maximized")  # 最大化窗口
    
    # 使用 WebDriver Manager 自動下載和配置最新版本的 ChromeDriver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        # 打開 Chrome 的幫助頁面
        driver.get("chrome://settings/help")
        print("已導航到 chrome://settings/help")

        # 等待頁面加載
        time.sleep(5)

    except Exception as e:
        print(f"自動更新失敗: {e}")

    finally:
        # 關閉瀏覽器
        driver.quit()
        print("任務完成，瀏覽器已關閉。")

def main():
    """執行整合任務：下載 ChromeDriver, 檢查更新, 重啟 Chrome"""
    try:
        # 取得最新版本的下載資訊
        version, downloads = get_latest_chromedriver_version()
        print(f"最新 ChromeDriver 版本為: {version}")
        
        # 針對當前平台選擇對應的下載連結
        platform = os.name
        if platform == "nt":  # Windows
            driver_info = next(item for item in downloads if "win64" in item["url"])
        elif platform == "posix" and os.uname().sysname == "Linux":
            driver_info = next(item for item in downloads if "linux64" in item["url"])
        elif platform == "posix" and os.uname().sysname == "Darwin":
            driver_info = next(item for item in downloads if "mac-x64" in item["url"])
        else:
            raise Exception("未支援的平台。")
        
        download_url = driver_info["url"]
        downloaded_file = download_chromedriver(download_url)
        extract_chromedriver(downloaded_file)
        
        # 下載並安裝最新 ChromeDriver 完成後，檢查更新並重啟瀏覽器
        auto_update_chrome()
        close_chrome()
        restart_chrome()
        
        print("ChromeDriver 更新完成並重啟瀏覽器。")
    except Exception as e:
        print(f"發生錯誤: {e}")

if __name__ == "__main__":
    main()