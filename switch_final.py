#encoding: utf-8
# XS724EM - 24-Port 10-Gigabit/Multi-Gigabit Ethernet Smart Managed Plus Switch
import os
import sys
import time
import ctypes
import shutil
import selenium
import subprocess
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from os import listdir
from os.path import isfile, isdir, join
from datetime import datetime
from multiprocessing import Process
from signal import signal
from signal import SIGTERM
import logging
import tkinter as tk
from tkinter import TclError

from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt


http_username = "admin"
http_password = "admin"

wan_ip = '192.168.100.1'
switch_password = "Asus#1234"
dut_url = "http://192.168.50.1/"
dut_aiprotection = "http://www.asusrouter.com/AiProtection_WebProtector.asp"
switch_url = "http://192.168.1.11/"
adv_8021q_url = switch_url + "iss/specific/Cf8021q.html?Gambit=mkfjffjfefjjfciffcobfjjjjfefggififjg"
index_url = switch_url+"index.asp"

logging.basicConfig(level=logging.INFO, format="[%(asctime)s - %(levelname)s] - %(message)s")
logger = logging.getLogger()

#Default Tag UntagS使用
''' 
default : portImage remImg
tag : portImage        tagImg
Untag: portImage  untImg
'''

# target_states = {
#     "3": "untImg",
#     "5": "unTImg"
# }
VLAN_ID2_target_states = {
    "4": "remImg",
    "5": "untImg",  # 編號5對應狀態untImg
    "6": "remImg",
    "7": "untImg",  # 編號7對應狀態tagImg
    "8": "remImg",
    "9": "untImg",  # 編號5對應狀態untImg
    "10": "remImg",
    "11": "untImg"  # 編號7對應狀態tagImg
}

tag_port = {
    "1": "tagImg",
    "5": "tagImg",  # 編號5對應狀態untImg
    "7": "tagImg" 
}
untag_port = {
    "1": "untImg",
    "5": "untImg",  # 編號5對應狀態untImg
    "7": "untImg" 
}

def print_msg(msg):
    logging.info(msg)
    show_message(msg)

def countdown(seconds):
    for i in range(seconds, 0, -1):
        print_msg(f"倒數: {i}秒")
        time.sleep(1)  # 暫停 1 秒

def show_message(message):
    try:
        label.config(text=message)
    except TclError:
        print("Label widget is no longer available.")

def btn_apply(driver):
    try:
        driver.switch_to.default_content()
        apply_button = driver.find_element(By.ID, "btn_Apply")
        apply_button.click()
        print_msg("Click 'Apply'")
        sleep(5)
    except:
        print_msg("Cannot click 'Apply'. Stop test.")
        sleep(5)


def Get_Key_From_Value(d, val):
    print('Get_Key_From_Value: %s, %s' %(d, val))
    for key, value in d.items():
        #print('%s, %s' %(key, value))
        if value.upper().replace(' ','_').replace('-','_') == val.upper().replace(' ','_').replace('-','_'):
            return key

def Ping(address, retry, success):
    #print('ping ' + address + '=')
    #return True
    i = 0
    ok = 0
    if len(address) == 0:
        msg = 'No IP, stop ping\n'
        print_msg(msg)
    else:
        cmd = 'ping -n 1 ' + address
        print_msg(cmd)
        while (i < retry):
            try:
                output = subprocess.check_output(cmd)
                #print(output)
                if b'TTL=' in output:
                    ok += 1
                    msg="PING OK"
                    #print_msg(msg)
                else:
                    msg="FAIL"
                    print_msg(msg)
                if ok == success:
                    msg="Ping Success"
                    print_msg(msg)
                    return True
            except subprocess.CalledProcessError as e:
                code = e.returncode
                msg="Ping Error! Re-send again. [ERROR NO]: " + str(code)
                print_msg(msg)
            i += 1
            time.sleep(1)

    return False

def Try_Login(driver):
    print_msg("Try to login")
    show_message("Try to login")
    try:
        element1 = driver.find_element("xpath", "//*[@id=\"Password\"]")
        sleep(1)
        if element1:
            print_msg("Find Password")
            element1 = driver.find_element("xpath", "//*[@id=\"Password\"]")
            element1.send_keys(switch_password);
            sleep(1)
            try:
                driver.find_element("xpath", "//*[@id=\"button_Login\"]").click()
            except:
                print_msg("Can not click Login button.")
            
            error_msg = driver.find_element(By.ID, "login_err_msg")
            # SWITCH 登入出現"Maximum number of sessions reached"時的問題
            if "Maximum number of sessions reached" in error_msg.text:
                print_msg("請關掉SWITCH電源並重新開機")
                show_message("請關掉SWITCH電源並重新開機")
                driver.quit()

            sleep(1)
    except:
        print_msg("Do not need login.")

# 定義檢查並點擊的函數
def check_and_click_button(member, target_state):
    xpath_check = f'.//div[contains(@class, "portImage") and contains(@class, "{target_state}")]'

    # 初始狀態檢查
    def check_state():
        try:
            port_image = member.find_element(By.XPATH, xpath_check)
            return True
        except:
            return False
    
    # 如果初始狀態已經符合目標狀態，則直接打印並返回
    if check_state():
        print(f"Port {member}已經包含 {target_state}，無需點擊！")
        return

    # 點擊並檢查直到達到目標狀態
    while not check_state():
        print_msg(f"Port {member}未包含 {target_state}，點擊並重試...")
        # 點擊按鈕
        member.click()
        print_msg(f"成功點擊按鈕，等待狀態更新...")
        time.sleep(1)  # 等待狀態更新

        if check_state():  # 確認是否達到目標狀態
            print_msg(f"Port {member} 成功切換為 {target_state}！")
        else:
            print_msg(f"Port {member} 未成功切換為 {target_state}！")
            continue  # 若未達到目標狀態，繼續點擊
    print_msg("切換成功")

    

# # VLAN_ID, tag_port, untag_port
# # 2, 1, 3
# # 3, 15, 21
def Set_VLAN(VLAN_ID, tag_port, untag_port):
    try:
        select = Select(driver.find_element("xpath", "//*[@id=\"vlanIdOption\"]"))
        sleep(1)
    except:
        print_msg("Can not find select element: VLAN_ID")

    try:
        # select.select_by_index(VLAN_ID)
        select.select_by_index(1)
        # print_msg(f"Select VID {VLAN_ID}")
        print_msg(f"Select VID {VLAN_ID}")
        sleep(1)
    except:
        # print_msg(f"Can not select VID {VLAN_ID}")
        print_msg(f"Can not select VID")
        sleep(15)
    
    # try:
    #     # tag
    #     for number, tag_port in tag_port.items():
    #         # 根據編號定位到對應的 portMember 元素
    #         xpath_member = f'//div[@class="portMember margin"]//span[text()="{number}"]/..'
    #         member = driver.find_element(By.XPATH, xpath_member)

    #         # 呼叫檢查並點擊函數
    #         check_and_click_button(member, tag_port)
    #     # untag
    #     for number, untag_port in untag_port.items():
    #         # 根據編號定位到對應的 portMember 元素
    #         xpath_member = f'//div[@class="portMember margin"]//span[text()="{number}"]/..'
    #         member = driver.find_element(By.XPATH, untag_port)

    #         # 呼叫檢查並點擊函數
    #         check_and_click_button(member, tag_port)
    # except Exception as e:
    #     print(f"發生錯誤: {e}")

def Set_VLAN():
    try:
        for number, target_state in VLAN_ID2_target_states.items():
            print_msg(f'number:{number}')
            print_msg(f'target_state:{target_state}')
            # 根據編號定位到對應的 portMember 元素
            xpath_member = f'//div[@class="portMember margin"]//span[text()="{number}"]/..'
            member = driver.find_element(By.XPATH, xpath_member)

            # 呼叫檢查並點擊函數
            check_and_click_button(member, target_state)
    except Exception as e:
        print(f"發生錯誤: {e}")

def Get_Value(f_lines, keyword):
    ret = ""
    
    for line in f_lines:
        if keyword in line:
            line_2 = line.replace('\n','')
            splitStr = line_2.split('=')
            ret = splitStr[1]
            break
    #print(ret)
    return ret

def main_test():
    driver.get(dut_url)
    sleep(1)
    print_msg("Try to Login")
    try:
        element1 = driver.find_element("xpath", "//*[@id=\"login_username\"]")
        if element1:
            print_msg("Find login_username")
            element1 = driver.find_element("xpath", "//*[@id=\"login_username\"]")
            print_msg(f'http_username: {http_username}')
            element1.send_keys(http_username)
            element2 = driver.find_element("xpath", "//*[@name=\"login_passwd\"]")
            print_msg(f'http_password: {http_password}')
            element2.send_keys(http_password)
            try:
                driver.find_element("xpath", "//div[@onclick=\"preLogin();\"]").click()
            except:
                print_msg("Do not find login(); try preLogin();")
                try:
                    driver.find_element("xpath", "//div[@onclick=\"preLogin();\"]").click()
                except:
                    print_msg("Can not find Login element!")
    except:
        print_msg("Do not need login.")
    countdown(5)
    driver.get(dut_aiprotection)
    print_msg("成功進到 AiProtection")
    countdown(10)

    element = driver.find_element("xpath", "//*[@id=\"iphone_switch\"]")
    element.click() 

    countdown(40)
    print_msg("Click 'SWITCH' to ON!")
   
def switch_logout():
    print_msg("登出")
    show_message("登出")

    sleep(3)
    driver.get(switch_url)
    sleep(1)
    move = driver.find_element(By.TAG_NAME, 'body')
    move.send_keys(Keys.CONTROL + Keys.HOME)

    element1 = driver.find_element("xpath", "//*[@id=\"Password\"]")
    sleep(1)
    if element1:
        print_msg("Find Password")
        element1 = driver.find_element("xpath", "//*[@id=\"Password\"]")
        element1.send_keys(switch_password)
        sleep(1)
        try:
            driver.find_element("xpath", "//*[@id=\"button_Login\"]").click()
        except:
            print_msg("Can not click Login button.")
        
        try:
            element1 = driver.find_element("xpath", "//*[@id=\"VLAN\"]")
            element1.click()
            print_msg("成功登入")
            show_message("成功登入")
            sleep(3)
            logout_button = driver.find_element(By.ID, "logout")
            logout_button.click()
            print_msg("成功登出")
            show_message("成功登出")
        except:
            print_msg("這個次數登入失敗")
            sleep(5)
            
    return


def monitor_restart(driver, print_msg):
    """監控設備是否正在重啟"""
    while True:
        try:
            element = driver.find_element(By.ID, "popUp_head")
            if "The switch is now restarting. Please wait" in element.text:
                print_msg("The switch is now restarting. Please wait")
                sleep(2)
            else:
                break
        except:
            break

# 重啟NETGEAR
def switch_restart():
    print_msg("重新啟動NETGEAR")
    show_message("重新啟動NETGEAR")
    sleep(3)
    driver.get(switch_url)
    sleep(1)
    move = driver.find_element(By.TAG_NAME, 'body')
    move.send_keys(Keys.CONTROL + Keys.HOME)
    element1 = driver.find_element("xpath", "//*[@id=\"Password\"]")
    sleep(1)
    if element1:
        print_msg("Find Password")
        show_message("Find Password")
        element1 = driver.find_element("xpath", "//*[@id=\"Password\"]")
        element1.send_keys(switch_password)
        sleep(1)
        try:
            driver.find_element("xpath", "//*[@id=\"button_Login\"]").click()
        except:
            print_msg("Can not click Login button.")
    
    # System
    try:
        element1 = driver.find_element("xpath", "//*[@id=\"System\"]")
        element1.click()
        print_msg("Click 'System'")
        show_message("Click 'System'")
        sleep(1)
    except:
        print_msg("Cannot click 'System'. Stop test.")
        sleep(5)
        return
    
    try:
        element1 = driver.find_element("xpath", "//*[@id=\"System_Maintenance\"]")
        element1.click()
        print_msg("Click 'Maintenance'")
        sleep(1)
    except:
        print_msg("Cannot click 'Maintenance'. Stop test.")
        sleep(5)
        return
    
    # 找到 "Device Restart" 按鈕（使用 XPath）
    try:
        restart_button = driver.find_element(By.XPATH, "//a[contains(@href, 'sys_reload.html')]")
        restart_button.click()
        print_msg("Click 'Device Restart'")
        sleep(1)
    except:
        print_msg("Cannot click 'Maintenance'. Stop test.")
        sleep(5)
        return
    
    try:
        driver.switch_to.frame("maincontent")
        sleep(5)
        checkbox = driver.find_element(By.XPATH, "//input[@type='checkbox' and @name='CBox']")
        checkbox.click()
        print_msg("Click 'Check box'")
    except:
        print_msg("Cannot click 'checkbox'. Stop test.")
        sleep(5)
        return
    try:
        driver.switch_to.default_content()
        apply_button = driver.find_element(By.ID, "btn_Apply")
        apply_button.click()
        print_msg("Click 'Apply'")
    except:
        print_msg("Cannot click 'Apply'. Stop test.")
        sleep(5)
        return
    
    monitor_restart(driver, print_msg)
    print_msg("測試結束")

def start():
    show_message("開始測試")
    driver.get(switch_url)
    sleep(1)
    move = driver.find_element(By.TAG_NAME, 'body')
    move.send_keys(Keys.CONTROL + Keys.HOME)
    
    Try_Login(driver)

    try:
        element1 = driver.find_element("xpath", "//*[@id=\"VLAN\"]")
        element1.click()
        print_msg("Click 'VLAN'")
        show_message("Click 'VLAN'")
        sleep(1)
    except:
        print_msg("Cannot click 'VLAN'. Stop test.")
        sleep(5)
        return
    
    try:
        element1 = driver.find_element("xpath", "//*[@id=\"VLAN_802.1Q\"]")
        element1.click()
        print_msg("Click '802.1Q'")
        show_message("Click '802.1Q'")
        sleep(1)
    except:
        print_msg("Cannot click '802.1Q'. Stop test.")
        sleep(5)
        return    

    try:
        element1 = driver.find_element("xpath", "//*[@id=\"f2\"]")
        element1.click()
        print_msg("Click 'Advanced'")
        show_message("Click 'Advanced'")
        sleep(1)
    except:
        print_msg("Cannot click 'Advanced'. Stop test.")
        sleep(5)
        return

    try:
        element1 = driver.find_element("xpath", "/html/body/table/tbody/tr[7]/td/table/tbody/tr/td[1]/table/tbody/tr/td/div/div[3]/div[2]/a/span")
        element1.click()
        print_msg("Click 'VLAN config'")
        show_message("Click 'VLAN config'")
        sleep(3)
    except:
        print_msg("Cannot click 'VLAN'. Stop test.")
        sleep(30)
        return

    try:
        element1 = driver.find_element("xpath", "/html/body/table/tbody/tr[7]/td/table/tbody/tr/td[1]/table/tbody/tr/td/div/div[4]/div[2]/a/span")
        element1.click()
        print_msg("Click 'VLAN membership'")
        show_message("Click 'VLAN membership'")
        sleep(3)
    except:
        print_msg("Cannot click 'VLAN'. Stop test.")
        sleep(30)
        return

    driver.switch_to.frame('maincontent')
    print_msg("Switch to frame")
    time.sleep(2)
#vlanIdOption
#//*[@id="vlanIdOption"]
    test = ['0','1','2']
    VLAN_ID = test[1]
    # Set_VLAN(VLAN_ID, tag_port, untag_port)
    try:
        select = Select(driver.find_element("xpath", "//*[@id=\"vlanIdOption\"]"))
        sleep(1)
    except:
        print_msg("Can not find select element: VLAN_ID")

    try:
        select.select_by_index(1)
        print_msg("Select VID 2")
        show_message("Select VID 2")
        sleep(1)
    except:
        print_msg("Can not select VID 2")
        sleep(15)

    try:
        Set_VLAN()
        # Set_VLAN(1, tag_port, untag_port)
        # Set_VLAN(2, tag_port, untag_port)
    except:
        print_msg("執行失敗")

    btn_apply(driver)
    # driver.switch_to.default_content()
    # try:
    #     apply_button = driver.find_element(By.ID, "btn_Apply")
    #     apply_button.click()
    #     print_msg("Click 'Apply'")
    #     sleep(5)
    # except:
    #     print_msg("Cannot click 'Apply'. Stop test.")
    sleep(15)

    # finally:
    #     driver.quit()

def main_status():
    global label
    global root
    # 藍色狀態列介面
    root = tk.Tk()
    root.overrideredirect(True)  # 移除視窗邊框
    root.attributes('-topmost', True)  # 讓視窗保持在最前
    root.configure(bg='blue')

    # 設定視窗大小
    width, height = 400, 100  # 視窗大小適中
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = screen_width - width - 10  # 靠右 10px 邊距
    y = screen_height - height - 100  # 向上移動，減少 y 的數值，數字越小越靠上
    root.geometry(f'{width}x{height}+{x}+{y}')  # 設定視窗大小和位置

    # 顯示文字的標籤，設置字體和顏色
    label = tk.Label(root, text='', fg='white', bg='blue', font=('Arial', 16, 'bold'))
    label.place(relx=0.5, rely=0.5, anchor='center')  # 設置文字在視窗中央

    # 顯示訊息
    show_message("Hello, world!")

    # start()  # 開始執行 start()
    switch_logout()
    switch_restart()
    root.destroy()  # 關閉藍色狀態列介面
    


def main():
    # 主介面，包含按鈕
    root = tk.Tk()
    root.title("Main Interface")  # 設置主視窗標題

    # 設定視窗大小
    width, height = 300, 150  # 視窗大小適中
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - width) // 2  # 計算螢幕中間的 X 座標
    y = (screen_height - height) // 2  # 計算螢幕中間的 Y 座標
    root.geometry(f'{width}x{height}+{x}+{y}')  # 設定視窗大小和位置

    def on_button_click():
        root.destroy()  # 關閉主介面
        main_status()  # 開啟藍色狀態列介面

    # 創建按鈕，按下後會呼叫 on_button_click()
    start_button = tk.Button(root, text="Start", font=("Arial", 14), command=on_button_click)
    start_button.place(relx=0.5, rely=0.5, anchor='center')  # 按鈕放在視窗中央

    root.mainloop()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Main Interface")  # 設置主視窗標題
        self.setFixedSize(300, 200)  # 設定視窗大小

        # 計算並設定視窗居中
        screen_geometry = QApplication.primaryScreen().geometry()
        window_geometry = self.geometry()
        x = (screen_geometry.width() - window_geometry.width()) // 2
        y = (screen_geometry.height() - window_geometry.height()) // 2
        self.move(x, y)  # 將視窗移動到螢幕正中央

        # 創建垂直布局 (QVBoxLayout)
        self.layout = QVBoxLayout()

        # 創建第一個按鈕，按下後會呼叫 on_button_click()
        self.start_button = QPushButton("Start", self)
        self.start_button.clicked.connect(self.on_button_click)

        # 創建第二個按鈕，按下後會執行其他操作
        self.restart_button = QPushButton("Restart", self)
        self.restart_button.clicked.connect(self.restart_button_click)

        # 將按鈕加入布局中
        self.layout.addWidget(self.start_button)
        self.layout.addWidget(self.restart_button)

        # 設定窗口的布局
        self.setLayout(self.layout)

    def on_button_click(self):
        self.close()  # 關閉主介面
        main_status()  # 開啟藍色狀態列介面
    
    def restart_button_click(self):
        self.close()
        switch_restart()

if __name__ == "__main__":
    now = datetime.now()
    now_time = now.strftime("%Y-%m-%d-%H-%M")
    driver = webdriver.Chrome()
    driver.maximize_window()

    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()  # 顯示視窗
        sys.exit(app.exec())  # 啟動應用程式事件循環，使用 exec() 替代 exec_()
        # switch_logout()
    except:
        print_msg("Error")
        sleep(3)
        driver.quit()
    finally:
        driver.quit()
    # 重啟NETGEAR
        