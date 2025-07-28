import os
import requests
from notion_client import Client
from datetime import datetime
import time
import sys

# 环境变量验证
required_envs = ["NOTION_TOKEN", "DATABASE_ID", "WR_COOKIE"]
missing_envs = [var for var in required_envs if not os.getenv(var)]

if missing_envs:
    print(f"❌ 缺少关键环境变量: {', '.join(missing_envs)}")
    sys.exit(1)

# 配置参数
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")
WR_COOKIE = os.getenv("WR_COOKIE")

# 初始化Notion客户端
try:
    notion = Client(auth=NOTION_TOKEN)
    print("✅ Notion客户端初始化成功")
except Exception as e:
    print(f"❌ Notion客户端初始化失败: {str(e)}")
    sys.exit(1)

def fetch_weread_notes():
    """获取微信读书笔记"""
    headers = {
        "Cookie": WR_COOKIE,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        print("⏳ 正在从微信读书获取笔记本列表...")
        response = requests.get(
            "https://i.weread.qq.com/user/notebooks", 
            headers=headers,
            timeout=15
        )
        
        # 检查HTTP状态码
        if response.status_code != 200:
            print(f"❌ 微信读书API请求失败: HTTP {response.status_code}")
            print(f"响应内容: {response.text[:200]}...")
            return []
        
        data = response.json()
        if "books" not in data:
            print("❌ 返回数据中未找到'books'字段")
            print(f"完整响应: {data}")
            return []
            
        print(f"✅ 获取到 {len(data['books'])} 本书的笔记信息")
        return data["books"]
        
    except Exception as e:
        print(f"❌ 获取笔记失败: {str(e)}")
        return []

def process_book_notes(book):
    """处理单本书的笔记"""
    book_id = book["bookId"]
    book_title = book["title"]
    headers = {"Cookie": WR_COOKIE}
    
    try:
        print(f"📖 正在处理书籍: 《{book_title}》")
        res = requests.get(
            f"https://i.weread.qq.com/book/bookmarklist?bookId={book_id}",
            headers=headers,
            timeout=15
        )
        
        if res.status_code != 200:
            print(f"  ❌ 书籍笔记请求失败: HTTP {res.status_code}")
            return []
        
        notes_data = res.json()
        notes = notes_data.get("updated", [])
        
        print(f"  ✅ 找到 {len(notes)} 条笔记")
        processed_notes = []
        
        for note in notes:
            note_type = "笔记" if note.get("abstract") else "划线"
            content = note.get("abstract") or note.get("markText", "")
            
            # 处理可能的空内容
            if not content.strip():
                continue
                
            processed_notes.append({
                "book": book_title,
                "author": book.get("author", "未知"),
                "date": datetime.fromtimestamp(note["createTime"]).strftime("%Y-%m-%d"),
                "content": content,
                "type": note_type,
                "bookId": book_id
            })
            
        return processed_notes
        
    except Exception as e:
        print(f"  ❌ 处理书籍失败: {str(e)}")
        return []

def sync_to_notion(note):
    """同步单条笔记到Notion"""
    try:
        properties = {
            "书名": {"title": [{"text": {"content": note["book"]}}]},
            "作者": {"rich_text": [{"text": {"content": note["author"]}}]},
            "阅读日期": {"date": {"start": note["date"]}},
            "类型": {"select": {"name": note["type"]}},
            "内容": {"rich_text": [{"text": {"content": note["content"]}}]},
            "书籍ID": {"rich_text": [{"text": {"content": note["bookId"]}}]},
        }
        
        notion.pages.create(
            parent={"database_id": DATABASE_ID},
            properties=properties
        )
        print(f"  ✅ 已同步: 《{note['book']}》- {note['type']}")
        return True
        
    except Exception as e:
        print(f"  ❌ 同步失败: {str(e)}")
        return False

if __name__ == "__main__":
    print("="*50)
    print("🚀 开始同步微信读书笔记到Notion")
    print("="*50)
    
    books = fetch_weread_notes()
    if not books:
        print("❌ 未获取到书籍信息，同步终止")
        sys.exit(1)
    
    total_notes = 0
    success_count = 0
    
    for book in books:
        notes = process_book_notes(book)
        if not notes:
            continue
            
        for note in notes:
            total_notes += 1
            if sync_to_notion(note):
                success_count += 1
            time.sleep(0.3)  # 避免请求过快
    
    print("="*50)
    print(f"📊 同步完成! 共处理 {total_notes} 条笔记, 成功 {success_count} 条")
    
    if total_notes > 0 and success_count == 0:
        print("❌ 所有笔记同步失败，请检查错误日志")
        sys.exit(2)
    
    sys.exit(0)
