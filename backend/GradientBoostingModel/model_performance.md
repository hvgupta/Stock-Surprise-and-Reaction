The model being used here is a Graident Boosting Regressor model, with the hyper param tuning being done through the library Optuna.

The features being used here is
```json
    {
        "eps_actual": "The actual eps for the given earnings period",
        "eps_estimate": "the estimated eps for the given earnings period",
        "drift": "the pre-event drift to the earnings release",
        "volatility": "the pre-event volatility to the earnings release",
        "current_ratio": "the current_ratio calculated from the earnings release",
        "gross_profit_pct": "the gross profit percentage from the earnings release",
        "asset_turnover": "the asset turnover from the earnings release",
        "gross_profit_z_score": "the sector normalized gross_profit for the earnings release",
        "surprise": "eps surprise for the earnings release",
        "pct_surprise_z_score": "the sector normalized surprise value for the earnings release",
        "day": "number of days from the earnings release",
        "reaction": "this is the value being predicted, it is the market reaction to the earnings release"
    }
```

The reason why each of the features where choosen
- `eps_actual`, `eps_estimate`, `surprise`, `pct_surprise_z_score`: One of the main factors of the reaction is eps
- `drift`, `volatility`: this is to capture the pre-event price movement information
- `current_ratio`, `gross_profit_pct`, `asset_turnover`, `gross_profit_z_score`