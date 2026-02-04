"""
M15 Filter Strategy - نسخه نهایی (اصلاح شده)

این ماژول فیلتر M15 با قوانین زیر:

1. فیلتر صفر (کندل بی‌معنی → REJECT):
   - (بدنه < 30% رنج AND ویک کل > 60% رنج) OR
   - بدنه < 20% رنج

2. کندل همروند سیگنال → EXECUTE_ALIGNED

3. کندل مخالف (Reversed) با شرایط سخت‌تر:
   - بدنه حداقل 55%
   - close در 30% انتهایی کندل
   - رنج ≥ میانگین 20 کندل قبلی
   → EXECUTE_REVERSED

4. در غیر این صورت → REJECT
"""

import MetaTrader5 as mt5
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict
from save_file import log as original_log
import inspect
import os


def log(message: str, color: str | None = None, save_to_file: bool = True):
    """Wrapper برای log با prefix"""
    try:
        frame = inspect.currentframe()
        caller = frame.f_back if frame else None
        lineno = getattr(caller, 'f_lineno', None)
        func = getattr(caller, 'f_code', None)
        fname = getattr(func, 'co_filename', None) if func else None
        funcname = getattr(func, 'co_name', None) if func else None
        base = os.path.basename(fname) if fname else 'unknown'
        prefix = f"[{base}:{funcname}:{lineno}] "
        return original_log(prefix + str(message), color=color, save_to_file=save_to_file)
    except Exception:
        return original_log(message, color=color, save_to_file=save_to_file)


def get_m15_candles(symbol: str, count: int = 21) -> Optional[list]:
    """
    دریافت کندل‌های M15 برای محاسبه میانگین
    
    Args:
        symbol: نماد معاملاتی
        count: تعداد کندل‌ها (پیش‌فرض 21 = 20 قبلی + 1 آخری)
    
    Returns:
        لیست کندل‌ها یا None
    """
    try:
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, count + 1)
        
        if rates is None or len(rates) < count:
            log(f"❌ Could not get {count} M15 candles for {symbol}", color='red')
            return None
        
        return rates
        
    except Exception as e:
        log(f"❌ Error getting M15 candles: {e}", color='red')
        return None


def calculate_avg_range(rates, current_idx: int, window: int = 20) -> float:
    """
    محاسبه میانگین رنج کندل‌های قبلی
    
    Args:
        rates: آرایه کندل‌ها
        current_idx: ایندکس کندل فعلی
        window: تعداد کندل‌های قبلی برای میانگین
    
    Returns:
        میانگین رنج
    """
    start_idx = max(0, current_idx - window)
    total_range = 0
    count = 0
    
    for i in range(start_idx, current_idx):
        candle_range = rates[i]['high'] - rates[i]['low']
        total_range += candle_range
        count += 1
    
    return total_range / count if count > 0 else 0


def is_candle_meaningful(candle: Dict, avg_range: float) -> Tuple[bool, str]:
    """
    فیلتر صفر: بررسی معنادار بودن کندل
    
    یک کندل بی‌معنی است اگر:
    - (بدنه < 30% رنج AND ویک کل > 60% رنج) OR
    - بدنه < 20% رنج
    
    Returns:
        (is_meaningful, reason)
    """
    candle_range = candle['high'] - candle['low']
    
    if candle_range == 0:
        return False, "رنج کندل صفر است"
    
    body = abs(candle['close'] - candle['open'])
    body_ratio = body / candle_range
    
    # شرط مستقیم: بدنه خیلی ضعیف (< 20%)
    if body_ratio < 0.20:
        return False, f"بدنه خیلی ضعیف: {body_ratio:.0%} < 20%"
    
    # ویک کل = رنج - بدنه
    wick_total = candle_range - body
    wick_ratio = wick_total / candle_range
    
    # شرط ترکیبی: بدنه ضعیف + فیتیله بلند
    if body_ratio < 0.30 and wick_ratio > 0.60:
        return False, f"کندل بی‌معنی: body={body_ratio:.0%}, wick={wick_ratio:.0%}"
    
    return True, "معتبر"


def is_reversed_valid(candle: Dict, avg_range: float) -> Tuple[bool, str]:
    """
    بررسی شرایط سخت‌گیرانه Reversed
    
    شرایط:
    1. بدنه حداقل 55%
    2. close در 30% انتهایی کندل
    3. رنج ≥ میانگین
    
    Returns:
        (is_valid, reason)
    """
    candle_range = candle['high'] - candle['low']
    
    if candle_range == 0:
        return False, "رنج صفر"
    
    body = abs(candle['close'] - candle['open'])
    body_ratio = body / candle_range
    
    # شرط 1: بدنه حداقل 55%
    if body_ratio < 0.55:
        return False, f"بدنه ضعیف: {body_ratio:.0%} < 55%"
    
    # شرط 2: close در 30% انتهایی
    close_position = (candle['close'] - candle['low']) / candle_range
    
    # اگر صعودی: close باید در 70% بالا باشد (30% انتهایی بالا)
    # اگر نزولی: close باید در 30% پایین باشد (30% انتهایی پایین)
    if candle['close'] > candle['open']:  # صعودی
        if close_position < 0.70:
            return False, f"close در {close_position:.0%} - نه در 30% بالایی"
    else:  # نزولی
        if close_position > 0.30:
            return False, f"close در {close_position:.0%} - نه در 30% پایینی"
    
    # شرط 3: رنج ≥ میانگین
    if candle_range < avg_range:
        return False, f"رنج کوچک: {candle_range:.5f} < avg {avg_range:.5f}"
    
    return True, f"Reversed معتبر: body={body_ratio:.0%}, close_pos={close_position:.0%}"


def get_last_completed_m15_candle(symbol: str) -> Optional[Dict]:
    """
    دریافت آخرین کندل M15 تکمیل‌شده (نه کندل در حال تشکیل)
    
    Returns:
        dict با کلیدهای: time, open, high, low, close, direction, body_ratio
        یا None در صورت خطا
    """
    try:
        # دریافت 22 کندل (20 برای میانگین + 1 تکمیل‌شده + 1 در حال تشکیل)
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 22)
        
        if rates is None or len(rates) < 22:
            log(f"❌ Could not get M15 candles for {symbol}", color='red')
            return None
        
        # کندل تکمیل‌شده - ایندکس -2 (آخرین کندل کامل قبل از کندل در حال تشکیل)
        candle = rates[-2]
        
        open_price = float(candle['open'])
        high_price = float(candle['high'])
        low_price = float(candle['low'])
        close_price = float(candle['close'])
        candle_time = datetime.fromtimestamp(candle['time'])
        
        # محاسبه جهت کندل
        if close_price > open_price:
            direction = 'bullish'
        elif close_price < open_price:
            direction = 'bearish'
        else:
            direction = 'neutral'
        
        # محاسبه نسبت بدنه
        candle_range = high_price - low_price
        body_size = abs(close_price - open_price)
        
        if candle_range > 0:
            body_ratio = (body_size / candle_range) * 100
        else:
            body_ratio = 0
        
        # محاسبه میانگین رنج 20 کندل قبلی
        avg_range = calculate_avg_range(rates, len(rates) - 2, window=20)
        
        return {
            'time': candle_time,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'direction': direction,
            'body_ratio': body_ratio,
            'range': candle_range,
            'body_size': body_size,
            'avg_range': avg_range
        }
        
    except Exception as e:
        log(f"❌ Error getting M15 candle: {e}", color='red')
        return None


def apply_m15_filter(
    signal_direction: str,  # 'buy' یا 'sell'
    entry_price: float,
    original_sl: float,
    win_ratio: float,
    symbol: str
) -> Tuple[str, str, float, float, float, Dict]:
    """
    اعمال فیلتر M15 نسخه نهایی
    
    Args:
        signal_direction: جهت سیگنال اصلی ('buy' یا 'sell')
        entry_price: قیمت ورود
        original_sl: استاپ‌لاس اصلی (fib 1.0)
        win_ratio: نسبت RR (مثلاً 2 برای 1:2)
        symbol: نماد معاملاتی
    
    Returns:
        Tuple[action, reason, final_sl, final_tp, final_direction, m15_info]
        - action: 'EXECUTE_ALIGNED', 'EXECUTE_REVERSED', 'REJECT'
        - reason: دلیل تصمیم
        - final_sl: استاپ‌لاس نهایی
        - final_tp: تیک‌پرافیت نهایی
        - final_direction: جهت نهایی پوزیشن ('buy' یا 'sell')
        - m15_info: اطلاعات کندل M15
    """
    
    # دریافت کندل M15
    m15 = get_last_completed_m15_candle(symbol)
    
    if m15 is None:
        log(f"⚠️ Could not get M15 candle - executing original signal", color='yellow')
        # در صورت عدم دسترسی به M15، سیگنال اصلی اجرا شود
        stop_distance = abs(entry_price - original_sl)
        if signal_direction == 'buy':
            final_tp = entry_price + (stop_distance * win_ratio)
        else:
            final_tp = entry_price - (stop_distance * win_ratio)
        
        return ('EXECUTE_ALIGNED', 'M15 data unavailable', original_sl, final_tp, signal_direction, {})
    
    avg_range = m15.get('avg_range', 0)
    
    log(f"📊 M15 Candle: time={m15['time']} dir={m15['direction']} body={m15['body_ratio']:.1f}% range={m15['range']:.5f} avg={avg_range:.5f}", color='cyan')
    
    # ===== فیلتر صفر: بررسی معنادار بودن کندل =====
    is_meaningful, meaning_reason = is_candle_meaningful(m15, avg_range)
    
    if not is_meaningful:
        log(f"🚫 M15 SKIP (فیلتر صفر): {meaning_reason}", color='yellow')
        return (
            'REJECT',
            f"فیلتر صفر: {meaning_reason}",
            0, 0, '',
            m15
        )
    
    # تعیین جهت مورد انتظار M15 (موافق با سیگنال)
    expected_m15_direction = 'bullish' if signal_direction == 'buy' else 'bearish'
    
    # بررسی تطابق جهت
    is_aligned = (m15['direction'] == expected_m15_direction)
    
    if is_aligned:
        # ✅ همروند - اجرای سیگنال اصلی
        log(f"✅ M15 ALIGNED: {m15['direction']} matches {signal_direction} signal", color='green')
        
        stop_distance = abs(entry_price - original_sl)
        if signal_direction == 'buy':
            final_tp = entry_price + (stop_distance * win_ratio)
        else:
            final_tp = entry_price - (stop_distance * win_ratio)
        
        return (
            'EXECUTE_ALIGNED',
            f"همروند ({m15['direction']}, body={m15['body_ratio']:.1f}%)",
            original_sl,
            final_tp,
            signal_direction,
            m15
        )
    
    else:
        # مخالف روند - بررسی شرایط سخت‌گیرانه Reversed
        reversed_ok, reversed_reason = is_reversed_valid(m15, avg_range)
        
        if reversed_ok:
            # ✅ Reversed معتبر - پوزیشن معکوس
            log(f"🔄 M15 REVERSED: {m15['direction']} - {reversed_reason}", color='blue')
            
            # معکوس کردن جهت
            reversed_direction = 'sell' if signal_direction == 'buy' else 'buy'
            
            # محاسبه SL و TP معکوس
            stop_distance = abs(entry_price - original_sl)
            
            if reversed_direction == 'buy':
                reversed_sl = entry_price - stop_distance
                reversed_tp = entry_price + (stop_distance * win_ratio)
            else:
                reversed_sl = entry_price + stop_distance
                reversed_tp = entry_price - (stop_distance * win_ratio)
            
            return (
                'EXECUTE_REVERSED',
                f"Reversed ({m15['direction']}) - {reversed_reason}",
                reversed_sl,
                reversed_tp,
                reversed_direction,
                m15
            )
        
        else:
            # ❌ Reversed نامعتبر - رد سیگنال
            log(f"❌ M15 REJECT: مخالف اما شرایط Reversed برقرار نیست - {reversed_reason}", color='red')
            
            return (
                'REJECT',
                f"مخالف ({m15['direction']}) - شرایط Reversed برقرار نیست: {reversed_reason}",
                0,
                0,
                '',
                m15
            )


def format_m15_email_info(action: str, reason: str, m15_info: Dict, 
                          original_direction: str, final_direction: str) -> str:
    """
    فرمت کردن اطلاعات M15 برای ایمیل
    """
    if not m15_info:
        return "M15 Info: Not available\n"
    
    status_emoji = {
        'EXECUTE_ALIGNED': '✅',
        'EXECUTE_REVERSED': '🔄',
        'REJECT': '❌'
    }.get(action, '❓')
    
    avg_range = m15_info.get('avg_range', 0)
    candle_range = m15_info.get('range', 0)
    range_ratio = (candle_range / avg_range * 100) if avg_range > 0 else 0
    
    lines = [
        f"\n📊 M15 Filter Analysis (نسخه نهایی):",
        f"   Status: {status_emoji} {action}",
        f"   Reason: {reason}",
        f"   M15 Candle Time: {m15_info.get('time', 'N/A')}",
        f"   M15 Direction: {m15_info.get('direction', 'N/A')}",
        f"   M15 Body Strength: {m15_info.get('body_ratio', 0):.1f}%",
        f"   M15 Range: {candle_range:.5f} (avg: {avg_range:.5f}, ratio: {range_ratio:.1f}%)",
        f"   Original Signal: {original_direction.upper()}",
    ]
    
    if action == 'EXECUTE_REVERSED':
        lines.append(f"   Final Direction: {final_direction.upper()} (REVERSED)")
    elif action == 'EXECUTE_ALIGNED':
        lines.append(f"   Final Direction: {final_direction.upper()} (ALIGNED)")
    
    return '\n'.join(lines) + '\n'


# تست ماژول
if __name__ == '__main__':
    # تست اتصال به MT5
    if not mt5.initialize():
        print("Failed to initialize MT5")
    else:
        print("MT5 initialized successfully")
        print("\n=== نسخه نهایی فیلتر M15 (اصلاح شده) ===")
        print("فیلتر صفر: (body<30% AND wick>60%) OR (body<20%) → REJECT")
        print("همروند: → EXECUTE_ALIGNED")
        print("Reversed: body≥55% AND close در 30% انتهایی AND range≥avg → EXECUTE_REVERSED")
        print("در غیر این صورت: → REJECT")
        
        # تست دریافت کندل M15
        candle = get_last_completed_m15_candle('EURUSD')
        if candle:
            print(f"\nLast M15 candle:")
            print(f"  Time: {candle['time']}")
            print(f"  Direction: {candle['direction']}")
            print(f"  Body ratio: {candle['body_ratio']:.1f}%")
            print(f"  Range: {candle['range']:.5f}")
            print(f"  Avg Range (20): {candle['avg_range']:.5f}")
            print(f"  O={candle['open']}, H={candle['high']}, L={candle['low']}, C={candle['close']}")
            
            # تست فیلتر صفر
            is_meaningful, meaning_reason = is_candle_meaningful(candle, candle['avg_range'])
            print(f"\n  فیلتر صفر: {'✅ معتبر' if is_meaningful else '🚫 ' + meaning_reason}")
            
            # تست شرایط Reversed
            reversed_ok, reversed_reason = is_reversed_valid(candle, candle['avg_range'])
            print(f"  شرایط Reversed: {'✅ ' + reversed_reason if reversed_ok else '❌ ' + reversed_reason}")
        
        # تست فیلتر
        print("\n--- Testing filter for BUY signal ---")
        result = apply_m15_filter(
            signal_direction='buy',
            entry_price=1.04500,
            original_sl=1.04300,
            win_ratio=2.0,
            symbol='EURUSD'
        )
        print(f"Action: {result[0]}")
        print(f"Reason: {result[1]}")
        print(f"SL: {result[2]}, TP: {result[3]}")
        print(f"Direction: {result[4]}")
        
        mt5.shutdown()
