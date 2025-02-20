import json
from time import time
from utils import language_utils

import functools
print = functools.partial(print, flush=True)


class CocoDatasetKarpathy:

    TrainSet_ID = 1
    ValidationSet_ID = 2
    TestSet_ID = 3

    def __init__(self,
                 images_path,
                 coco_annotations_path,
                 precalc_features_hdf5_filepath,
                 preproc_images_hdf5_filepath=None,
                 limited_num_train_images=None,
                 limited_num_val_images=None,
                 limited_num_test_images=None,
                 dict_min_occurrences=1,
                 verbose=True
                 ):
        super(CocoDatasetKarpathy, self).__init__()
        idx_of_ds = 0
        idx_of_train = 0
        idx_of_val  = 0
        self.use_images_instead_of_features = False
        if precalc_features_hdf5_filepath is None or precalc_features_hdf5_filepath == 'None' or \
                precalc_features_hdf5_filepath == 'none' or precalc_features_hdf5_filepath == '':
            self.use_images_instead_of_features = True
            print("Warning: since no hdf5 path is provided using images instead of pre-calculated features.")
            print("Features path: " + str(precalc_features_hdf5_filepath))

            self.preproc_images_hdf5_filepath = None
            if preproc_images_hdf5_filepath is not None:
                print("Preprocessed hdf5 file path not None: " + str(preproc_images_hdf5_filepath))
                print("Using preprocessed hdf5 file instead.")
                self.preproc_images_hdf5_filepath = preproc_images_hdf5_filepath

        else:
            self.precalc_features_hdf5_filepath = precalc_features_hdf5_filepath
            print("Features path: " + str(self.precalc_features_hdf5_filepath))
            print("Features path provided, images are provided in form of features.")

        if images_path is None:
            self.images_path = ""
        else:
            self.images_path = images_path

        self.karpathy_train_dict = dict()
        self.karpathy_val_dict = dict()
        
  

        with open(coco_annotations_path, 'r',encoding='utf-8') as f:
            json_file_img = json.load(f)['images']
        
        with open(coco_annotations_path, 'r',encoding='utf-8') as f:
            json_file_annotations = json.load(f)['annotations']


        if verbose:
            print("Initializing dataset... ", end=" ")
        for json_item in json_file_img:
            new_item = dict()

            new_item['img_path'] = self.images_path + json_item['filename']
            id_of_img = int(json_item['id'])


            
            
            new_item_captions  = [item['caption'] for item in json_file_annotations if item['image_id'] == id_of_img]

            new_item['img_id'] = id_of_img
            new_item['captions'] = new_item_captions

            if idx_of_ds < 3000:
                self.karpathy_train_dict[idx_of_train] = new_item
                idx_of_train += 1

                idx_of_ds += 1
            else:
                self.karpathy_val_dict[idx_of_val] = new_item
                
                idx_of_val += 1


        self.karpathy_train_list = []
        self.karpathy_val_list = []
        for key in self.karpathy_train_dict.keys():
            self.karpathy_train_list.append(self.karpathy_train_dict[key])
        for key in self.karpathy_val_dict.keys():
            self.karpathy_val_list.append(self.karpathy_val_dict[key])

        self.train_num_images = len(self.karpathy_train_list)
        self.val_num_images = len(self.karpathy_val_list)
        
        
        if limited_num_train_images is not None:
            self.karpathy_train_list = self.karpathy_train_list
            self.train_num_images = limited_num_train_images
        if limited_num_val_images is not None:
            self.karpathy_val_list = self.karpathy_val_list
            self.val_num_images = limited_num_val_images
        

        if verbose:
            print("Num train images: " + str(self.train_num_images))
            print("Num val images: " + str(self.val_num_images))


        tokenized_captions_list = []
        for i in range(self.train_num_images):
            for caption in self.karpathy_train_list[i]['captions']:
                tmp = language_utils.lowercase_and_clean_trailing_spaces([caption])
                tmp = language_utils.add_space_between_non_alphanumeric_symbols(tmp)
                tmp = language_utils.remove_punctuations(tmp)
                tokenized_caption = ['SOS'] + language_utils.tokenize(tmp)[0] + ['EOS']
                tokenized_captions_list.append(tokenized_caption)

        

        counter_dict = dict()
        for i in range(len(tokenized_captions_list)):
            for word in tokenized_captions_list[i]:
                if word not in counter_dict:
                    counter_dict[word] = 1
                else:
                    counter_dict[word] += 1



        less_than_min_occurrences_set = set()
        for k, v in counter_dict.items():
            if v < dict_min_occurrences:
                less_than_min_occurrences_set.add(k)
        if verbose:
            print("tot tokens " + str(len(counter_dict)) +
                  " less than " + str(dict_min_occurrences) + ": " + str(len(less_than_min_occurrences_set)) +
                  " remaining: " + str(len(counter_dict) - len(less_than_min_occurrences_set)))

        self.num_caption_vocab = 4
        self.max_seq_len = 0
        discovered_words = ['PAD', 'SOS', 'EOS', 'UNK']
        for i in range(len(tokenized_captions_list)):
            caption = tokenized_captions_list[i]
            if len(caption) > self.max_seq_len:
                self.max_seq_len = len(caption)
            for word in caption:
                if (str(word) not in discovered_words) and (not str(word) in less_than_min_occurrences_set) and (word.isdigit() is False):
                    discovered_words.append(word)
                    self.num_caption_vocab += 1

        discovered_words.sort()
        self.caption_word2idx_dict = dict()
        self.caption_idx2word_list = []
        for i in range(len(discovered_words)):
            self.caption_word2idx_dict[discovered_words[i]] = i
            self.caption_idx2word_list.append(discovered_words[i])
        if verbose:
            print("There are " + str(self.num_caption_vocab) + " vocabs in dict")
        

    def get_image_path(self, img_idx, dataset_split):

        if dataset_split == CocoDatasetKarpathy.ValidationSet_ID:
            img_path = self.karpathy_val_list[img_idx]['img_path']
            img_id = self.karpathy_val_list[img_idx]['img_id']
        else:
            img_path = self.karpathy_train_list[img_idx]['img_path']
            img_id = self.karpathy_train_list[img_idx]['img_id']

        return img_path, img_id

    def get_all_images_captions(self, dataset_split):
        all_image_references = []

        if dataset_split == CocoDatasetKarpathy.ValidationSet_ID:
            dataset = self.karpathy_val_list
        else:
            dataset = self.karpathy_train_list

        for img_idx in range(len(dataset)):
            all_image_references.append(dataset[img_idx]['captions'])
        return all_image_references

    def get_eos_token_idx(self):
        return self.caption_word2idx_dict['EOS']

    def get_sos_token_idx(self):
        return self.caption_word2idx_dict['SOS']

    def get_pad_token_idx(self):
        return self.caption_word2idx_dict['PAD']

    def get_unk_token_idx(self):
        return self.caption_word2idx_dict['UNK']

    def get_eos_token_str(self):
        return 'EOS'

    def get_sos_token_str(self):
        return 'SOS'

    def get_pad_token_str(self):
        return 'PAD'

    def get_unk_token_str(self):
        return 'UNK'
