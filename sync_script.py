import os
import requests
from notion_client import Client
from datetime import datetime
import time

# 环境变量配置
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")
WR_COOKIE = os.getenv("WR_COOKIE")

# 初始化Notion客户端
notion = Client(auth=NOTION_TOKEN)

def get_books():
    """获取书架图书列表"""
    headers = {
        "Cookie": WR_COOKIE,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(
            "https://i.weread.qq.com/user/notebooks",
            headers=headers,
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("books", [])
        else:
            print(f"获取书籍失败: HTTP {response.status_code}")
            print(response.text[:200])
    except Exception as e:
        print(f"请求异常: {str(e)}")
    return []

def get_notes(book_id):
    """获取图书笔记"""
    headers = {
        "Cookie": WR_COOKIE,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(
            f"https://i.weread.qq.com/book/bookmarklist?bookId={book_id}",
            headers=headers,
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("updated", [])
    except:
        pass
    return []

def sync_to_notion(book, notes):
    """同步单本书笔记到Notion"""
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
                "书名": {"title": [{"text": {"content": book["title"]}}]},
                "作者": {"rich_text": [{"text": {"content": book.get("author", "未知")}}]},
                "阅读日期": {"date": {"start": create_time.strftime("%Y-%m-%d")}},
                "类型": {"select": {"name": note_type}},
                "内容": {"rich_text": [{"text": {"content": note.get("abstract") or note.get("markText", "")}}]},
                "书籍ID": {"rich_text": [{"text": {"content": book["bookId"]}}]},
            }
            
            # 创建页面
            notion.pages.create(
                parent={"database_id": DATABASE_ID},
                properties=properties
            )
            success_count += 1
            print(f"已同步: 《{book['title']}》- {note_type}")
            time.sleep(0.3)
        except Exception as e:
            print(f"同步失败: {str(e)}")
    
    return success_count

if __name__ == "__main__":
    print("="*60)
    print("微信读书同步到Notion")
    print("="*60)
    
    # 获取书籍列表
    books = get_books()
    if not books:
        print("❌ 未获取到书籍信息，可能Cookie已过期")
        print("请运行Update WeRead Cookie工作流获取更新说明")
        exit(1)
    
    print(f"获取到 {len(books)} 本书籍")
    
    # 同步到Notion
    total_notes = 0
    for book in books:
        book_id = book["bookId"]
        print(f"处理书籍: 《{book['title']}》")
        notes = get_notes(book_id)
        if not notes:
            print("  未找到笔记")
            continue
            
        print(f"  找到 {len(notes)} 条笔记")
        synced = sync_to_notion(book, notes)
        total_notes += synced
        time.sleep(1)
    
    print("="*60)
    print(f"✅ 同步完成! 共处理 {total_notes} 条笔记")
    print("="*60)
