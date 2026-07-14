import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fund_llm.llm_client import MockLLMClient
from fund_llm.news_summary import (
    _build_summary_prompts,
    classify_news_items,
    compute_news_confidence,
    normalize_news_items,
    run_mock_news_summary,
    run_news_summary,
)


def backend_style_rows():
    """news backend get_recent_news 的原始行字段形状。"""
    return [
        {
            "news_title": "公司业绩超预期，机构上调评级",
            "news_content": "多家机构认为盈利改善趋势确立，维持增持评级。",
            "publish_time": "2026-07-07 09:30:00",
            "文章来源": "证券时报",
        },
        {
            "news_title": "监管处罚落地，短期承压",
            "news_content": "公司收到监管警示函，市场担忧后续整改风险。",
            "publish_time": "2026-07-07 08:00:00",
            "文章来源": "财联社",
        },
        {
            "news_title": "行业会议召开",
            "news_content": "多家公司参加行业交流会议。",
            "publish_time": "2026-07-06 15:00:00",
            "文章来源": "上证报",
        },
    ]


class NormalizeNewsItemsTest(unittest.TestCase):
    def test_backend_chinese_field_names_are_recognized(self):
        items = normalize_news_items(backend_style_rows())

        self.assertEqual(len(items), 3)
        self.assertEqual(items[0]["title"], "公司业绩超预期，机构上调评级")
        self.assertTrue(items[0]["content"].startswith("多家机构"))
        self.assertEqual(items[0]["published_at"], "2026-07-07 09:30:00")
        self.assertEqual(items[0]["source"], "证券时报")

    def test_english_field_names_are_recognized(self):
        items = normalize_news_items(
            [{"title": "T", "summary": "S", "published_at": "2026-07-07", "source": "wire"}]
        )
        self.assertEqual(items[0]["content"], "S")

    def test_rows_without_title_and_content_are_dropped(self):
        items = normalize_news_items(
            [{"publish_time": "2026-07-07"}, "not-a-dict", {"news_title": "ok"}]
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "ok")

    def test_item_cap_is_enforced(self):
        rows = [{"title": f"t{i}"} for i in range(30)]
        self.assertEqual(len(normalize_news_items(rows, max_items=5)), 5)
        # 硬上限 20，即使请求更大也不放行
        self.assertEqual(len(normalize_news_items(rows, max_items=99)), 20)


class ClassifyNewsItemsTest(unittest.TestCase):
    def test_counts_and_overall_label(self):
        sentiment = classify_news_items(normalize_news_items(backend_style_rows()))

        self.assertEqual(sentiment["positive_count"], 1)
        self.assertEqual(sentiment["negative_count"], 1)
        self.assertEqual(sentiment["neutral_count"], 1)
        self.assertEqual(sentiment["label"], "neutral")
        self.assertGreaterEqual(sentiment["risk_event_count"], 1)
        self.assertEqual(len(sentiment["item_signals"]), 3)
        self.assertEqual(sentiment["item_signals"][1]["sentiment"], "negative")
        self.assertEqual(sentiment["item_signals"][1]["risk_event"], "true")

    def test_mixed_label_when_both_sides_are_strong(self):
        rows = (
            [{"title": "利好 增长 超预期"}] * 2
            + [{"title": "利空 处罚 亏损"}] * 2
        )
        sentiment = classify_news_items(normalize_news_items(rows))
        self.assertEqual(sentiment["label"], "mixed")

    def test_positive_majority_label(self):
        rows = [{"title": "增长 超预期"}] * 3 + [{"title": "行业会议"}]
        sentiment = classify_news_items(normalize_news_items(rows))
        self.assertEqual(sentiment["label"], "positive")


class NewsConfidenceTest(unittest.TestCase):
    def test_confidence_grows_with_richness_and_stays_bounded(self):
        rich = normalize_news_items(backend_style_rows() * 3)
        sparse = normalize_news_items([{"title": "only one headline"}])

        rich_conf = compute_news_confidence(rich)
        sparse_conf = compute_news_confidence(sparse)

        self.assertGreater(rich_conf, sparse_conf)
        self.assertGreaterEqual(sparse_conf, 0.4)
        self.assertLessEqual(rich_conf, 0.9)


class RunNewsSummaryTest(unittest.TestCase):
    def test_mock_pipeline_produces_full_result(self):
        result = run_mock_news_summary(backend_style_rows(), symbol="300059")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["request_id"], "news-summary-300059-3")
        self.assertEqual(result["related_symbols"], ["300059"])
        self.assertEqual(result["items_analyzed"], 3)
        self.assertEqual(result["metadata"]["llm_mode"], "mock")
        self.assertEqual(result["metadata"]["analysis_level"], "news")
        self.assertIn("prompt_version", result["metadata"])
        self.assertIn("summary", result)
        self.assertEqual(len(result["item_signals"]), 3)
        titles = [event["title"] for event in result["analysis_trace"]]
        self.assertIn("Classified news sentiment deterministically", titles)

    def test_symbol_is_echoed_not_invented(self):
        result = run_mock_news_summary(backend_style_rows())
        self.assertEqual(result["related_symbols"], [])

    def test_empty_items_raise_value_error(self):
        with self.assertRaises(ValueError):
            run_mock_news_summary([{"publish_time": "2026-07-07"}])

    def test_llm_failure_falls_back_to_deterministic_summary(self):
        class BrokenLLMClient:
            def chat(self, system_prompt, user_prompt, **kwargs):
                raise RuntimeError("provider down")

        result = run_news_summary(backend_style_rows(), BrokenLLMClient(), symbol="300059")

        self.assertEqual(result["metadata"]["summary_source"], "deterministic_fallback")
        self.assertIn("300059", result["summary"])
        self.assertIn("risk-event", result["summary"])

    def test_prompt_contains_precomputed_labels(self):
        client = MockLLMClient("digest")
        run_news_summary(backend_style_rows(), client, symbol="300059")

        prompt = client.call_log[0]["user_prompt"]
        self.assertIn("Overall tone (computed in code)", prompt)

        items = normalize_news_items(backend_style_rows())
        system_prompt, _ = _build_summary_prompts(items, classify_news_items(items), "300059")
        self.assertIn("Translate Chinese numeric units", system_prompt)
        self.assertIn("do not leave Chinese unit", system_prompt)

    def test_chinese_unit_in_english_summary_triggers_retry(self):
        class PreservedThenConvertedClient:
            is_mock = False

            def __init__(self):
                self.calls = []

            def chat(self, system_prompt, user_prompt, **kwargs):
                self.calls.append(user_prompt)
                if len(self.calls) == 1:
                    return (
                        "The latest report showed an outflow of 412.75亿元, while the "
                        "remaining headlines were broadly neutral and offered limited direction. "
                        "Investors should treat the news flow as a secondary signal and continue "
                        "monitoring subsequent company disclosures and market activity."
                    )
                return (
                    "The latest report showed an outflow of 41.275 billion yuan, while the remaining "
                    "headlines were broadly neutral and offered limited direction. Investors "
                    "should treat the news flow as a secondary signal and continue monitoring "
                    "subsequent company disclosures and market activity."
                )

        rows = backend_style_rows() + [
            {"news_title": "主力资金净流出412.75亿元", "news_content": "市场资金流出。"}
        ]
        client = PreservedThenConvertedClient()
        result = run_news_summary(rows, client, symbol="300059")

        self.assertEqual(len(client.calls), 2)
        self.assertEqual(result["metadata"]["unit_retry"], "true")
        self.assertEqual(result["metadata"]["summary_source"], "llm")
        self.assertIn("41.275 billion yuan", result["summary"])
        self.assertNotIn("亿元", result["summary"])

    def test_persistent_chinese_unit_is_normalized_after_retry(self):
        class AlwaysPreservesUnitClient:
            is_mock = False

            def chat(self, system_prompt, user_prompt, **kwargs):
                return (
                    "The company reported net profit of 233.43亿元, setting a new record for the "
                    "period while the broader batch of headlines remained mixed and investors "
                    "continued monitoring subsequent company disclosures and market activity."
                )

        rows = backend_style_rows() + [
            {"news_title": "净利润233.43亿元", "news_content": "公司发布中期业绩。"}
        ]
        result = run_news_summary(rows, AlwaysPreservesUnitClient(), symbol="600030")

        self.assertEqual(result["metadata"]["unit_retry"], "true")
        self.assertEqual(result["metadata"]["summary_source"], "llm")
        self.assertIn("23.343 billion yuan", result["summary"])
        self.assertNotIn("亿元", result["summary"])

    def test_chinese_answer_triggers_english_retry(self):
        class ChineseThenEnglishClient:
            is_mock = False

            def __init__(self):
                self.calls = []

            def chat(self, system_prompt, user_prompt, **kwargs):
                self.calls.append(user_prompt)
                if len(self.calls) == 1:
                    # 中文整段没有空格，英文词数检查会判为不完整
                    return "整体舆情基调偏负面，公司参投私募基金属于财务性投资。"
                return (
                    "Recent coverage of the company centers on a 200 million yuan "
                    "investment into a private fund plus mixed capital-flow headlines, "
                    "leaving the overall tone slightly negative for now."
                )

        client = ChineseThenEnglishClient()
        result = run_news_summary(backend_style_rows(), client, symbol="300059")

        self.assertEqual(len(client.calls), 2)
        self.assertIn("MUST be written in English", client.calls[1])
        self.assertEqual(result["metadata"]["summary_source"], "llm")
        self.assertEqual(result["metadata"]["language_retry"], "true")
        self.assertTrue(result["summary"].startswith("Recent coverage"))

    def test_persistent_chinese_answer_falls_back(self):
        class AlwaysChineseClient:
            is_mock = False

            def chat(self, system_prompt, user_prompt, **kwargs):
                return "始终返回中文摘要。"

        result = run_news_summary(backend_style_rows(), AlwaysChineseClient(), symbol="300059")

        self.assertEqual(result["metadata"]["summary_source"], "deterministic_fallback")
        self.assertIn("300059", result["summary"])


if __name__ == "__main__":
    unittest.main()
