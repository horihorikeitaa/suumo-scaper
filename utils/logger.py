import logging
import config


def setup_logger():
    """ロガーを設定する関数"""
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    )
    return logging.getLogger()
