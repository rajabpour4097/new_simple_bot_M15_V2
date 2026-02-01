"""
تست BUY و SELL برای بررسی تفاوت - آیا فقط یکی خطا می‌دهد؟
"""
import MetaTrader5 as mt5
from metatrader5_config import MT5_CONFIG
import time

def test_direction(direction='buy'):
    """تست یک جهت خاص"""
    print(f"\n{'='*50}")
    print(f"🧪 Testing {direction.upper()} order")
    print(f"{'='*50}")
    
    symbol = MT5_CONFIG['symbol']
    info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)
    
    point = info.point
    pip_size = 10 * point if info.digits in (3, 5) else point
    
    volume = 0.01
    
    if direction == 'buy':
        entry = tick.ask
        sl = entry - 20 * pip_size  # 20 pips below
        tp = entry + 40 * pip_size  # 40 pips above (RR=2)
        order_type = mt5.ORDER_TYPE_BUY
    else:  # sell
        entry = tick.bid
        sl = entry + 20 * pip_size  # 20 pips above
        tp = entry - 40 * pip_size  # 40 pips below (RR=2)
        order_type = mt5.ORDER_TYPE_SELL
    
    print(f"📊 Parameters:")
    print(f"   Symbol: {symbol}")
    print(f"   Entry: {entry:.{info.digits}f}")
    print(f"   SL: {sl:.{info.digits}f}")
    print(f"   TP: {tp:.{info.digits}f}")
    print(f"   Volume: {volume}")
    print(f"   pip_size: {pip_size}")
    print(f"   SL distance: {abs(entry - sl) / pip_size:.1f} pips")
    print(f"   TP distance: {abs(entry - tp) / pip_size:.1f} pips")
    
    # بررسی صحت SL/TP
    if direction == 'buy':
        if sl >= entry:
            print(f"   ❌ ERROR: SL ({sl}) >= Entry ({entry}) for BUY!")
            return None
        if tp <= entry:
            print(f"   ❌ ERROR: TP ({tp}) <= Entry ({entry}) for BUY!")
            return None
    else:
        if sl <= entry:
            print(f"   ❌ ERROR: SL ({sl}) <= Entry ({entry}) for SELL!")
            return None
        if tp >= entry:
            print(f"   ❌ ERROR: TP ({tp}) >= Entry ({entry}) for SELL!")
            return None
    
    print(f"   ✅ SL/TP validation passed")
    
    # ساخت request
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": entry,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": 234000,
        "comment": f"Test {direction}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    # order_check
    print(f"\n📋 Order Check:")
    check = mt5.order_check(request)
    if check:
        print(f"   retcode: {check.retcode}")
        print(f"   comment: {check.comment}")
        print(f"   margin: {check.margin}")
        if check.retcode != 0:
            print(f"   ❌ Check failed!")
            # تست FOK
            request['type_filling'] = mt5.ORDER_FILLING_FOK
            check2 = mt5.order_check(request)
            print(f"   FOK check: retcode={check2.retcode if check2 else 'None'}")
            # تست RETURN
            request['type_filling'] = mt5.ORDER_FILLING_RETURN
            check3 = mt5.order_check(request)
            print(f"   RETURN check: retcode={check3.retcode if check3 else 'None'}")
            return None
    else:
        print(f"   ❌ order_check returned None!")
        print(f"   last_error: {mt5.last_error()}")
        return None
    
    # ارسال واقعی
    print(f"\n📤 Sending order...")
    result = mt5.order_send(request)
    if result:
        print(f"   retcode: {result.retcode}")
        print(f"   deal: {result.deal}")
        print(f"   order: {result.order}")
        print(f"   comment: {result.comment}")
        
        if result.retcode == 10009:
            print(f"   ✅ SUCCESS! Order ticket: {result.order}")
            
            # بستن پوزیشن
            time.sleep(1)
            positions = mt5.positions_get(symbol=symbol, magic=234000)
            if positions:
                pos = positions[0]
                print(f"\n📤 Closing position {pos.ticket}...")
                tick = mt5.symbol_info_tick(symbol)
                close_type = mt5.ORDER_TYPE_SELL if direction == 'buy' else mt5.ORDER_TYPE_BUY
                close_price = tick.bid if direction == 'buy' else tick.ask
                
                close_req = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": volume,
                    "type": close_type,
                    "position": pos.ticket,
                    "price": close_price,
                    "deviation": 20,
                    "magic": 234000,
                    "comment": "Close test",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
                close_result = mt5.order_send(close_req)
                if close_result and close_result.retcode == 10009:
                    print(f"   ✅ Closed successfully!")
                else:
                    print(f"   ⚠️ Close retcode: {close_result.retcode if close_result else 'None'}")
            
            return result
        else:
            print(f"   ❌ FAILED!")
            return None
    else:
        print(f"   ❌ order_send returned None!")
        print(f"   last_error: {mt5.last_error()}")
        return None

def main():
    # اتصال به MT5
    if not mt5.initialize():
        print(f"❌ MT5 initialization failed: {mt5.last_error()}")
        return
    
    print("✅ MT5 connected")
    print(f"Symbol: {MT5_CONFIG['symbol']}")
    
    # اطلاعات حساب
    acc = mt5.account_info()
    term = mt5.terminal_info()
    print(f"\n📊 Account: Balance={acc.balance}, TradeAllowed={acc.trade_allowed}")
    print(f"📊 Terminal: TradeAllowed={term.trade_allowed}, Connected={term.connected}")
    
    # تست هر دو جهت
    buy_result = test_direction('buy')
    time.sleep(2)
    sell_result = test_direction('sell')
    
    # نتیجه نهایی
    print(f"\n{'='*50}")
    print("📊 SUMMARY:")
    print(f"   BUY:  {'✅ PASSED' if buy_result else '❌ FAILED'}")
    print(f"   SELL: {'✅ PASSED' if sell_result else '❌ FAILED'}")
    print(f"{'='*50}")
    
    mt5.shutdown()

if __name__ == "__main__":
    main()
