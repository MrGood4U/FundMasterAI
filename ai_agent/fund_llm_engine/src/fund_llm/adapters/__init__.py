from fund_llm.adapters.backend_function_client import (
    BackendFunctionClient,
    build_fund_input_from_backend_functions,
)


def build_input_from_code(*args, **kwargs):
    from fund_llm.adapters.akshare_ingestion import build_input_from_code as _build_input_from_code

    return _build_input_from_code(*args, **kwargs)


__all__ = [
    "BackendFunctionClient",
    "build_fund_input_from_backend_functions",
    "build_input_from_code",
]
