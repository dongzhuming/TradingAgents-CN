#!/usr/bin/env python3
"""
米筐金融数据源工具
提供rqdatac数据获取的统一接口
"""

import pandas as pd
from typing import Optional, Dict, Any
import warnings
from datetime import datetime, timedelta
import requests
import time, os

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')
warnings.filterwarnings('ignore')

class RqDataProvider:

    """米筐金融数据提供器"""
    def __init__(self):
        """初始化米筐金融提供器"""
        try:
            self.connected = False
            self.auth_url = 'https://rqdata.ricequant.com/auth'
            self.data_url = 'https://rqdata.ricequant.com/api'
            response = self._authorize()
            if response.ok:
                self.connected = True
                self._token = response.text
                logger.info(f"✅ RiceQuant金融数据接口授权成功")
            else:
                self.connected = False
                logger.error(f"❌ RiceQuant金融数据接口授权失败。[错误码]：{response.status_code}，[原因]: {response.text}")

            # 设置更长的超时时间
            # self._configure_timeout()


        except ImportError:
            self.ak = None
            self.connected = False
            logger.error(f"❌ RiceQuant金融数据接口授权失败")

    def _authorize(self):
        # 获取API token
        user_name = os.getenv('RICEQUANT_USERNAME', '')
        password = os.getenv('RICEQUANT_PASSWORD', '')

        if not user_name or not password:
            logger.warning("⚠️ 无法获取米筐用户名密码，请检查配置(RICEQUANT_USERNAME= , RICEQUANT_PASSWORD=)")
            return
        auth_json = {'user_name': user_name, 'password': password}
        return requests.post(self.auth_url, json=auth_json)

    def _normalize_symbol(self, symbol) -> str:
        """
        标准化股票代码为RiceQuant格式

        Args:
            symbol: 原始股票代码

        Returns:
            str: RiceQuant格式的股票代码
        """
        return self.id_convert([symbol])[0]
        # data_json = {'method': 'id_convert', 'order_book_ids': [symbol]}
        # headers = {'token': self._token}
        # response = requests.post(self.data_url, json=data_json, headers=headers)
        # _split = response.text.split('\n')
        # return _split[1]

    def _parse_data(self, response, **kwargs) -> pd.DataFrame:
        from io import StringIO
        data = StringIO(response.text)
        df = pd.read_csv(data, **kwargs)
        return df

    def id_convert(self, symbols: list[str]) -> list[str]:
        try:
            data_json = {'method': 'id_convert', 'order_book_ids': symbols}
            headers = {'token': self._token}
            response = requests.post(self.data_url, json=data_json, headers=headers)
            return self._parse_data(response)['order_book_id'].tolist()
        except Exception as e:
            logger.error(f"❌ [RiceQuant数据详细日志] 无法转换股票代码({symbols})")
            return []

    def get_stock_data(self, symbol: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取股票日线数据

        Args:
            symbol: 股票代码（如：000001 或 000001.SZ）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）

        Returns:
            DataFrame: 日线数据
        """
        # 记录详细的调用信息
        logger.info(f"🔍 [RiceQuant数据详细日志] get_stock_daily 开始执行")
        logger.info(
            f"🔍 [RiceQuant数据详细日志] 输入参数: symbol='{symbol}', start_date='{start_date}', end_date='{end_date}'")
        logger.info(f"🔍 [RiceQuant数据详细日志] 连接状态: {self.connected}")

        if not self.connected:
            logger.error(f"❌ [RiceQuant数据详细日志] 未连接，无法获取数据")
            return pd.DataFrame()

        try:
            # 标准化股票代码
            logger.debug(f"🔍 [股票代码追踪] get_stock_daily 调用 _normalize_symbol，传入参数: '{symbol}'")
            order_book_id = self._normalize_symbol(symbol)
            logger.debug(f"🔍 [股票代码追踪] _normalize_symbol 返回结果: '{order_book_id}'")

            # 设置默认日期
            original_start = start_date
            original_end = end_date

            if end_date is None:
                end_date = datetime.now().strftime('%Y%m%d')
                logger.info(f"🔍 [RiceQuant详细日志] 结束日期为空，设置为当前日期: {end_date}")
            else:
                end_date = end_date.replace('-', '')
                logger.debug(f"🔍 [RiceQuant详细日志] 结束日期转换: '{original_end}' -> '{end_date}'")

            if start_date is None:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
                logger.info(f"🔍 [RiceQuant详细日志] 开始日期为空，设置为一年前: {start_date}")
            else:
                start_date = start_date.replace('-', '')
                logger.debug(f"🔍 [RiceQuant详细日志] 开始日期转换: '{original_start}' -> '{start_date}'")

            logger.info(f"🔄 从RiceQuant获取{order_book_id}数据 ({start_date} 到 {end_date})...")
            logger.info(
                f"🔍 [股票代码追踪] 调用 RiceQuant API daily，传入参数: order_book_id='{order_book_id}', start_date='{start_date}', end_date='{end_date}'")

            # 记录API调用前的状态
            api_start_time = time.time()
            logger.debug(f"🔍 [RiceQuant详细日志] API调用开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}")

            # 获取日线数据
            try:
                data_json = {'method': 'get_price', 'order_book_ids': [order_book_id],
                             'start_date': start_date, 'end_date':end_date}
                headers = {'token': self._token}
                response = requests.post(self.data_url, json=data_json, headers=headers)
                data = self._parse_data(response, index_col=[0, 1])
                api_duration = time.time() - api_start_time
                logger.info(f"🔍 [RiceQuant详细日志] API调用完成，耗时: {api_duration:.3f}秒")

            except Exception as api_error:
                api_duration = time.time() - api_start_time
                logger.error(f"❌ [RiceQuant详细日志] API调用异常，耗时: {api_duration:.3f}秒")
                logger.error(f"❌ [RiceQuant详细日志] API异常类型: {type(api_error).__name__}")
                logger.error(f"❌ [RiceQuant详细日志] API异常信息: {str(api_error)}")
                raise api_error

            # 详细记录返回数据的信息
            logger.info(
                f"🔍 [股票代码追踪] RiceQuant API get_price 返回数据形状: {data.shape if data is not None and hasattr(data, 'shape') else 'None'}")
            logger.info(f"🔍 [RiceQuant详细日志] 返回数据类型: {type(data)}")

            if data is not None:
                logger.debug(f"🔍 [RiceQuant详细日志] 数据是否为空: {data.empty}")
                if not data.empty:
                    logger.debug(f"🔍 [RiceQuant详细日志] 数据列名: {list(data.columns)}")
                    logger.debug(f"🔍 [RiceQuant详细日志] 数据索引类型: {type(data.index)}")
                    if 'order_book_id' in data.columns:
                        unique_codes = data['order_book_id'].unique()
                        logger.info(f"🔍 [股票代码追踪] 返回数据中的order_book_id: {unique_codes}")
                    if 'trade_date' in data.columns:
                        date_range = f"{data['trade_date'].min()} 到 {data['trade_date'].max()}"
                        logger.debug(f"🔍 [RiceQuant详细日志] 数据日期范围: {date_range}")
                else:
                    logger.warning(f"⚠️ [RiceQuant详细日志] 返回的DataFrame为空")
            else:
                logger.warning(f"⚠️ [RiceQuant详细日志] 返回数据为None")

            if data is not None and not data.empty:

                logger.debug(f"✅ 获取{symbol}数据成功: {len(data)}条")

                # 缓存数据
                # if self.enable_cache and self.cache_manager:
                #     try:
                #         logger.info(f"🔍 [Tushare详细日志] 开始缓存数据...")
                #         cache_key = self.cache_manager.save_stock_data(
                #             symbol=symbol,
                #             data=data,
                #             data_source="tushare"
                #         )
                #         logger.info(f"💾 A股历史数据已缓存: {symbol} (tushare) -> {cache_key}")
                #         logger.info(f"🔍 [Tushare详细日志] 数据缓存完成")
                #     except Exception as cache_error:
                #         logger.error(f"⚠️ 缓存保存失败: {cache_error}")
                #         logger.error(f"⚠️ [Tushare详细日志] 缓存异常类型: {type(cache_error).__name__}")

                logger.info(f"🔍 [RiceQuant详细日志] get_stock_daily 执行成功，返回数据")
                return data
            else:
                logger.warning(f"⚠️ RiceQuant返回空数据: {order_book_id}")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"❌ 获取{symbol}数据失败: {e}")
            logger.error(f"❌ [RiceQuant] 异常类型: {type(e).__name__}")
            logger.error(f"❌ [RiceQuant] 异常信息: {str(e)}")
            import traceback
            logger.error(f"❌ [RiceQuant] 异常堆栈: {traceback.format_exc()}")
            return pd.DataFrame()

    def get_stock_info(self, symbol: str) -> Dict:
        if not self.connected:
            return {'symbol': symbol, 'name': f'未知股票{symbol}', 'source': 'unknown'}
        try:
            logger.info(f"🔍 [RiceQuant详细日志] 查询合约({symbol})基本信息")
            order_book_id = self._normalize_symbol(symbol)
            data_json = {'method': 'instruments', 'order_book_ids': [order_book_id]}
            headers = {'token': self._token}
            response = requests.post(self.data_url, json=data_json, headers=headers)
            instrument = self._parse_data(response).iloc[0].to_dict()
            logger.info(f"🔍 [RiceQuant详细日志] instruments 执行成功，返回数据")
            return {'symbol': symbol,
                    'trading_code': instrument['trading_code'],
                    'name': instrument['symbol'],  # 米筐symbol为证券名称
                    'industry': instrument['industry_name'],
                    'sector': instrument['sector_code_name'],
                    'list_date': instrument['listed_date'],
                    'market': instrument['board_type'],
                    'area': instrument['province'],
                    'source': 'RiceQuant'
                    }

        except Exception as e:
            logger.error(f"❌ 获取{symbol}数据失败: {e}")
            logger.error(f"❌ [RiceQuant] 异常类型: {type(e).__name__}")
            logger.error(f"❌ [RiceQuant] 异常信息: {str(e)}")
            import traceback
            logger.error(f"❌ [RiceQuant] 异常堆栈: {traceback.format_exc()}")
            return {}

    def get_financial_data(self, symbol: str, period: str) -> Dict:
        """
        获取财务数据

        Args:
            symbol: 股票代码
            period: 报告期（YYYYMMDD）

        Returns:
            Dict: 财务数据
        """
        if not self.connected:
            return {}

        try:
            logger.info(f"🔍 [RiceQuant详细日志] 查询合约({symbol})快报信息")
            order_book_id = self._normalize_symbol(symbol)

            factors = ['pe_ratio_ttm', 'pb_ratio_ttm', 'ps_ratio_ttm', 'dividend_yield_ttm', 'return_on_equity_ttm',
                       'return_on_asset_ttm', 'gross_profit_margin_ttm', 'net_profit_margin_ttm',
                       'debt_to_asset_ratio_ttm', 'current_ratio_ttm', 'quick_ratio_ttm', 'cash_ratio_ttm']
            # 获取快报数据
            data_json = {'method': 'get_factor', 'order_book_ids': order_book_id, 'factor': factors,
                         'start_date': period, 'end_date': period}
            headers = {'token': self._token}
            response = requests.post(self.data_url, json=data_json, headers=headers)
            logger.info(f"🔍 [RiceQuant详细日志] current_performance 执行成功，返回数据")
            data = self._parse_data(response).iloc[0].to_dict()

            return data
        except Exception as e:
            logger.error(f"❌ 获取{symbol}数据失败: {e}")
            logger.error(f"❌ [RiceQuant] 异常类型: {type(e).__name__}")
            logger.error(f"❌ [RiceQuant] 异常信息: {str(e)}")
            import traceback
            logger.error(f"❌ [RiceQuant] 异常堆栈: {traceback.format_exc()}")
            return {}

    def get_previous_trading_date(self, period: str):
        if not self.connected:
            return None

        try:
            logger.info(f"🔍 [RiceQuant详细日志] 获取前一个交易日")
            data_json = {'method': 'get_previous_trading_date', 'date': period, 'n': 1, 'market': 'cn'}
            headers = {'token': self._token}
            response = requests.post(self.data_url, json=data_json, headers=headers)
            logger.info(f"🔍 [RiceQuant详细日志] get_previous_trading_date 执行成功，返回数据")
            return response.text.split('\n')[1]
        except Exception as e:
            logger.error(f"❌ 获取前一个交易日失败: {e}")
            logger.error(f"❌ [RiceQuant] 异常类型: {type(e).__name__}")
            logger.error(f"❌ [RiceQuant] 异常信息: {str(e)}")
            import traceback
            logger.error(f"❌ [RiceQuant] 异常堆栈: {traceback.format_exc()}")
            return None

# 全局提供器实例
_rqdata_provider = None

def get_rqdata_provider() -> RqDataProvider:
    """获取全局RqData提供器实例"""
    global _rqdata_provider
    if _rqdata_provider is None:
        _rqdata_provider = RqDataProvider()
    return _rqdata_provider

if __name__ == '__main__':
    # RqDataProvider().get_stock_daily('601919', '2025-01-01', '2025-02-01')
    # print(RqDataProvider().get_stock_info('601919'))
    print(RqDataProvider().get_financial_data('601919', '2025-09-12'))