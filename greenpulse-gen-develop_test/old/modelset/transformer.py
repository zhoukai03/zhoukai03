import os
import math
from itertools import chain
import numpy as np
import torch
from torch import nn
from torch.optim.lr_scheduler import StepLR
from torch.utils.data import Dataset, DataLoader


import modelset.base as base


class MyDataset(Dataset):
    def __init__(self, data):
        self.data = data

    def __getitem__(self, item):
        return self.data[item]

    def __len__(self):
        return len(self.data)


# 定义位置编码类
class PositionalEncoding(nn.Module):
    def __init__(self, d_model, dropout=0.1, max_len=5000):
        super(PositionalEncoding, self).__init__()

        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)

        div_term = torch.exp(torch.arange(0, d_model, 2) * (-math.log(10000.0) / d_model))

        pe[:, 0::2] = np.sin(position * div_term)
        pe[:, 1::2] = np.cos(position * div_term)

        pe = pe.unsqueeze(0).transpose(0, 1)

        self.register_buffer("pe", pe)

    def forward(self, x):
        x = x + self.pe[: x.size(1), :].squeeze(1)
        return x


# 定义模型
class TransformerModel(nn.Module):

    def __init__(self, params, device) -> None:
        super(TransformerModel, self).__init__()

        # 编码器输入数据编码
        self.input_fc = nn.Linear(params.input_size, params.d_model)
        # 解码器输入数据编码
        self.output_fc = nn.Linear(params.output_size, params.d_model)
        # 位置编码
        self.pos_emb = PositionalEncoding(params.d_model)
        # 定义编码层，d_model必须是nhead的整数倍
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=params.d_model,
            nhead=params.nhead,
            dim_feedforward=params.diff,
            batch_first=True,
            dropout=0.1,
            device=device,
        )
        decoder_layer = nn.TransformerDecoderLayer(
            d_model=params.d_model,
            nhead=params.nhead,
            dim_feedforward=params.diff,
            dropout=0.1,
            batch_first=True,
            device=device,
        )
        self.encoder = torch.nn.TransformerEncoder(encoder_layer, num_layers=params.ed_num_layers)
        self.decoder = torch.nn.TransformerDecoder(decoder_layer, num_layers=params.de_num_layers)
        self.fc = nn.Linear(params.output_size * params.d_model, params.output_size)
        self.fc1 = nn.Linear(params.seq_len * params.d_model, params.d_model)
        self.fc2 = nn.Linear(params.d_model, params.output_size)

    def forward(self, x):  # x.shape=(batch_size,seq_len,input_size)
        # y = x[:, -output_size:, :]
        x = self.input_fc(x)  # （batch_size,seq_len,d_model）
        x = self.pos_emb(x)  # (batch_size,seq_len,d_model）
        x = self.encoder(x)  # (batch_size,seq_len,d_model）
        # y = self.output_fc(y)  #  (batch_size,output_size,d_model）
        # out = self.decoder(y, x)  # (batch_size,output_size,d_model）
        out = x.flatten(start_dim=1)  # (batch_size,output_size*d_model）
        out = self.fc1(out)  # (output_size)
        out = self.fc2(out)
        return out


class transformer(base.BaseModel):
    def __init__(self, params, **kwargs):
        _device = kwargs.get("device", None)
        if _device is None:
            self.device = torch.device(device="cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device=_device)
        self.model = TransformerModel(params, self.device).to(self.device)
        self.optimizer = torch.optim.Adam(
            self.model.parameters(), lr=params.learning_rate, weight_decay=params.weight_decay
        )
        self.scheduler = StepLR(self.optimizer, step_size=params.step_size, gamma=params.gamma)
        self.params = params

    def get_val_loss(self, Val):
        self.model.eval()
        loss_function = nn.MSELoss().to(self.device)
        val_loss = []
        for seq, label in Val:
            with torch.no_grad():
                seq, label = seq.to(self.device), label.to(self.device)
                label = label.to(self.device)
                y_pred = self.model(seq)
                loss = loss_function(y_pred, label)
                val_loss.append(loss.item())

        return np.mean(val_loss)

    def predict(self, data, **kwargs):
        seq = []
        data = data.to_numpy().tolist()
        for i in range(self.params.seq_len, len(data), self.params.step_size):
            train_seq = []
            for j in range(i - self.params.seq_len, i):
                train_seq.append(data[j])
            train_seq = torch.FloatTensor(train_seq)
            seq.append((train_seq))

        seq = MyDataset(seq)
        data = DataLoader(dataset=seq, batch_size=self.params.batch_size, shuffle=self.params.shuffle, num_workers=0, drop_last=False)

        self.model.eval()
        pred = []

        visual_path = kwargs.get("visual")
        if visual_path is not None:
            from torch.utils.tensorboard import SummaryWriter
            writer_loss = SummaryWriter(os.path.join(visual_path, "loss"))
            writer_model = SummaryWriter(os.path.join(visual_path, "model"))
            for idx, seq in enumerate(data, 0):
                seq = seq.to(self.device)
                with torch.no_grad():
                    y_pred = self.model(seq)
                    y_pred = list(chain.from_iterable(y_pred.data.tolist()))
                    pred.extend(y_pred)
            pred = np.asarray(pred)
        else:
            for idx, seq in enumerate(data, 0):
                seq = seq.to(self.device)
                with torch.no_grad():
                    y_pred = self.model(seq)
                    y_pred = list(chain.from_iterable(y_pred.data.tolist()))
                    pred.extend(y_pred)
            pred = np.asarray(pred)

        return pred

    def train(self, x_train, y_train, x_val, y_val, **kwargs):
        """
        train_data, val_data 需要归一化 (0,1) 区间内
        """
        seq = []
        x_train = x_train.to_numpy().tolist()
        y_train = y_train.to_numpy().tolist()
        for i in range(self.params.seq_len, len(x_train), self.params.step_size):
            train_seq = []
            train_label = []
            for j in range(i - self.params.seq_len, i):
                train_seq.append(x_train[j])
                train_label.append(y_train[j])

            train_seq = torch.FloatTensor(train_seq)
            train_label = torch.FloatTensor(train_label)
            seq.append((train_seq, train_label))

        seq = MyDataset(seq)
        train_data = DataLoader(dataset=seq, batch_size=self.params.batch_size, shuffle=self.params.shuffle, num_workers=0, drop_last=False)

        loss_function = nn.MSELoss().to(self.device)
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
                for batch_idx, (seq, target) in enumerate(train_data, 0):
                    seq = seq.to(self.device)
                    target = target.to(self.device)
                    self.optimizer.zero_grad()
                    y_pred = self.model(seq)
                    loss = loss_function(y_pred, target)
                    train_loss.append(loss.item())
                    loss.backward()
                    self.optimizer.step()
                self.scheduler.step()
                writer_loss.add_scalar("loss", np.mean(train_loss), epoch)
        else:
            for epoch in range(epochs):
                self.model.train()
                train_loss = []
                for batch_idx, (seq, target) in enumerate(train_data, 0):
                    seq = seq.to(self.device)
                    target = target.to(self.device)
                    self.optimizer.zero_grad()
                    y_pred = self.model(seq)
                    loss = loss_function(y_pred, target)
                    train_loss.append(loss.item())
                    loss.backward()
                    self.optimizer.step()
                self.scheduler.step()

    def dump(self, file_path, **kwarg):
        state = {"model": self.model.state_dict(), "optimizer": self.optimizer.state_dict()}
        torch.save(state, file_path)

    def load(self, file_path, **kwarg):
        self.model.load_state_dict(torch.load(file_path)["model"], **kwarg)
