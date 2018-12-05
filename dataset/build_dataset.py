from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
import os, cv2
import math, h5py
import numpy as np
import tensorflow as tf

import preprocess.first as first
import preprocess.default as default

flags = tf.app.flags
#/media/deeplearning/f3cff4c9-1ab9-47f0-8b82-231dedcbd61b/lcz
flags.DEFINE_string('dataset_folder', '/home/data/lcz', 'Folder containing dataset.')
flags.DEFINE_string('output_dir', '/media/jun/data/lcz/tfrecord', 'Output location of dataset.')
flags.DEFINE_string('preprocess_method', 'multilabel', 'The image data preprocess term.')
flags.DEFINE_float('split_factor', 0.98, 'The image data preprocess term.')
FLAGS = flags.FLAGS

_NUM_CLASSES = 17
_NUM_SHARDS = 4
_PREPROCESS_METHOD = {
    'default': default.default_preprocess,
    'first': first.first_preprocess,
    'multilabel': default.new_preprocess, 
}

def _int64_feature(value):
  return tf.train.Feature(int64_list=tf.train.Int64List(value=[value]))

def _float_feature(value):
  return tf.train.Feature(float_list=tf.train.FloatList(value=value))

def convert_dataset(dataset, s1, s2, labels, preprocess_fn, dataset_idx=None, num_shares=2):
  sys.stdout.write('Processing ' + dataset + '\n')
  sys.stdout.flush()

  if dataset_idx is None:
    num_samples = int(labels.shape[0])
  else:
    num_samples = len(dataset_idx)
  sys.stdout.write('Number of samples: %d\n' % (num_samples))
  sys.stdout.flush()

  num_per_shard = int(math.ceil(num_samples / float(num_shares)))
  for shard_id in range(num_shares):
    output_filename = os.path.join(
        FLAGS.output_dir,
        FLAGS.preprocess_method,
        '%s-%05d-of-%05d.tfrecord' % (dataset, shard_id, num_shares))
    writer = tf.python_io.TFRecordWriter(output_filename)
    start_idx = shard_id * num_per_shard
    end_idx = min((shard_id + 1) * num_per_shard, num_samples)
    for i in range(start_idx, end_idx):
      sys.stdout.write('\r>> Converting image %d/%d shard %d' % (
          i + 1, num_samples, shard_id))
      sys.stdout.flush()
      if dataset_idx is None:
        idx = i
      else:
        idx = dataset_idx[i]
      label = int(np.argmax(labels[idx])+1)
      wid_label = int(np.where(label<=10, 0, 1))

      s1_data = s1[idx]
      s2_data = s2[idx]
      img_data = preprocess_fn(s1_data, s2_data)
      img_data = np.reshape(img_data,[-1]).astype(np.float32)

      example = tf.train.Example(features=tf.train.Features(feature={
          'data': _float_feature(img_data),
          'class': _int64_feature(wid_label),
          'label': _int64_feature(label),
          'idx': _int64_feature(int(idx))
      }))
      writer.write(example.SerializeToString())
    sys.stdout.write('\n')
    sys.stdout.flush()

def convert_dataset_balance(dataset, s1, s2, labels, preprocess_fn, dataset_idx=None, class_num=None):
  sys.stdout.write('Processing ' + dataset + '\n')
  sys.stdout.flush()
  if dataset_idx is None:
    class_num = np.sum(labels, axis=0)
    dataset_idx = []
    for i in range(_NUM_CLASSES):
      dataset_idx.append(np.where(labels[:,i])[0])
  per_class_num = np.max(class_num)

  sys.stdout.write('Number of samples: %d\n' % (_NUM_CLASSES*per_class_num))
  sys.stdout.flush()

  num_per_shard = int(math.ceil(per_class_num/float(_NUM_SHARDS)))
  for shard_id in range(_NUM_SHARDS):
    output_filename = os.path.join(
        FLAGS.output_dir,
        FLAGS.preprocess_method,
        '%s-%05d-of-%05d.tfrecord' % (dataset, shard_id, _NUM_SHARDS))
    writer = tf.python_io.TFRecordWriter(output_filename)
    start_idx = shard_id * num_per_shard
    end_idx = min((shard_id+1) * num_per_shard, per_class_num)
    for i in range(start_idx, end_idx):
      sys.stdout.write('\r>> Converting batch of images %d/%d shard %d' % (
          i + 1, per_class_num, shard_id))
      sys.stdout.flush()
      for j in range(_NUM_CLASSES):
        try:
          idx = dataset_idx[j][i]
        except:
          idx = dataset_idx[j][np.random.randint(class_num[j])]

        label = int(np.argmax(labels[idx])+1)
        if label != (j+1):
          raise RuntimeError('Label is wrong.')
        wid_label = int(np.where(label<=10, 0, 1))
        s1_data = s1[idx]
        s2_data = s2[idx]
        img_data = preprocess_fn(s1_data, s2_data)
        img_data = np.reshape(img_data, [-1]).astype(np.float32)

        example = tf.train.Example(features=tf.train.Features(feature={
            'data': _float_feature(img_data),
            'class': _int64_feature(wid_label),
            'label': _int64_feature(label),
            'idx': _int64_feature(int(idx))
        }))
        writer.write(example.SerializeToString())
    sys.stdout.write('\n')
    sys.stdout.flush()


def _split_train_val(labels, split_factor):
  class_num_train = []
  train_dataset_idx = []
  val_dataset_idx = []
  for i in range(_NUM_CLASSES):
    idxs = np.where(labels[:,i])[0]
    np.random.shuffle(idxs)
    num_train = int(split_factor*len(idxs))
    class_num_train.append(num_train)
    train_dataset_idx.append(idxs[:num_train])
    val_dataset_idx += list(idxs[num_train:])
  return val_dataset_idx, train_dataset_idx, class_num_train


def main():
  if FLAGS.preprocess_method not in _PREPROCESS_METHOD:
    raise ValueError('The specified preprocess method is not supported yet.')
  preprocess_fn = _PREPROCESS_METHOD[FLAGS.preprocess_method]
  tf.gfile.MakeDirs(FLAGS.output_dir)
  tf.gfile.MakeDirs(os.path.join(FLAGS.output_dir, FLAGS.preprocess_method))

  path_training = os.path.join(FLAGS.dataset_folder, 'training.h5')
  path_validation = os.path.join(FLAGS.dataset_folder, 'validation.h5')
  fid_training = h5py.File(path_training,'r')
  s1_training = fid_training['sen1']
  s2_training = fid_training['sen2']
  label_training = fid_training['label']
  fid_validation = h5py.File(path_validation,'r')
  s1_validation = fid_validation['sen1']
  s2_validation = fid_validation['sen2']
  label_validation = fid_validation['label']
  
  val_train, train_train, num_train_train = _split_train_val(label_training, FLAGS.split_factor)
  val_val, train_val, num_train_val = _split_train_val(label_validation, FLAGS.split_factor)

  convert_dataset('oritrain', s1_training, s2_training, label_training, preprocess_fn)
  convert_dataset('orival', s1_validation, s2_validation, label_validation, preprocess_fn)
  convert_dataset_balance('train-val', s1_validation, s2_validation, label_validation,
                          preprocess_fn, train_val, num_train_val)
  convert_dataset('val-train', s1_training, s2_training, label_training, preprocess_fn, val_train)
  convert_dataset('val-val', s1_validation, s2_validation, label_validation,
                  preprocess_fn, val_val, num_shares=1)
  convert_dataset_balance('train-train', s1_training, s2_training, label_training,
                          preprocess_fn, train_train, num_train_train)

if __name__ == '__main__':
  main()