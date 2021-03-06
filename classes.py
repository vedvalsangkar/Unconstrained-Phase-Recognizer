#!/usr/bin/python3.5

# The custom datasets used for assignment 2 were built using the following site as a guide:
# https://github.com/utkuozbulak/pytorch-custom-dataset-examples
#
# Class and method structure was used with appropriate modifications as needed for this project.


import pandas as pd
import numpy as np

import torch

from torch.utils import data
from torchvision import transforms
from PIL import Image
from torch.utils.data.dataset import Dataset


class A2TrainDataSet(Dataset):

    def __init__(self, csv_file, image_root_folder='IJBA_images/'):
        """
        Training dataset loader class constructor. The file taken as input is expected to be cleaned before use.

        :param csv_file          : Input file containing image locations, subject and template numbers.
        :param image_root_folder : Folder containing the images
        """

        col_names = ['TEMPLATE_ID', 'SUBJECT_ID', 'FILE']

        self.to_tensor = transforms.ToTensor()
        self.data_info = pd.read_csv(filepath_or_buffer=csv_file,
                                     header=0,
                                     usecols=col_names,
                                     dtype=object)

        self.encoder = pd.read_csv(filepath_or_buffer="class_map.csv",
                                   header=0,
                                   index_col=1)

        # self.encoder.index = self.encoder.index.astype(object)

        self.decoder = pd.read_csv(filepath_or_buffer="class_map.csv",
                                   header=0,
                                   index_col=0,
                                   dtype=object)

        self.images = np.asarray(image_root_folder + self.data_info['SUBJECT_ID'] + '/' + self.data_info['FILE'])

        self.data_len = len(self.data_info.index)

        self.labels = np.asarray(self.data_info['SUBJECT_ID'].astype(int))

    def __getitem__(self, index):
        """
        Method for item retrieval. Overloaded to avoid dataloader bottleneck.

        :param index: Index of the required item.
        :return: Image and label as a tensor.
        """

        # Open image
        image_name = self.images[index]

        image_label = self.encoder.loc[self.labels[index], 'ENC']

        image = Image.open(image_name)

        tensor_img = self.to_tensor(image)

        return tensor_img, torch.tensor(image_label)

    def __len__(self):
        """
        Returns number of data entries.
        :return: Data size.
        """
        return self.data_len

    def clean(self, split):
        """
        Cleaner function which checks for images seen in input file. Dumps a "cleaned" version without those images
        which do not exist.
        :param split: Split number/file to clean.
        :return: None
        """
        del_list = []
        for i in range(self.data_len):
            try:
                _ = Image.open(self.images[i])
            except:
                print("Unable to access image {0} with index: {1}. Deleting.".format(self.images[i], i))
                del_list.append(i)

        self.data_info.drop(labels=self.data_info.index[del_list],
                            inplace=True)
        self.data_info.to_csv(path_or_buf="IJBA_sets/split" + str(split) + "/train_" + str(split) + "_clean.csv",
                              index=False)


class A2VerifyDataSet(Dataset):

    def __init__(self, comp_file, meta_file, image_root_folder='IJBA_images/'):
        """
        Testing dataset loader class constructor.
        :param comp_file         : File containing the comparisons as template pairs.
        :param meta_file         : File containing image locations, subject and template numbers.
        :param image_root_folder : Folder containing the images
        """

        meta_cols = ['TEMPLATE_ID', 'SUBJECT_ID', 'FILE']
        comp_cols = ['TEMPLATE_1', 'TEMPLATE_2']

        self.comp_data = pd.read_csv(filepath_or_buffer=comp_file,
                                     header=None,
                                     dtype=object)
        self.comp_data.columns = comp_cols

        self.template_1 = self.comp_data['TEMPLATE_1'].values.tolist()
        self.template_2 = self.comp_data['TEMPLATE_2'].values.tolist()

        self.meta_data = pd.read_csv(filepath_or_buffer=meta_file,
                                     header=0,
                                     usecols=meta_cols,
                                     dtype=object)

        self.data_len = len(self.comp_data.index)

        self.image_root_folder = image_root_folder

    def __getitem__(self, index):
        """
        Method for item retrieval. Overloaded to avoid dataloader bottleneck.

        :param index : Index of the required item.
        :return      : List of images for template 1, 2 and whether they are of the same subject or not.
        """
        template_1 = self.template_1[index]
        template_2 = self.template_2[index]

        t1 = self.meta_data[self.meta_data['TEMPLATE_ID'] == template_1].reset_index()
        t2 = self.meta_data[self.meta_data['TEMPLATE_ID'] == template_2].reset_index()

        list1 = (self.image_root_folder + t1['SUBJECT_ID'] + '/' + t1['FILE']).values.tolist()
        list2 = (self.image_root_folder + t2['SUBJECT_ID'] + '/' + t2['FILE']).values.tolist()

        label1 = t1.loc[0, 'SUBJECT_ID']
        label2 = t2.loc[0, 'SUBJECT_ID']

        return list1, list2, (label1 == label2)

    def __len__(self):
        """
        Returns number of data entries.

        :return: Data size.
        """
        return self.data_len


class Helper:

    def __init__(self, filename="log.txt"):
        """
        Class constructor.
        :param filename:
        """
        self.file = open(file=filename,
                         mode='w')
        self.flag_file = False

    def write_file(self, flag=False):
        """
        Setter method to set flag.
        :param flag: Flag for write to file or stdout.
        :return:
        """
        self.flag_file = flag

    def log(self, msg, end="\n"):
        """
        Method to print/write to file.
        :param msg: Message to write.
        :param end: Line ender.
        :return:
        """
        if self.flag_file:
            print(msg, end=end, file=self.file)
        else:
            print(msg, end=end)

    def close(self):
        """
        Closes the file.
        """
        self.file.close()

    def get_data(self, mode="both", training_batch_size=256, testing_batch_size=1, shuffle=True):
        """
        Get training and testing datasets and loaders.

        :param mode                : Data load mode. 'train', 'test' or 'both'.
        :param training_batch_size : Batch size for training.
        :param testing_batch_size  : Batch size for testing.
        :param shuffle             : Shuffle input images
        :return:                   : Training and testing datasets and loaders as created.
        """

        split_pre = "IJBA_sets/split"
        t_pre = "/train_"
        comp = "/verify_comparisons_"
        meta = "/verify_metadata_"
        ext = ".csv"
        ext2 = "_clean.csv"

        training_set = {}
        training_loader = {}
        testing_set = {}
        testing_loader = {}

        if mode == 'train' or mode == 'both':
            for set_n in range(1, 11):
                training_set[set_n] = A2TrainDataSet(split_pre + str(set_n) + t_pre + str(set_n) + ext2)
                training_loader[set_n] = data.DataLoader(dataset=training_set[set_n],
                                                         batch_size=training_batch_size,
                                                         shuffle=shuffle)
        if mode == 'test' or mode == 'both':
            for set_n in range(1, 11):
                testing_set[set_n] = A2VerifyDataSet(comp_file=split_pre + str(set_n) + comp + str(set_n) + ext,
                                                     meta_file=split_pre + str(set_n) + meta + str(set_n) + ext)

                testing_loader[set_n] = data.DataLoader(dataset=testing_set[set_n],
                                                        batch_size=testing_batch_size,
                                                        shuffle=shuffle)

        if mode == 'train':
            return training_set, training_loader
        if mode == 'test':
            return testing_set, testing_loader

        return training_set, training_loader, testing_set, testing_loader
