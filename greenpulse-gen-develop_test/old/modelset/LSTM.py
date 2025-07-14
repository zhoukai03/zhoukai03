import os
import torch
import torch.nn as nn
import numpy as np
import pandas as pd

import modelset.base as base


class lstm(nn.Module):
    def __init__(self, params):
        super(lstm, self).__init__()
        self.rnn = nn.LSTM(
            input_size=params.input_size, hidden_size=64, num_layers=1, batch_first=True
        )
        self.out = nn.Sequential(nn.Linear(64, 1))
        self.activation = nn.ReLU()

    def forward(self, x):
        r_out, (h_n, h_c) = self.rnn(x, None)
        out = self.out(r_out[:, -1, :])

        return out


class LSTM(base.BaseModel):

    def __init__(self, params, **kwargs):
        self.params = params
        self.model = lstm(params)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=params.learning_rate)

    def train(self, x_train, y_train, x_val, y_val, **kwargs):
        # 调整数据格式 数据 df->numpy->tensor
        x_train = torch.from_numpy(x_train.to_numpy()).float()
        x_train = x_train.reshape(x_train.shape[0], 1, x_train.shape[1])
        y_train = torch.squeeze(torch.from_numpy(y_train.to_numpy()).float())

        x_val = torch.from_numpy(x_val.to_numpy()).float()
        x_val = x_val.reshape(x_val.shape[0], 1, x_val.shape[1])
        y_val = torch.squeeze(torch.from_numpy(y_val.to_numpy()).float())

        loss_fn1 = torch.nn.L1Loss()
        loss_fn2 = torch.nn.MSELoss()
        for e in range(self.params.epochs):
            self.model.train()
            y_pred = self.model(x_train)
            y_pred = torch.squeeze(y_pred)
            loss_pred = 0 * loss_fn1(y_pred, y_train) + 1 * loss_fn2(y_pred, y_train)

            self.optimizer.zero_grad()
            loss_pred.backward()
            self.optimizer.step()

            self.model.eval()
            with torch.no_grad():
                y_pred_val = self.model(x_val)
                y_pred_val = torch.squeeze(y_pred_val)
                loss_val = 0 * loss_fn1(y_pred_val, y_val) + 1 * loss_fn2(y_pred_val, y_val)

    def predict(self, data, **kwargs):
        _data = torch.from_numpy(data.to_numpy()).float()
        _data = _data.reshape(_data.shape[0], 1, _data.shape[1])
        self.model.eval()
        with torch.no_grad():
            y_pred = self.model(_data)
        pred = y_pred.detach().numpy()
        pred = pred[:, 0]

        return pred

    def dump(self, file_path, **kwarg):
        state = {
            "model": self.model.state_dict(),
            "optimizer": self.optimizer.state_dict(),
        }
        torch.save(state, file_path)

    def load(self, file_path, **kwarg):
        self.model.load_state_dict(torch.load(file_path)["model"], **kwarg)
