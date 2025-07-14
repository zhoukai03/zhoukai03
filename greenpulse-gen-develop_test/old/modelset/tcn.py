import os
import numpy as np
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader


import modelset.base as base


class Chomp1d(nn.Module):
    def __init__(self, chomp_size):
        super(Chomp1d, self).__init__()
        self.chomp_size = chomp_size

    def forward(self, x):
        return x[:, :, : -self.chomp_size].contiguous()


class TCN(nn.Module):
    def __init__(self, params, input_size):
        super(TCN, self).__init__()
        # padding = (ks - 1)*dilation
        self.conv1 = nn.Sequential(nn.Conv1d(in_channels=input_size, out_channels=10, kernel_size=3, padding=2, dilation=1), Chomp1d(2), nn.ReLU())
        self.conv2 = nn.Sequential(nn.Conv1d(in_channels=10, out_channels=10, kernel_size=3, padding=6, dilation=3), Chomp1d(6), nn.ReLU())
        self.conv3 = nn.Sequential(nn.Conv1d(in_channels=10, out_channels=10, kernel_size=3, padding=12, dilation=6), Chomp1d(12), nn.ReLU())
        self.conv4 = nn.Sequential(nn.Conv1d(in_channels=10, out_channels=10, kernel_size=3, padding=18, dilation=9), Chomp1d(18), nn.ReLU())
        self.linear = nn.Sequential(nn.Linear(params.hid_size, 1))
        self.dowansample = nn.Conv1d(in_channels=input_size, out_channels=10, kernel_size=1)
        self.relu = nn.ReLU()

    def forward(self, x):
        x = x.permute(0, 2, 1)
        out = self.conv1(x)
        out = self.conv2(out)
        out = self.conv3(out)
        out = self.conv4(out)
        res = self.dowansample(x)
        out = self.relu(res + out)
        out = out.permute(0, 2, 1)
        out = self.linear(out)
        out = out[:, :, 0]
        return out


class tcn(base.BaseModel):
    def __init__(self, params, **kwargs):
        _device = kwargs.get("device", None)
        if _device is None:
            self.device = torch.device(device="cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device=_device)
        _input_size = kwargs.get("input_size", None)
        if _input_size is None:
            _input_size = params.input_size
        self.model = TCN(params, _input_size)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=params.learning_rate)
        self.params = params

    def predict(self, data, **kwargs):
        data_x = torch.from_numpy(data.to_numpy()).float()
        data_x = data_x.reshape(data_x.shape[0], 1, data_x.shape[1])

        self.model.eval()

        visual_path = kwargs.get("visual")
        if visual_path is not None:
            from torch.utils.tensorboard import SummaryWriter
            writer_loss = SummaryWriter(os.path.join(visual_path, "loss"))
            writer_model = SummaryWriter(os.path.join(visual_path, "model"))
        with torch.no_grad():
            y_pred = self.model(data_x)
        pred = y_pred.detach().numpy()

        return pred

    def train(self, X_train, Y_train, X_val, Y_val, **kwargs):
        """
        train_data, val_data 需要归一化 (0,1) 区间内
        """
        x_train = torch.from_numpy(X_train.to_numpy()).float()
        x_train = x_train.reshape(x_train.shape[0], 1, x_train.shape[1])
        y_train = torch.squeeze(torch.from_numpy(Y_train.to_numpy()).float())

        x_val = torch.from_numpy(X_val.to_numpy()).float()
        x_val = x_val.reshape(x_val.shape[0], 1, x_val.shape[1])
        y_val = torch.squeeze(torch.from_numpy(Y_val.to_numpy()).float())

        loss_function = nn.MSELoss()
        epochs = self.params.epochs

        visual_path = kwargs.get("visual")
        if visual_path is not None:
            from torch.utils.tensorboard import SummaryWriter

            writer_loss = SummaryWriter(os.path.join(visual_path, "loss"))
            writer_model = SummaryWriter(os.path.join(visual_path, "model"))

            # writer_model.add_graph(TransformerModel, self.params)

        for epoch in range(epochs):
            self.model.train()
            train_loss = []

            self.optimizer.zero_grad()

            y_pred = tcn(x_train)
            y_pred = torch.squeeze(y_pred)
            loss = loss_function(y_pred, y_train)

            y_valid = tcn(X_val)
            y_valid = torch.squeeze(y_valid)
            v_loss = loss_function(y_valid, y_val)

            loss.backward()
            self.optimizer.step()

            if visual_path is not None:
                writer_loss.add_scalar("loss", np.mean(loss), epoch)
                writer_loss.add_scalar("val_loss", np.mean(v_loss), epoch)

    def dump(self, file_path, **kwarg):
        state = {"model": self.model.state_dict(), "optimizer": self.optimizer.state_dict()}
        torch.save(state, file_path)

    def load(self, file_path, **kwarg):
        self.model.load_state_dict(torch.load(file_path)["model"], **kwarg)
