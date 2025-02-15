# Copyright 2023 The KerasNLP Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for OPT tokenizer layer."""
import os

import pytest
import tensorflow as tf

from keras_nlp.backend import keras
from keras_nlp.models.opt.opt_tokenizer import OPTTokenizer
from keras_nlp.tests.test_case import TestCase


class OPTTokenizerTest(TestCase):
    def setUp(self):
        self.vocab = {
            "<pad>": 0,
            "</s>": 1,
            "Ġair": 2,
            "plane": 3,
            "Ġat": 4,
            "port": 5,
            "Ġkoh": 6,
            "li": 7,
            "Ġis": 8,
            "Ġthe": 9,
            "Ġbest": 10,
        }

        merges = ["Ġ a", "Ġ t", "Ġ k", "Ġ i", "Ġ b", "Ġa i", "p l", "n e"]
        merges += ["Ġa t", "p o", "r t", "o h", "l i", "Ġi s", "Ġb e", "s t"]
        merges += ["Ġt h", "Ġai r", "pl a", "Ġk oh", "Ġth e", "Ġbe st", "po rt"]
        merges += ["pla ne"]
        self.merges = merges

        self.tokenizer = OPTTokenizer(vocabulary=self.vocab, merges=self.merges)

    def test_tokenize(self):
        input_data = " airplane at airport"
        output = self.tokenizer(input_data)
        self.assertAllEqual(output, [2, 3, 4, 2, 5])

    def test_tokenize_special_tokens(self):
        input_data = "</s> airplane at airport</s><pad>"
        output = self.tokenizer(input_data)
        self.assertAllEqual(output, [1, 2, 3, 4, 2, 5, 1, 0])

    def test_tokenize_batch(self):
        input_data = [" airplane at airport", " kohli is the best"]
        output = self.tokenizer(input_data)
        self.assertAllEqual(output, [[2, 3, 4, 2, 5], [6, 7, 8, 9, 10]])

    def test_detokenize(self):
        input_tokens = [2, 3, 4, 2, 5]
        output = self.tokenizer.detokenize(input_tokens)
        self.assertEqual(output, " airplane at airport")

    def test_vocabulary_size(self):
        self.assertEqual(self.tokenizer.vocabulary_size(), 11)

    def test_errors_missing_special_tokens(self):
        with self.assertRaises(ValueError):
            OPTTokenizer(vocabulary=["a", "b", "c"], merges=[])

    def test_serialization(self):
        config = keras.saving.serialize_keras_object(self.tokenizer)
        new_tokenizer = keras.saving.deserialize_keras_object(config)
        self.assertEqual(
            new_tokenizer.get_config(),
            self.tokenizer.get_config(),
        )

    @pytest.mark.large  # Saving is slow, so mark these large.
    @pytest.mark.tf_only
    def test_saved_model(self):
        input_data = tf.constant([" airplane at airport"])

        inputs = keras.Input(dtype="string", shape=())
        outputs = self.tokenizer(inputs)
        model = keras.Model(inputs, outputs)

        path = os.path.join(self.get_temp_dir(), "model.keras")
        model.save(path, save_format="keras_v3")

        restored_model = keras.models.load_model(path)
        self.assertAllEqual(
            model(input_data),
            restored_model(input_data),
        )
