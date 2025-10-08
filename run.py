from datetime import datetime
import json, time, redis
from typing import Dict, Any, Optional, Union
from web.utils.analysis_runner import run_stock_analysis
from tradingagents.config.database_manager import get_database_manager

r = get_database_manager().get_redis_client()
# 模拟Web界面的进度更新函数
progress_messages = []

TASK_QUEUE = "TRADING_AGENTS:TASK_QUEUE"

def mock_update_progress(message, current=None, total=None):
    progress_messages.append(message)
    if current and total:
        print(f"📊 进度 {current}/{total}: {message}")
    else:
        print(f"📊 {message}")

def stock_analysis(params: Dict[str, Any]) -> Dict[str, Any]:
    return run_stock_analysis(**params)

def worker_loop():
    print("[Worker] 等待任务...")
    while True:
        try:
            task_data = r.brpop([TASK_QUEUE], timeout=5)  # 阻塞式读取
            if task_data:
                _, task_json = task_data
                task = json.loads(task_json)
                if 'task_id' in task:
                    task_id = task['task_id']
                else:
                    print("task_id is missing")
                    continue
                stock_analysis(task['params'])
        except redis.exceptions.TimeoutError:
            print("任务队列监听中...")
        except Exception as e:
            print(f"[Worker] 出错: {e}")
            time.sleep(5)

if __name__ == '__main__':
    worker_loop()
