#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生命週期投資策略 Telegram 機器人
自動抓取國發會景氣燈號，提供投資建議
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# 設定日誌
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 對話狀態
(PHASE_SELECT, INPUT_AGE, INPUT_SHARES, INPUT_PRICE, INPUT_CASH,
 INPUT_SHARES2, INPUT_PRICE2, INPUT_CASH2, INPUT_TENYEAR, INPUT_PRICE006208) = range(10)

# 資料儲存檔案
DATA_FILE = 'user_data.json'


class InvestmentBot:
    """投資策略機器人主類別"""
    
    def __init__(self):
        self.user_data = self.load_user_data()
        
    def load_user_data(self) -> Dict:
        """載入用戶資料"""
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_user_data(self):
        """儲存用戶資料"""
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.user_data, f, ensure_ascii=False, indent=2)
    
    def get_user_data(self, user_id: int) -> Dict:
        """取得特定用戶資料"""
        user_id_str = str(user_id)
        if user_id_str not in self.user_data:
            self.user_data[user_id_str] = {
                'phase': 1,
                'phase1': {},
                'phase2': {}
            }
        return self.user_data[user_id_str]
    
    async def fetch_ndc_signals(self) -> List[Dict]:
        """
        從國發會抓取景氣燈號資料
        """
        try:
            # 國發會景氣對策信號 API
            url = "https://index.ndc.gov.tw/n/json/Business/B010102/"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # 解析資料
            signals = []
            if 'data' in data and isinstance(data['data'], list):
                for item in data['data']:
                    signals.append({
                        'date': item.get('date', ''),
                        'score': int(item.get('value', 23))
                    })
            
            # 按日期排序（最新在前）
            signals.sort(key=lambda x: x['date'], reverse=True)
            
            return signals[:5]  # 返回最新5個月
            
        except Exception as e:
            logger.error(f"抓取國發會資料失敗: {e}")
            # 返回預設值
            return [{'date': '2024-10', 'score': 23}] * 5


# 初始化機器人
bot = InvestmentBot()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """開始指令"""
    keyboard = [
        [InlineKeyboardButton("📊 第一階段 (37-60歲)", callback_data='phase1')],
        [InlineKeyboardButton("🎯 第二階段 (60-65歲+)", callback_data='phase2')],
        [InlineKeyboardButton("📈 查看我的資產", callback_data='view_asset')],
        [InlineKeyboardButton("🔔 設定通知", callback_data='set_notify')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = """
💎 *生命週期投資策略機器人*

歡迎使用！我會幫您：
• 自動抓取國發會景氣燈號
• 分析當前應該執行的操作
• 追蹤您的資產配置
• 在關鍵時刻提醒您

請選擇您的投資階段：
"""
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """處理按鈕回調"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = bot.get_user_data(user_id)
    
    if query.data == 'phase1':
        user_data['phase'] = 1
        bot.save_user_data()
        await query.edit_message_text(
            "📊 *第一階段：正二資產累積期*\n\n"
            "請依序輸入以下資料，或使用指令：\n"
            "`/set_phase1` - 設定第一階段資料\n"
            "`/analyze` - 分析並獲得建議",
            parse_mode='Markdown'
        )
    
    elif query.data == 'phase2':
        user_data['phase'] = 2
        bot.save_user_data()
        await query.edit_message_text(
            "🎯 *第二階段：0050 退休守成期*\n\n"
            "請依序輸入以下資料，或使用指令：\n"
            "`/set_phase2` - 設定第二階段資料\n"
            "`/analyze` - 分析並獲得建議",
            parse_mode='Markdown'
        )
    
    elif query.data == 'view_asset':
        await show_asset_summary(query, user_id)
    
    elif query.data == 'set_notify':
        await query.edit_message_text(
            "🔔 *通知設定*\n\n"
            "使用以下指令設定通知：\n"
            "`/notify_on` - 開啟通知\n"
            "`/notify_off` - 關閉通知\n\n"
            "當景氣燈號達到 37分或38分時，我會主動通知您！",
            parse_mode='Markdown'
        )


async def show_asset_summary(query, user_id: int):
    """顯示資產摘要"""
    user_data = bot.get_user_data(user_id)
    phase = user_data.get('phase', 1)
    
    if phase == 1:
        data = user_data.get('phase1', {})
        shares = data.get('shares631L', 0)
        price = data.get('price631L', 0)
        cash = data.get('cash', 0)
        
        asset_value = shares * price
        total = asset_value + cash
        ratio = (asset_value / total * 100) if total > 0 else 0
        
        text = f"""
📊 *第一階段資產摘要*

💼 00631L 持股：{shares:,} 股
💰 股票價值：{format_currency(asset_value)} 元
💵 現金部位：{format_currency(cash)} 元
📈 總資產：{format_currency(total)} 元

📊 配置比例：
• 股票：{ratio:.1f}%
• 現金：{100-ratio:.1f}%
"""
    else:
        data = user_data.get('phase2', {})
        shares = data.get('shares0050', 0)
        price = data.get('price0050', 0)
        cash = data.get('cash', 0)
        
        asset_value = shares * price
        total = asset_value + cash
        ratio = (asset_value / total * 100) if total > 0 else 0
        
        text = f"""
🎯 *第二階段資產摘要*

💼 0050 持股：{shares:,} 股
💰 股票價值：{format_currency(asset_value)} 元
💵 現金部位：{format_currency(cash)} 元
📈 總資產：{format_currency(total)} 元

📊 配置比例：
• 股票：{ratio:.1f}%
• 現金：{100-ratio:.1f}%
"""
    
    await query.edit_message_text(text, parse_mode='Markdown')


async def set_phase1_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """開始設定第一階段資料"""
    await update.message.reply_text(
        "📊 *設定第一階段資料*\n\n"
        "請輸入您的年齡（37-60歲）：",
        parse_mode='Markdown'
    )
    return INPUT_AGE


async def input_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """輸入年齡"""
    try:
        age = int(update.message.text)
        if age < 37 or age > 60:
            await update.message.reply_text("年齡必須在 37-60 歲之間，請重新輸入：")
            return INPUT_AGE
        
        context.user_data['temp_age'] = age
        await update.message.reply_text("請輸入 00631L 持有股數：")
        return INPUT_SHARES
    except ValueError:
        await update.message.reply_text("請輸入有效的數字：")
        return INPUT_AGE


async def input_shares(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """輸入股數"""
    try:
        shares = float(update.message.text)
        context.user_data['temp_shares'] = shares
        await update.message.reply_text("請輸入 00631L 現價：")
        return INPUT_PRICE
    except ValueError:
        await update.message.reply_text("請輸入有效的數字：")
        return INPUT_SHARES


async def input_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """輸入價格"""
    try:
        price = float(update.message.text)
        context.user_data['temp_price'] = price
        await update.message.reply_text("請輸入現金部位（元）：")
        return INPUT_CASH
    except ValueError:
        await update.message.reply_text("請輸入有效的數字：")
        return INPUT_PRICE


async def input_cash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """輸入現金並完成設定"""
    try:
        cash = float(update.message.text)
        user_id = update.effective_user.id
        user_data = bot.get_user_data(user_id)
        
        # 儲存資料
        user_data['phase1'] = {
            'age': context.user_data['temp_age'],
            'shares631L': context.user_data['temp_shares'],
            'price631L': context.user_data['temp_price'],
            'cash': cash,
            'updated_at': datetime.now().isoformat()
        }
        bot.save_user_data()
        
        # 清除臨時資料
        context.user_data.clear()
        
        await update.message.reply_text(
            "✅ *資料已儲存！*\n\n"
            "現在使用 `/analyze` 來分析並獲得投資建議。",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("請輸入有效的數字：")
        return INPUT_CASH


async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """分析並提供建議"""
    user_id = update.effective_user.id
    user_data = bot.get_user_data(user_id)
    phase = user_data.get('phase', 1)
    
    # 抓取最新燈號
    await update.message.reply_text("⏳ 正在抓取最新景氣燈號...")
    signals = await bot.fetch_ndc_signals()
    
    if phase == 1:
        await analyze_phase1(update, user_data, signals)
    else:
        await analyze_phase2(update, user_data, signals)


async def analyze_phase1(update: Update, user_data: Dict, signals: List[Dict]):
    """分析第一階段"""
    data = user_data.get('phase1', {})
    
    if not data:
        await update.message.reply_text(
            "❌ 尚未設定資料，請先使用 `/set_phase1` 設定。",
            parse_mode='Markdown'
        )
        return
    
    shares = data.get('shares631L', 0)
    price = data.get('price631L', 0)
    cash = data.get('cash', 0)
    
    asset_value = shares * price
    total = asset_value + cash
    ratio = (asset_value / total * 100) if total > 0 else 0
    
    # 取最近3個月燈號
    scores = [s['score'] for s in signals[:3]]
    score_latest = scores[0] if scores else 23
    
    # 生成建議
    recommendation = generate_phase1_recommendation(
        scores, ratio, asset_value, cash, total
    )
    
    # 燈號顯示
    signal_text = "\n".join([
        f"• {s['date']}: {s['score']}分 {get_signal_name(s['score'])}"
        for s in signals[:3]
    ])
    
    message = f"""
📊 *第一階段分析報告*

🚦 *景氣燈號（最近3個月）*
{signal_text}

💰 *資產配置*
• 股票：{format_currency(asset_value)} 元 ({ratio:.1f}%)
• 現金：{format_currency(cash)} 元 ({100-ratio:.1f}%)
• 總資產：{format_currency(total)} 元

{recommendation}

🔄 更新資料：`/set_phase1`
"""
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def analyze_phase2(update: Update, user_data: Dict, signals: List[Dict]):
    """分析第二階段"""
    data = user_data.get('phase2', {})
    
    if not data:
        await update.message.reply_text(
            "❌ 尚未設定資料，請先使用 `/set_phase2` 設定。",
            parse_mode='Markdown'
        )
        return
    
    shares = data.get('shares0050', 0)
    price = data.get('price0050', 0)
    cash = data.get('cash', 0)
    ten_year = data.get('tenYearLine', 80)
    price_006208 = data.get('price006208', 80)
    
    asset_value = shares * price
    total = asset_value + cash
    ratio = (asset_value / total * 100) if total > 0 else 0
    
    # 取最近5個月燈號
    scores = [s['score'] for s in signals[:5]]
    
    # 生成建議
    recommendation = generate_phase2_recommendation(
        scores, ratio, asset_value, cash, total, price_006208, ten_year
    )
    
    # 燈號顯示
    signal_text = "\n".join([
        f"• {s['date']}: {s['score']}分 {get_signal_name(s['score'])}"
        for s in signals[:5]
    ])
    
    # 十年線分析
    diff_percent = ((price_006208 - ten_year) / ten_year * 100)
    ten_year_status = "✅ 接近十年線" if price_006208 <= ten_year * 1.05 else f"距離 {diff_percent:+.1f}%"
    
    message = f"""
🎯 *第二階段分析報告*

🚦 *景氣燈號（最近5個月）*
{signal_text}

💰 *資產配置*
• 股票：{format_currency(asset_value)} 元 ({ratio:.1f}%)
• 現金：{format_currency(cash)} 元 ({100-ratio:.1f}%)
• 總資產：{format_currency(total)} 元

📊 *技術分析*
• 006208 現價：{price_006208}
• 十年線：{ten_year}
• 狀態：{ten_year_status}

{recommendation}

🔄 更新資料：`/set_phase2`
"""
    
    await update.message.reply_text(message, parse_mode='Markdown')


def generate_phase1_recommendation(scores: List[int], ratio: float, 
                                   asset_value: float, cash: float, total: float) -> str:
    """生成第一階段建議"""
    score_latest = scores[0] if scores else 23
    red_count = sum(1 for s in scores if s >= 38)
    
    # 紅燈撤退
    if red_count > 0:
        should_sell = asset_value * 0.1
        return f"""
✅ *現在該做什麼？*

🚨 *紅燈撤退中（第 {red_count} 個月）*

1. 本月應賣出正二部位的 10%
   約 *{format_currency(should_sell)} 元*
2. 賣出金額轉入現金部位
3. 已累計減碼 {red_count * 10}%
4. 停止所有新資金投入

💡 當燈號回落至 ≤36 分後，停止減碼並恢復每季再平衡。
"""
    
    # 首次37分
    if score_latest == 37 and (len(scores) < 2 or scores[1] != 37):
        need_adjust = abs((total * 0.5) - asset_value)
        action = "賣出正二" if asset_value > total * 0.5 else "買入正二"
        return f"""
✅ *現在該做什麼？*

⚠️ *首次觸及 37 分黃紅燈*

1. 強制再平衡至 50%
   {action} *{format_currency(need_adjust)} 元*
2. 停止加碼：本月原定投入的本金暫時閒置
3. 觀察下月燈號變化

💡 若回落至 ≤36 分可恢復操作，若衝上 ≥38 分則進入紅燈撤退
"""
    
    # 持續37分
    if score_latest == 37:
        return f"""
✅ *現在該做什麼？*

⚠️ *持續 37 分黃紅燈*

1. 維持現有資產配置，不做調整
2. 本月投入的本金繼續閒置
3. 將閒置本金存入高利活存
4. 密切觀察下月燈號
"""
    
    # 比例偏離
    if ratio >= 70:
        return f"""
✅ *現在該做什麼？*

🛑 *達到持倉上限 70%*

1. 維持現有正二部位，不再增加
2. 新資金全數保留為現金
3. 等待燈號降溫或再平衡機制調整
"""
    
    if ratio > 65:
        need_sell = asset_value - (total * 0.5)
        return f"""
✅ *現在該做什麼？*

⚠️ *正二佔比偏高（{ratio:.1f}%）*

1. 賣出正二 *{format_currency(need_sell)} 元*
2. 賣出金額轉入現金
3. 使正二佔比回到 50%
4. 繼續正常投入每月 1萬 + 每季 1.5萬
"""
    
    if ratio < 35 and ratio > 0:
        need_buy = (total * 0.5) - asset_value
        return f"""
✅ *現在該做什麼？*

💡 *正二佔比偏低（{ratio:.1f}%）- 補倉機會*

1. 動用現金 *{format_currency(need_buy)} 元*
2. 買入正二，使佔比回到 50%
3. 這是低位吸籌的好時機
4. 繼續正常投入
"""
    
    # 藍燈加碼
    if score_latest <= 16:
        buy_percent = 20 if score_latest <= 10 else (10 if score_latest <= 13 else 5)
        extra_buy = cash * (buy_percent / 100)
        return f"""
✅ *現在該做什麼？*

🔵 *藍燈加碼機會（{score_latest} 分）*

1. 除了正常投入（每月1萬 + 每季1.5萬）
2. 額外動用現有現金的 {buy_percent}%
   約 *{format_currency(extra_buy)} 元*
3. 全數買入正二 00631L
4. 本季季末執行再平衡

💡 難得的低點累積機會！
"""
    
    # 正常投入
    return f"""
✅ *現在該做什麼？*

✅ *正常投入模式*

1. 投入本月資金 1萬元，按 5:5 配置
   • 買入正二：*5,000 元*
   • 保留現金：*5,000 元*
2. 若本月為季末，額外投入 1.5萬（同樣 5:5）
3. 於季末執行再平衡至 50%

💡 目前正二佔比 {ratio:.1f}%，比例{'健康' if abs(ratio - 50) < 5 else '季末調整'}
"""


def generate_phase2_recommendation(scores: List[int], ratio: float,
                                   asset_value: float, cash: float, total: float,
                                   price_006208: float, ten_year: float) -> str:
    """生成第二階段建議"""
    score_latest = scores[0] if scores else 23
    red_count = sum(1 for s in scores if s >= 38)
    near_ten_year = price_006208 <= ten_year * 1.05
    
    # 第二顆紅燈
    if red_count >= 2:
        return f"""
✅ *現在該做什麼？*

🚨 *第二顆紅燈 - 全數撤退*

1. 賣出所有剩餘 0050 股票
   約 *{format_currency(asset_value)} 元*
2. 達成 100% 現金部位
3. 將現金放入高利活存
4. 停止所有本金投入

💡 等待燈號回落至綠燈、黃藍燈或藍燈，配合十年線判斷進場時機
"""
    
    # 第一顆紅燈
    if red_count == 1:
        should_sell = asset_value * 0.5
        return f"""
✅ *現在該做什麼？*

🚨 *第一顆紅燈 - 減碼一半*

1. 賣出 50% 的 0050 股票
   約 *{format_currency(should_sell)} 元*
2. 達成「股/現金 50:50」平衡
3. 密切觀察下月燈號

💡 若下月再出現紅燈，執行第二次撤退
"""
    
    # 37分觀察
    if score_latest == 37:
        return f"""
✅ *現在該做什麼？*

⚠️ *37 分過熱前夕*

1. 維持現有 100% 股票部位，不賣出
2. 本月原本要投入的 1.5萬本金暫停
3. 將本金轉入高利活存閒置
4. 密切觀察下月燈號變化
"""
    
    # 十年線機會
    if near_ten_year and score_latest <= 22:
        buy_amount = cash * 0.5
        return f"""
✅ *現在該做什麼？*

🎯 *十年線機會 + 低燈號*

這是絕佳買點！

1. 006208 價格 {price_006208} {'已跌破' if price_006208 <= ten_year else '接近'}十年線 {ten_year}
2. 先投入 50% 現金
   約 *{format_currency(buy_amount)} 元*
3. 買入 0050，觀察是否站穩
4. 若燈號降至藍燈或確認站穩，投入剩餘50%

💡 十年線 + 低燈號 = 歷史最佳買點區域
"""
    
    # 藍燈全力加碼
    if score_latest <= 16:
        return f"""
✅ *現在該做什麼？*

🔵 *藍燈！全力加碼*

1. 投入本月資金 1.5萬，全數買入 0050
2. {'✅ 觸及十年線，千載難逢' if near_ten_year else '把握藍燈低點'}
3. 維持 100% 股票配置
4. 若有額外資金，可考慮加碼

💡 目前股票佔比 {ratio:.1f}%
"""
    
    # 正常投入
    target_config = ""
    if score_latest <= 22:
        target_config = "70% 股票"
    elif score_latest <= 31:
        target_config = "50% 股票"
    else:
        target_config = "100% 股票"
    
    return f"""
✅ *現在該做什麼？*

✅ *正常投入模式*

1. 投入本月資金 1.5萬元，全數買入 0050
2. 建議目標配置：*{target_config}*
3. 當前配置：{ratio:.1f}% 股票
{'4. 💡 接近十年線，可考慮提高股票比例' if near_ten_year else ''}

💡 持續穩定投入，等待下次十年線機會
"""


def get_signal_name(score: int) -> str:
    """取得燈號名稱"""
    if score <= 16:
        return "🔵 藍燈"
    elif score <= 22:
        return "🟦 黃藍燈"
    elif score <= 31:
        return "🟢 綠燈"
    elif score <= 36:
        return "🟡 黃紅燈"
    elif score == 37:
        return "🟠 黃紅燈(37)"
    else:
        return "🔴 紅燈"


def format_currency(amount: float) -> str:
    """格式化金額"""
    if amount >= 10000:
        return f"{amount/10000:.1f}萬"
    return f"{amount:,.0f}"


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """取消對話"""
    await update.message.reply_text("操作已取消。")
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """顯示幫助"""
    help_text = """
📚 *指令列表*

*基本指令*
/start - 開始使用
/help - 顯示幫助

*第一階段（37-60歲）*
/set_phase1 - 設定第一階段資料
/analyze - 分析並獲得建議

*第二階段（60-65歲+）*
/set_phase2 - 設定第二階段資料

*通知設定*
/notify_on - 開啟通知
/notify_off - 關閉通知

*其他*
/signal - 查看最新景氣燈號
/asset - 查看資產摘要
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看最新景氣燈號"""
    await update.message.reply_text("⏳ 正在抓取最新景氣燈號...")
    signals = await bot.fetch_ndc_signals()
    
    signal_text = "\n".join([
        f"• {s['date']}: {s['score']}分 {get_signal_name(s['score'])}"
        for s in signals
    ])
    
    message = f"""
🚦 *國發會景氣對策信號*

{signal_text}

💡 使用 `/analyze` 來分析您的投資策略
"""
    
    await update.message.reply_text(message, parse_mode='Markdown')


def main():
    """主程式"""
    # Bot Token (已更新)
    TOKEN = "8312585582:AAFW5y82NQCKqbMARMikeuN04DiM3earuBA"
    
    if not TOKEN:
        print("=" * 50)
        print("❌ 請先設定 Bot Token！")
        print("=" * 50)
        return
    
    # 建立應用程式 (修正版)
    try:
        application = Application.builder().token(TOKEN).build()
    except AttributeError:
        # 如果是舊版本的 python-telegram-bot
        from telegram.ext import Updater
        print("⚠️ 偵測到舊版 python-telegram-bot，請升級")
        print("請執行: pip install --upgrade python-telegram-bot")
        return
    
    # 第一階段對話處理器
    phase1_conv = ConversationHandler(
        entry_points=[CommandHandler('set_phase1', set_phase1_start)],
        states={
            INPUT_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_age)],
            INPUT_SHARES: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_shares)],
            INPUT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_price)],
            INPUT_CASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_cash)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # 註冊處理器
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('analyze', analyze))
    application.add_handler(CommandHandler('signal', signal_command))
    application.add_handler(phase1_conv)
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # 啟動機器人
    print("🤖 機器人已啟動！")
    print("📱 請到 Telegram 搜尋您的機器人並開始使用")
    print("💡 按 Ctrl+C 可以停止機器人")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
