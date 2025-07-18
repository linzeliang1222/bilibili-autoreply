#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站扫码登录实现
支持自动刷新 Cookie
https://github.com/linzeliang1222/bilibili_autoreply
"""

import binascii
import requests
import qrcode
import time
import json
import os
from lxml import etree
from datetime import datetime
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA

key = RSA.importKey('''\
-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDLgd2OAkcGVtoE3ThUREbio0Eg
Uc/prcajMKXvkCKFCWhJYJcLkcM2DKKcSeFpD/j6Boy538YXnR6VhcuUJOhH2x71
nzPjfdTcqMz7djHum0qSZA0AyCBDABUqCrfNgCiJ00Ra7GmRj+YCK1NJEuewlb40
JNrRuoEUXpabUzGB8QIDAQAB
-----END PUBLIC KEY-----''')

class Auth:
    def __init__(self):
        self.userdata_file = '.userdata'
        self.refresh_token_file = '.refresh_token'
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.bilibili.com/'
        })
        
    def load_userdata(self):
        """加载本地用户数据"""
        try:
            print("🚀 开始加载本地用户数据...")
            userdata = self.get_userdata()
            if userdata:
                for name, value in userdata.items():
                    self.session.cookies.set(name, value, domain='.bilibili.com', path='/')
                print("✅ 本地用户数据加载成功～")
                return True
            else:
                print("❗ 本地用户数据不存在！")
                return False
        except Exception as e:
            print(f"❌ 本地用户数据加载失败：{e}")
            return False

    def auto_refresh_cookie(self):
        print("🚧 正在自动刷新 Cookie...")
        hash_value = self.get_correspond_path()
        url = "https://www.bilibili.com/correspond/1/" + hash_value
        response = self.session.get(url)
        tree = etree.HTML(response.text)
        result = tree.xpath("//div[@id='1-name']/text()")
        if result:
            try:
                refresh_csrf = result[0].strip()
                self.refresh_cookie(refresh_csrf)
            except Exception as e:
                print(f"❌ 自动刷新 Cookie 失败：{e}")
                return False
            print("✅ 自动刷新 Cookie 成功...")
            return True
        else:
            print("❌ 解析获取 refresh_csrf 失败！")
            return False

    def refresh_cookie(self, refresh_csrf):
        url = "https://passport.bilibili.com/x/passport-login/web/cookie/refresh"
        data = {
            "csrf": self.get_userdata()['bili_jct'],
            "refresh_csrf": refresh_csrf,
            "source": "main_web",
            "refresh_token": self.get_refresh_token()
        }
        response = self.session.post(url, data=data)
        data = response.json()
        if data["code"] == 0 and data["data"]["refresh_token"]:
            refresh_token_old = self.get_refresh_token()
            self.save_userdata()
            self.save_refresh_token(data["data"]["refresh_token"])
            self.load_userdata()
            # 确认刷新，使原 Cookie 失效
            self.confirm_refresh(refresh_token_old)
            return True
        else:
            raise Exception(f'❌ 刷新 Cookie 失败：{data}')

    def confirm_refresh(self, refresh_token_old):
        """确认刷新 Cookie"""
        url = "https://passport.bilibili.com/x/passport-login/web/confirm/refresh"
        data = {
            "csrf": self.get_userdata()['bili_jct'], 
            "refresh_token": refresh_token_old
        }
        response = self.session.post(url, data=data)
        data = response.json()
        if data['code'] != 0:
            raise Exception(f'❌ 确认刷新 Cookie 失败：{data}')

    def get_correspond_path(self):
        ts = round(time.time() * 1000)
        cipher = PKCS1_OAEP.new(key, SHA256)
        encrypted = cipher.encrypt(f'refresh_{ts}'.encode())
        return binascii.b2a_hex(encrypted).decode()

    def save_refresh_token(self, refresh_token):
        """保存刷新令牌"""
        try:
            with open(self.refresh_token_file, 'w', encoding='utf-8') as f:
                f.write(refresh_token)
        except Exception as e:
            raise Exception(f"❌ 保存 refresh_token 失败：{e}")

    def get_refresh_token(self):
        """获取刷新令牌"""
        try:
            with open(self.refresh_token_file, 'r', encoding='utf-8') as f:
                refresh_token = f.read().strip()
            return refresh_token
        except Exception as e:
            print(f"❌ 获取 refresh_token 失败：{e}")
            return None

    def get_userdata(self):
        """获取用户数据"""
        try:
            if os.path.exists(self.userdata_file):
                with open(self.userdata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"❌ 获取用户数据失败：{e}")
            return None

    def save_userdata(self):
        """保存用户数据"""
        try:
            sess_data = self.session.cookies.get("SESSDATA")
            user_id = self.session.cookies.get("DedeUserID")
            ck_md5 = self.session.cookies.get("DedeUserID__ckMd5")
            bili_jct = self.session.cookies.get("bili_jct")
            sid = self.session.cookies.get("sid")
            userdata = {
                "SESSDATA": sess_data,
                "DedeUserID": user_id,
                "bili_jct": bili_jct,
                "DedeUserID__ckMd5": ck_md5,
                "sid": sid,
            }
            with open(self.userdata_file, 'w', encoding='utf-8') as f:
                json.dump(userdata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise Exception(f"❌ 保存用户数据失败：：{e}")
    
    def get_qrcode(self):
        """获取登录二维码"""
        try:
            url = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
            response = self.session.get(url)
            data = response.json()
            if data['code'] == 0:
                qr_url = data['data']['url']
                qrcode_key = data['data']['qrcode_key']
                print("✅ 获取二维码成功\n")
                return qr_url, qrcode_key
            else:
                print(f"❌ 获取二维码失败：{data}")
                return None, None
        except Exception as e:
            print(f"❌ 获取二维码时发生错误：{e}")
            return None, None
    
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
        url = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"
        params = {'qrcode_key': qrcode_key}
        response = self.session.get(url, params=params)
        return response
    
    def qrcode_login(self):
        """二维码登录"""
        print("🚀 开始扫码登录...")
        qr_url, qrcode_key = self.get_qrcode()
        self.show_qrcode(qr_url)
        while True:
            response = self.check_qrcode_status(qrcode_key)
            if not response:
                time.sleep(2)
                continue
            try:
                data = response.json()
                code = data['data']['code']
                message = data['data'].get('message', '')
                if code == 0:
                    print("🎉 登录成功！")
                    self.save_userdata()
                    self.save_refresh_token(data['data']['refresh_token'])
                    return True
                elif code == 86101:
                    print("⏳ 等待扫码中...", end='\r')
                    time.sleep(2)
                elif code == 86090:
                    print("📱 已扫码，请在手机上确认登录～", end='\r')
                    time.sleep(2)
                elif code == 86038:
                    print("❗ 二维码已过期，请重新登录！")
                    return False
                else:
                    print(f"❌ 登录失败：{message} (code: {code})")
                    return False
            except Exception as e:
                print(f"❌ 解析登录状态时发生错误：{e}")
                return False
    
    def print_user_info(self):
        """打印用户信息"""
        try:
            url = "https://api.bilibili.com/x/web-interface/nav"
            response = self.session.get(url)
            data = response.json()
            if data['code'] == 0 and data['data']['isLogin']:
                user_data = data['data']
                print(f"👤 当前登录用户：{user_data.get('uname')}({user_data.get('mid')})")
                return True
            else:
                print("❌ 未登录或登录已过期！")
                return False
        except Exception as e:
            print(f"❌ 检查登录状态失败：{e}")
            return False

    def get_user_info(self):
        """获取用户信息"""
        try:
            url = "https://api.bilibili.com/x/web-interface/nav"
            response = self.session.get(url)
            data = response.json()
            if data['code'] == 0 and data['data']['isLogin']:
                user_data = data['data']
                return user_data.get('uname'), user_data.get('mid')
            else:
                print("❌ 未登录或登录已过期！")
                return None, None
        except Exception as e:
            print(f"❌ 检查登录状态失败：{e}")
            return None, None

    def check_cookie(self):
        """检查 Cookie，过期自动刷新"""
        print("🚀 开始检查 Cookie 是否有效...")
        url = "https://passport.bilibili.com/x/passport-login/web/cookie/info"
        params = {'csrf': self.get_userdata()['bili_jct']}
        response = self.session.get(url, params=params)
        data = response.json()
        if data['code'] == 0:
            if data['data']['refresh'] == False:
                print("✅ 当前 Cookie 有效～")
                return True
            else:
                print("❌ 当前 Cookie 无效！")
                return self.auto_refresh_cookie()
        print("❌ Cookie 检查异常，需要重新登录：", data)
        return False
    
    def login(self):
        """主登录方法"""
        print("-" * 27)
        print("🔒 哔哩哔哩用户认证模块 ")
        print("-" * 27)
        if self.load_userdata():
            if self.check_cookie() == False:
                os.remove(self.userdata_file)
                os.remove(self.refresh_token_file)
                print("🤯 准备重新登录...")
            elif self.print_user_info():
                return True
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
