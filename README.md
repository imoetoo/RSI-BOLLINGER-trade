Overview:

-This trading bot implements a strategy based on the Relative Strength Index (RSI) and Bollinger Bands for trading the FTM/USDT pair on the ProfitView platform. The strategy aims to identify potential entry points for trades based on specific market conditions.

Platform:

ProfitView: This bot is designed to operate within the ProfitView trading ecosystem.
Strategy Description
The bot utilizes the following trading strategy:

Long Position: Enter a long position when the candle closes below the lower Bollinger Band and the RSI is less than 30.
Short Position: Enter a short position when the candle closes above the upper Bollinger Band and the RSI is greater than 70.
Configuration Parameters
The following parameters can be configured in the trading bot:

SRC: 'woo'
The exchange identifier.

VENUE: 'WooLive'
The exchange venue as configured in ProfitView.

SYMBOL: 'PERP_FTM_USDT'
The trading pair to be used.

Trading Parameters

RSI_PERIOD: 14
The period for calculating the RSI.

RSI_OVERBOUGHT: 70
The threshold for identifying overbought conditions.

RSI_OVERSOLD: 30
The threshold for identifying oversold conditions.

BB_PERIOD: 20
The period for calculating Bollinger Bands.

BB_STDDEV: 2
The standard deviation multiplier for Bollinger Bands.

ORDER_SIZE: 100
The size of each trade order.

Stop Parameters:

STOP_PROFIT_PERCENT: 2
The percentage gain at which to take profit.

STOP_LOSS_PERCENT: 4
The percentage loss at which to stop loss.

Lifecycle Methods:
on_start(): Initializes the bot, fetches the latest balance, and retrieves initial candle data.

Callback Methods:
trade_update(src, sym, data): Triggered on market trades for subscribed symbols, processes trading logic.

Helper Methods:

fetch_initial_candles(): Fetches the initial set of candles to populate the candle list.
queryLatest(): Updates current position and stop prices based on the latest account data.
mainLogic(data): Executes the main trading logic based on new market data.
determineTrade(close, upper, lower, rsi): Determines whether to enter a long or short position based on the calculated indicators.
sendMarketOrder(side, size): Sends a market order to the exchange.

Running the Bot
To run the bot, ensure you have the required libraries and dependencies installed in your Python environment. Execute the script within the ProfitView platform where the Link class is defined.

Notes:
Ensure that the API keys and necessary permissions are configured correctly in the ProfitView platform.
Monitor the bot's performance and adjust parameters as needed to optimize trading strategies.
