from unittest import TestCase

import torch
from diffusers import T2IAdapter
from mmengine.optim import OptimWrapper
from torch.optim import SGD

from diffengine.models.editors import (SDXLControlNetDataPreprocessor,
                                       StableDiffusionXLT2IAdapter)
from diffengine.models.losses import L2Loss


class TestStableDiffusionXLControlNet(TestCase):

    def test_init(self):
        with self.assertRaisesRegex(AssertionError,
                                    '`lora_config` should be None'):
            _ = StableDiffusionXLT2IAdapter(
                'hf-internal-testing/tiny-stable-diffusion-xl-pipe',
                data_preprocessor=SDXLControlNetDataPreprocessor(),
                lora_config=dict(rank=4))

        with self.assertRaisesRegex(AssertionError,
                                    '`finetune_text_encoder` should be False'):
            _ = StableDiffusionXLT2IAdapter(
                'hf-internal-testing/tiny-stable-diffusion-xl-pipe',
                data_preprocessor=SDXLControlNetDataPreprocessor(),
                finetune_text_encoder=True)

    def test_infer(self):
        StableDiffuser = StableDiffusionXLT2IAdapter(
            'hf-internal-testing/tiny-stable-diffusion-xl-pipe',
            adapter_model='hf-internal-testing/tiny-adapter',
            data_preprocessor=SDXLControlNetDataPreprocessor())
        assert isinstance(StableDiffuser.adapter, T2IAdapter)

        # test infer
        result = StableDiffuser.infer(
            ['an insect robot preparing a delicious meal'],
            ['tests/testdata/color.jpg'],
            height=64,
            width=64)
        assert len(result) == 1
        assert result[0].shape == (64, 64, 3)

        # test device
        assert StableDiffuser.device.type == 'cpu'

        # test adapter model is None
        StableDiffuser = StableDiffusionXLT2IAdapter(
            'hf-internal-testing/tiny-stable-diffusion-xl-pipe',
            adapter_model_channels=[32, 64],
            adapter_downscale_factor=4,
            data_preprocessor=SDXLControlNetDataPreprocessor())
        assert isinstance(StableDiffuser.adapter, T2IAdapter)

        result = StableDiffuser.infer(
            ['an insect robot preparing a delicious meal'],
            ['tests/testdata/color.jpg'],
            height=64,
            width=64)
        assert len(result) == 1
        assert result[0].shape == (64, 64, 3)

        # test device
        assert StableDiffuser.device.type == 'cpu'

    def test_train_step(self):
        # test load with loss module
        StableDiffuser = StableDiffusionXLT2IAdapter(
            'hf-internal-testing/tiny-stable-diffusion-xl-pipe',
            adapter_model='hf-internal-testing/tiny-adapter',
            loss=L2Loss(),
            data_preprocessor=SDXLControlNetDataPreprocessor())

        # test train step
        data = dict(
            inputs=dict(
                img=[torch.zeros((3, 64, 64))],
                text=['a dog'],
                time_ids=[torch.zeros((1, 6))],
                condition_img=[torch.zeros((3, 64, 64))]))
        optimizer = SGD(StableDiffuser.parameters(), lr=0.1)
        optim_wrapper = OptimWrapper(optimizer)
        log_vars = StableDiffuser.train_step(data, optim_wrapper)
        assert log_vars
        self.assertIsInstance(log_vars['loss'], torch.Tensor)

    def test_train_step_with_gradient_checkpointing(self):
        # test load with loss module
        StableDiffuser = StableDiffusionXLT2IAdapter(
            'hf-internal-testing/tiny-stable-diffusion-xl-pipe',
            adapter_model='hf-internal-testing/tiny-adapter',
            loss=L2Loss(),
            data_preprocessor=SDXLControlNetDataPreprocessor(),
            gradient_checkpointing=True)

        # test train step
        data = dict(
            inputs=dict(
                img=[torch.zeros((3, 64, 64))],
                text=['a dog'],
                time_ids=[torch.zeros((1, 6))],
                condition_img=[torch.zeros((3, 64, 64))]))
        optimizer = SGD(StableDiffuser.parameters(), lr=0.1)
        optim_wrapper = OptimWrapper(optimizer)
        log_vars = StableDiffuser.train_step(data, optim_wrapper)
        assert log_vars
        self.assertIsInstance(log_vars['loss'], torch.Tensor)

    def test_val_and_test_step(self):
        StableDiffuser = StableDiffusionXLT2IAdapter(
            'hf-internal-testing/tiny-stable-diffusion-xl-pipe',
            adapter_model='hf-internal-testing/tiny-adapter',
            loss=L2Loss(),
            data_preprocessor=SDXLControlNetDataPreprocessor())

        # test val_step
        with self.assertRaisesRegex(NotImplementedError, 'val_step is not'):
            StableDiffuser.val_step(torch.zeros((1, )))

        # test test_step
        with self.assertRaisesRegex(NotImplementedError, 'test_step is not'):
            StableDiffuser.test_step(torch.zeros((1, )))
