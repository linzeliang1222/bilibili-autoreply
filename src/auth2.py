#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站扫码登录实现
https://github.com/linzeliang1222/bilibili_autoreply
"""

import qrcode
import time
import json
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlparse, parse_qs

class Auth:
    def __init__(self):
        print("-" * 27)
        print("🔒 哔哩哔哩用户认证模块 ")
        print("-" * 27)
        self.cookies_file = '.cookie'
        self.local_storage_file = '.local-storage'
        self.session_storage_file = '.session-storage'
        self.user_name = None
        self.user_id = None
        chrome_options = Options()
        user_data_dir = os.path.join(os.getcwd(), "chrome_user_data", "session_" + str(os.getpid()))
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--lang=zh-CN")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--mute-audio")
        chrome_options.add_argument("--blink-settings=imagesEnabled=false")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        print("🚀 正在启动 Chrome，请稍后...")
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)
        print("✅ Chrome 启动成功！")

    def get_driver(self):
        return self.driver

    def get_user_name(self):
        return self.user_name

    def get_user_id(self):
        return self.user_id

    def save_user_data(self):
        """保存用户数据"""
        try:
            # 保存 cookie
            cookies = self.driver.get_cookies()
            with open(self.cookies_file, "w", encoding="utf-8") as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            # 保存 localStorage
            local_storage = self.driver.execute_script(
                "var items = {}; for (var i = 0; i < localStorage.length; i++) "
                "{ var key = localStorage.key(i); items[key] = localStorage.getItem(key); } return items;"
            )
            with open(self.local_storage_file, "w", encoding="utf-8") as f:
                json.dump(local_storage, f, ensure_ascii=False, indent=2)
            # 保存 sessionStorage
            session_storage = self.driver.execute_script(
                "var items = {}; for (var i = 0; i < sessionStorage.length; i++) "
                "{ var key = sessionStorage.key(i); items[key] = sessionStorage.getItem(key); } return items;"
            )
            with open(self.session_storage_file, "w", encoding="utf-8") as f:
                json.dump(session_storage, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 保存用户数据失败：{e}")

    def load_cookies(self):
        """加载 Cookie"""
        try:
            if not os.path.exists(self.cookies_file):
                print("❗ 无有效 Cookie 文件存在，跳过加载！")
                return
            with open(self.cookies_file, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            self.driver.delete_all_cookies()
            for cookie in cookies:
                if "domain" in cookie and cookie["domain"].startswith("."):
                    cookie["domain"] = cookie["domain"][1:]
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    print(f"❌ 添加 cookie 失败: {cookie}，原因: {e}")
        except Exception as e:
            raise Exception(f"❌ 加载 Cookie 失败：{e}")

    def load_local_storage(self):
        """加载 LocalStorage"""
        try:
            if not os.path.exists(self.local_storage_file):
                print("❗ 无有效 LocalStorage 文件存在，跳过加载！")
                return
            with open(self.local_storage_file, "r", encoding="utf-8") as f:
                local_storage = json.load(f)
            for key, value in local_storage.items():
                self.driver.execute_script(
                    f"window.localStorage.setItem({json.dumps(key)}, {json.dumps(value)});"
                )
        except Exception as e:
            raise Exception(f"❌ 加载 LocalStorage 失败：{e}")

    def load_session_storage(self):
        """加载 SessionStorage"""
        try:
            if not os.path.exists(self.session_storage_file):
                print("❗ 无有效 SessionStorage 文件存在，跳过加载！")
                return
            with open(self.session_storage_file, "r", encoding="utf-8") as f:
                session_storage = json.load(f)
            for key, value in session_storage.items():
                self.driver.execute_script(
                    f"window.sessionStorage.setItem({json.dumps(key)}, {json.dumps(value)});"
                )
        except Exception as e:
            raise Exception(f"❌ 加载 SessionStorage 失败：{e}")

    def load_user_data(self):
        """加载用户数据"""
        try:
            print("🚀 正在加载用户数据，请稍后...")
            self.driver.get("https://www.bilibili.com")
            self.load_cookies()
            self.driver.refresh()
            self.load_local_storage()
            self.load_session_storage()
            self.driver.refresh()
            # 检查用户是否登录
            if self.check_status():
                print("✅ 用户数据加载成功～")
                return True
            return False
        except Exception as e:
            raise Exception(f"❌ 加载用户数据失败：{e}")
    
    def get_qrcode_info(self):
        """获取登录二维码"""
        try:
            self.driver.get("https://passport.bilibili.com/login")
            qrcode_element = self.driver.find_element(By.XPATH, '//*[@id="app-main"]/div/div[2]/div[1]/div[2]/div[1]/div')
            qrcdoe_url = qrcode_element.get_attribute("title")
            if qrcdoe_url:
                parsed_url = urlparse(qrcdoe_url)
                params = parse_qs(parsed_url.query)
                qrcode_key = params.get("qrcode_key", [None])[0]
                print("✅ 获取二维码成功\n")
                return qrcdoe_url, qrcode_key
            else:
                raise Exception("❌ 获取二维码失败：未找到二维码 URL")
        except Exception as e:
            raise Exception(f"❌ 获取二维码时发生错误：{e}")
    
    def show_qrcode(self, qr_url):
        """在终端显示二维码"""
        qr = qrcode.QRCode(version=1, box_size=1, border=1)
        qr.add_data(qr_url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)
        print("\n📱 ↑ ↑ ↑ 请使用哔哩哔哩客户端扫描上方二维码登录 ↑ ↑ ↑")
        print("⏰ 二维码有效期为 3 分钟～")
    
    def check_qrcode_status(self, qrcode_key):
        """检查二维码登录状态"""
        self.driver.get("https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key=" + qrcode_key)
        json_text = self.driver.find_element("tag name", "pre").text
        return json.loads(json_text)
    
    def qrcode_login(self):
        """二维码登录"""
        print("🚀 开始扫码登录...")
        qrcode_url, qrcode_key = self.get_qrcode_info()
        self.show_qrcode(qrcode_url)
        while True:
            response_data = self.check_qrcode_status(qrcode_key)
            try:
                code = response_data['data']['code']
                message = response_data['data'].get('message', '')
                if code == 0:
                    print("🎉 登录成功！")
                    self.save_user_data()
                    return True
                elif code == 86101:
                    print("⏳ 等待扫码中...", end='\r')
                    time.sleep(2)
                elif code == 86090:
                    print("📱 已扫码，请在手机上确认登录～", end='\r')
                    time.sleep(2)
                elif code == 86038:
                    print("💩 二维码已过期，请重新登录！")
                    return False
                else:
                    print(f"❌ 登录失败：{message} (code: {code})")
                    return False
            except Exception as e:
                print(f"❌ 解析登录状态时发生错误：{e}")
                return False

    def check_status(self):
        """检查用户是否登录成功"""
        print("🔍 检查用户是否登录成功...")
        self.driver.get("https://api.bilibili.com/x/web-interface/nav")
        json_text = self.driver.find_element("tag name", "pre").text
        data = json.loads(json_text)
        if data['code'] == 0:
            user_data = data['data']
            if user_data.get('isLogin'):
                self.user_name = user_data.get('uname')
                self.user_id = user_data.get('mid')
                print(f"👤 当前登录用户：{self.user_name}({self.user_id})")
                return True
        print("❌ 当前用户未登录！")
        return False
    
    def login(self):
        """主登录方法"""
        if self.load_user_data():
            return True
        else:
            try:
                os.remove(self.cookies_file)
                os.remove(self.session_storage_file)
                os.remove(self.local_storage_file)
            except:
                pass
        if self.qrcode_login():
            print("🎉 登录成功～")
            return True
        else:
            print("❌ 登录失败！")
            return False

def main():
    """主函数"""
    auth_client = Auth()
    if auth_client.login():
        print("登录成功后操作...")
    else:
        print("登录失败后操作...")

if __name__ == "__main__":
    main()
