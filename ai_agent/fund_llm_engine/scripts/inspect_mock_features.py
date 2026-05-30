import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from fund_llm.contracts import FundAnalysisInput
from fund_llm.feature_builder import FeatureBuilder
from fund_llm.mock_pipeline import build_mock_input


def main() -> None:
    if len(sys.argv) > 1:
        input_path = os.path.abspath(sys.argv[1])
        with open(input_path, "r", encoding="utf-8") as file:
            payload = FundAnalysisInput.from_dict(json.load(file))
    else:
        payload = build_mock_input()

    features = FeatureBuilder().build(payload).to_dict()
    print(json.dumps(features, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
