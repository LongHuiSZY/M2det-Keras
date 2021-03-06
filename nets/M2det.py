import keras
import numpy as np
import tensorflow as tf
from utils.utils import PriorProbability
from nets.VGG import VGG16

def conv2d(inputs, filters, kernel_size, strides, padding, name='conv'):
    conv = keras.layers.Conv2D(filters=filters, kernel_size=kernel_size, strides=strides, padding=padding, name=name+'_conv')(inputs)
    bn = keras.layers.BatchNormalization(name=name+'_BN')(conv)
    relu = keras.layers.Activation('relu',name=name)(bn)
    return relu


def FFMv1(C4, C5, feature_size_1=256, feature_size_2=512,
          name='FFMv1'):
    # 40,40,256
    F4 = conv2d(C4, filters=feature_size_1, kernel_size=(3, 3), strides=(1, 1), padding='same', name='F4')
    # 20,20,512
    F5 = conv2d(C5, filters=feature_size_2, kernel_size=(1, 1), strides=(1, 1), padding='same', name='F5')
    # 40,40,512
    F5 = keras.layers.UpSampling2D(size=(2, 2), name='F5_Up')(F5)

    outputs = keras.layers.Concatenate(name=name)([F4, F5])
    # 40,40,768
    return outputs


def FFMv2(stage, base, tum, base_size=(40,40,768), tum_size=(40,40,128), feature_size=128, name='FFMv2'):

    # 40,40,128
    outputs = conv2d(base, filters=feature_size, kernel_size=(1, 1), strides=(1, 1), padding='same', name=name+"_"+str(stage) + '_base_feature')
    outputs = keras.layers.Concatenate(name=name+"_"+str(stage))([outputs, tum])
    # 40,40,256
    return outputs


def TUM(stage, inputs, feature_size=256, name="TUM"):
    # 128
    output_features = feature_size // 2

    size_buffer = []

    # 40,40,256
    f1 = inputs
    # 20,20,256
    f2 = conv2d(f1, filters=feature_size, kernel_size=(3, 3), strides=(2, 2), padding='same',name=name + "_" + str(stage) + '_f2')
    # 10,10,256
    f3 = conv2d(f2, filters=feature_size, kernel_size=(3, 3), strides=(2, 2), padding='same',name=name + "_" + str(stage) + '_f3')
    # 5,5,256   
    f4 = conv2d(f3, filters=feature_size, kernel_size=(3, 3), strides=(2, 2), padding='same',name=name + "_" + str(stage) + '_f4')
    # 3,3,256
    f5 = conv2d(f4, filters=feature_size, kernel_size=(3, 3), strides=(2, 2), padding='same',name=name + "_" + str(stage) + '_f5')
    # 1,1,256
    f6 = conv2d(f5, filters=feature_size, kernel_size=(3, 3), strides=(2, 2), padding='valid',name=name + "_" + str(stage) + '_f6')

    # 40,40
    size_buffer.append([int(f1.shape[2])] * 2)
    # 20,20
    size_buffer.append([int(f2.shape[2])] * 2)
    # 10,10
    size_buffer.append([int(f3.shape[2])] * 2)
    # 5,5
    size_buffer.append([int(f4.shape[2])] * 2)
    # 3,3
    size_buffer.append([int(f5.shape[2])] * 2)
    
    # print(size_buffer)
    level = 2
    c6 = f6
    # 1,1,256
    c5 = conv2d(c6, filters=feature_size, kernel_size=(3, 3), strides=(1, 1), padding='same',name=name + "_" + str(stage) + '_c5')
    # 3,3,256
    c5 = keras.layers.Lambda(lambda x: tf.image.resize_bilinear(x, size=size_buffer[4]), name=name + "_" + str(stage) + '_upsample_add5')(c5)
    c5 = keras.layers.Add()([c5, f5])
 
    # 3,3,256
    c4 = conv2d(c5, filters=feature_size, kernel_size=(3, 3), strides=(1, 1), padding='same', name=name + "_" + str(stage) + '_c4')
    # 5,5,256
    c4 = keras.layers.Lambda(lambda x: tf.image.resize_bilinear(x, size=size_buffer[3]), name=name + "_" + str(stage) + '_upsample_add4')(c4)
    c4 = keras.layers.Add()([c4, f4])

    # 5,5,256
    c3 = conv2d(c4, filters=feature_size, kernel_size=(3, 3), strides=(1, 1), padding='same', name=name + "_" + str(stage) + '_c3')
    # 10,10,256
    c3 = keras.layers.Lambda(lambda x: tf.image.resize_bilinear(x, size=size_buffer[2]), name=name + "_" + str(stage) + '_upsample_add3')(c3)
    c3 = keras.layers.Add()([c3, f3])

    # 10,10,256
    c2 = conv2d(c3, filters=feature_size, kernel_size=(3, 3), strides=(1, 1), padding='same', name=name + "_" + str(stage) + '_c2')
    # 20,20,256
    c2 = keras.layers.Lambda(lambda x: tf.image.resize_bilinear(x, size=size_buffer[1]), name=name + "_" + str(stage) + '_upsample_add2')(c2)
    c2 = keras.layers.Add()([c2, f2])

    # 20,20,256
    c1 = conv2d(c2, filters=feature_size, kernel_size=(3, 3), strides=(1, 1), padding='same', name=name + "_" + str(stage) + '_c1')
    # 40,40,256
    c1 = keras.layers.Lambda(lambda x: tf.image.resize_bilinear(x, size=size_buffer[0]), name=name + "_" + str(stage) + '_upsample_add1')(c1)
    c1 = keras.layers.Add()([c1, f1])

    level = 3

    # 40,40,128 
    o1 = conv2d(c1, filters=output_features, kernel_size=(1, 1), strides=(1, 1), padding='valid',name=name + "_" + str(stage) + '_o1')
    # 20,20,128
    o2 = conv2d(c2, filters=output_features, kernel_size=(1, 1), strides=(1, 1), padding='valid',name=name + "_" + str(stage) + '_o2')
    # 10,10,128
    o3 = conv2d(c3, filters=output_features, kernel_size=(1, 1), strides=(1, 1), padding='valid',name=name + "_" + str(stage) + '_o3')
    # 5,5,128
    o4 = conv2d(c4, filters=output_features, kernel_size=(1, 1), strides=(1, 1), padding='valid',name=name + "_" + str(stage) + '_o4')
    # 3,3,128
    o5 = conv2d(c5, filters=output_features, kernel_size=(1, 1), strides=(1, 1), padding='valid',name=name + "_" + str(stage) + '_o5')
    # 1,1,128
    o6 = conv2d(c6, filters=output_features, kernel_size=(1, 1), strides=(1, 1), padding='valid',name=name + "_" + str(stage) + '_o6')

    outputs = [o1, o2, o3, o4, o5, o6]

    return outputs

def _create_feature_pyramid(base_feature, stage=8):
    features = [[],[],[],[],[],[]]
    # 将输入进来的
    inputs = keras.layers.Conv2D(filters=256, kernel_size=1, strides=1, padding='same')(base_feature)
    # 第一个TUM模块
    outputs = TUM(1,inputs)
    max_output = outputs[0]
    for j in range(len(features)):
        features[j].append(outputs[j])

    # 第2,3,4个TUM模块，需要将上一个Tum模块输出的40x40x128的内容，传入到下一个Tum模块中
    for i in range(2, stage+1):
        # 将Tum模块的输出和基础特征层传入到FFmv2层当中
        # 输入为base_feature 40x40x768，max_output 40x40x128
        # 输出为40x40x256
        inputs = FFMv2(i - 1,base_feature, max_output)
        # 输出为40x40x128、20x20x128、10x10x128、5x5x128、3x3x128、1x1x128
        outputs = TUM(i,inputs)

        max_output = outputs[0]
        for j in range(len(features)):
            features[j].append(outputs[j])
    # 进行了4次TUM
    # 将获得的同样大小的特征层堆叠到一起
    concatenate_features = []
    for feature in features:
        concat = keras.layers.Concatenate()([f for f in feature])
        concatenate_features.append(concat)
    return concatenate_features


def _calculate_input_sizes(concatenate_features):
    input_size = []
    for features in concatenate_features:
        size = (int(features.shape[1]), int(features.shape[2]), int(features.shape[3]))
        input_size.append(size)

    return input_size

# 注意力机制
def SE_block(inputs, input_size, compress_ratio=16, name='SE_block'):
    pool = keras.layers.GlobalAveragePooling2D()(inputs)
    reshape = keras.layers.Reshape((1, 1, input_size[2]))(pool)

    fc1 = keras.layers.Conv2D(filters=input_size[2] // compress_ratio, kernel_size=1, strides=1, padding='valid',
                              activation='relu', name=name+'_fc1')(reshape)
    fc2 = keras.layers.Conv2D(filters=input_size[2], kernel_size=1, strides=1, padding='valid', activation='sigmoid',
                              name=name+'_fc2')(fc1)

    reweight = keras.layers.Multiply(name=name+'_reweight')([inputs, fc2])

    return reweight


def SFAM(feature_pyramid,input_sizes, compress_ratio=16, name='SFAM'):
    outputs = []
    for i in range(len(input_sizes)):
        input_size = input_sizes[i]
        _input = feature_pyramid[i]
        _output = SE_block(_input, input_size, compress_ratio=compress_ratio, name='SE_block_' + str(i))

        outputs.append(_output)
    return outputs


def m2det(num_classes,inputs, num_anchors=6, name='m2det'):
    if inputs==None:
        inputs = keras.layers.Input(shape=(320, 320, 3))
    else:
        inputs = inputs
    
    C3, C4, C5 = VGG16(inputs).outputs[1:]

    # 40,40,768
    base_feature = FFMv1(C4, C5, feature_size_1=256, feature_size_2=512)

    feature_pyramid = _create_feature_pyramid(base_feature, stage=4)

    feature_pyramid_sizes = _calculate_input_sizes(feature_pyramid)

    outputs = SFAM(feature_pyramid,feature_pyramid_sizes)

    regressions = []
    classifications = []
    for feature in outputs:
        classification = keras.layers.Conv2D(filters=num_classes * num_anchors,kernel_size=3,strides=1,padding='same')(feature)
        classification = keras.layers.Reshape((-1, num_classes))(classification)
        classification = keras.layers.Activation('softmax')(classification)

        regression = keras.layers.Conv2D(filters=num_anchors * 4,kernel_size=3,strides=1,padding='same')(feature)
        regression = keras.layers.Reshape((-1, 4))(regression)

        regressions.append(regression)
        classifications.append(classification)
    
    regressions = keras.layers.Concatenate(axis=1, name="regression")(regressions)
    classifications = keras.layers.Concatenate(axis=1, name="classification")(classifications)
    pyramids = [regressions,classifications]

    return keras.models.Model(inputs=inputs, outputs=pyramids, name=name)

