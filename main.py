import os
import requests
from notion_client import Client
from datetime import datetime
import sys
import json
import time

print("=" * 80)
print("🚀 微信读书到Notion同步脚本启动")
print("=" * 80)

# 环境变量验证
required_envs = ["NOTION_TOKEN", "DATABASE_ID", "WR_COOKIE"]
print("🔍 检查环境变量...")
missing_envs = [var for var in required_envs if not os.getenv(var)]

if missing_envs:
    print(f"❌ 错误: 缺少以下关键环境变量: {', '.join(missing_envs)}")
    print("请确保在GitHub Secrets中设置了这些变量")
    sys.exit(1)
else:
    print("✅ 所有必需环境变量已设置")

# 配置参数
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")
WR_COOKIE = os.getenv("WR_COOKIE")

print(f"🔑 NOTION_TOKEN: {NOTION_TOKEN[:5]}...{NOTION_TOKEN[-5:]}")
print(f"📁 DATABASE_ID: {DATABASE_ID}")
print(f"🍪 WR_COOKIE: {WR_COOKIE[:15]}... (长度: {len(WR_COOKIE)})")

# 初始化Notion客户端
print("\n🔌 初始化Notion客户端...")
try:
    notion = Client(auth=NOTION_TOKEN, log_level="DEBUG")
    
    # 测试连接
    print("  测试Notion连接...")
    me = notion.users.me()
    print(f"  ✅ Notion连接成功! 用户: {me['name']} ({me['id']})")
    
    # 测试数据库访问
    print("  测试数据库访问...")
    db_info = notion.databases.retrieve(database_id=DATABASE_ID)
    print(f"  ✅ 数据库访问成功! 名称: {db_info['title'][0]['text']['content']}")
    
except Exception as e:
    print(f"❌ Notion客户端初始化失败: {str(e)}")
    print("可能原因:")
    print("1. NOTION_TOKEN 无效")
    print("2. 数据库未连接集成")
    print("3. 数据库ID错误")
    sys.exit(1)

def fetch_weread_notes():
    """获取微信读书笔记"""
    print("\n📚 从微信读书获取笔记数据...")
    headers = {
        "Cookie": WR_COOKIE,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://weread.qq.com/"
    }
    
    try:
        print("  请求笔记本列表...")
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
        print(f"\n📖 处理书籍: 《{book_title}》")
        res = requests.get(
            f"https://i.weread.qq.com/book/bookmarklist?bookId={book_id}",
            headers=headers,
            timeout=15
        )
        
        if res.status_code != 200:
            print(f"  ❌ 书籍笔记请求失败: HTTP {res.status_code}")
            print(f"  响应内容: {res.text[:200]}...")
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
                
            # 创建时间转换
            try:
                create_time = datetime.fromtimestamp(note["createTime"])
            except KeyError:
                create_time = datetime.now()
                
            processed_notes.append({
                "book": book_title,
                "author": book.get("author", "未知"),
                "date": create_time.strftime("%Y-%m-%d"),
                "content": content[:200] + "..." if len(content) > 200 else content,
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
        # 打印详细错误
        try:
            error_details = json.loads(str(e))
            print(f"  错误类型: {error_details.get('code')}")
            print(f"  错误消息: {error_details.get('message')}")
        except:
            pass
        return False

if __name__ == "__main__":
    books = fetch_weread_notes()
    if not books:
        print("❌ 未获取到书籍信息，同步终止")
        sys.exit(1)
    
    total_notes = 0
    success_count = 0
    
    print("\n🔄 开始同步笔记到Notion...")
    for book in books[:1]:  # 只处理第一本书用于测试
        notes = process_book_notes(book)
        if not notes:
            continue
            
        for note in notes[:1]:  # 只同步第一条笔记
            total_notes += 1
            if sync_to_notion(note):
                success_count += 1
            time.sleep(1)  # 避免请求过快
    
    print("\n" + "=" * 50)
    print(f"📊 同步完成! 共处理 {total_notes} 条笔记, 成功 {success_count} 条")
    
    if total_notes > 0 and success_count == 0:
        print("❌ 所有笔记同步失败，请检查错误日志")
        sys.exit(1)
    
    print("✅ 脚本执行成功!")
    sys.exit(0)
