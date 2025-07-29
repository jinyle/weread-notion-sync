import os
import requests

def test_cookie(cookie):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Cookie": cookie
    }
    
    print("测试Cookie有效性...")
    print(f"Cookie长度: {len(cookie)}字符")
    
    try:
        # 测试API：获取用户信息
        response = requests.get(
            "https://i.weread.qq.com/user/notebooks",
            headers=headers,
            timeout=10
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Cookie有效! 返回数据示例:")
            data = response.json()
            if "books" in data and len(data["books"]) > 0:
                print(f"  用户名: {data.get('userName', '未知')}")
                print(f"  书架书籍数: {len(data['books'])}")
                return True
            else:
                print("⚠️ 返回数据异常，但HTTP状态正常")
                print(f"响应内容: {response.text[:200]}")
        else:
            print(f"❌ 请求失败: HTTP {response.status_code}")
            print(f"错误信息: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ 发生异常: {str(e)}")
    
    return False

if __name__ == "__main__":
    cookie = os.getenv("WR_COOKIE", "")
    if not cookie:
        print("❌ 未找到WR_COOKIE环境变量")
        exit(1)
        
    print("="*60)
    print("微信读书Cookie测试工具")
    print("="*60)
    
    if test_cookie(cookie):
        print("✅ 测试通过! 可以运行主同步脚本")
        exit(0)
    else:
        print("❌ Cookie无效，请更新后再试")
        exit(1)
