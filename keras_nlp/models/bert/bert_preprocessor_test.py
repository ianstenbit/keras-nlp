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
"""Tests for BERT preprocessor layer."""

import os

import pytest
import tensorflow as tf

from keras_nlp.backend import keras
from keras_nlp.models.bert.bert_preprocessor import BertPreprocessor
from keras_nlp.models.bert.bert_tokenizer import BertTokenizer
from keras_nlp.tests.test_case import TestCase


class BertPreprocessorTest(TestCase):
    def setUp(self):
        self.vocab = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]"]
        self.vocab += ["THE", "QUICK", "BROWN", "FOX"]
        self.vocab += ["the", "quick", "brown", "fox"]
        self.preprocessor = BertPreprocessor(
            BertTokenizer(vocabulary=self.vocab),
            sequence_length=8,
        )

    def test_tokenize_strings(self):
        input_data = "THE QUICK BROWN FOX."
        output = self.preprocessor(input_data)
        self.assertAllEqual(output["token_ids"], [2, 5, 6, 7, 8, 1, 3, 0])
        self.assertAllEqual(output["segment_ids"], [0, 0, 0, 0, 0, 0, 0, 0])
        self.assertAllEqual(output["padding_mask"], [1, 1, 1, 1, 1, 1, 1, 0])

    def test_tokenize_list_of_strings(self):
        # We should handle a list of strings as as batch.
        input_data = ["THE QUICK BROWN FOX."] * 4
        output = self.preprocessor(input_data)
        self.assertAllEqual(output["token_ids"], [[2, 5, 6, 7, 8, 1, 3, 0]] * 4)
        self.assertAllEqual(
            output["segment_ids"], [[0, 0, 0, 0, 0, 0, 0, 0]] * 4
        )
        self.assertAllEqual(
            output["padding_mask"], [[1, 1, 1, 1, 1, 1, 1, 0]] * 4
        )

    def test_tokenize_labeled_batch(self):
        x = tf.constant(["THE QUICK BROWN FOX."] * 4)
        y = tf.constant([1] * 4)
        sw = tf.constant([1.0] * 4)
        x_out, y_out, sw_out = self.preprocessor(x, y, sw)
        self.assertAllEqual(x_out["token_ids"], [[2, 5, 6, 7, 8, 1, 3, 0]] * 4)
        self.assertAllEqual(
            x_out["segment_ids"], [[0, 0, 0, 0, 0, 0, 0, 0]] * 4
        )
        self.assertAllEqual(
            x_out["padding_mask"], [[1, 1, 1, 1, 1, 1, 1, 0]] * 4
        )
        self.assertAllEqual(y_out, y)
        self.assertAllEqual(sw_out, sw)

    def test_tokenize_labeled_dataset(self):
        x = tf.constant(["THE QUICK BROWN FOX."] * 4)
        y = tf.constant([1] * 4)
        sw = tf.constant([1.0] * 4)
        ds = tf.data.Dataset.from_tensor_slices((x, y, sw))
        ds = ds.map(self.preprocessor)
        x_out, y_out, sw_out = ds.batch(4).take(1).get_single_element()
        self.assertAllEqual(x_out["token_ids"], [[2, 5, 6, 7, 8, 1, 3, 0]] * 4)
        self.assertAllEqual(
            x_out["segment_ids"], [[0, 0, 0, 0, 0, 0, 0, 0]] * 4
        )
        self.assertAllEqual(
            x_out["padding_mask"], [[1, 1, 1, 1, 1, 1, 1, 0]] * 4
        )
        self.assertAllEqual(y_out, y)
        self.assertAllEqual(sw_out, sw)

    def test_tokenize_multiple_sentences(self):
        sentence_one = tf.constant("THE QUICK")
        sentence_two = tf.constant("BROWN FOX.")
        output = self.preprocessor((sentence_one, sentence_two))
        self.assertAllEqual(output["token_ids"], [2, 5, 6, 3, 7, 8, 1, 3])
        self.assertAllEqual(output["segment_ids"], [0, 0, 0, 0, 1, 1, 1, 1])
        self.assertAllEqual(output["padding_mask"], [1, 1, 1, 1, 1, 1, 1, 1])

    def test_tokenize_multiple_batched_sentences(self):
        sentence_one = tf.constant(["THE QUICK"] * 4)
        sentence_two = tf.constant(["BROWN FOX."] * 4)
        # The first tuple or list is always interpreted as an enumeration of
        # separate sequences to concatenate.
        output = self.preprocessor((sentence_one, sentence_two))
        self.assertAllEqual(output["token_ids"], [[2, 5, 6, 3, 7, 8, 1, 3]] * 4)
        self.assertAllEqual(
            output["segment_ids"], [[0, 0, 0, 0, 1, 1, 1, 1]] * 4
        )
        self.assertAllEqual(
            output["padding_mask"], [[1, 1, 1, 1, 1, 1, 1, 1]] * 4
        )

    def test_errors_for_2d_list_input(self):
        ambiguous_input = [["one", "two"], ["three", "four"]]
        with self.assertRaises(ValueError):
            self.preprocessor(ambiguous_input)

    def test_serialization(self):
        config = keras.saving.serialize_keras_object(self.preprocessor)
        new_preprocessor = keras.saving.deserialize_keras_object(config)
        self.assertEqual(
            new_preprocessor.get_config(),
            self.preprocessor.get_config(),
        )

    @pytest.mark.large  # Saving is slow, so mark these large.
    @pytest.mark.tf_only
    def test_saved_model(self):
        input_data = tf.constant(["THE QUICK BROWN FOX."])
        inputs = keras.Input(dtype="string", shape=())
        outputs = self.preprocessor(inputs)
        model = keras.Model(inputs, outputs)
        path = os.path.join(self.get_temp_dir(), "model.keras")
        model.save(path, save_format="keras_v3")
        restored_model = keras.models.load_model(path)
        self.assertAllEqual(
            model(input_data)["token_ids"],
            restored_model(input_data)["token_ids"],
        )
