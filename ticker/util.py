def get_weights(tickers, raw_weights):
    sum_weights = sum(raw_weights)
    weights = {
        ticker: w / sum_weights for ticker, w in zip(tickers, raw_weights)
    }
    return weights