"""
تست ارسال سفارش - بررسی علت خطا
"""
import MetaTrader5 as mt5
from metatrader5_config import MT5_CONFIG

def test_order():
    # اتصال به MT5
    if not mt5.initialize():
        print(f"❌ MT5 initialize failed: {mt5.last_error()}")
        return
    
    print(f"✅ MT5 connected")
    
    # اطلاعات حساب
    acc = mt5.account_info()
    print(f"\n📊 Account Info:")
    print(f"   Balance: {acc.balance}")
    print(f"   Equity: {acc.equity}")
    print(f"   Trade mode: {acc.trade_mode}")
    print(f"   Trade allowed: {acc.trade_allowed}")
    
    # اطلاعات ترمینال
    term = mt5.terminal_info()
    print(f"\n📊 Terminal Info:")
    print(f"   Trade allowed: {term.trade_allowed}")
    print(f"   Connected: {term.connected}")
    
    # اطلاعات symbol
    symbol = MT5_CONFIG['symbol']
    info = mt5.symbol_info(symbol)
    print(f"\n📊 Symbol Info ({symbol}):")
    print(f"   Trade mode: {info.trade_mode}")  # 0=disabled, 4=full
    print(f"   Filling mode: {info.filling_mode}")
    print(f"   Visible: {info.visible}")
    print(f"   Point: {info.point}")
    print(f"   Digits: {info.digits}")
    print(f"   Min volume: {info.volume_min}")
    print(f"   Max volume: {info.volume_max}")
    print(f"   Volume step: {info.volume_step}")
    
    # گرفتن tick
    tick = mt5.symbol_info_tick(symbol)
    print(f"\n📊 Current Tick:")
    print(f"   Bid: {tick.bid}")
    print(f"   Ask: {tick.ask}")
    print(f"   Spread: {(tick.ask - tick.bid) * 10000:.1f} pips")
    
    # تست ارسال سفارش کوچک
    entry = tick.ask
    sl = entry - 0.0010  # 10 pips
    tp = entry + 0.0020  # 20 pips
    volume = 0.01
    
    print(f"\n📤 Testing BUY order:")
    print(f"   Entry: {entry}")
    print(f"   SL: {sl}")
    print(f"   TP: {tp}")
    print(f"   Volume: {volume}")
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": mt5.ORDER_TYPE_BUY,
        "price": entry,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": 234000,
        "comment": "Test order",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    # order_check قبل از ارسال
    check = mt5.order_check(request)
    print(f"\n📋 Order Check Result:")
    if check:
        print(f"   retcode: {check.retcode}")
        print(f"   comment: {check.comment}")
        print(f"   margin: {check.margin}")
        print(f"   balance: {check.balance}")
    else:
        print(f"   ❌ order_check returned None")
        print(f"   last_error: {mt5.last_error()}")
    
    # اگر check موفق بود، ارسال واقعی
    if check and check.retcode == 0:
        print(f"\n📤 Sending real order...")
        result = mt5.order_send(request)
        if result:
            print(f"   retcode: {result.retcode}")
            print(f"   deal: {result.deal}")
            print(f"   order: {result.order}")
            print(f"   comment: {result.comment}")
            if result.retcode == 10009:
                print(f"   ✅ Order executed! Order ticket: {result.order}")
                
                # صبر و گرفتن position ticket از لیست پوزیشن‌ها
                import time
                time.sleep(1)
                
                positions = mt5.positions_get(symbol=symbol)
                print(f"\n📊 Positions for {symbol}: {len(positions) if positions else 0}")
                
                position_ticket = None
                if positions:
                    for pos in positions:
                        print(f"   Position: ticket={pos.ticket}, vol={pos.volume}, magic={pos.magic}")
                        if pos.magic == 234000:
                            position_ticket = pos.ticket
                            print(f"   ✅ Found our position ticket: {position_ticket}")
                
                if position_ticket:
                    # گرفتن tick جدید
                    tick = mt5.symbol_info_tick(symbol)
                    
                    # بستن با position ticket (نه order ticket!)
                    close_req = {
                        "action": mt5.TRADE_ACTION_DEAL,
                        "symbol": symbol,
                        "volume": volume,
                        "type": mt5.ORDER_TYPE_SELL,
                        "position": position_ticket,  # ✅ Position ticket
                        "price": tick.bid,
                        "deviation": 20,
                        "magic": 234000,
                        "comment": "Close test",
                        "type_time": mt5.ORDER_TIME_GTC,
                        "type_filling": mt5.ORDER_FILLING_IOC,
                    }
                    print(f"\n📤 Closing position {position_ticket}...")
                    close_result = mt5.order_send(close_req)
                    if close_result:
                        print(f"   Close retcode: {close_result.retcode}")
                        print(f"   Close comment: {close_result.comment}")
                        if close_result.retcode == 10009:
                            print(f"   ✅ Position closed successfully!")
                        else:
                            print(f"   ❌ Close failed - trying without position field...")
                            # روش جایگزین - بدون position field
                            close_req2 = {
                                "action": mt5.TRADE_ACTION_DEAL,
                                "symbol": symbol,
                                "volume": volume,
                                "type": mt5.ORDER_TYPE_SELL,
                                "price": tick.bid,
                                "deviation": 20,
                                "magic": 234000,
                                "comment": "Close test v2",
                                "type_time": mt5.ORDER_TIME_GTC,
                                "type_filling": mt5.ORDER_FILLING_IOC,
                            }
                            close_result2 = mt5.order_send(close_req2)
                            print(f"   Alt close retcode: {getattr(close_result2, 'retcode', 'N/A')}")
                else:
                    print("   ⚠️ Position not found - may have been closed by TP/SL")
        else:
            print(f"   ❌ order_send returned None")
            print(f"   last_error: {mt5.last_error()}")
    else:
        print(f"\n⚠️ Order check failed, not sending real order")
        
    mt5.shutdown()
    print("\n✅ Test completed")

if __name__ == "__main__":
    test_order()
