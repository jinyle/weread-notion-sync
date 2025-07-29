import os
import requests
import sys

def test_cookie(cookie):
    print("="*60)
    print("微信读书Cookie测试工具")
    print("="*60)
    print(f"Cookie长度: {len(cookie)}字符")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Cookie": cookie,
        "Referer": "https://weread.qq.com/"
    }
    
    try:
        print("测试API：获取用户信息...")
        response = requests.get(
            "https://i.weread.qq.com/user/notebooks",
            headers=headers,
            timeout=10
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Cookie有效! 返回数据示例:")
            try:
                data = response.json()
                if "books" in data and len(data["books"]) > 0:
                    print(f"  用户名: {data.get('userName', '未知')}")
                    print(f"  书架书籍数: {len(data['books'])}")
                    print("✅ 测试通过! 可以运行主同步脚本")
                    return True
                else:
                    print("⚠️ 返回数据异常，但HTTP状态正常")
                    print(f"响应内容: {response.text[:200]}")
            except:
                print("⚠️ JSON解析失败，原始响应:")
                print(response.text[:500])
        else:
            print(f"❌ 请求失败: HTTP {response.status_code}")
            print(f"错误信息: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ 发生异常: {str(e)}")
    
    print("❌ Cookie无效，请更新后再试")
    return False

if __name__ == "__main__":
    cookie = os.getenv("WR_COOKIE", "")
    if not cookie:
        print("❌ 未找到WR_COOKIE环境变量")
        sys.exit(1)
        
    success = test_cookie(cookie)
    sys.exit(0 if success else 1)
