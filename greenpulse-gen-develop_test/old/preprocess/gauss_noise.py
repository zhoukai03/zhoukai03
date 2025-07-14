def gauss_noise(data, mean=0, var=0.005):
    import numpy as np
    '''
    添加高斯噪声
    data : numpy.ndarray
    mean : 均值
    var : 方差
    '''
    noise = np.random.normal(mean, var ** 0.5, data.shape)
    out = data + data * noise  # 直接将归一化的图片与噪声相加

    return out

