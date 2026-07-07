"""News summary endpoint logic (frontend News page AI Summary).

设计与其他分析路径一致的防幻觉分工：

- 逐条新闻的情绪标签由 `SentimentAgent` 的确定性关键词分类器打出（代码算，不是 LLM 猜）；
- 整体情绪 label / 计数 / 置信度全部确定性计算；
- LLM 只负责把已分类的新闻写成摘要，失败或输出不完整时回退确定性摘要；
- `related_symbols` 只回传请求里给的 symbol，绝不让 LLM 从文本里编股票代码。

输入直接接受 news backend `get_recent_news` 的原始行（news_title / news_content /
publish_time 等中英文字段都能识别），前端拿到新闻后原样转发即可，不需要改字段。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fund_llm import config
from fund_llm.agents.chief_agent import _summary_looks_incomplete
from fund_llm.agents.sentiment_agent import _classify_text_signal, _looks_like_risk_event
from fund_llm.contracts import AnalysisTraceEvent
from fund_llm.llm_client import LLMClient, MockLLMClient

# 限制进入 prompt 的新闻条数，避免超长输入。
DEFAULT_MAX_ITEMS = 10
HARD_MAX_ITEMS = 20

CONFIDENCE_FLOOR = 0.4
CONFIDENCE_CEILING = 0.9

_TITLE_KEYS = ("title", "news_title", "announcement_title", "新闻标题", "标题")
_CONTENT_KEYS = ("content", "summary", "news_content", "新闻内容", "内容", "摘要")
_TIME_KEYS = ("published_at", "publish_time", "announcement_date", "发布时间", "时间", "date")
_SOURCE_KEYS = ("source", "文章来源", "来源")


def _first_text(row: Dict[str, Any], keys) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def normalize_news_items(raw_items: Any, max_items: int = DEFAULT_MAX_ITEMS) -> List[Dict[str, str]]:
    """Normalize heterogeneous news rows into {title, content, published_at, source}.

    丢弃标题和正文都为空的行；超出上限的行截断。
    """
    if not isinstance(raw_items, list):
        return []
    limit = max(1, min(int(max_items or DEFAULT_MAX_ITEMS), HARD_MAX_ITEMS))

    normalized: List[Dict[str, str]] = []
    for row in raw_items:
        if not isinstance(row, dict):
            continue
        title = _first_text(row, _TITLE_KEYS)
        content = _first_text(row, _CONTENT_KEYS)
        if not title and not content:
            continue
        normalized.append(
            {
                "title": title,
                "content": content[:500],
                "published_at": _first_text(row, _TIME_KEYS),
                "source": _first_text(row, _SOURCE_KEYS),
            }
        )
        if len(normalized) >= limit:
            break
    return normalized


def classify_news_items(items: List[Dict[str, str]]) -> Dict[str, Any]:
    """Deterministic per-item and aggregate sentiment classification."""
    item_signals: List[Dict[str, str]] = []
    counts = {"positive": 0, "negative": 0, "neutral": 0}
    risk_event_count = 0

    for item in items:
        text = " ".join(part for part in [item["title"], item["content"]] if part)
        label = _classify_text_signal(text)
        counts[label] += 1
        is_risk = _looks_like_risk_event(text)
        if is_risk:
            risk_event_count += 1
        item_signals.append(
            {
                "title": item["title"] or item["content"][:60],
                "sentiment": label,
                "risk_event": "true" if is_risk else "false",
            }
        )

    positive, negative = counts["positive"], counts["negative"]
    if positive and negative and min(positive, negative) >= 2 and abs(positive - negative) <= 1:
        overall = "mixed"
    elif positive > negative:
        overall = "positive"
    elif negative > positive:
        overall = "negative"
    else:
        overall = "neutral"

    return {
        "label": overall,
        "positive_count": positive,
        "negative_count": negative,
        "neutral_count": counts["neutral"],
        "risk_event_count": risk_event_count,
        "item_signals": item_signals,
    }


def compute_news_confidence(items: List[Dict[str, str]]) -> float:
    """Data-quality driven confidence, aligned with the agents' 0.4-0.9 convention."""
    confidence = CONFIDENCE_FLOOR
    confidence += min(len(items), 6) * 0.05
    if items:
        with_content = sum(1 for item in items if len(item["content"]) >= 40)
        confidence += (with_content / len(items)) * 0.10
        with_time = sum(1 for item in items if item["published_at"])
        confidence += (with_time / len(items)) * 0.05
        if any(item["source"] for item in items):
            confidence += 0.05
    return round(max(CONFIDENCE_FLOOR, min(CONFIDENCE_CEILING, confidence)), 2)


def _build_deterministic_summary(
    items: List[Dict[str, str]],
    sentiment: Dict[str, Any],
    symbol: str,
) -> str:
    subject = f"for {symbol}" if symbol else "in this batch"
    parts = [
        f"Recent {len(items)} news item(s) {subject} lean {sentiment['label']} "
        f"({sentiment['positive_count']} positive / {sentiment['negative_count']} negative / "
        f"{sentiment['neutral_count']} neutral)."
    ]
    if sentiment["risk_event_count"]:
        parts.append(
            f"{sentiment['risk_event_count']} headline(s) contain risk-event language and deserve a closer read."
        )
    latest = items[0]
    parts.append(f"Latest headline: {latest['title'] or latest['content'][:80]}.")
    parts.append("Treat news tone as a secondary cross-check, not a standalone trading signal.")
    return " ".join(parts)


def _build_summary_prompts(
    items: List[Dict[str, str]],
    sentiment: Dict[str, Any],
    symbol: str,
) -> tuple:
    item_lines = "\n".join(
        f"- [{signal['sentiment']}] {item['title'] or 'N/A'} | {item['content'][:160] or 'N/A'} "
        f"| {item['published_at'] or 'N/A'} | {item['source'] or 'N/A'}"
        for item, signal in zip(items, sentiment["item_signals"])
    )
    system_prompt = (
        "You are a financial news summarizer. Write a concise digest of the provided news items only. "
        "Respond in English only, even though headlines may be Chinese. "
        "Each item is pre-labeled with a deterministic sentiment tag; do not re-score them. "
        "Do not invent facts, price targets, or ticker symbols that are not in the items. "
        "Keep the summary under 120 words and end with a complete sentence."
    )
    user_prompt = (
        f"Subject symbol: {symbol or 'not specified'}\n"
        f"Overall tone (computed in code): {sentiment['label']} "
        f"({sentiment['positive_count']} positive / {sentiment['negative_count']} negative / "
        f"{sentiment['neutral_count']} neutral, {sentiment['risk_event_count']} risk-event headline(s))\n"
        f"News items:\n{item_lines}\n\n"
        "Please write one short paragraph summarizing what happened and the overall tone."
    )
    return system_prompt, user_prompt


def _build_trace(
    items: List[Dict[str, str]],
    sentiment: Dict[str, Any],
    summary_source: str,
) -> List[AnalysisTraceEvent]:
    return [
        AnalysisTraceEvent(
            category="feature",
            title="Classified news sentiment deterministically",
            detail=(
                "Labeled every news item with keyword-rule sentiment and risk-event flags in code "
                "before any LLM call, so the tone statistics cannot be hallucinated."
            ),
            status="success",
            evidence={
                "items_used": len(items),
                "label": sentiment["label"],
                "positive": sentiment["positive_count"],
                "negative": sentiment["negative_count"],
                "risk_events": sentiment["risk_event_count"],
            },
            technical={"classifier": "SentimentAgent keyword rules"},
        ),
        AnalysisTraceEvent(
            category="aggregation",
            title="Summarized news digest",
            detail=(
                "Generated the digest strictly from the provided items; ticker symbols are echoed "
                "from the request instead of being inferred by the model."
            ),
            status="success",
            evidence={"summary_source": summary_source},
            technical={},
        ),
    ]


def run_news_summary(
    raw_items: Any,
    llm_client,
    symbol: str = "",
    max_items: int = DEFAULT_MAX_ITEMS,
) -> Dict[str, Any]:
    items = normalize_news_items(raw_items, max_items=max_items)
    if not items:
        raise ValueError(
            "No usable news items were provided. Each item needs at least a title or content field."
        )

    sentiment = classify_news_items(items)
    confidence = compute_news_confidence(items)
    symbol = str(symbol or "").strip()

    summary_source = "llm"
    language_retry = False
    system_prompt, user_prompt = _build_summary_prompts(items, sentiment, symbol)
    try:
        summary = llm_client.chat(system_prompt, user_prompt, max_tokens=700)
    except Exception:
        summary = ""
        summary_source = "deterministic_fallback"

    if (
        summary
        and not getattr(llm_client, "is_mock", False)
        and _summary_looks_incomplete(summary)
    ):
        # 输入是纯中文新闻时，模型偶尔无视指令用中文作答；英文输出是硬要求
        # （质量门按英文词数判断），这里做一次显式纠偏重试，仍不合格才回退。
        language_retry = True
        try:
            summary = llm_client.chat(
                system_prompt,
                user_prompt
                + "\n\nIMPORTANT: Your answer MUST be written in English only. "
                "Do not answer in Chinese; translate the key facts into English.",
                max_tokens=700,
            )
        except Exception:
            summary = ""
        if _summary_looks_incomplete(summary):
            summary = ""
            summary_source = "deterministic_fallback"

    if not summary:
        summary = _build_deterministic_summary(items, sentiment, symbol)
        summary_source = "deterministic_fallback"

    item_signals = sentiment.pop("item_signals")
    metadata = {
        "analysis_level": "news",
        "items_used": str(len(items)),
        "summary_source": summary_source,
        "language_retry": str(language_retry).lower(),
        "prompt_version": config.PROMPT_VERSION,
    }

    return {
        "request_id": f"news-summary-{symbol or 'general'}-{len(items)}",
        "status": "success",
        "summary": summary,
        "sentiment": sentiment,
        "confidence": confidence,
        "related_symbols": [symbol] if symbol else [],
        "items_analyzed": len(items),
        "item_signals": item_signals,
        "metadata": metadata,
        "analysis_trace": [event.to_dict() for event in _build_trace(items, sentiment, summary_source)],
    }


def run_mock_news_summary(
    raw_items: Any,
    symbol: str = "",
    max_items: int = DEFAULT_MAX_ITEMS,
    mock_response: str = "Mock news digest generated from deterministic sentiment classification.",
) -> Dict[str, Any]:
    result = run_news_summary(raw_items, MockLLMClient(mock_response), symbol=symbol, max_items=max_items)
    result["metadata"]["llm_mode"] = "mock"
    return result


def run_real_news_summary(
    raw_items: Any,
    symbol: str = "",
    max_items: int = DEFAULT_MAX_ITEMS,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    timeout_seconds: Optional[int] = None,
) -> Dict[str, Any]:
    llm_client = LLMClient(
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout_seconds=timeout_seconds,
    )
    result = run_news_summary(raw_items, llm_client, symbol=symbol, max_items=max_items)
    result["metadata"].update(
        {
            "llm_mode": "real",
            "llm_model": llm_client.model,
            "llm_base_url": llm_client.base_url,
        }
    )
    return result
