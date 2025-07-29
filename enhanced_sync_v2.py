import os
import requests
import json
import time
import random
import string
from datetime import datetime
from notion_client import Client
from urllib.parse import unquote

# 环境变量配置
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")
WR_COOKIE = os.getenv("WR_COOKIE")

# 初始化Notion客户端
notion = Client(auth=NOTION_TOKEN)

def generate_device_id():
    """生成16位设备ID"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))

def parse_cookie(cookie_str):
    """解析Cookie字符串为字典"""
    cookie_dict = {}
    for item in cookie_str.split(';'):
        item = item.strip()
        if '=' in item:
            key, value = item.split('=', 1)
            cookie_dict[key] = unquote(value)
    return cookie_dict

def get_weread_userid(cookie_dict):
    """从Cookie中提取用户ID"""
    return cookie_dict.get('wr_vid', 'unknown')

def get_book_list(user_id, device_id):
    """获取书架图书列表"""
    url = f"https://i.weread.qq.com/shelf/sync?userVid={user_id}&synckey=0&lectureSynckey=0"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.162 Mobile Safari/537.36",
        "Referer": "https://weread.qq.com/",
        "wr-platform": "android",
        "wr-device-id": device_id,
        "wr-brand": "samsung",
        "wr-model": "SM-G981B",
        "wr-os": "android",
        "wr-os-version": "10",
        "wr-version": "2.22.0",
        "wr-timezone": "Asia/Shanghai",
        "wr-channel": "qq",
        "Cookie": f"wr_vid={user_id}; wr_deviceId={device_id}"  # 关键修改
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        print(f"书架API响应状态: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            return data.get("books", [])
        
        # 打印详细错误信息
        print(f"错误响应内容: {response.text[:200]}")
        if response.status_code == 401:
            print("⚠️ 认证失败! 请检查Cookie是否过期")
        
    except Exception as e:
        print(f"获取书架异常: {str(e)}")
    
    return []

def get_book_notes(book_id, user_id, device_id):
    """获取图书笔记"""
    url = f"https://i.weread.qq.com/book/bookmarklist?bookId={book_id}&userVid={user_id}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.162 Mobile Safari/537.36",
        "Referer": f"https://weread.qq.com/web/reader/{book_id.replace('_', '')}",
        "wr-platform": "android",
        "wr-device-id": device_id,
        "Cookie": f"wr_vid={user_id}; wr_deviceId={device_id}"  # 关键修改
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.json().get("updated", [])
        
        print(f"获取笔记失败: HTTP {response.status_code}")
        print(f"URL: {url}")
        
    except Exception as e:
        print(f"获取笔记异常: {str(e)}")
    
    return []

def sync_to_notion(book_info, notes):
    """同步笔记到Notion"""
    if not notes:
        return 0
        
    success_count = 0
    for note in notes:
        try:
            # 确定笔记类型
            note_type = "笔记" if note.get("abstract") else "划线"
            
            # 创建时间转换
            create_time = datetime.fromtimestamp(note["createTime"])
            
            # 创建Notion页面属性
            properties = {
                "书名": {"title": [{"text": {"content": book_info["title"]}}]},
                "作者": {"rich_text": [{"text": {"content": book_info.get("author", "未知")}}]},
                "阅读日期": {"date": {"start": create_time.strftime("%Y-%m-%d")}},
                "类型": {"select": {"name": note_type}},
                "内容": {"rich_text": [{"text": {"content": note.get("abstract") or note.get("markText", "")}}]},
                "书籍ID": {"rich_text": [{"text": {"content": book_info["bookId"]}}]},
            }
            
            # 创建页面
            notion.pages.create(
                parent={"database_id": DATABASE_ID},
                properties=properties
            )
            success_count += 1
            print(f"已同步: 《{book_info['title']}》- {note_type}")
            time.sleep(0.3)  # 避免请求过快
        except Exception as e:
            print(f"同步失败: {str(e)}")
    
    return success_count

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 微信读书到Notion同步开始 (增强版)")
    print("=" * 60)
    
    # 生成随机设备ID
    device_id = generate_device_id()
    print(f"生成设备ID: {device_id}")
    
    # 解析Cookie
    cookie_dict = parse_cookie(WR_COOKIE)
    user_id = get_weread_userid(cookie_dict)
    print(f"用户ID: {user_id}")
    
    # 获取书架图书
    print("获取书架图书中...")
    books = get_book_list(user_id, device_id)
    
    if not books:
        print("❌ 未获取到书籍信息，请检查日志")
        exit(1)
        
    print(f"获取到 {len(books)} 本书籍")
    
    # 处理每本书的笔记
    total_notes = 0
    for book in books:
        book_id = book["bookId"]
        print(f"处理书籍: 《{book['title']}》")
        notes = get_book_notes(book_id, user_id, device_id)
        if not notes:
            print("  未找到笔记")
            continue
            
        print(f"  找到 {len(notes)} 条笔记")
        synced = sync_to_notion(book, notes)
        total_notes += synced
        time.sleep(1)  # 避免请求过快
    
    print("=" * 60)
    print(f"✅ 同步完成! 共处理 {total_notes} 条笔记")
    print("=" * 60)
