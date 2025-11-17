添加更多网站
编辑 sites_config.json，添加新网站：
json{
  "name": "网站名称",
  "url": "https://example.com/events",
  "enabled": true,
  "selectors": {
    "container": ["div.event-class"],
    "title": ["h2", "h3"],
    "date": ["span.date"],
    "description": ["p"],
    "link": ["a"]
  }
}
功能特点
1. 多网站支持

在 sites_config.json 中配置任意数量的网站
每个网站可以有自定义的HTML选择器
可以单独启用/禁用每个网站

2. 智能解析

自动适配不同的网页结构
如果找不到结构化数据，会退回到内容hash检测

3. 关键词过滤（可选）

可以设置关键词只接收特定主题的事件
支持"任一匹配"或"全部匹配"模式

4. 检查频率选项
修改 .github/workflows/monitor.yml 中的 cron 表达式：

每周一次: '0 1 * * 1' (周一)
每两周一次: '0 1 */14 * *'
每月一次: '0 1 1 * *' (每月1号)
每三天一次: '0 1 */3 * *'
每天一次: '0 1 * * *'

5. 测试和调试
本地测试:
bash# 安装依赖
pip install -r requirements.txt

# 运行测试
python monitor.py