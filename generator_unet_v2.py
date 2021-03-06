# this code is a deeper unet than unet_1.py
# it currently extends to 512 as the largest layer, 
# Will need to test if 1080 card can handle a 1024 layer as the center one
# may be able to accomodate it using a batch size of 1 if nessessary
#1/24 added more 512 layers... might break gpu
import os
import sys
import random
import warnings

import numpy as np
import pandas as pd

import matplotlib.pyplot as plt

from tqdm import tqdm
from itertools import chain
from skimage.io import imread, imshow, imread_collection, concatenate_images
from skimage.transform import resize
from skimage.morphology import label

from keras.optimizers import Adam, SGD, RMSprop
from keras.models import Model, load_model
from keras.layers import Input
from keras.layers.core import Dropout, Lambda
from keras.layers.convolutional import Conv2D, Conv2DTranspose
from keras.layers.pooling import MaxPooling2D
from keras.layers.merge import concatenate
from keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint, TensorBoard
from keras import backend as K
from keras import regularizers
from keras.layers import Input, concatenate, Conv2D, MaxPooling2D, Activation, UpSampling2D, BatchNormalization


from keras.preprocessing.image import ImageDataGenerator

from losses import bce_dice_loss, dice_loss, weighted_bce_dice_loss, weighted_dice_loss, dice_coeff

import tensorflow as tf


import cv2
import os
import pandas as pd
from sklearn.model_selection import train_test_split



def make_df(train_path, test_path, img_size):
	print('lets do this!')
	train_ids = next(os.walk(train_path))[1]
	test_ids = next(os.walk(test_path))[1]
	X_train = np.zeros((len(train_ids), img_size, img_size, 3), dtype=np.uint8)
	Y_train = np.zeros((len(train_ids), img_size, img_size, 1), dtype=np.bool)
	for i, id_ in enumerate(train_ids):
		path = train_path + id_
		#print(path)
		img = cv2.imread(path + '/images/' + id_ + '.png')
		img = cv2.resize(img, (img_size, img_size))
		X_train[i] = img
		mask = np.zeros((img_size, img_size, 1), dtype=np.bool)
		for mask_file in next(os.walk(path + '/masks/'))[2]:
			mask_ = cv2.imread(path + '/masks/' + mask_file, 0)
			mask_ = cv2.resize(mask_, (img_size, img_size))
			mask_ = mask_[:, :, np.newaxis]
			mask = np.maximum(mask, mask_)
		Y_train[i] = mask
	X_test = np.zeros((len(test_ids), img_size, img_size, 3), dtype=np.uint8)
	sizes_test = []
	for i, id_ in enumerate(test_ids):
		path = test_path + id_
		img = cv2.imread(path + '/images/' + id_ + '.png')
		sizes_test.append([img.shape[0], img.shape[1]])
		img = cv2.resize(img, (img_size, img_size))
		X_test[i] = img

	return X_train, Y_train, X_test, sizes_test



# Check if training data looks all right
#ix = random.randint(0, len(train_ids))
#imshow(X_train[ix])
#plt.show()
#imshow(np.squeeze(Y_train[ix]))
#plt.show()

'''
Need to fix this part
'''

# Define IoU metric
def mean_iou(y_true, y_pred):
	prec = []
	for t in np.arange(0.5, 1.0, 0.05):
		y_pred_ = tf.to_int32(y_pred > t)
		score, up_opt = tf.metrics.mean_iou(y_true, y_pred_, 2)
		K.get_session().run(tf.local_variables_initializer())
		with tf.control_dependencies([up_opt]):
			score = tf.identity(score)
		prec.append(score)
	return K.mean(K.stack(prec), axis=0)


# Build U-Net model    
#added regularization since conv layers have small numbers of nodes the effect is smaller
def get_unet_256(input_shape=(256, 256, 3),
				 num_classes=1):

	inputs = Input(shape=input_shape)
	# 256

	down0 = Conv2D(32, (3, 3), padding='same')(inputs)
	down0 = BatchNormalization()(down0)
	down0 = Activation('relu')(down0)
	down0 = Conv2D(32, (3, 3), padding='same')(down0)
	down0 = BatchNormalization()(down0)
	down0 = Activation('relu')(down0)
	down0_pool = MaxPooling2D((2, 2), strides=(2, 2))(down0)
	# 128

	down1 = Conv2D(64, (3, 3), padding='same')(down0_pool)
	down1 = BatchNormalization()(down1)
	down1 = Activation('relu')(down1)
	down1 = Conv2D(64, (3, 3), padding='same')(down1)
	down1 = BatchNormalization()(down1)
	down1 = Activation('relu')(down1)
	down1_pool = MaxPooling2D((2, 2), strides=(2, 2))(down1)
	# 64

	down2 = Conv2D(128, (3, 3), padding='same')(down1_pool)
	down2 = BatchNormalization()(down2)
	down2 = Activation('relu')(down2)
	down2 = Conv2D(128, (3, 3), padding='same')(down2)
	down2 = BatchNormalization()(down2)
	down2 = Activation('relu')(down2)
	down2_pool = MaxPooling2D((2, 2), strides=(2, 2))(down2)
	# 32

	down3 = Conv2D(256, (3, 3), padding='same')(down2_pool)
	down3 = BatchNormalization()(down3)
	down3 = Activation('relu')(down3)
	down3 = Conv2D(256, (3, 3), padding='same')(down3)
	down3 = BatchNormalization()(down3)
	down3 = Activation('relu')(down3)
	down3_pool = MaxPooling2D((2, 2), strides=(2, 2))(down3)
	# 16

	down4 = Conv2D(512, (3, 3), padding='same')(down3_pool)
	down4 = BatchNormalization()(down4)
	down4 = Activation('relu')(down4)
	down4 = Conv2D(512, (3, 3), padding='same')(down4)
	down4 = BatchNormalization()(down4)
	down4 = Activation('relu')(down4)
	down4_pool = MaxPooling2D((2, 2), strides=(2, 2))(down4)
	# 8

	center = Conv2D(1024, (3, 3), padding='same')(down4_pool)
	center = BatchNormalization()(center)
	center = Activation('relu')(center)
	center = Conv2D(1024, (3, 3), padding='same')(center)
	center = BatchNormalization()(center)
	center = Activation('relu')(center)
	# center

	up4 = UpSampling2D((2, 2))(center)
	up4 = concatenate([down4, up4], axis=3)
	up4 = Conv2D(512, (3, 3), padding='same')(up4)
	up4 = BatchNormalization()(up4)
	up4 = Activation('relu')(up4)
	up4 = Conv2D(512, (3, 3), padding='same')(up4)
	up4 = BatchNormalization()(up4)
	up4 = Activation('relu')(up4)
	up4 = Conv2D(512, (3, 3), padding='same')(up4)
	up4 = BatchNormalization()(up4)
	up4 = Activation('relu')(up4)
	# 16

	up3 = UpSampling2D((2, 2))(up4)
	up3 = concatenate([down3, up3], axis=3)
	up3 = Conv2D(256, (3, 3), padding='same')(up3)
	up3 = BatchNormalization()(up3)
	up3 = Activation('relu')(up3)
	up3 = Conv2D(256, (3, 3), padding='same')(up3)
	up3 = BatchNormalization()(up3)
	up3 = Activation('relu')(up3)
	up3 = Conv2D(256, (3, 3), padding='same')(up3)
	up3 = BatchNormalization()(up3)
	up3 = Activation('relu')(up3)
	# 32

	up2 = UpSampling2D((2, 2))(up3)
	up2 = concatenate([down2, up2], axis=3)
	up2 = Conv2D(128, (3, 3), padding='same')(up2)
	up2 = BatchNormalization()(up2)
	up2 = Activation('relu')(up2)
	up2 = Conv2D(128, (3, 3), padding='same')(up2)
	up2 = BatchNormalization()(up2)
	up2 = Activation('relu')(up2)
	up2 = Conv2D(128, (3, 3), padding='same')(up2)
	up2 = BatchNormalization()(up2)
	up2 = Activation('relu')(up2)
	# 64

	up1 = UpSampling2D((2, 2))(up2)
	up1 = concatenate([down1, up1], axis=3)
	up1 = Conv2D(64, (3, 3), padding='same')(up1)
	up1 = BatchNormalization()(up1)
	up1 = Activation('relu')(up1)
	up1 = Conv2D(64, (3, 3), padding='same')(up1)
	up1 = BatchNormalization()(up1)
	up1 = Activation('relu')(up1)
	up1 = Conv2D(64, (3, 3), padding='same')(up1)
	up1 = BatchNormalization()(up1)
	up1 = Activation('relu')(up1)
	# 128

	up0 = UpSampling2D((2, 2))(up1)
	up0 = concatenate([down0, up0], axis=3)
	up0 = Conv2D(32, (3, 3), padding='same')(up0)
	up0 = BatchNormalization()(up0)
	up0 = Activation('relu')(up0)
	up0 = Conv2D(32, (3, 3), padding='same')(up0)
	up0 = BatchNormalization()(up0)
	up0 = Activation('relu')(up0)
	up0 = Conv2D(32, (3, 3), padding='same')(up0)
	up0 = BatchNormalization()(up0)
	up0 = Activation('relu')(up0)
	# 256

	classify = Conv2D(num_classes, (1, 1), activation='sigmoid')(up0)

	model = Model(inputs=inputs, outputs=classify)

	model.compile(optimizer=RMSprop(lr=0.0001), loss=bce_dice_loss, metrics=['binary_crossentropy'])

	return model


def generator(xtr, xval, ytr, yval, batch_size):
	data_gen_args = dict(horizontal_flip=True,
						 vertical_flip=True,
						 rotation_range=90.,
						 width_shift_range=0.3,
						 height_shift_range=0.3,
						 shear_range = 0.3,
						 zoom_range=0.3)
	image_datagen = ImageDataGenerator(**data_gen_args)
	mask_datagen = ImageDataGenerator(**data_gen_args)
	image_datagen.fit(xtr, seed=7)
	mask_datagen.fit(ytr, seed=7)
	image_generator = image_datagen.flow(xtr, batch_size=batch_size, seed=7)
	mask_generator = mask_datagen.flow(ytr, batch_size=batch_size, seed=7)
	train_generator = zip(image_generator, mask_generator)

	val_gen_args = dict()
	image_datagen_val = ImageDataGenerator(**val_gen_args)
	mask_datagen_val = ImageDataGenerator(**val_gen_args)
	image_datagen_val.fit(xval, seed=7)
	mask_datagen_val.fit(yval, seed=7)
	image_generator_val = image_datagen_val.flow(xval, batch_size=batch_size, seed=7)
	mask_generator_val = mask_datagen_val.flow(yval, batch_size=batch_size, seed=7)
	val_generator = zip(image_generator_val, mask_generator_val)

	return train_generator, val_generator



def rle_encoding(x):
	dots = np.where(x.T.flatten() == 1)[0]
	run_lengths = []
	prev = -2
	for b in dots:
		if (b>prev+1): run_lengths.extend((b + 1, 0))
		run_lengths[-1] += 1
		prev = b
	return run_lengths

def prob_to_rles(x, cutoff=0.5):
	lab_img = label(x > cutoff)
	for i in range(1, lab_img.max() + 1):
		yield rle_encoding(lab_img == i)

if __name__ == "__main__":


	# Set some parameters
	img_size = 256
	batch_size_n = 8
	val_hold_out = 0.05 #with larger set might as well keep more samples....?

	IMG_HEIGHT = 256
	IMG_CHANNELS = 3

	#TRAIN_PATH = 'C:/Users/micha/Desktop/2018_dsb/input/stage1_train/'
	TEST_PATH = 'C:/Users/micha/Desktop/2018_dsb/input/stage1_test/'
	TRAIN_PATH = 'C:/Users/micha/Desktop/2018_dsb/input/stage1_aug_train/'

	model_names = 'standard_unet_2_1.h5'
	save_names = 'standard_unet_2_1.csv'

	sub_name ='C:/Users/micha/Desktop/2018_dsb/submission_files/sub-'+save_names
	final_sub_name ='C:/Users/micha/Desktop/2018_dsb/submission_files/final_sub-'+save_names

	save_name_file = 'C:/Users/micha/Desktop/2018_dsb/models/model-'+model_names
	final_model = 'C:/Users/micha/Desktop/2018_dsb/models/final_model-'+model_names

	print('building train and val sets')
	X_train, Y_train, X_test, sizes_test = make_df(TRAIN_PATH, TEST_PATH, img_size)
	xtr, xval, ytr, yval = train_test_split(X_train, Y_train, test_size=val_hold_out, random_state=7)
	train_generator, val_generator = generator(xtr, xval, ytr, yval, batch_size_n)
	model = get_unet_256()

	model.summary()

	#load old models if restarting runs
	# Fit model
	#earlystopper = EarlyStopping(patience=patience, verbose=1)
	callbacks = [EarlyStopping(monitor='val_loss',
							   patience=8,
							   verbose=1,
							   min_delta=1e-4),
				 ReduceLROnPlateau(monitor='val_loss',
								   factor=0.1,
								   patience=4,
								   verbose=1,
								   epsilon=1e-4),
				 ModelCheckpoint(monitor='val_loss',
								 filepath=save_name_file,
								 save_best_only=True),
				 ModelCheckpoint(final_model),
				 TensorBoard(log_dir='logs')]

	#checkpointer = ModelCheckpoint(save_name_file, verbose=1, save_best_only=True)
	#ever_epoch_checkpt = ModelCheckpoint(final_model)
	model.fit_generator(train_generator, steps_per_epoch=len(xtr)/batch_size_n, epochs=epoch_n,
						validation_data=val_generator, validation_steps=len(xval)/batch_size_n,callbacks=callbacks,verbose = 2)
	model.save(final_model)

	#### PREDICTIONS ... but can always run in submission file

	model = load_model(save_name_file)

	preds_test = model.predict(X_test, verbose=1)

	preds_test_upsampled = []
	
	for i in range(len(preds_test)):
		preds_test_upsampled.append(cv2.resize(preds_test[i], 
										   (sizes_test[i][1], sizes_test[i][0])))
		
	test_ids = next(os.walk(test_path))[1]
	new_test_ids = []
	rles = []
	for n, id_ in enumerate(test_ids):
		rle = list(prob_to_rles(preds_test_upsampled[n]))
		rles.extend(rle)
		new_test_ids.extend([id_] * len(rle))
	sub = pd.DataFrame()
	sub['ImageId'] = new_test_ids
	sub['EncodedPixels'] = pd.Series(rles).apply(lambda x: ' '.join(str(y) for y in x))
	
	sub.to_csv(sub_name, index=False)


	model = load_model(final_model)

	preds_test = model.predict(X_test, verbose=1)

	preds_test_upsampled = []
	for i in range(len(preds_test)):
		preds_test_upsampled.append(cv2.resize(preds_test[i], 
										   (sizes_test[i][1], sizes_test[i][0])))
		
	test_ids = next(os.walk(test_path))[1]
	new_test_ids = []
	rles = []
	for n, id_ in enumerate(test_ids):
		rle = list(prob_to_rles(preds_test_upsampled[n]))
		rles.extend(rle)
		new_test_ids.extend([id_] * len(rle))
	sub = pd.DataFrame()
	sub['ImageId'] = new_test_ids
	sub['EncodedPixels'] = pd.Series(rles).apply(lambda x: ' '.join(str(y) for y in x))
	
	sub.to_csv(final_sub_name, index=False)
