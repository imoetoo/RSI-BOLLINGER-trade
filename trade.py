from profitview import Link, http, logger
# Below libraries are already imported by default by ProfitView
import pandas as pd
import numpy as np
import talib
from datetime import datetime

class Trading(Link):
    """RSI + Bollinger Bands Strategy for FTM/USDT"""
    
    '''
    An RSI and Bollinger Bands trading strategy:
    
    - Long when candle closes below lower Bollinger Band AND RSI < 30
    - Short when candle closes above upper Bollinger Band AND RSI > 70
    '''
    # ---------------------------
    # Configuration Parameters
    # ---------------------------
    
    # Account and symbol 
    SRC = 'woo'                  # Example exchange identifier
    VENUE = 'WooLive'                # Exchange venue as configured in ProfitView
    SYMBOL = 'PERP_FTM_USDT'             # Trading pair
    
    # Define trading parameters (constants)
    RSI_PERIOD = 14                 # Period for RSI calculation
    RSI_OVERBOUGHT = 70             # RSI threshold for overbought
    RSI_OVERSOLD = 30               # RSI threshold for oversold
    BB_PERIOD = 20                  # Period for Bollinger Bands
    BB_STDDEV = 2                   # Standard deviation multiplier for Bollinger Bands
    ORDER_SIZE = 100                # Size of order to place
    
    # Account position 
    positionSide = ''               # 'Buy' for long, 'Sell' for short
    positionSize = 0                # Size of the current position
    positionPx = 0                  # Entry price of the current position
    
    # Stop price
    STOP_PROFIT_PERCENT = 2         # Take-profit at 2% gain
    STOP_LOSS_PERCENT = 4           # Stop-loss at 4% loss
    stopProfitPx = 0                # Initialization of variable
    stopLossPx = 0
    
    # Initialize the candle_list to store the most recent BB_PERIOD candles
    candle_list = []
    last_candle_time = None          # To track the latest candle time

    # ---------------------------
    # Lifecycle Methods
    # ---------------------------
    
    def on_start(self):
        """Called on start up of trading script"""
        logger.info("Bot starting up...")
		logger.info("My current balance is %s", self.fetch_balances(self.VENUE))
        
        # Get the latest account position
        self.queryLatest()
        
        # Fetch initial candle data
        candles = self.fetch_initial_candles()
        
        if candles:
            self.candle_list = candles
            self.last_candle_time = candles[-1]['time']
            logger.info(f"Initialized with {len(self.candle_list)} candles.")
        else:
            logger.error("Failed to fetch initial candle data.")

    # ---------------------------
    # Callback Methods
    # ---------------------------
    
    def trade_update(self, src, sym, data):
        """Called on market trades from subscribed symbols"""
        if sym == self.SYMBOL:
            self.mainLogic(data)
    
    # ---------------------------
    # Helper Methods
    # ---------------------------
    
    def fetch_initial_candles(self):
        """Fetch the initial set of candles to populate candle_list"""
        response = self.fetch_candles(
            venue=self.VENUE,
            sym=self.SYMBOL,
            level='1h',               # 1-hour candlesticks
            since=None                 # Fetch the most recent candles
        )
        
        if response['error'] is None:
            candles = response['data']
            if len(candles) >= self.BB_PERIOD:
                # Returns last BB_PERIOD candles (e.g., the recent 20 candles) 
                return candles[-self.BB_PERIOD:]
            else:
                logger.error(f"Not enough candles fetched: {len(candles)}")
                return None
        else:
            logger.error(f"Error fetching candles: {response['error']}")
            return None
            
    def queryLatest(self):
        """Update current position and stop prices"""
        positionData = self.fetch_positions(self.VENUE)['data']
        
        if len(positionData) > 0: 
            position = positionData[0]
            self.positionSide = position['side']
            self.positionSize = position['pos_size']
            self.positionPx = position['entry_price']
        else:
            self.positionSide = ''
            self.positionSize = 0
            self.positionPx = 0
            
        if self.positionSide == 'Buy':
            self.stopProfitPx = self.positionPx * (1 + self.STOP_PROFIT_PERCENT / 100)
            self.stopLossPx = self.positionPx * (1 - self.STOP_LOSS_PERCENT / 100)
        elif self.positionSide == 'Sell':
            self.stopProfitPx = self.positionPx * (1 - self.STOP_PROFIT_PERCENT / 100)
            self.stopLossPx = self.positionPx * (1 + self.STOP_LOSS_PERCENT / 100)
        else:
            self.stopProfitPx = 0
            self.stopLossPx = 0
            
        logger.info(f"Position: {self.positionSide} {self.positionSize}@{self.positionPx}, "
                    f"StopProfitPx={self.stopProfitPx}, StopLossPx={self.stopLossPx}")

    def mainLogic(self, data):
        """Main logic executed on each trade update"""
        # Determine if a new candle has formed
        latest_trade_time = data['time']  # Epoch timestamp in milliseconds
        
        # Check if the latest_trade_time falls into a new candle period
        if self.is_new_candle(latest_trade_time):
            # Fetch the latest candle
            new_candle = self.fetch_latest_candle()
            
            if new_candle:
                # Append the new candle and maintain the candle_list size
                self.candle_list.append(new_candle)
                self.candle_list = self.candle_list[-self.BB_PERIOD:]
                self.last_candle_time = new_candle['time']
                
                logger.info(f"New candle added at {self.format_time(new_candle['time'])}")
                
				if len(self.candle_list) >= self.BB_PERIOD:
					# Calculate indicators
					df = pd.DataFrame(self.candle_list)
					closes = df['close'].astype(float).values
					highs = df['high'].astype(float).values
					lows = df['low'].astype(float).values

					# Calculate Bollinger Bands
					upper, middle, lower = talib.BBANDS(
						closes, 
						timeperiod=self.BB_PERIOD, 
						nbdevup=self.BB_STDDEV, 
						nbdevdn=self.BB_STDDEV,
						matype=0
					)

					# Calculate RSI
					rsi = talib.RSI(closes, timeperiod=self.RSI_PERIOD)

					# Get the latest candle's close, upper BB, lower BB, and RSI
					latest_close = closes[-1]
					latest_upper = upper[-1]
					latest_lower = lower[-1]
					latest_rsi = rsi[-1]

					logger.info(f"Latest Close: {latest_close}, Upper BB: {latest_upper}, "
								f"Lower BB: {latest_lower}, RSI: {latest_rsi}")

					# Determine trade signals
					self.determineTrade(latest_close, latest_upper, latest_lower, latest_rsi)
				else:
					logger.error("Failed to fetch the latest candle.")
    
    def is_new_candle(self, trade_time):
        """Determine if a new candle has formed based on trade_time"""
        # Convert trade_time from milliseconds to datetime
        trade_datetime = datetime.utcfromtimestamp(trade_time / 1000)
        trade_hour = trade_datetime.replace(minute=0, second=0, microsecond=0)
        trade_epoch = int(trade_hour.timestamp() * 1000)
        
        # If last_candle_time is None or less than the current trade's candle time, it's a new candle
        if (self.last_candle_time is None) or (trade_epoch > self.last_candle_time):
            return True
        return False
    
    def fetch_latest_candle(self):
        """Fetch the latest candle"""
        response = self.fetch_candles(
            venue=self.VENUE,
            sym=self.SYMBOL,
            level='1h',               # 1-hour candlesticks
            since=None                 # Fetch the latest candle
        )
        
        if response['error'] is None and len(response['data']) > 0:
            return response['data'][-1]
        else:
            logger.error(f"Error fetching latest candle: {response['error']}")
            return None
    
    def format_time(self, epoch_ms):
        """Format epoch milliseconds to readable string"""
        return datetime.utcfromtimestamp(epoch_ms / 1000).strftime('%Y-%m-%d %H:%M:%S')
    
    def determineTrade(self, close, upper, lower, rsi):
        """Determine whether to enter a long or short position based on indicators"""
        signal = 0  # 1 for long, -1 for short
        
        # Long condition
        if (close < lower) and (rsi < self.RSI_OVERSOLD):
            signal = 1
            logger.info("Long signal detected.")
        
        # Short condition
        elif (close > upper) and (rsi > self.RSI_OVERBOUGHT):
            signal = -1
            logger.info("Short signal detected.")
        
        # Execute trade based on signal and current position
        if signal == 1 and self.positionSize == 0:
            self.openPosition(signal)
        elif signal == -1 and self.positionSize == 0:
            self.openPosition(signal)
        else:
            logger.info("No trade executed. Either no signal or already in a position.")
    
    def openPosition(self, signal):
        """Open a long or short position based on the signal"""
        if signal == 1:
            side = 'Buy'
            logger.info(f"Opening LONG position: {self.ORDER_SIZE} {self.SYMBOL}")
            self.sendMarketOrder(side, self.ORDER_SIZE)
        elif signal == -1:
            side = 'Sell'
            logger.info(f"Opening SHORT position: {self.ORDER_SIZE} {self.SYMBOL}")
            self.sendMarketOrder(side, self.ORDER_SIZE)
        else:
            logger.error("Invalid signal for opening position.")
    
    def sendMarketOrder(self, side, size):
        """Send a market order to the exchange"""
        response = self.create_market_order(
            venue=self.VENUE,
            sym=self.SYMBOL,
            side=side,
            size=size
        )
        
        if response['error'] is None:
            retData = response['data']
            logger.info(f"Market Order Executed: {retData['side']} {retData['order_size']}@{retData['order_price']}")
            
            # Update position and stop prices
            self.queryLatest()
        else:
            logger.error(f"Failed to execute market order: {response['error']}")
    
    def determineStop(self, tradePx):
        """Check whether to trigger stop-loss or take-profit"""
        logger.info(f"Checking Stop conditions: TradePx={tradePx}, StopProfitPx={self.stopProfitPx}, StopLossPx={self.stopLossPx}")
        
        # Check for Stop-Profit or Stop-Loss
        if self.positionSide == 'Buy':
            if tradePx >= self.stopProfitPx:
                logger.info("Take-Profit condition met for LONG position.")
                self.closePosition()
            elif tradePx <= self.stopLossPx:
                logger.info("Stop-Loss condition met for LONG position.")
                self.closePosition()
        elif self.positionSide == 'Sell':
            if tradePx <= self.stopProfitPx:
                logger.info("Take-Profit condition met for SHORT position.")
                self.closePosition()
            elif tradePx >= self.stopLossPx:
                logger.info("Stop-Loss condition met for SHORT position.")
                self.closePosition()
    
    def closePosition(self):
        """Close the current position"""
        size = abs(self.positionSize)
        side = 'Sell' if self.positionSide == 'Buy' else 'Buy'
        
        if size > 0:
            logger.info(f"Closing position: {side} {size} {self.SYMBOL}")
            self.sendMarketOrder(side, size)
        else:
            logger.error("No position to close.")
