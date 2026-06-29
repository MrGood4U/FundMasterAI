"""
News-backend 全部接口的 Function Calling 定义。

每个函数包含 LLM agent 所需的 name / description / parameters / returns，
以及路由元信息（path / method），agent 可据此生成 HTTP 请求并解析响应。

所有接口的 HTTP 响应格式统一为:
  {"code": 200, "data": [...], "message": "success"}
  data 为对象数组，每条记录的结构见各函数的 returns 字段。
"""

FUNCTIONS = [
    # =====================================================================
    # 个股新闻
    # =====================================================================
    {
        "name": "get_stock_recent_news",
        "description": "获取个股近期新闻公告列表，包含新闻标题、内容摘要、发布时间、来源和原文链接。适合跟踪特定股票的舆情动态和消息面。",
        "path": "/api/news/stock/get_recent_news",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "股票代码，如 600519（贵州茅台）",
                },
            },
            "required": ["symbol"],
        },
        "returns": {
            "keyword": "关键词",
            "news_title": "新闻标题",
            "news_content": "新闻内容摘要",
            "publish_time": "发布时间",
            "source": "文章来源",
            "url": "新闻原文链接",
        },
    },

    # =====================================================================
    # 公募基金公告
    # =====================================================================
    {
        "name": "get_public_fund_announcement",
        "description": "获取公募基金分红公告列表，包含公告标题、公告日期和原文链接。用于跟踪基金的分红、拆分、费率变更等重大事项。注意：该接口目前仅返回分红相关公告，不包含其他类型的基金公告。",
        "path": "/api/news/public_fund/get_announcement",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "基金代码，如 000001（华夏成长混合）",
                },
            },
            "required": ["code"],
        },
        "returns": {
            "fund_code": "基金代码",
            "fund_name": "基金名称",
            "announcement_title": "公告标题",
            "announcement_date": "公告日期",
            "report_id": "报告ID",
            "url": "公告原文链接（东方财富基金公告页）",
        },
    },
]


def get_all_functions():
    """返回所有接口的函数定义列表。"""
    return FUNCTIONS


def get_functions_by_tag(tag: str):
    """按标签筛选函数。tag 为 stock / fund。"""
    prefix_map = {
        "stock": "get_stock",
        "fund": "get_public_fund",
    }
    prefix = prefix_map.get(tag)
    if prefix is None:
        return []
    return [f for f in FUNCTIONS if f["name"].startswith(prefix)]
