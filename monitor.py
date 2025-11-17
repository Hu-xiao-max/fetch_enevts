import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import hashlib
import sys
from urllib.parse import urljoin

def load_config():
    """加载网站配置"""
    with open('sites_config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def fetch_page_content(url, timeout=30):
    """获取网页内容"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"获取页面失败 {url}: {e}")
        return None

def extract_events_generic(html, url, selectors):
    """通用的事件提取器"""
    if not html:
        return []
    
    soup = BeautifulSoup(html, 'html.parser')
    events = []
    
    # 尝试使用配置的选择器查找事件容器
    containers = []
    for selector in selectors.get('container', []):
        containers.extend(soup.select(selector))
    
    # 如果没找到容器，尝试一些通用的选择器
    if not containers:
        containers = soup.find_all(['article', 'div'], 
                                  class_=lambda x: x and any(word in str(x).lower() 
                                  for word in ['event', 'post', 'item', 'entry']) if x else False)
    
    for container in containers[:20]:  # 限制最多处理20个事件
        event = {}
        
        # 提取标题
        for selector in selectors.get('title', []):
            title = container.select_one(selector)
            if title:
                event['title'] = title.get_text(strip=True)
                break
        
        # 提取日期
        for selector in selectors.get('date', []):
            date = container.select_one(selector)
            if date:
                event['date'] = date.get_text(strip=True)
                break
        
        # 提取描述
        for selector in selectors.get('description', []):
            desc = container.select_one(selector)
            if desc:
                event['description'] = desc.get_text(strip=True)[:300]
                break
        
        # 提取链接
        for selector in selectors.get('link', []):
            link_elem = container.select_one(selector)
            if link_elem and link_elem.get('href'):
                event['link'] = urljoin(url, link_elem['href'])
                break
        
        # 只添加至少有标题的事件
        if event.get('title'):
            events.append(event)
    
    # 如果没找到结构化的事件，返回页面内容的hash用于变化检测
    if not events:
        text_content = soup.get_text()
        page_hash = hashlib.md5(text_content.encode()).hexdigest()[:16]
        events = [{'page_hash': page_hash, 'content_preview': text_content[:500].replace('\n', ' ')}]
    
    return events

def fetch_site_events(site_config):
    """获取单个网站的事件"""
    print(f"正在检查: {site_config['name']}")
    
    html = fetch_page_content(site_config['url'])
    if not html:
        return None
    
    events = extract_events_generic(html, site_config['url'], site_config.get('selectors', {}))
    
    # 为每个事件添加来源信息
    for event in events:
        event['source'] = site_config['name']
        event['source_url'] = site_config['url']
    
    return events

def load_last_events():
    """加载上次保存的事件"""
    if os.path.exists('last_events.json'):
        with open('last_events.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_events(all_events):
    """保存当前事件"""
    with open('last_events.json', 'w', encoding='utf-8') as f:
        json.dump(all_events, f, ensure_ascii=False, indent=2)

def find_new_events(current_events, last_events, site_name):
    """找出新增的事件"""
    last_site_events = last_events.get(site_name, [])
    
    # 转换为可比较的集合
    last_set = {json.dumps(e, sort_keys=True) for e in last_site_events}
    current_set = {json.dumps(e, sort_keys=True) for e in current_events}
    
    new_set = current_set - last_set
    new_events = [json.loads(e) for e in new_set]
    
    return new_events

def format_email_body(all_new_events):
    """格式化邮件内容"""
    if not any(all_new_events.values()):
        return "本周没有检测到新事件"
    
    total_count = sum(len(events) for events in all_new_events.values())
    body = f"# 📅 本周事件更新汇总\n\n"
    body += f"检测到 **{total_count}** 个新事件/更新\n\n"
    body += f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
    body += "---\n\n"
    
    for site_name, events in all_new_events.items():
        if not events:
            continue
            
        body += f"## 📌 {site_name}\n\n"
        
        for i, event in enumerate(events, 1):
            if 'page_hash' in event:
                body += f"**⚡ 页面内容已更新**\n"
                if 'content_preview' in event:
                    body += f"预览: {event['content_preview'][:200]}...\n\n"
                body += f"查看完整页面: {event.get('source_url', '')}\n\n"
            else:
                body += f"### 事件 {i}\n"
                if 'title' in event:
                    body += f"**{event['title']}**\n\n"
                if 'date' in event:
                    body += f"📅 时间: {event['date']}\n\n"
                if 'description' in event:
                    desc = event['description']
                    if len(desc) > 200:
                        desc = desc[:200] + "..."
                    body += f"📝 描述: {desc}\n\n"
                if 'link' in event:
                    body += f"🔗 链接: {event['link']}\n\n"
            
            body += "---\n\n"
    
    # 添加监控的网站列表
    body += "## 📊 监控的网站\n\n"
    config = load_config()
    for site in config['sites']:
        if site.get('enabled', True):
            body += f"- [{site['name']}]({site['url']})\n"
    
    return body

def main():
    print("="*50)
    print("开始检查网站更新...")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    
    config = load_config()
    sites = [s for s in config['sites'] if s.get('enabled', True)]
    
    print(f"将检查 {len(sites)} 个网站\n")
    
    # 加载上次的事件
    last_events = load_last_events()
    
    # 收集所有网站的事件
    current_all_events = {}
    all_new_events = {}
    
    for site in sites:
        # 获取当前事件
        current_events = fetch_site_events(site)
        
        if current_events is None:
            print(f"⚠️  跳过 {site['name']} (获取失败)\n")
            continue
        
        print(f"✓ 找到 {len(current_events)} 个事件/内容")
        
        site_name = site['name']
        current_all_events[site_name] = current_events
        
        # 找出新事件
        new_events = find_new_events(current_events, last_events, site_name)
        if new_events:
            print(f"  🆕 发现 {len(new_events)} 个新事件/更新！")
            all_new_events[site_name] = new_events
        else:
            print(f"  没有新更新")
        
        print()
    
    # 处理结果
    total_new = sum(len(events) for events in all_new_events.values())
    
    if total_new > 0:
        print(f"\n🎉 总计发现 {total_new} 个更新！")
        
        # 生成邮件内容
        email_body = format_email_body(all_new_events)
        
        # 保存邮件内容
        with open('email_content.txt', 'w', encoding='utf-8') as f:
            f.write(email_body)
        
        print("\n邮件内容已生成")
        
        # 设置GitHub Actions输出
        print(f"::set-output name=has_updates::true")
        print(f"::set-output name=update_count::{total_new}")
        
        # 保存当前事件
        save_events(current_all_events)
        
        # 提交更改到Git
        os.system('git config --local user.email "action@github.com"')
        os.system('git config --local user.name "GitHub Action"')
        os.system('git add last_events.json')
        os.system('git commit -m "Update events cache"')
    else:
        print("\n没有发现新更新")
        print(f"::set-output name=has_updates::false")
        print(f"::set-output name=update_count::0")
        
        # 即使没有新事件也更新缓存（防止网站结构变化导致的误报）
        if current_all_events:
            save_events(current_all_events)

if __name__ == "__main__":
    main()