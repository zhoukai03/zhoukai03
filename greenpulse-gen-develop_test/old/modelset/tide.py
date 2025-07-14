import torch
import torch.nn as nn
import torch.nn.functional as F
from einops import rearrange
import modelset.base as base
import numpy as np


class ResidualBlock(nn.Module):
    def __init__(self, in_dim, hidden_dim, out_dim, dropout_rate=0.2):
        super(ResidualBlock, self).__init__()
        self.linear_1 = nn.Linear(in_dim, hidden_dim)
        self.linear_2 = nn.Linear(hidden_dim, out_dim)
        self.linear_res = nn.Linear(in_dim, out_dim)
        self.dropout = nn.Dropout(dropout_rate)
        self.layernorm = nn.LayerNorm(out_dim)

    def forward(self, x):
        # x: [B,L,in_dim] or [B,in_dim]
        h = F.relu(self.linear_1(x))  # [B,L,in_dim] -> [B,L,hidden_dim] or [B,in_dim] -> [B,hidden_dim]
        h = self.dropout(self.linear_2(h))  # [B,L,hidden_dim] -> [B,L,out_dim] or [B,hidden_dim] -> [B,out_dim]
        res = self.linear_res(x)  # [B,L,in_dim] -> [B,L,out_dim] or [B,in_dim] -> [B,out_dim]
        out = self.layernorm(h + res)  # [B,L,out_dim] or [B,out_dim]

        # out: [B,L,out_dim] or [B,out_dim]
        return out


class Encoder(nn.Module):
    def __init__(self, layer_num, hidden_dim, r, r_hat, L, H, A, featureProjectionHidden):
        super(Encoder, self).__init__()
        self.encoder_layer_num = layer_num
        self.horizon = H
        self.feature_projection = ResidualBlock(r, featureProjectionHidden, r_hat)
        self.first_encoder_layer = ResidualBlock(L + A + (L + H) * r_hat, hidden_dim, hidden_dim)
        self.other_encoder_layers = nn.ModuleList([
            ResidualBlock(hidden_dim, hidden_dim, hidden_dim) for _ in range(layer_num - 1)
        ])

    def forward(self, x, covariates, attributes):
        # x: [B*N,L], covariates: [B*N,L+H,r], attributes: [B*N,1]

        # Feature Projection
        covariates = self.feature_projection(covariates)  # [B*N,L+H,r] -> [B*N,L+H,r_hat]
        covariates_future = covariates[:, -self.horizon:, :]  # [B*N,H,r_hat]

        # Flatten
        covariates_flat = rearrange(covariates, 'b l r -> b (l r)')  # [B*N,L+H,r_hat] -> [B*N,(L+H)*r_hat]

        # Concat
        e = torch.cat([x, attributes, covariates_flat], dim=1)  # [B*N,L+1+(L+H)*r_hat]

        # Dense Encoder
        e = self.first_encoder_layer(e)  # [B*N,L+1+(L+H)*r_hat] -> [B*N,hidden_dim]
        for i in range(self.encoder_layer_num - 1):
            e = self.other_encoder_layers[i](e)  # [B*N,hidden_dim] -> [B*N,hidden_dim]

        # e: [B*N,hidden_dim], covariates_future: [B*N,H,r_hat]
        return e, covariates_future


class Decoder(nn.Module):
    def __init__(self, layer_num, hidden_dim, r_hat, H, p, temporalDecoderHidden):
        super(Decoder, self).__init__()
        self.decoder_layer_num = layer_num
        self.horizon = H
        self.last_decoder_layer = ResidualBlock(hidden_dim, hidden_dim, p * H)
        self.other_decoder_layers = nn.ModuleList([
            ResidualBlock(hidden_dim, hidden_dim, hidden_dim) for _ in range(layer_num - 1)
        ])
        self.temporaldecoder = ResidualBlock(p + r_hat, temporalDecoderHidden, 1)

    def forward(self, e, covariates_future):
        # e: [B*N,hidden_dim], covariates_future: [B*N,H,r_hat]

        # Dense Decoder
        for i in range(self.decoder_layer_num - 1):
            e = self.other_decoder_layers[i](e)  # [B*N,hidden_dim] -> [B*N,hidden_dim]
        g = self.last_decoder_layer(e)  # [B*N,hidden_dim] -> [B*N,p*H]

        # Unflatten
        matrixD = rearrange(g, 'b (h p) -> b h p', h=self.horizon)  # [B*N,p*H] -> [B*N,H,p]

        # Stack
        out = torch.cat([matrixD, covariates_future], dim=-1)  # [B*N,H,p+r_hat]

        # Temporal Decoder
        out = self.temporaldecoder(out)  # [B*N,H,p+r_hat] -> [B*N,H,1]

        # out: [B*N,H,1]
        return out


class TiDE(nn.Module):
    def __init__(self, params, **kwargs):
        # B: Batchsize
        # L: Lookback
        # H: Horizon
        # N: the number of series
        # r: the number of covariates for each series
        # r_hat: temporalWidth in the paper, i.e., \hat{r} << r
        # p: decoderOutputDim in the paper
        # hidden_dim: hiddenSize in the paper
        super(TiDE, self).__init__()
        self.encoder = Encoder(params.encoder_layer_num, params.hidden_dim, params.r, params.r_hat, params.L, params.H,
                               params.A, params.featureProjectionHidden)
        self.decoder = Decoder(params.decoder_layer_num, params.hidden_dim, params.r_hat, params.H, params.p,
                               params.temporalDecoderHidden)
        self.residual = nn.Linear(params.L, params.H)

    def forward(self, x, covariates, attributes):
        # x: [B,L,N], covariates: [B,L+H,N,r], attributes: [B,N,2]
        batch_size = x.size(0)

        # Channel Independence: Convert Multivariate series to Univariate series
        x = rearrange(x, 'b l n -> (b n) l')  # [B,L,N] -> [B*N,L]
        covariates = rearrange(covariates, 'b l n r -> (b n) l r')  # [B,L+H,N,r] -> [B*N,L+H,r]
        attributes = rearrange(attributes, 'b n t -> (b n) t')  # [B,N,2] -> [B*N,2]

        # Encoder
        e, covariates_future = self.encoder(x, covariates, attributes)

        # Decoder
        out = self.decoder(e, covariates_future)  # out: [B*N,H,1]

        # Global Residual
        prediction = out.squeeze(-1) + self.residual(x)  # prediction: [B*N,H]

        # Reshape
        prediction = rearrange(prediction, '(b n) h -> b h n', b=batch_size)  # [B*N,H] -> [B,H,N]

        # prediction: [B,H,N]
        return prediction


class tide(base.BaseModel):
    def __init__(self, params, **kwargs):
        _device = kwargs.get("device", None)
        if _device is None:
            self.device = torch.device(device="cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device=_device)
        self.model = TiDE(params).to(self.device)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=params.learning_rate)
        self.params = params
        print(self.device)

    def predict(self, data, **kwargs):
        self.model.eval()

        data_x, data_covariates, data_attributes = data[0], data[1], data[2]

        data_x = torch.tensor(data_x, dtype=torch.float32).to(self.device)
        data_covariates = torch.tensor(data_covariates, dtype=torch.float32).to(self.device)
        data_attributes = torch.tensor(data_attributes, dtype=torch.float32).to(self.device)

        pred_x = torch.zeros((1, self.params.L, data_x.size(-1)), dtype=torch.float32).to(self.device)
        pred_cova = torch.zeros((1, self.params.L + self.params.H, 1, data_covariates.size(-1)),
                                dtype=torch.float32).to(self.device)
        pred_attr = torch.zeros((1, 1, data_attributes.size(-1)), dtype=torch.float32).to(self.device)

        for i in range(0, int(int(len(data_x) - self.params.H) / 1 / int(self.params.L)) * 1 * int(self.params.L),
                       1 * self.params.L):
            pred_x[0] = data_x[i + 0 * self.params.L:i + 1 * self.params.L, :]

            pred_cova[0, :, 0, :] = data_covariates[i + 0 * self.params.L:i + 1 * self.params.L + self.params.H, :]

            pred_attr[0, 0, 0] = data_attributes[i, 0]
            pred_attr[0, 0, 1] = data_attributes[i, 1]

            with torch.no_grad():
                y_pred = self.model(pred_x, pred_cova, pred_attr)
            if "pred_y" in locals():
                pred_y = torch.cat((pred_y, y_pred), dim=0)
            else:
                pred_y = y_pred
            print("y_pred shape: ", y_pred.shape)
            print("pred_y shape: ", pred_y.shape)
        return pred_y.detach().numpy()

    def train(self, X_train, Y_train, X_val=None, Y_val=None, **kwargs):
        """
        train_data, val_data 需要归一化 (0,1) 区间内
        """

        loss_function = nn.MSELoss()
        epochs = self.params.epochs

        for epoch in range(epochs):
            self.model.train()
            self.optimizer.zero_grad()

            y_train = torch.tensor(Y_train.values, dtype=torch.float32).to(self.device)
            y_val = torch.tensor(Y_val.values, dtype=torch.float32).to(self.device)

            X_train_x, X_train_covariates, X_train_attributes = X_train[0], X_train[1], X_train[2]

            X_train_x = torch.tensor(X_train_x.values, dtype=torch.float32).to(self.device)
            X_train_covariates = torch.tensor(X_train_covariates.values, dtype=torch.float32).to(self.device)
            X_train_attributes = torch.tensor(X_train_attributes.values, dtype=torch.float32).to(self.device)

            train_x = torch.zeros((self.params.B, self.params.L, X_train_x.size(-1)), dtype=torch.float32).to(
                self.device)
            train_cova = torch.zeros((self.params.B, self.params.L + self.params.H, 1, X_train_covariates.size(-1)),
                                     dtype=torch.float32).to(self.device)
            train_attr = torch.zeros((self.params.B, 1, X_train_attributes.size(-1)), dtype=torch.float32).to(
                self.device)
            train_y = torch.zeros((self.params.B, self.params.H, 1), dtype=torch.float32).to(self.device)

            t_loss = []
            for i in range(0,
                           int(int(
                               len(X_train_x) - self.params.H - self.params.B * self.params.L) / self.params.B / int(
                               self.params.L)) * self.params.B * int(self.params.L), 96):

                for j in range(0, self.params.B):
                    train_x[j] = X_train_x[i + j * self.params.L:i + (j + 1) * self.params.L, :]
                    train_y[j] = y_train[i + (j + 1) * self.params.L:i + (j + 1) * self.params.L + self.params.H, :]

                    train_cova[j, :, 0, :] = X_train_covariates[
                                             i + j * self.params.L:i + (j + 1) * self.params.L + self.params.H,
                                             :]
                    train_attr[j, 0, :] = X_train_attributes[i, :]

                y_pred = self.model(train_x, train_cova, train_attr)
                y_pred = torch.squeeze(y_pred)
                loss = loss_function(y_pred, train_y[:, :, 0])
                t_loss.append(loss.item())
                loss.backward()
                self.optimizer.step()

            if X_val is not None and Y_val is not None and epoch % 10 == 0:
                self.model.eval()
                X_val_x, X_val_covariates, X_val_attributes = X_val[0], X_val[1], X_val[2]

                X_val_x = torch.tensor(X_val_x.values, dtype=torch.float32).to(self.device)
                X_val_covariates = torch.tensor(X_val_covariates.values, dtype=torch.float32).to(self.device)
                X_val_attributes = torch.tensor(X_val_attributes.values, dtype=torch.float32).to(self.device)

                val_x = torch.zeros((1, self.params.L, X_val_x.size(-1)), dtype=torch.float32).to(self.device)
                val_cova = torch.zeros((1, self.params.L + self.params.H, 1, X_val_covariates.size(-1)),
                                       dtype=torch.float32).to(self.device)
                val_attr = torch.zeros((1, 1, X_val_attributes.size(-1)), dtype=torch.float32).to(self.device)
                val_y = torch.zeros((1, self.params.H, 1), dtype=torch.float32).to(self.device)

                v_loss = []
                for i in range(0, int(int(len(X_val_x) - self.params.H - 1 * self.params.L) / 1 / int(
                        self.params.L)) * 1 * int(self.params.L), 96):
                    val_x[0] = X_val_x[i + 0 * self.params.L:i + 1 * self.params.L, :]

                    val_cova[0, :, 0, :] = X_val_covariates[
                                           i + 0 * self.params.L:i + 1 * self.params.L + self.params.H, :]

                    val_attr[0, 0, :] = X_val_attributes[i, :]

                    val_y[0] = y_val[i + 1 * self.params.L:i + 1 * self.params.L + self.params.H, :]

                    y_valid = self.model(val_x, val_cova, val_attr)
                    y_valid = torch.squeeze(y_valid)
                    v_loss.append(loss_function(y_valid, val_y[:, :, 0]).item())

                print("Epoch: {}/{}.. ".format(epoch, epochs),
                      "Training Loss: {:.3f}.. ".format(np.mean(t_loss)),
                      "Validation Loss: {:.3f}.. ".format(np.mean(v_loss)))
                self.model.train()

    def dump(self, file_path, **kwarg):
        state = {"model": self.model.state_dict(), "optimizer": self.optimizer.state_dict()}
        torch.save(state, file_path)

    def load(self, file_path, **kwarg):
        self.model.load_state_dict(torch.load(file_path)["model"], **kwarg)
