import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import hashlib
from urllib.parse import urljoin

def load_config():
    """加载网站配置"""
    with open('sites_config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def fetch_page_content(url, timeout=30):
    """获取网页内容"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"获取页面失败 {url}: {e}")
        return None

def extract_page_signature(html, url):
    """提取页面特征用于变化检测"""
    if not html:
        return None
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # 移除脚本和样式
    for script in soup(['script', 'style']):
        script.decompose()
    
    # 获取主要内容区域的文本
    text_content = soup.get_text()
    
    # 清理文本
    lines = [line.strip() for line in text_content.splitlines()]
    cleaned_text = ' '.join(line for line in lines if line and len(line) > 10)
    
    # 生成内容签名
    signature = hashlib.md5(cleaned_text.encode()).hexdigest()
    
    # 提取可能的事件信息（用于报告）
    events_preview = []
    
    # 查找可能包含事件的元素
    possible_events = soup.find_all(['article', 'div', 'li'], limit=5)
    for elem in possible_events:
        text = elem.get_text(strip=True)[:200]
        if len(text) > 50:  # 足够长才可能是事件描述
            events_preview.append(text)
    
    return {
        'signature': signature,
        'preview': events_preview[:3],  # 最多3个预览
        'content_length': len(cleaned_text)
    }

def load_last_state():
    """加载上次的状态"""
    if os.path.exists('last_state.json'):
        try:
            with open('last_state.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_state(state):
    """保存当前状态"""
    with open('last_state.json', 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def check_site(site_config, last_state):
    """检查单个网站"""
    site_name = site_config['name']
    url = site_config['url']
    
    print(f"\n检查: {site_name}")
    print(f"URL: {url}")
    
    # 获取页面内容
    html = fetch_page_content(url)
    if not html:
        return {
            'status': 'error',
            'message': '无法访问网站'
        }
    
    # 提取页面特征
    current_data = extract_page_signature(html, url)
    if not current_data:
        return {
            'status': 'error',
            'message': '无法解析页面内容'
        }
    
    # 对比上次的状态
    last_data = last_state.get(site_name, {})
    last_signature = last_data.get('signature')
    
    has_changes = last_signature != current_data['signature']
    
    result = {
        'status': 'success',
        'has_changes': has_changes,
        'content_length': current_data['content_length']
    }
    
    if has_changes:
        result['preview'] = current_data.get('preview', [])
        if last_signature:
            print(f"  🆕 检测到内容更新！")
        else:
            print(f"  📝 首次检查，记录初始状态")
    else:
        print(f"  ✅ 没有新的更新")
    
    return result, current_data

def format_report(all_results):
    """生成报告"""
    has_any_updates = any(r.get('has_changes', False) for r in all_results.values() if r.get('status') == 'success')
    
    if not has_any_updates:
        # 没有更新时不生成报告
        return None
    
    report = "# 🎯 网站事件更新通知\n\n"
    report += f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
    report += "---\n\n"
    
    update_count = 0
    
    for site_name, result in all_results.items():
        if result.get('status') != 'success':
            continue
            
        if result.get('has_changes'):
            update_count += 1
            report += f"## 📌 {site_name}\n\n"
            report += "**✨ 检测到页面更新**\n\n"
            
            # 添加内容预览
            previews = result.get('preview', [])
            if previews:
                report += "**内容预览：**\n\n"
                for i, preview in enumerate(previews, 1):
                    # 截断过长的预览
                    if len(preview) > 150:
                        preview = preview[:150] + "..."
                    report += f"{i}. {preview}\n\n"
            
            # 添加网站链接
            site_url = next((s['url'] for s in load_config()['sites'] if s['name'] == site_name), '')
            if site_url:
                report += f"🔗 [查看完整页面]({site_url})\n\n"
            
            report += "---\n\n"
    
    if update_count > 0:
        report = f"## 📊 更新摘要\n\n发现 **{update_count}** 个网站有更新\n\n---\n\n" + report
    
    return report

def main():
    print("="*60)
    print("🤖 网站事件监控系统")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 加载配置
    config = load_config()
    sites = [s for s in config['sites'] if s.get('enabled', True)]
    
    if not sites:
        print("❌ 没有配置要监控的网站")
        return
    
    print(f"\n📋 将检查 {len(sites)} 个网站")
    
    # 加载上次状态
    last_state = load_last_state()
    
    # 检查所有网站
    all_results = {}
    new_state = {}
    
    for site in sites:
        site_name = site['name']
        result, current_data = check_site(site, last_state)
        all_results[site_name] = result
        
        if result.get('status') == 'success' and current_data:
            new_state[site_name] = {
                'signature': current_data['signature'],
                'last_check': datetime.now().isoformat()
            }
    
    # 保存新状态
    if new_state:
        save_state(new_state)
        print(f"\n💾 状态已保存")
    
    # 生成报告
    report = format_report(all_results)
    
    if report:
        # 有更新，保存报告
        with open('report.md', 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n📬 发现更新！报告已生成")
        print("::set-output name=has_updates::true")
    else:
        # 没有更新
        print(f"\n✅ 所有网站都没有新的更新")
        print("::set-output name=has_updates::false")
        
        # 生成简单的状态报告
        with open('report.md', 'w', encoding='utf-8') as f:
            f.write("# ✅ 无更新\n\n")
            f.write(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n")
            f.write("所有监控的网站都没有检测到新的更新。")

if __name__ == "__main__":
    main()
