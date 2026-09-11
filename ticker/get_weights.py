from tickers import tickers2, raw_weights2
from util import get_weights

money = 40000
for i, j in get_weights(tickers2, raw_weights2).items():
    print(f"{i}: {j*money:.2f} ({j*100:.2f}%)")