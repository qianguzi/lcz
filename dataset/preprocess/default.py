from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np


def default_preprocess(s1_data, s2_data):
  s1_ = np.log10(s1_data[:,:,4:6]) 

  s1_[:,:,0] = np.where(s1_[:,:,0]>0.5, 0.5, s1_[:,:,0])
  s1_[:,:,0] = (np.where(s1_[:,:,0]<-3.5, -3.5, s1_[:,:,0])+3.5) / 4
  s1_[:,:,1] = np.where(s1_[:,:,1]>1.5, 1.5, s1_[:,:,1])
  s1_[:,:,1] = (np.where(s1_[:,:,1]<-3, -3, s1_[:,:,1])+3) / 4.5

  s2_ = np.concatenate([s2_data[:,:,0:3], np.expand_dims(s2_data[:,:,6], -1)], -1)
  for i in range(3):
    s2_[:,:,i] = np.log10(s2_[:,:,i] + 0.05)
  s2_[:,:,3] = np.log10(s2_[:,:,3] + 0.07)

  s2_[:,:,0] = np.where(s2_[:,:,0]>-0.4, -0.4, s2_[:,:,0])
  s2_[:,:,0] = (np.where(s2_[:,:,0]<-1.0, -1.0, s2_[:,:,0])+1.0) / 0.6
  s2_[:,:,1] = np.where(s2_[:,:,1]>-0.3, -0.3, s2_[:,:,1])
  s2_[:,:,1] = (np.where(s2_[:,:,1]<-1.1, -1.1, s2_[:,:,1])+1.1) / 0.8
  s2_[:,:,2] = np.where(s2_[:,:,2]>-0.25, -0.25, s2_[:,:,2])
  s2_[:,:,2] = (np.where(s2_[:,:,2]<-1.15, -1.15, s2_[:,:,2])+1.15) / 0.9
  s2_[:,:,3] = np.where(s2_[:,:,3]>-0.15, -0.15, s2_[:,:,3])
  s2_[:,:,3] = (np.where(s2_[:,:,3]<-1.15, -1.15, s2_[:,:,3])+1.15) / 1.0

  img_data = np.concatenate([s1_, s2_], -1)
  return img_data
