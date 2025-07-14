#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/14 10:03
# @Author  : aqw
# @Email    : 1149918650@qq.com
# @File    : short_model_train.py
# @Project: 提供给北京的代码
# @Description: 短期风电预测模型构建、训练、测试
import warnings
warnings.filterwarnings('ignore')
from utils import *
import numpy as np
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import tensorflow as tf
import pickle
import platform
import logging

handler1 = logging.StreamHandler()
logfile = os.path.join(os.path.dirname(__file__), 'wind_short_model.log')
handler2 = logging.FileHandler(logfile, mode='a+')

handler1.setLevel(logging.INFO)
handler2.setLevel(logging.DEBUG)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s-%(filename)s[line:%(lineno)d]-%(levelname)s:%(message)s',
                    handlers=[handler1, handler2])

os.environ["CUDA_VISIBLE_DEVICES"] = "2"


# ----------------------------------------------------------------------------------------------Model
class Model():
    def __init__(self, x, y, args, is_training, keep_prob, useGpu, types):
        self.x = x
        self.y = y
        # self.keep_prob=0.5
        self.keep_prob = keep_prob
        self.batch_size = self.x.get_shape().as_list()[0]
        self.outputSize = self.y.get_shape().as_list()[-1]
        self.lr = args['lr']
        self.is_training = is_training
        self.types = types
        if useGpu:
            self.device='/gpu:0'
        else:
            self.device='/cpu:0'
        self.global_step = tf.Variable(0, trainable=False)
        self.lr = tf.train.exponential_decay(self.lr, self.global_step, 1000, 0.98)
        self.build_model()

    def fc(self):
        a1 = self.x
        unit = [500, 500, 500, 250]
        for i in range(len(unit)):
            a1 = tf.contrib.layers.fully_connected(a1, unit[i],normalizer_fn=tf.layers.batch_normalization,normalizer_params={'training': self.is_training})
            a1 = tf.contrib.layers.dropout(a1, keep_prob=self.keep_prob, is_training=self.is_training)
        with tf.name_scope('pred'):
            self.pred = tf.contrib.layers.fully_connected(a1, self.outputSize)
        tf.add_to_collection('pred', self.pred)

    def conv1d(self):
        # x[-1,8,?]
        a1 = self.x
        unit = [100, 100, 50]
        ks = [3, 3, 3]
        for i in range(len(unit)):
            a1 = tf.layers.conv1d(a1, filters=unit[i], kernel_size=ks[i], strides=2, padding='SAME')
        a1 = tf.layers.flatten(a1)
        unit = [150, 150, 100]
        # self.unit = [1024, 500, 500, 500, 250]
        for i in range(len(unit)):
            # 'scale':True weights_regularizer=tf.contrib.layers.l2_regularizer(0.0001)
            a1 = tf.contrib.layers.fully_connected(a1, unit[i], normalizer_fn=tf.layers.batch_normalization, normalizer_params={'training': self.is_training}, weights_regularizer=tf.contrib.layers.l2_regularizer(0.0001))
            a1 = tf.contrib.layers.dropout(a1, keep_prob=self.keep_prob, is_training=self.is_training)
        with tf.name_scope('pred'):
            self.pred = tf.contrib.layers.fully_connected(a1, self.outputSize,
                                                          weights_regularizer=tf.contrib.layers.l2_regularizer(0.0001))
        tf.add_to_collection('pred', self.pred)

    def model(self):
        if 'fc' in self.types:
            self.fc()
        else:
            self.conv1d()

    def summaries(self):
        tf.contrib.layers.summarize_tensors(tf.trainable_variables())
        tf.summary.scalar('loss', self.loss)
        # tf.summary.scalar('acc',self.acc)

    def build_model(self):
        with tf.device(self.device):
            self.model()
            self.loss = 0.05 * tf.reduce_mean(tf.square(self.y - self.pred)) + tf.reduce_mean(tf.abs(self.y - self.pred))
            self.update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
            with tf.control_dependencies(self.update_ops):
                # self.optim = tf.train.AdamOptimizer(self.lr).minimize(self.loss, global_step=self.global_step)
                self.optim = tf.train.AdamOptimizer(self.lr).minimize(self.loss)
            self.summaries()
            self.saver = tf.train.Saver()


def acc96(pred, y, teDate):
    date = teDate
    acc = 1 - (np.sqrt(np.mean(np.square(np.array(pred) - np.array(y)), axis=1))) / cap
    pred = time96(pred, teDate, date, 'pred')
    y = time96(y, teDate, date, 'y')
    rmse = np.sqrt(np.mean(np.square(np.array(pred) - np.array(y)), axis=1))
    acc96 = 1 - rmse / cap
    return acc96, acc


def acc(pred, y, teDate):
    rmse = np.sqrt(np.mean(np.square(np.array(pred) - np.array(y)), axis=1))
    acc_ = 1 - rmse / cap
    return acc_

# ----------------------------------------------------------------------------------Train
def train(trX, teX, trY, teY, savePath, types):
    with tf.Graph().as_default():
        batch_size = trX.shape[0]
        if 'fc' in types:
            inputSize = trX.shape[-1]
            x = tf.placeholder(tf.float32, [None, inputSize], name='input')
        else:
            inputSize = trX.shape[-1]
            time_seq = trX.shape[1]
            x = tf.placeholder(tf.float32, [None, time_seq, inputSize], name='input')
        outputSize = trY.shape[-1]
        y = tf.placeholder(tf.float32, [None, outputSize], name='output')
        keep_prob = tf.placeholder(tf.float32, [], name='keep_prob')
        is_training = tf.placeholder(tf.bool, [], name='is_train')

        if platform.system() == 'Windows':
            args['useGpu'] = False
        elif platform.system() == 'Linux':
            args['useGpu'] = True
        model = Model(x, y, args, is_training, keep_prob, useGpu=args['useGpu'], types=types)

        sess = tf.Session(config=tf.ConfigProto(allow_soft_placement=True, log_device_placement=False))
        sess.run(tf.global_variables_initializer())
        # train
        teDate = list(teY.index)
        tracc, teacc, trmse, temse = [], [], [], []
        teacc96 = []
        if teY.shape[-1] == 96:
            if types == 'power':
                bestAcc = 0.78
                bestCost = 8
            else:
                bestAcc = 0.89
                bestCost = 0.5

        else:
            bestAcc = 0.86
            bestCost = 650

        for i in range(args['epoch'] + 1):
            for start, end in zip(range(0, len(trX), batch_size), range(batch_size, len(trX) + 1, batch_size)):
                _ = sess.run(model.optim,feed_dict={x: trX[start:end], y: trY[start:end], keep_prob: 0.5, is_training: True})

            # test
            if i % args['saveStep'] == 0:
                trPred, trCost, trlr = sess.run([model.pred, model.loss, model.lr],feed_dict={x: trX, y: trY, keep_prob: 1.0,is_training: False})
                tePred, teCost, telr = sess.run([model.pred, model.loss, model.lr],feed_dict={x: teX, y: teY, keep_prob: 1.0,is_training: False})

                # teWriter.add_summary(teSummary, i)
                if trY.shape[-1] == 60:
                    trAcc96, trAcc = acc96(trPred, trY, teDate)
                    teAcc96, teAcc = acc96(tePred, teY, teDate)
                else:
                    trAcc96 = trAcc = acc(trPred, trY, teDate)
                    teAcc96 = teAcc = acc(tePred, teY, teDate)
                logging.info(
                    "Epoch:{},TrLoss:{:.6f},trAcc:{:.5f},TeLoss:{:.6f},teAcc:{:.5f},teAcc96:{:.5f}".format(i, trCost,np.array(trAcc).mean(),teCost,np.array(teAcc).mean(),np.array(teAcc96).mean()))
                tracc.append(np.mean(trAcc))
                trmse.append(trCost)
                teacc.append(np.mean(teAcc))
                teacc96.append(np.mean(teAcc96))
                temse.append(teCost)
                # save model
                if bestAcc < np.array(teAcc).mean():
                    bestAcc = np.array(teAcc).mean()
                    bestCost = teCost
                    logging.info('1,bestAcc:%s;bestCost:%s' % (bestAcc, teCost))
                    # save model
                    Path = os.path.join(savePath, args['savePath'])
                    os.makedirs(Path, exist_ok=True)
                    model.saver.save(sess, os.path.join(Path, 'model.ckpt'), global_step=i)
                    # fig
                    fig(tePred, teY, teDate, teAcc, teCost, i, savePath, cap)
                    p = os.path.join(savePath, 'result_%s.pkl' % i)
                    pickle.dump(
                        {'tePred': tePred, 'teY': teY, 'teDate': teDate, 'teAcc': teAcc, 'teCost': teCost, 'i': i},
                        open(p, 'wb'))
                elif bestCost > teCost:
                    bestCost = teCost
                    logging.info('2,bestAcc:%s;bestCost:%s' % (bestAcc, teCost))
                    # save model
                    Path = os.path.join(savePath, args['savePath'])
                    os.makedirs(Path, exist_ok=True)
                    model.saver.save(sess, os.path.join(Path, 'model.ckpt'), global_step=i)
                    fig(tePred, teY, teDate, teAcc, teCost, i, savePath, cap)
                    p = os.path.join(savePath, 'result_%s.pkl' % i)
                    pickle.dump(
                        {'tePred': tePred, 'teY': teY, 'teDate': teDate, 'teAcc': teAcc, 'teCost': teCost, 'i': i},
                        open(p, 'wb'))

        # saver.save(sess,os.path.join(savePath,'model.ckpt'),global_step=i)
        # mse
        plt.plot(trmse, 'r', label='train')
        plt.plot(temse, 'b', label='test')
        plt.title('trMse:%s  teMse:%s' % (np.array(trmse[10:]).mean(), np.array(temse[10:]).mean()))
        plt.legend(loc='upper right')
        plt.savefig(os.path.join(savePath, 'mse.png'))
        plt.close()
        # acc
        plt.plot(tracc, 'r', label='train')
        plt.plot(teacc, 'b', label='test')
        plt.title('tracc:%s,teacc:%s' % (np.mean(tracc[10:]), np.mean(teacc[10:])))
        plt.legend(loc='upper right')
        plt.savefig(os.path.join(savePath, 'all_acc.png'))
        plt.close()
        return np.array(trmse[10:]).mean(), np.array(temse[10:]).mean(), np.array(tracc[10:]).mean(), np.array(
            teacc[10:]).mean()


def run():
    types = 'fc'
    for ty in ['ws']:
        global cap
        if ty == 'power':
            cap = 99
        else:
            cap = 25
        for time_type in ['short']:
            if 'ncep' in ty:
                datavar = 'ncep'
            elif 'hxec' in ty:
                datavar = 'hxec'
            logging.info('{}, {} {} '.format(time_type, types,datavar))
            savePath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model_result', ty, time_type, types)
            os.makedirs(savePath, exist_ok=True)
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', ty, time_type)
            trX, trY, teX, teY, trdate, tedate = getData(datavar, savePath, path)
            tet = [i for i in tedate if i in trdate]
            assert len(tet) == 0, 'tedate in trdate'
            # train
            if 'fc' not in types:
                trX = np.array(trX).reshape((len(trX), 8, -1))
                teX = np.array(teX).reshape((len(teX), 8, -1))
            logging.info('{} {} {} {}'.format(trX.shape, trY.shape, teX.shape, teY.shape))
            logging.info('=============================================train')
            _ = train(trX, teX, trY, teY, savePath, types)


if __name__ == '__main__':
    run()
