from catboost import CatBoostRegressor
import joblib
import modelset.base as base


class regressor(base.BaseModel):
    """
    模型类, 继承自 base.model
    """

    def __init__(self, params, **kwargs):
        self.model = CatBoostRegressor(
            iterations=params.iterations,
            depth=params.depth,
            learning_rate=params.learning_rate,
            loss_function=params.loss_function,
            eval_metric=params.eval_metric,
            verbose=params.verbose,
            subsample=params.subsample,
            early_stopping_rounds=params.early_stopping_rounds,
            colsample_bylevel=params.colsample_bylevel,
            **kwargs,
        )

    def predict(self, data, **kwargs):
        return self.model.predict(data, **kwargs)

    def train(self, train_x, train_y, val_x=None, val_y=None, **kwargs):
        if val_x is not None and val_y is not None:
            self.model.fit(train_x, train_y, eval_set=(val_x, val_y), **kwargs)
        else:
            self.model.fit(train_x, train_y, **kwargs)

    def dump(self, file_path, **kwarg):
        joblib.dump(self.model, file_path, **kwarg)

    def load(self, file_path, **kwarg):
        self.model = joblib.load(file_path, **kwarg)
