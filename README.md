# Image Segmentation 2018 DSB

## Background

In my spare time I am going to be working on building out a response for the 2018 data science bowl hosted on Kaggle. This year's competition is based around generated image masks for cells which appear in images. The images are mostly 256x256 but some extend to be 256x320, for the most part the data looks clean and make for a standard segmentation problem. The initial pipeline will be built around a Unet architecture. For now it is a relatively small network, but testing will be done to expand the size of the network. 

## Initial Results

The mini Unet is enough to get a leaderboard score of .269 with relatively little data and no augmentation. Next iterations are going to use heavily augmented data, this may lead to overfitting, but it is worth testing.

Deeper Unet with 14K data augmentation gets to .334 or something which is good enough for a early top 20 spot which is cool. Next steps are going to build out wauys to augment the dataset...

Issue with continuing to scale up the augmentation is that it is likely to cause the repetition of data which may lead to overfitting in the long run. Currently testing a dataset with around 26K samples, log loss is performing well. Time shall tell. 



## Further Testing/TODO List

-Test code to use generators for data augmentation (built, need to debug)
  Can go ahead and test on single images. Or another thing to do is apply noise ahead of time

-test gaussian noise layer? might help with data augmentation

-Start building ensemble... look to some other challenges on ensemble methods in segmentation challenges... since one model is not going to be enough to win long term... can also look to other challenges on how to implement ensemble methods for segmentation tasks.

-add images to readme

## Done List

-Deploy deeper Unet I think I can get at least up to 512 conv layers using my 1080X Nvidia card (DONE)
  1080 is able to handle deeper Unet, but it requires that we use single image batches. Was able to build the Unet down to 1024 level. 