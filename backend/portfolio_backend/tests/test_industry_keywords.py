from utils.industry_keywords import classify_stock


class TestClassifyStock:
    def test_classify(self):
        assert classify_stock("恒瑞医药") == "制造业"
