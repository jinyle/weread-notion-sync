import os
import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from notion_client import Client

def we_read_login():
    """使用浏览器登录微信读书并获取Cookie"""
    print("启动浏览器环境...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # 在GitHub Actions中需要指定chromedriver路径
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        driver = webdriver.Chrome(options=chrome_options)
    else:
        driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print("访问微信读书登录页面...")
        driver.get("https://weread.qq.com/")
        
        # 等待登录二维码出现
        print("等待登录二维码...")
        qr_container = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CLASS_NAME, "login_dialog_qrcode"))
        
        # 获取二维码图片（在GitHub Actions中需要特殊处理）
        if os.environ.get('GITHUB_ACTIONS') == 'true':
            # 在Actions中无法显示图片，提示用户手动登录
            print("="*60)
            print("请在手机上打开微信读书APP扫描二维码登录")
            print("1. 打开微信读书APP")
            print("2. 点击'我' -> '扫一扫'")
            print("3. 扫描下方二维码")
            print("注意：登录后请返回此页面等待完成")
            print("="*60)
            
            # 保存二维码供下载
            qr_container.screenshot("qrcode.png")
            print("::set-output name=qr_path::qrcode.png")
        else:
            # 本地运行直接显示二维码
            qr_container.screenshot("qrcode.png")
            print("请扫描qrcode.png登录")
        
        # 等待登录完成（检测用户头像出现）
        print("等待登录完成...")
        WebDriverWait(driver, 300).until(
            EC.presence_of_element_located((By.CLASS_NAME, "wr_avatar")))
        
        print("登录成功! 获取Cookie...")
        cookies = driver.get_cookies()
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        
        print("获取书架信息...")
        driver.get("https://i.weread.qq.com/user/notebooks")
        notebooks = json.loads(driver.find_element(By.TAG_NAME, "pre").text)
        
        return cookie_str, notebooks.get("books", [])
        
    finally:
        driver.quit()

def sync_to_notion(books, cookie):
    """同步笔记到Notion"""
    if not books:
        print("没有书籍信息")
        return 0
    
    # 初始化Notion客户端
    notion = Client(auth=os.getenv("NOTION_TOKEN"))
    database_id = os.getenv("DATABASE_ID")
    
    total_notes = 0
    
    for book in books:
        book_id = book["bookId"]
        print(f"处理书籍: 《{book['title']}》")
        
        # 获取笔记
        notes = get_book_notes(book_id, cookie)
        if not notes:
            continue
            
        print(f"  找到 {len(notes)} 条笔记")
        
        # 同步笔记
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
                    "书籍ID": {"rich_text": [{"text": {"content": book_id}}]},
                }
                
                # 创建页面
                notion.pages.create(
                    parent={"database_id": database_id},
                    properties=properties
                )
                total_notes += 1
                print(f"  已同步: {note_type}")
                time.sleep(0.3)
            except Exception as e:
                print(f"  同步失败: {str(e)}")
    
    return total_notes

def get_book_notes(book_id, cookie):
    """获取图书笔记"""
    url = f"https://i.weread.qq.com/book/bookmarklist?bookId={book_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Cookie": cookie,
        "Referer": f"https://weread.qq.com/web/reader/{book_id.replace('_', '')}"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.json().get("updated", [])
    except:
        pass
    
    return []

if __name__ == "__main__":
    # 在GitHub Actions中需要先安装依赖
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        print("="*60)
        print("GitHub Actions 环境检测")
        print("="*60)
    
    # 登录并获取数据
    cookie, books = we_read_login()
    
    if not books:
        print("未获取到书籍信息")
        exit(1)
    
    print(f"获取到 {len(books)} 本书籍")
    
    # 同步到Notion
    total_notes = sync_to_notion(books, cookie)
    
    print("="*60)
    print(f"✅ 同步完成! 共处理 {total_notes} 条笔记")
    print("="*60)
