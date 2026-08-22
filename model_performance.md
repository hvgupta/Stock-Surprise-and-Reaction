The model being used here is a Graident Boosting Regressor model, with the hyper param tuning being done through the library Optuna.

The features being used here is
```json
    {
        "eps_actual": "The actual eps for the given earnings period",
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
- `eps_actual`, `surprise`, `pct_surprise_z_score`: One of the main factors of the reaction is eps
- `drift`, `volatility`: this is to capture the pre-event price movement information
- `current_ratio`, `gross_profit_pct`, `asset_turnover`, `gross_profit_z_score`: basic ratios to estimate the performance of the company
- `day`: number of days from reaction date

## Linear Regression
The first model tested was the linear regression model:

Since none of the data points dont have much correlation with the target variable `reaction`,
| Variable Name | Correlation to `reaction`|
|--|--|
|eps_actual|0.010420|
|drift|-0.024274|
|volatility|-0.002649|
|current_ratio|0.001806|
|gross_profit_pct|0.011346|
|asset_turnover|0.011928|
|gross_profit_z_score|0.001783|
|surprise|-0.017003|
|day|-0.027079|
|pct_surprise_z_score|-0.050647|

therefore the performance of the model was not great.

| Test $R^2$ | Test MSE | Mean Baseline MSE |
|--|--|--|
|-0.006772008307610156| 16.279766876101846 | 16.212247956582114|

## Gradient Boosting Tree
The next model I tried was Gradient Boosting Tree.
The same dataset was passed in and the hyper parameters were optimized through the library `Optuna`

the parameters which it came up with
```
n_estimators: 410
learning_rate: 0.015288053636138697
max_depth: 9
min_samples_split: 3
min_samples_leaf: 1
subsample: 0.8429807819369488
max_features: log2
loss: squared_error
```
The $R^2$ is much higher, however there is only a moderate improvement in the MSE.
$7.687975387262753$ as compared to $16.212247956582114$

## Diagnostics

The reason why the tree-based model could have stalled:
1) The model has captured all of the signals, and rest of the data is noise
2) The model is not able to reduce the MSE due to the architecure of the regressor-tree. 

In order to determine if the problem is the data or the limitation of the model, I trained a simple feedforward neural network of too see if it out performs the tree-based model.

I used optuna again with feedforward models. (Batch Normalization was used)

The best performing model had the following parameters
```
hidden_layer_sizes: (16, 16, 16)
activation: relu
alpha: 0.0003198865079384374
learning_rate_init: 0.005716566580790451
max_iter: 1000
```
This shows us that the feedforward model performs similar to the linear regression model and worse than the tree-based model. This shows us that either there is not enough information or the data is very noisy.