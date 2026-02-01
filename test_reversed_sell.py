"""
تست شبیه‌سازی دقیق پوزیشن REVERSED - مثل main_metatrader_new.py
"""
import MetaTrader5 as mt5
from metatrader5_config import MT5_CONFIG
import time

def test_reversed_sell():
    """شبیه‌سازی دقیق کدی که در ربات برای reversed SELL اجرا می‌شود"""
    
    print("="*60)
    print("🧪 Testing REVERSED SELL (like main_metatrader_new.py)")
    print("="*60)
    
    if not mt5.initialize():
        print(f"❌ MT5 initialization failed")
        return
    
    print("✅ MT5 connected")
    
    symbol = MT5_CONFIG['symbol']
    win_ratio = MT5_CONFIG.get('win_ratio', 2)
    info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)
    
    print(f"\n📊 Symbol: {symbol}")
    print(f"   Ask: {tick.ask}")
    print(f"   Bid: {tick.bid}")
    print(f"   win_ratio: {win_ratio}")
    
    # شبیه‌سازی یک سیگنال BUY اصلی
    # فرض کنید یک swing تشخیص داده شده
    buy_entry_price = tick.ask  # قیمت ورود اصلی برای BUY
    stop = buy_entry_price - 0.0020  # 20 pips SL (مثلاً از fib 1.0)
    
    print(f"\n📊 Original BUY signal parameters:")
    print(f"   buy_entry_price: {buy_entry_price:.5f}")
    print(f"   original stop (fib 1.0): {stop:.5f}")
    
    # === این همان چیزی است که apply_m15_filter برمی‌گرداند برای REVERSED ===
    stop_distance = abs(buy_entry_price - stop)
    # برای SELL:
    reversed_sl = buy_entry_price + stop_distance  # SL بالای entry اصلی
    reversed_tp = buy_entry_price - (stop_distance * win_ratio)  # TP پایین entry اصلی
    final_direction = 'sell'
    
    print(f"\n📊 apply_m15_filter returns for REVERSED SELL:")
    print(f"   final_sl (from filter): {reversed_sl:.5f}")
    print(f"   final_tp (from filter): {reversed_tp:.5f}")
    print(f"   final_direction: {final_direction}")
    
    # === این مقادیر در main به trade_sl و trade_tp assign می‌شوند ===
    trade_type = final_direction  # 'sell'
    trade_sl = reversed_sl
    trade_tp = reversed_tp
    
    print(f"\n📊 Before recalculation:")
    print(f"   trade_sl: {trade_sl:.5f}")
    print(f"   trade_tp: {trade_tp:.5f}")
    
    # === گرفتن tick جدید (مثل main) ===
    last_tick = mt5.symbol_info_tick(symbol)
    
    # === این قسمت مشکل‌ساز است! ===
    # در main: if m15_action == 'EXECUTE_REVERSED' and trade_type == 'sell':
    actual_entry = last_tick.bid  # قیمت واقعی برای SELL
    original_stop_distance = abs(buy_entry_price - stop)  # فاصله SL اصلی
    trade_sl_recalc = actual_entry + original_stop_distance  # محاسبه مجدد!
    trade_tp_recalc = actual_entry - (original_stop_distance * win_ratio)  # محاسبه مجدد!
    
    print(f"\n📊 After recalculation (this overwrites!):")
    print(f"   actual_entry (bid): {actual_entry:.5f}")
    print(f"   trade_sl_recalc: {trade_sl_recalc:.5f}")
    print(f"   trade_tp_recalc: {trade_tp_recalc:.5f}")
    
    # استفاده از مقادیر محاسبه مجدد شده (مثل main)
    trade_sl = trade_sl_recalc
    trade_tp = trade_tp_recalc
    
    print(f"\n📊 Final values to send:")
    print(f"   trade_type: {trade_type}")
    print(f"   trade_sl: {trade_sl:.5f}")
    print(f"   trade_tp: {trade_tp:.5f}")
    
    # بررسی صحت SL/TP برای SELL
    entry_for_sell = last_tick.bid
    print(f"\n🔍 Validation for SELL:")
    print(f"   Entry (bid): {entry_for_sell:.5f}")
    print(f"   SL: {trade_sl:.5f} (should be > entry)")
    print(f"   TP: {trade_tp:.5f} (should be < entry)")
    
    if trade_sl <= entry_for_sell:
        print(f"   ❌ ERROR: SL ({trade_sl:.5f}) <= Entry ({entry_for_sell:.5f}) for SELL!")
    else:
        print(f"   ✅ SL position OK")
    
    if trade_tp >= entry_for_sell:
        print(f"   ❌ ERROR: TP ({trade_tp:.5f}) >= Entry ({entry_for_sell:.5f}) for SELL!")
    else:
        print(f"   ✅ TP position OK")
    
    # === تست ارسال واقعی ===
    print(f"\n📤 Testing actual order send...")
    
    volume = 0.01
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": mt5.ORDER_TYPE_SELL,
        "price": entry_for_sell,
        "sl": trade_sl,
        "tp": trade_tp,
        "deviation": 20,
        "magic": 234001,
        "comment": "Test REVERSED",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    print(f"   Request: {request}")
    
    # order_check
    check = mt5.order_check(request)
    print(f"\n📋 Order Check:")
    if check:
        print(f"   retcode: {check.retcode}")
        print(f"   comment: {check.comment}")
        if check.retcode != 0:
            print(f"   ❌ Check failed!")
            
            # تست با filling modes دیگر
            for fill_mode, fill_name in [(mt5.ORDER_FILLING_FOK, "FOK"), 
                                          (mt5.ORDER_FILLING_RETURN, "RETURN")]:
                request['type_filling'] = fill_mode
                check2 = mt5.order_check(request)
                print(f"   {fill_name}: retcode={check2.retcode if check2 else 'None'}, comment={check2.comment if check2 else 'N/A'}")
    else:
        print(f"   ❌ order_check returned None!")
        print(f"   last_error: {mt5.last_error()}")
    
    # ارسال
    if check and check.retcode == 0:
        print(f"\n📤 Sending order...")
        result = mt5.order_send(request)
        if result:
            print(f"   retcode: {result.retcode}")
            print(f"   comment: {result.comment}")
            if result.retcode == 10009:
                print(f"   ✅ SUCCESS!")
                # بستن
                time.sleep(1)
                positions = mt5.positions_get(symbol=symbol, magic=234001)
                if positions:
                    pos = positions[0]
                    tick = mt5.symbol_info_tick(symbol)
                    close_req = {
                        "action": mt5.TRADE_ACTION_DEAL,
                        "symbol": symbol,
                        "volume": volume,
                        "type": mt5.ORDER_TYPE_BUY,
                        "position": pos.ticket,
                        "price": tick.ask,
                        "deviation": 20,
                        "magic": 234001,
                        "comment": "Close",
                        "type_time": mt5.ORDER_TIME_GTC,
                        "type_filling": mt5.ORDER_FILLING_IOC,
                    }
                    mt5.order_send(close_req)
                    print(f"   Position closed")
            else:
                print(f"   ❌ FAILED!")
        else:
            print(f"   ❌ order_send returned None!")
    
    mt5.shutdown()
    print("\n✅ Test completed")

if __name__ == "__main__":
    test_reversed_sell()
