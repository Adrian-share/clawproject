#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ETF 策略回测系统（策略2）- 价格突破M20策略"""

import json
import akshare as ak
from datetime import datetime
from pathlib import Path

# 配置文件路径
CONFIG_PATH = "/root/.openclaw/workspace/config/etf-monitor.json"
DATA_DIR = Path("/root/.openclaw/workspace/data/etf-monitor")
REPORT_DIR = Path("/root/.openclaw/workspace/reports")

DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

print("正在加载配置...")
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config = json.load(f)

etf_list = []
for category, etfs in config['etf_list'].items():
    for etf in etfs:
        etf['category'] = category
        etf_list.append(etf)

class BacktestEngine:
    def __init__(self, buy_amount=100):
        self.buy_amount = buy_amount
        self.cash = 0
        self.holdings = {}
        self.trades = []
        self.daily_values = []
    
    def calculate_signals(self, prices):
        """计算买入和卖出信号 - 策略2：价格突破M20"""
        if len(prices) < 21:
            return False, False, 0
        
        # 计算均线
        m5 = sum(prices[-5:]) / 5
        m10 = sum(prices[-10:]) / 10
        m20 = sum(prices[-20:]) / 20
        yesterday_m20 = sum(prices[-21:-1]) / 20
        
        current_price = prices[-1]
        
        # 买入信号：价格 > M20（价格在M20之上）
        buy_signal = current_price > m20
        
        # 卖出信号：M20 拐头向下
        sell_signal = m20 < yesterday_m20
        
        return buy_signal, sell_signal, m20
    
    def run_backtest(self, df, code, name):
        """对单个 ETF 进行回测"""
        df = df.sort_values('date').reset_index(drop=True)
        df = df.tail(252)  # 近一年的数据
        
        if len(df) < 21:
            return None
        
        cash = 0
        holdings = 0
        trades = []
        daily_values = []
        buy_signal_active = False
        
        for i in range(20, len(df)):
            row = df.iloc[i]
            date = row['date']
            price = row['close']
            prices = df.iloc[:i+1]['close'].tolist()
            
            # 计算信号
            buy_signal, sell_signal, m20 = self.calculate_signals(prices)
            
            # 处理买入信号
            if buy_signal and not buy_signal_active:
                buy_signal_active = True
                trades.append({
                    'date': date,
                    'action': 'BUY_START',
                    'price': price,
                    'amount': 0,
                    'shares': holdings,
                    'm20': m20,
                    'reason': '价格突破M20'
                })
            
            # 处理每日买入
            if buy_signal_active and not sell_signal:
                shares_to_buy = self.buy_amount / price
                cash -= self.buy_amount
                holdings += shares_to_buy
                
                trades.append({
                    'date': date,
                    'action': 'BUY_DAILY',
                    'price': price,
                    'amount': self.buy_amount,
                    'shares': holdings,
                    'm20': m20,
                    'reason': '每日定投'
                })
            
            # 处理卖出信号
            if sell_signal and buy_signal_active:
                sell_amount = holdings * price
                cash += sell_amount
                
                trades.append({
                    'date': date,
                    'action': 'SELL_ALL',
                    'price': price,
                    'amount': sell_amount,
                    'shares': 0,
                    'm20': m20,
                    'reason': 'M20拐头向下',
                    'profit': sell_amount + cash
                })
                
                holdings = 0
                buy_signal_active = False
            
            # 记录每日资产价值
            total_value = cash + holdings * price
            daily_values.append({
                'date': date,
                'price': price,
                'holdings': holdings,
                'cash': cash,
                'total_value': total_value,
                'buy_signal': buy_signal_active,
                'sell_signal': sell_signal,
                'm20': m20
            })
        
        final_value = cash + holdings * df.iloc[-1]['close']
        total_invested = -sum(t['amount'] for t in trades if t['action'] in ['BUY_DAILY'])
        
        return {
            'code': code,
            'name': name,
            'start_date': df.iloc[0]['date'],
            'end_date': df.iloc[-1]['date'],
            'start_price': df.iloc[0]['close'],
            'end_price': df.iloc[-1]['close'],
            'final_value': final_value,
            'total_invested': total_invested,
            'total_profit': final_value,
            'profit_pct': (final_value / abs(total_invested) - 1) * 100 if total_invested != 0 else 0,
            'holdings': holdings,
            'trade_count': len(trades),
            'trades': trades,
            'daily_values': daily_values
        }

print(f"\n{'='*60}")
print("ETF 策略回测系统 - 策略2（价格突破M20）")
print(f"{'='*60}")
print(f"回测周期: 近一年（约252个交易日）")
print(f"买入金额: 每天100元")
print(f"卖出规则: 收到卖出信号后全部卖出")
print(f"{'='*60}\n")

results = []
failed_etfs = []

for etf in etf_list:
    code = etf['code']
    name = etf['name']
    category = etf['category']
    
    if code.startswith('51') or code.startswith('58'):
        symbol = 'sh' + code
    else:
        symbol = 'sz' + code
    
    try:
        print(f"正在回测 {name} ({code})...", end=' ')
        df = ak.fund_etf_hist_sina(symbol=symbol)
        
        engine = BacktestEngine(buy_amount=100)
        result = engine.run_backtest(df, code, name)
        
        if result:
            result['category'] = category
            results.append(result)
            
            total_invested = result['total_invested']
            total_profit = result['total_profit']
            profit_pct = (total_profit / abs(total_invested) * 100) if total_invested != 0 else 0
            
            print(f"✅ 投入: {-total_invested:.2f}, 收益: {total_profit:.2f} ({profit_pct:.2f}%)")
        else:
            print(f"⏭️ 数据不足，跳过")
            failed_etfs.append(f"{name} ({code}) - 数据不足")
            
    except Exception as e:
        print(f"❌ 失败: {e}")
        failed_etfs.append(f"{name} ({code}) - {str(e)}")

# 生成报告
print(f"\n{'='*60}")
print("回测结果汇总 - 策略2（价格突破M20）")
print(f"{'='*60}\n")

results_sorted = sorted(results, key=lambda x: (x['total_profit'] / abs(x['total_invested']) if x['total_invested'] != 0 else -999), reverse=True)

report_lines = [
    "ETF 策略回测报告 - 策略2（价格突破M20）",
    f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    f"回测周期: 近一年",
    "",
    "================================",
    "策略说明",
    "================================",
    "买入信号: 价格 > M20（价格在M20之上）",
    "卖出信号: M20 拐头向下",
    "买入规则: 收到买入信号后，每天定投100元",
    "卖出规则: 收到卖出信号后，全部卖出持仓",
    "",
    "================================",
    "回测结果（按收益率排序）",
    "================================",
    ""
]

total_profit = 0
winning_trades = 0

for i, result in enumerate(results_sorted, 1):
    total_invested = result['total_invested']
    total_profit_val = result['total_profit']
    profit_pct = (total_profit_val / abs(total_invested) * 100) if total_invested != 0 else 0
    
    if total_profit_val > 0:
        winning_trades += 1
    
    total_profit += total_profit_val
    
    status = "🟢" if total_profit_val > 0 else "🔴"
    report_lines.extend([
        f"{status} #{i} {result['name']} ({result['code']})",
        f"    分类: {result['category']}",
        f"    投入: {-total_invested:.2f} 元",
        f"    收益: {total_profit_val:.2f} 元 ({profit_pct:+.2f}%)",
        f"    交易次数: {result['trade_count']} 次",
        f"    最终持仓: {result['holdings']:.2f} 份",
        ""
    ])

win_rate = (winning_trades / len(results) * 100) if len(results) > 0 else 0
avg_profit = total_profit / len(results) if len(results) > 0 else 0

report_lines.extend([
    "================================",
    "汇总统计",
    "================================",
    f"回测标的数: {len(results)}",
    f"盈利标的数: {winning_trades}",
    f"胜率: {win_rate:.2f}%",
    f"总收益: {total_profit:.2f} 元",
    f"平均收益: {avg_profit:.2f} 元",
    ""
])

if failed_etfs:
    report_lines.extend([
        "================================",
        "失败/跳过的标的",
        "================================"
    ])
    for item in failed_etfs:
        report_lines.append(f"❌ {item}")
    report_lines.append("")

report_lines.extend([
    "================================",
    "详细交易记录示例",
    "================================",
    ""
])

# 显示第一个有交易的标的的详细记录
for result in results_sorted:
    if result['trades']:
        report_lines.extend([
            f"标的: {result['name']} ({result['code']})",
            ""
        ])
        
        trades_to_show = result['trades'][:15]
        for trade in trades_to_show:
            if trade['action'] == 'BUY_START':
                report_lines.append(f"  {trade['date']} 🟢 买入信号出现 (价格 > M20: {trade['m20']:.4f})")
            elif trade['action'] == 'BUY_DAILY':
                report_lines.append(f"  {trade['date']} 💰 买入 {trade['amount']:.2f} 元 @ {trade['price']:.4f} (M20: {trade['m20']:.4f})")
            elif trade['action'] == 'SELL_ALL':
                report_lines.append(f"  {trade['date']} 🔴 卖出全部 @ {trade['price']:.4f}, 回收 {trade['amount']:.2f} 元 (M20: {trade['m20']:.4f})")
        
        if len(result['trades']) > 15:
            report_lines.append(f"  ... 还有 {len(result['trades']) - 15} 笔交易")
        
        report_lines.extend([
            f"",
            f"  回测期末: {result['end_date']}",
            f"  期末价格: {result['end_price']:.4f}",
            f"  剩余持仓: {result['holdings']:.2f} 份",
            f"  持仓市值: {result['holdings'] * result['end_price']:.2f} 元",
            f"  累计收益: {result['total_profit']:.2f} 元",
            ""
        ])
        break

report = "\n".join(report_lines)

report_file = REPORT_DIR / ("backtest_strategy2_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".txt")
with open(report_file, 'w', encoding='utf-8') as f:
    f.write(report)

def jsonify_result(result):
    result_copy = result.copy()
    result_copy['start_date'] = str(result_copy['start_date'])
    result_copy['end_date'] = str(result_copy['end_date'])
    result_copy['trades'] = [{**t, 'date': str(t['date'])} for t in result_copy['trades']]
    result_copy['daily_values'] = [{**d, 'date': str(d['date'])} for d in result_copy['daily_values']]
    return result_copy

json_file = REPORT_DIR / ("backtest_strategy2_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".json")
with open(json_file, 'w', encoding='utf-8') as f:
    json.dump({
        'timestamp': datetime.now().isoformat(),
        'strategy': {
            'name': '价格突破M20',
            'buy_signal': '价格 > M20',
            'sell_signal': 'M20 拐头向下'
        },
        'summary': {
            'total_etfs': len(results),
            'winning_trades': winning_trades,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'avg_profit': avg_profit
        },
        'results': [jsonify_result(r) for r in results_sorted]
    }, f, ensure_ascii=False, indent=2)

print(report)
print(f"\n报告已保存: {report_file}")
print(f"详细数据已保存: {json_file}")
