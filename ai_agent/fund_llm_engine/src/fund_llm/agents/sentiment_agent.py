from collections import Counter

from fund_llm.agents.base import BaseAgent, clamp, score_to_stance
from fund_llm.contracts import AgentOutput, FundFeaturePack, NewsItem

POSITIVE_LABELS = {"positive", "bullish", "favorable", "positive_signal", "正面", "利好"}
NEGATIVE_LABELS = {"negative", "bearish", "unfavorable", "negative_signal", "负面", "利空"}
POSITIVE_KEYWORDS = (
    "回暖",
    "改善",
    "增长",
    "修复",
    "超预期",
    "新高",
    "上涨",
    "增持",
    "positive",
    "recovery",
    "beat",
    "upgrade",
)
NEGATIVE_KEYWORDS = (
    "承压",
    "回撤",
    "下调",
    "处罚",
    "减持",
    "违约",
    "流出",
    "波动",
    "亏损",
    "negative",
    "risk",
    "downgrade",
    "outflow",
)
RISK_EVENT_KEYWORDS = (
    "风险",
    "诉讼",
    "监管",
    "处罚",
    "暴雷",
    "赎回",
    "违约",
    "risk",
    "lawsuit",
    "redemption",
)


def _classify_text_signal(text: str, explicit_label: str | None = None) -> str:
    normalized_label = (explicit_label or "").strip().lower()
    if normalized_label in POSITIVE_LABELS:
        return "positive"
    if normalized_label in NEGATIVE_LABELS:
        return "negative"

    lowered_text = (text or "").lower()
    positive_hits = sum(keyword in lowered_text for keyword in POSITIVE_KEYWORDS)
    negative_hits = sum(keyword in lowered_text for keyword in NEGATIVE_KEYWORDS)
    if positive_hits > negative_hits:
        return "positive"
    if negative_hits > positive_hits:
        return "negative"
    return "neutral"


def _looks_like_risk_event(text: str) -> bool:
    lowered_text = (text or "").lower()
    return any(keyword in lowered_text for keyword in RISK_EVENT_KEYWORDS)


class SentimentAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "SentimentAgent"

    def analyze(self, features: FundFeaturePack) -> AgentOutput:
        structured_items = features.news_items
        fallback_items = [
            NewsItem(summary=summary, topic="general")
            for summary in features.news_summary
            if summary
        ]
        active_items = structured_items or fallback_items

        positive_count = 0
        negative_count = 0
        neutral_count = 0
        risk_event_count = 0
        topic_counter = Counter()

        for item in active_items:
            text = " ".join(part for part in [item.title, item.summary] if part).strip()
            classification = _classify_text_signal(text, item.sentiment_label)
            if classification == "positive":
                positive_count += 1
            elif classification == "negative":
                negative_count += 1
            else:
                neutral_count += 1

            if _looks_like_risk_event(text):
                risk_event_count += 1
            if item.topic:
                topic_counter[item.topic] += 1

        news_signal_count = len(active_items)
        has_structured_news = features.data_quality_flags.get("has_structured_news", False)
        has_news_signal = features.data_quality_flags.get("has_news_signal", False)

        if not has_news_signal:
            raw_score = 55.0
        else:
            raw_score = 60 + (positive_count * 6) - (negative_count * 7) - (risk_event_count * 4)
            if positive_count and not negative_count:
                raw_score += 2
            if negative_count and positive_count == 0:
                raw_score -= 3
            if has_structured_news:
                raw_score += 2
        score = clamp(raw_score)
        stance = score_to_stance(score)

        top_topics = [topic for topic, _ in topic_counter.most_common(3)]
        prompt_items = active_items[:5]
        if prompt_items:
            prompt_block = "\n".join(
                f"- title={item.title or 'N/A'} | summary={item.summary or 'N/A'} | source={item.source or 'N/A'} | "
                f"date={item.published_at or 'N/A'} | topic={item.topic or 'N/A'} | label={item.sentiment_label or 'N/A'}"
                for item in prompt_items
            )
        else:
            prompt_block = "- No recent news items were provided."

        system_prompt = (
            "You are a fund sentiment analyst. Assess whether recent news flow is supportive, neutral, or adverse "
            "for the fund, and keep the explanation grounded in the provided signals."
        )
        user_prompt = (
            f"Fund: {features.fund_info.name} ({features.fund_info.code})\n"
            f"Fund category: {features.fund_info.category}\n"
            f"News signal count: {news_signal_count}\n"
            f"Structured news available: {has_structured_news}\n"
            f"Positive signal count: {positive_count}\n"
            f"Negative signal count: {negative_count}\n"
            f"Neutral signal count: {neutral_count}\n"
            f"Risk-event signal count: {risk_event_count}\n"
            f"Top topics: {top_topics}\n"
            f"Client risk profile: {features.extra_context.get('client_risk_profile', '')}\n"
            f"Missing fields: {features.missing_fields}\n"
            f"News items:\n{prompt_block}\n\n"
            "Please explain whether the recent news flow is supportive, mixed, or adverse for this fund."
        )
        narrative = self.llm_client.chat(system_prompt, user_prompt)

        key_points = []
        if not has_news_signal:
            key_points.append("No recent news signal was provided.")
        else:
            key_points.append(f"Processed {news_signal_count} recent news signal(s).")
            if positive_count:
                key_points.append(f"Positive news signals count is {positive_count}.")
            if negative_count:
                key_points.append(f"Negative news signals count is {negative_count}.")
            if top_topics:
                key_points.append(f"Recent news topics include {', '.join(top_topics)}.")
            if risk_event_count:
                key_points.append("Recent headlines include risk-event language.")

        risks = []
        if not has_news_signal:
            risks.append("No recent news items were provided, so sentiment coverage is limited.")
        if negative_count > positive_count:
            risks.append("Recent news flow leans negative.")
        if risk_event_count:
            risks.append("Recent headlines include potential event-risk language.")

        recommendations = ["Use recent news flow only as a secondary cross-check alongside fundamentals."]
        if not has_news_signal:
            recommendations = ["Add recent news or event summaries before relying on sentiment-driven conclusions."]
        elif negative_count > positive_count:
            recommendations = ["Watch for follow-up disclosures before increasing exposure."]
        elif positive_count > negative_count and risk_event_count == 0:
            recommendations = ["Recent news tone is supportive, but still confirm it with hard performance data."]

        confidence = 0.48
        if has_news_signal:
            confidence += min(news_signal_count, 3) * 0.08
        if has_structured_news:
            confidence += 0.10
        if top_topics:
            confidence += 0.04
        confidence = min(confidence, 0.86)

        return AgentOutput(
            agent_name=self.name,
            status="success",
            score=score,
            stance=stance,
            key_points=key_points,
            risks=risks,
            recommendations=recommendations,
            confidence=confidence,
            narrative=narrative,
        )
