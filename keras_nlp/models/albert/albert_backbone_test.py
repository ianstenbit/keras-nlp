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
"""Test for ALBERT backbone model."""

import os

import pytest
import tensorflow as tf

from keras_nlp.backend import keras
from keras_nlp.backend import ops
from keras_nlp.models.albert.albert_backbone import AlbertBackbone
from keras_nlp.tests.test_case import TestCase


class AlbertBackboneTest(TestCase):
    def setUp(self):
        self.backbone = AlbertBackbone(
            vocabulary_size=10,
            num_layers=2,
            num_heads=2,
            num_groups=1,
            num_inner_repetitions=1,
            embedding_dim=16,
            hidden_dim=2,
            intermediate_dim=4,
            max_sequence_length=5,
        )
        self.batch_size = 8
        self.input_batch = {
            "token_ids": ops.ones((2, 5), dtype="int32"),
            "segment_ids": ops.ones((2, 5), dtype="int32"),
            "padding_mask": ops.ones((2, 5), dtype="int32"),
        }

        self.input_dataset = tf.data.Dataset.from_tensor_slices(
            self.input_batch
        ).batch(2)

    def test_valid_call_albert(self):
        self.backbone(self.input_batch)

    def test_name(self):
        # Check default name passed through
        self.assertRegexpMatches(self.backbone.name, "albert_backbone")

    def test_variable_sequence_length_call_albert(self):
        for seq_length in (2, 3, 4):
            input_data = {
                "token_ids": ops.ones((2, seq_length), dtype="int32"),
                "segment_ids": ops.ones((2, seq_length), dtype="int32"),
                "padding_mask": ops.ones((2, seq_length), dtype="int32"),
            }
            self.backbone(input_data)

    def test_predict(self):
        self.backbone.predict(self.input_batch)
        self.backbone.predict(self.input_dataset)

    def test_serialization(self):
        new_backbone = keras.saving.deserialize_keras_object(
            keras.saving.serialize_keras_object(self.backbone)
        )
        self.assertEqual(new_backbone.get_config(), self.backbone.get_config())

    def test_error_for_invalid_num_groups(self):
        with self.assertRaises(ValueError):
            self.model = AlbertBackbone(
                vocabulary_size=10,
                num_layers=3,
                num_heads=2,
                num_groups=2,
                num_inner_repetitions=1,
                embedding_dim=4,
                hidden_dim=64,
                intermediate_dim=128,
            )

    @pytest.mark.large
    def test_saved_model(self):
        model_output = self.backbone(self.input_batch)
        path = os.path.join(self.get_temp_dir(), "model.keras")
        self.backbone.save(path, save_format="keras_v3")
        restored_model = keras.models.load_model(path)

        # Check we got the real object back.
        self.assertIsInstance(restored_model, AlbertBackbone)

        # Check that output matches.
        restored_output = restored_model(self.input_batch)
        self.assertAllClose(
            model_output["pooled_output"], restored_output["pooled_output"]
        )


@pytest.mark.tpu
@pytest.mark.usefixtures("tpu_test_class")
class AlbertBackboneTPUTest(TestCase):
    def setUp(self):
        with self.tpu_strategy.scope():
            self.backbone = AlbertBackbone(
                vocabulary_size=10,
                num_layers=2,
                num_heads=2,
                num_groups=1,
                num_inner_repetitions=1,
                embedding_dim=16,
                hidden_dim=2,
                intermediate_dim=2,
                max_sequence_length=4,
            )

        self.input_batch = {
            "token_ids": ops.ones((8, 128), dtype="int32"),
            "segment_ids": ops.ones((8, 128), dtype="int32"),
            "padding_mask": ops.ones((8, 128), dtype="int32"),
        }
        self.input_dataset = tf.data.Dataset.from_tensor_slices(
            self.input_batch
        ).batch(2)

    def test_predict(self):
        self.backbone.compile()
        self.backbone.predict(self.input_dataset)
