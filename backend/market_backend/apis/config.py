import os
from typing import Dict, Any
from configparser import ConfigParser

# 获取当前 Python 脚本所在的绝对路径
script_dir = os.path.dirname(os.path.abspath(__file__))

# 组合出配置文件的绝对路径
config_path = os.path.join(script_dir, "config.ini")

config = ConfigParser()
config.read(config_path)
config_dict = {
    'okx': {
        "api_key": config.get('okx', 'API_KEY'),
        "api_secret": config.get('okx', 'API_SECRET'),
        "api_pass": config.get('okx', 'API_PASS'),
    },
    'tickflow': {
        "api_key": config.get('tick_flow', 'API_KEY'),
    },
    'openbb': {
        "fmp_api_key": config.get('openbb', 'FMP_API_KEY', fallback=''),
    }
}

def get_okx_api_key() -> str:
    return config_dict['okx']['api_key']

def get_okx_api_secret() -> str:
    return config_dict['okx']['api_secret']

def get_okx_api_pass() -> str:
    return config_dict['okx']['api_pass']

def get_tickflow_api_key() -> str:
    return config_dict['tickflow']['api_key']

def get_openbb_fmp_api_key() -> str:
    return config_dict['openbb']['fmp_api_key']