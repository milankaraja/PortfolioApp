import sys
import json
from yahoo_fin.stock_info import get_data
from yahoo_fin.stock_info import tickers_nifty50
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
from datetime import date
from datetime import timedelta
import requests
import matplotlib.pyplot as plt
import yfinance as yf  # Make sure to import the yfinance library

data_input = sys.argv[1]


    

#json_string = json.loads(data_input)
#data_output = json_string[0]["country"]

# start and end date
startDate='2023-03-01'
endDate='2023-05-31'


#############



startDate = date.today() - timedelta(days=365)
endDate = date.today()

# Factory Pattern for Trade Creation
class Trade:
    def __init__(self, id, country, stockName, price, amount, tradeDate, trade, created_at, updated_at, user_id):
        self.id = id
        self.country = country
        self.stockName = stockName
        self.price = price
        self.amount = amount
        self.tradeDate = tradeDate
        self.trade = trade
        self.created_at = created_at
        self.updated_at = updated_at
        self.user_id = user_id

    def __str__(self):
        return f"Trade(name={self.stockName}, price={self.price})"

    def lastPrice(self):
        if self.country == "India":
            tickerData = yf.Ticker(str(self.stockName) + ".NS")
        else:
            tickerData = yf.Ticker(str(self.stockName))
        priceData = tickerData.history(period='1d', start=startDate, end=endDate)
        lastPrice = priceData.tail(1)
        return lastPrice["Close"].to_numpy().tolist()[0]

    def totalValueNew(self):
        return self.amount * self.lastPrice()


class USTrade(Trade):
    def __init__(self, id, country, stockName, price, amount, tradeDate, trade, created_at, updated_at, user_id,
                 exchange_rate):
        super().__init__(id, country, stockName, price, amount, tradeDate, trade, created_at, updated_at, user_id)
        self.exchange_rate = exchange_rate


class IndianTrade(Trade):
    def __init__(self, id, country, stockName, price, amount, tradeDate, trade, created_at, updated_at, user_id,
                 exchange_rate):
        super().__init__(id, country, stockName, price, amount, tradeDate, trade, created_at, updated_at, user_id)
        self.exchange_rate = exchange_rate


class TradeFactory:
    def __init__(self):
        self.value_provider = PortfolioValueProvider()

    def create_trade(self, id, country, stockName, price, amount, tradeDate, trade, created_at, updated_at, user_id):
        exchange_rate = self.value_provider.get_exchange_rate(country)
        if country == "USA":
            return USTrade(id, country, stockName, price, amount, tradeDate, trade, created_at, updated_at, user_id,
                           exchange_rate)
        elif country == "India":
            return IndianTrade(id, country, stockName, price, amount, tradeDate, trade, created_at, updated_at, user_id,
                               exchange_rate)
        else:
            raise ValueError("Invalid country")


# Portfolio Class with Aggregation and API Interaction
class Portfolio:
    def __init__(self):
        self.trades = []
        self.value_provider = PortfolioValueProvider()
        self.net_values = None  # Store the calculated net values
        self.portfolio_status = {}  # Store the portfolio's status for each date

    def add_trade(self, trade):
        self.trades.append(trade)
        self.update_portfolio_status()

    def add_trades(self, trade_data):
        trade_factory = TradeFactory()
        for trade_info in trade_data:
            self.trades.extend([trade_factory.create_trade(**trade_info)])
        self.update_portfolio_status()

    def calculate_net(self):
        if self.net_values is None:
            net_value = {}
            total_quantity = {}
            average_price = {}
            current_value = {}
            for trade in self.trades:
                if trade.stockName in net_value:
                    net_value[trade.stockName] += trade.amount * trade.price
                    total_quantity[trade.stockName] += trade.amount
                    average_price[trade.stockName] = net_value[trade.stockName] / total_quantity[trade.stockName]
                    current_value[trade.stockName] = total_quantity[trade.stockName] * self.value_provider.get_asset_value(
                        trade.stockName, trade.country, startDate, endDate)
                else:
                    net_value[trade.stockName] = trade.amount * trade.price
                    total_quantity[trade.stockName] = trade.amount
                    average_price[trade.stockName] = net_value[trade.stockName] / total_quantity[trade.stockName]
                    current_value[trade.stockName] = total_quantity[trade.stockName] * self.value_provider.get_asset_value(
                        trade.stockName, trade.country, startDate, endDate)
            self.net_values = net_value, total_quantity, average_price, current_value

        return self.net_values

    def calculate_current_value(self, currency):
        current_value = {}
        for trade in self.trades:
            if trade.country == "USA":
                if currency == "USA":
                    currency_converter = 1
                else:
                    currency_converter = self.value_provider.get_exchange_rate("India")
            else:
                if currency == "USA":
                    currency_converter = self.value_provider.get_exchange_rate("USA")
                else:
                    currency_converter = 1
            asset_value = self.value_provider.get_asset_value(trade.stockName, trade.country, startDate,
                                                             trade.tradeDate)
            if asset_value is not None:
                current_value[trade.stockName] = asset_value * trade.amount * currency_converter
        return current_value

    def update_portfolio_status(self):
        for trade in self.trades:
            if trade.tradeDate not in self.portfolio_status:
                self.portfolio_status[trade.tradeDate] = {}

            if trade.stockName not in self.portfolio_status[trade.tradeDate]:
                self.portfolio_status[trade.tradeDate][trade.stockName] = trade.amount
            else:
                self.portfolio_status[trade.tradeDate][trade.stockName] += trade.amount

    def get_portfolio_status_by_date(self, date):
        return self.portfolio_status.get(date, {})

    def get_portfolio_status_for_dates(self, dates):
        portfolio_status_for_dates = []

        for date in dates:
            portfolio_status_for_dates.append({
                'date': date,
                'assets_quantity': self.get_portfolio_status_by_date(date)
            })

        return portfolio_status_for_dates

    def calculate_daily_values_oneyear(self, currency):
        daily_values = []
        trade_dates = []
        stock_quantity = {}
        start_dt = startDate
        end_dt = endDate
        delta = timedelta(days=1)

        # store the dates between two dates in a list
        dates_oneyear = []

        while start_dt <= end_dt:
            dates_oneyear.append(start_dt.isoformat())
            start_dt += delta

        sorted_trades = sorted(self.trades, key=lambda trade: trade.tradeDate)
        for date in dates_oneyear:
            total_value_for_date = 0
            for trade in sorted_trades:
                if trade.tradeDate == date:
                    total_value_for_date += trade.amount * self.value_provider.get_asset_value(trade.stockName,
                                                                                               trade.country, date)
            daily_values.append(total_value_for_date)

        portfolio_status = self.get_portfolio_status_for_dates(dates_oneyear)

        return portfolio_status, dates_oneyear

    def assets_on_dates_oneyear(self):
        dates_oneyear = []
        start_dt = startDate
        end_dt = endDate
        delta = timedelta(days=1)

        while start_dt <= end_dt:
            dates_oneyear.append(start_dt.isoformat())
            start_dt += delta

        assets_by_date = {}

        trade_dates_set = set(trade.tradeDate for trade in self.trades)
        sorted_trades = sorted(self.trades, key=lambda trade: trade.tradeDate)

        for date1 in dates_oneyear:
            assets_on_date = {}
            for trade in self.trades:
                if trade.tradeDate <= date1:
                    if trade.country not in assets_on_date:
                        assets_on_date[trade.country] = {}
                    if trade.stockName in assets_on_date[trade.country]:
                        assets_on_date[trade.country][trade.stockName] += trade.amount
                    else:
                        assets_on_date[trade.country][trade.stockName] = trade.amount
            assets_by_date[date1] = assets_on_date

        return assets_by_date

    @staticmethod
    def portfolio_value_for_dates(portfolio_dict, currency):
        stock_data = {}

        for date, country_stocks in portfolio_dict.items():
            for country, stocks in country_stocks.items():
                for stock_name in stocks.keys():
                    if stock_name not in stock_data:
                        if country == 'India':
                            stock_data[stock_name] = yf.Ticker(str(stock_name) + ".NS").history(period='1d',
                                                                                                   start=startDate,
                                                                                                   end=endDate)
                        else:
                            stock_data[stock_name] = yf.Ticker(str(stock_name)).history(period='1d', start=startDate,
                                                                                         end=endDate)

        portfolio_value_by_dates = {}

        for date, country_stocks in portfolio_dict.items():
            total_value = 0

            for country, stocks in country_stocks.items():
                for stock_name, quantity in stocks.items():
                    stock_history = stock_data[stock_name]

                    if date in stock_history.index:
                        stock_value_usd = stock_history.loc[date]["Close"] * quantity

                        if currency == 'USD':
                            total_value += stock_value_usd
                        elif currency == 'INR' and country != 'India':
                            exchange_rate = PortfolioValueProvider.get_exchange_rate(country)
                            stock_value_rupees = stock_value_usd * exchange_rate
                            total_value += stock_value_rupees

            if total_value > 0:
                portfolio_value_by_dates[date] = total_value
        return portfolio_value_by_dates


# Data Collection
class PortfolioValueProvider:
    def __init__(self):
        pass

    def get_asset_value(self, stockName, country, startDate, endDate):
        if country == "India":
            tickerData = yf.Ticker(str(stockName) + ".NS")
        else:
            tickerData = yf.Ticker(str(stockName))
        priceData = tickerData.history(period='1d', start=startDate, end=endDate)
        lastPrice = priceData.tail(1)
        return lastPrice["Close"].to_numpy().tolist()[0]

    def get_asset_values(self, stockName, country, startDate, endDate):
        if country == "India":
            tickerData = yf.Ticker(str(stockName) + ".NS")
        else:
            tickerData = yf.Ticker(str(stockName))
        priceData = tickerData.history(period='1d', start=startDate, end=endDate)
        return priceData["Close"].to_numpy().tolist()

    @staticmethod
    def get_exchange_rate(country, target_currency='USD'):
        if country in PortfolioValueProvider.exchange_rates and target_currency in PortfolioValueProvider.exchange_rates[
            country]:
            return PortfolioValueProvider.exchange_rates[country][target_currency]
        else:
            return 1.0

    # Sample exchange rates (USD to other currencies)
    exchange_rates = {
        'USA': {
            'USD': 1.0,  # 1 USD to USD
            'INR': 75.0,  # Sample exchange rate: 1 USD to 75 INR
            'EUR': 0.85,  # Sample exchange rate: 1 USD to 0.85 EUR
        },
        'India': {
            'INR': 1.0,  # 1 INR to INR
            'USD': 0.013,  # Sample exchange rate: 1 INR to 0.013 USD
            'EUR': 0.011,  # Sample exchange rate: 1 INR to 0.011 EUR
        }
    }


# Output
class PortfolioOutput:
    def __init__(self, portfolio, currency):
        self.portfolio = portfolio
        self.currency = currency

    def portfolio_daily_value(self):
        return self.portfolio.calculate_current_value(self.currency)

    def portfolio_net_cost(self):
        return self.portfolio.calculate_net()[0]

    def portfolio_total_quantity(self):
        return self.portfolio.calculate_net()[1]

    def portfolio_net_cost_per_unit(self):
        return self.portfolio.calculate_net()[2]

    def portfolio_net(self):
        return self.portfolio.calculate_net()

    def portfolio_daily_values_oneyear(self):
        return self.portfolio.assets_on_dates_oneyear()

    def portfolio_value_date_rs(self):
        input_dict = self.portfolio_daily_values_oneyear()
        values = self.portfolio.portfolio_value_for_dates(input_dict, "USD")
        return values


# Final Output
class OutputForPHP:
    def __init__(self, currency):
        self.output_list = []
        self.portfolio = Portfolio()
        self.currency = currency

    def output_portfolio(self, trade_data):
        self.portfolio.add_trades(trade_data)
        portfolioOutput = PortfolioOutput(self.portfolio, self.currency)
        output = portfolioOutput.portfolio_net()
        output_currentValue = portfolioOutput.portfolio_daily_value()
        output_dailyvalues2 = portfolioOutput.portfolio_value_date_rs()
        output_dailyvalues = portfolioOutput.portfolio_daily_values_oneyear()

        output_list = [
            [
                key,
                [list(output[1].values())[i], list(output[0].values())[i], list(output[2].values())[i],
                 list(output[3].values())[i]]
            ]
            for i, key in enumerate(output[0].keys())
        ]
        #output_list.append([list(output[0].values()), list(output[0].keys()), list(output[3].values())])

        return list(output_dailyvalues2.keys()), list(output_dailyvalues2.values()), output_list,list(output[0].values()), list(output[0].keys()), list(output[3].values())




# Get the portfolio output



def main():
    dataInput = json.loads(data_input)
    output = OutputForPHP("USA").output_portfolio(dataInput)
    #portfolio
    data_portfolio = output[2]
    
    #portfolio price chart data
    #data2_output= tickerEgData["close"]
    date_array= output[0]
    price_array = output[1]
    #final output array
    data_price= date_array,price_array,data_input,data_portfolio,output[3],output[4],output[5]
    # Date Array, Price Array, Input data, Portfolio Array

#removed print
    return(print(json.JSONEncoder().encode(data_price)))



if __name__=="__main__":
    main()