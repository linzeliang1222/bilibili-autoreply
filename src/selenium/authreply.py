import os
import time
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from auth import Auth

# 回复频率（单位：分钟）
frequency = 3

# 回复话术
follow_user_reply_template = "发过去了，没收到就私我【校招】，再次发给你"
not_follow_user_reply_template = "麻烦关注一下哈，不然收不到消息～"

# 认证
driver = None
username = None
auth_client = Auth()
if auth_client.login():
    username = auth_client.get_user_name()
    driver = auth_client.get_driver()
else:
    raise Exception("💔 未登录成功！")

# 脚本开始
input_time_str = input("请输入开始扫描的时间，默认使用当前时间(yyyy-MM-dd HH:mm:ss): ").strip()
if input_time_str:
    try:
        # 如果用户只输入了 "YYYY-MM-DD HH:MM:SS"，则自动添加当前的微秒部分
        if len(input_time_str) == 19:  # "YYYY-MM-DD HH:MM:SS" 长度为 19
            now_micro = datetime.now().microsecond
            input_time_str = input_time_str + f".{now_micro:06d}"
        last_seen_timestamp = datetime.strptime(input_time_str, "%Y-%m-%d %H:%M:%S.%f")
        print(f"使用输入的时间：{last_seen_timestamp}")
    except Exception as e:
        print(f"解析时间失败，使用当前时间，错误信息：{e}")
        last_seen_timestamp = datetime.now()
else:
    last_seen_timestamp = datetime.now()

# 存储已回复过的评论（采用“用户mid-评论时间”的组合作为标识，同一用户多次评论也会分别记录）
replied_comments = set()
# 排除回复的用户名，默认不回复自己
exclude_username = username

# 打开评论页面
print("正在打开评论页面...")
driver.get("https://member.bilibili.com/platform/comment/article")

def parse_comment_time(time_str):
    """
    将评论时间字符串解析为 datetime 对象。
    示例格式：'2025-03-25 21:27:38'
    """
    try:
        return datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
    except Exception as e:
        print(f"解析时间失败: '{time_str}' -> {e}")
        return None

def get_comment_identifier(comment):
    """
    获取评论标识，采用用户头像的 mid 与评论时间组合，保证同一用户多次评论也能分别回复。
    """
    try:
        avatar = comment.find_element(By.XPATH, ".//a[contains(@class, 'user-avatar')]")
        mid = avatar.get_attribute("mid")
        time_element = comment.find_element(By.XPATH, ".//div[contains(@class, 'ci-action')]//span[@class='date']")
        time_str = time_element.text.strip()
        return f"{mid}-{time_str}"
    except Exception:
        return None

def is_comment_replied(comment):
    """
    判断此评论是否已回复过。
    """
    cid = get_comment_identifier(comment)
    return cid in replied_comments if cid else False

def get_follow_status(comment):
    """
    从评论中查找关注状态，查找 ci-title 中的 relation-label，
    如果有显示（style 中不包含 "display: none"）且有文本，则返回该文本，否则返回空字符串。
    """
    try:
        ci_title = comment.find_element(By.XPATH, ".//div[contains(@class, 'ci-title')]")
        labels = ci_title.find_elements(By.XPATH, ".//span[contains(@class, 'relation-label')]")
        for label in labels:
            style = label.get_attribute("style") or ""
            text = label.text.strip()
            if "display: none" not in style and text:
                return text
        return ""
    except Exception:
        return ""

def has_reply_tag(comment):
    """
    判断评论的标题区域是否包含回复标签，
    检查是否有 <span class="ci-title-split">回复</span>，
    如果存在则说明该评论已为回复，不需要再次回复。
    """
    try:
        ci_title = comment.find_element(By.XPATH, ".//div[contains(@class, 'ci-title')]")
        reply_tags = ci_title.find_elements(By.XPATH, ".//span[contains(@class, 'ci-title-split')]")
        for tag in reply_tags:
            if tag.text.strip() == "回复":
                return True
        return False
    except Exception:
        return False

def reply_to_comment(comment):
    """
    执行回复操作：
      - 如果评论的用户名等于排除用户名，则跳过回复；
      - 根据关注状态决定回复内容：
           如果 follow_status 在 ["已关注", "粉丝"] 中，则回复 "发你啦！"，否则回复 "关注一下哈，不然发不过去"；
      - 点击回复链接、输入回复内容、点击提交成功后，将该评论标识记录到 replied_comments 中。
    """
    try:
        user_avatar = comment.find_element(By.XPATH, ".//a[contains(@class, 'user-avatar')]")
        username = user_avatar.get_attribute("card") or user_avatar.text.strip()
    except Exception:
        username = "未知用户"

    if exclude_username and username == exclude_username:
        print(f"跳过用户 {username}（排除回复）")
        return False

    # 已经回复过的评论跳过
    if is_comment_replied(comment):
        print(f"评论 {username} 已回复，跳过")
        return False

    follow_status = get_follow_status(comment)
    if follow_status in ["已关注", "粉丝"]:
        reply_content = follow_user_reply_template
    else:
        reply_content = not_follow_user_reply_template

    print(f"准备回复用户：{username}，回复内容：{reply_content}")

    try:
        # 点击回复链接，查找包含文字 "回复" 的链接元素
        reply_link = comment.find_element(By.XPATH, ".//span[contains(@class, 'reply action')]/a[text()='回复']")
        reply_link.click()
        time.sleep(1)  # 等待回复框出现
    except Exception as e:
        print(f"点击回复按钮失败：{e}")
        return False

    try:
        # 找到回复输入框（textarea），清空后输入回复内容
        reply_box = comment.find_element(By.XPATH, ".//div[contains(@class, 'reply-wrap')]//textarea")
        reply_box.clear()
        reply_box.send_keys(reply_content)
    except Exception as e:
        print(f"无法找到回复输入框：{e}")
        return False

    try:
        # 找到提交回复的按钮，查找按钮内包含文字 "发表回复"
        submit_btn = comment.find_element(By.XPATH, ".//div[contains(@class, 'reply-wrap')]//button[.//span[text()='发表回复']]")
        submit_btn.click()
        print(f"已成功回复 {username}")
        cid = get_comment_identifier(comment)
        if cid:
            replied_comments.add(cid)
        time.sleep(1)
        return True
    except Exception as e:
        print(f"点击提交按钮失败：{e}")
        return False

def process_current_page():
    """
    扫描当前页所有评论：
      - 对每条评论解析时间（格式：YYYY-MM-DD HH:MM:SS）
      - 如果评论未回复（即不包含回复标签且未记录在 replied_comments 中），则进行回复
      - 对于时间晚于 last_seen_timestamp 的评论（即本轮内真正新出现的评论），更新页面的最大时间
      - 返回一个二元组 (page_has_eligible, page_max_time)
        其中 page_has_eligible 表示本页是否有符合回复条件的评论（即有回复动作），
        page_max_time 为本页中所有新回复评论的最大时间（不更新全局），旧评论则不参与更新
    """
    comment_items = driver.find_elements(By.XPATH, "//div[contains(@class, 'comment-list-item')]")
    print("当前加载评论数量：", len(comment_items))
    page_has_eligible = False
    page_max_time = last_seen_timestamp
    for comment in comment_items:
        try:
            time_element = comment.find_element(By.XPATH, ".//div[contains(@class, 'ci-action')]//span[@class='date']")
            time_str = time_element.text.strip()

            if not time_str:
                print("调试：未获取到时间文本，元素内容：", time_element.get_attribute("outerHTML"))
                continue
            comment_time = parse_comment_time(time_str)
            if comment_time is None:
                continue
        except Exception as e:
            print("解析评论时间异常：", e)
            continue

        # 如果评论时间不大于 last_seen_timestamp，则跳过（即只处理之后产生的评论）

        if comment_time <= last_seen_timestamp:
            continue

        # 如果此评论发布时间晚于上次记录的最新时间，则将其视为新评论，用于更新会话内最大时间
        if comment_time > last_seen_timestamp and comment_time > page_max_time:
            page_max_time = comment_time

        if has_reply_tag(comment):
            print("评论包含回复标签，视为已回复，跳过回复")
            continue

        if not is_comment_replied(comment):
            if reply_to_comment(comment):
                page_has_eligible = True

    return page_has_eligible, page_max_time

def click_next_page():
    """
    点击下一页按钮，xpath: //li[contains(@class, 'bcc-pagination-next')]
    """
    try:
        next_page_btn = driver.find_element(By.XPATH, "//li[contains(@class, 'bcc-pagination-next')]")
        next_page_btn.click()
        time.sleep(3)  # 等待页面加载
        return True
    except Exception as e:
        print("点击下一页失败：", e)
        return False

def process_session():
    """
    单次扫描会话：
      - 从当前页面开始，依次扫描所有评论，尝试回复所有未回复的评论
      - 对每一页，收集新回复评论的最大时间（page_max_time），用于更新全局 last_seen_timestamp
      - 如果当前页无符合回复条件的评论，则进行一次容错扫描（点击下一页再检测一次）
      - 当容错页面仍无符合回复条件的评论时结束本轮会话扫描，
        最后将本会话中新回复的最大评论时间更新到全局 last_seen_timestamp（旧未回复评论将会在下次会话中继续处理）
    """
    global last_seen_timestamp
    session_max_time = last_seen_timestamp
    print("当前 last_seen_timestamp：", last_seen_timestamp)
    while True:
        page_replied, page_max_time = process_current_page()

        if page_max_time > session_max_time:
            session_max_time = page_max_time

        if page_replied:
            # 当前页有符合条件回复的评论，直接点击下一页继续扫描
            if not click_next_page():
                print("下一页按钮不存在，结束本轮会话扫描")
                break
        else:
            # 当前页无符合条件评论，进行一次容错扫描：点击下一页再检测一次
            print("当前页面无符合回复条件的评论，进行容错扫描下一页")
            if not click_next_page():
                print("下一页按钮不存在，结束本轮会话扫描")
                break
            fault_page_replied, fault_page_max_time = process_current_page()
            if fault_page_max_time > session_max_time:
                session_max_time = fault_page_max_time
            if fault_page_replied:
                if not click_next_page():
                    print("无法点击下一页，结束本轮会话扫描")
                    break
            else:
                print("容错扫描页面无符合回复条件的评论，本轮会话扫描结束")
                break

    print("更新 last_seen_timestamp 为：", session_max_time)
    last_seen_timestamp = session_max_time

def main_loop():
    """
    主循环：每隔 frequency 分钟刷新页面，启动一次新的会话扫描
    """
    while True:
        driver.get("https://member.bilibili.com/platform/comment/article")
        time.sleep(3)
        print(f"----------> [{datetime.now()}] 开始新一轮检测新评论...")
        process_session()
        print(f"本轮检测结束，等待 {frequency} 分钟后再次检测。")
        time.sleep(frequency * 60)

if __name__ == "__main__":
    try:
        main_loop()
    finally:
        driver.quit()
