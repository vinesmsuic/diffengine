from typing import List, Optional, Union

import numpy as np
import torch
from diffusers import StableDiffusionXLAdapterPipeline, T2IAdapter
from diffusers.utils import load_image
from mmengine import print_log
from PIL import Image
from torch import nn

from diffengine.models.editors.stable_diffusion_xl import StableDiffusionXL
from diffengine.models.losses.snr_l2_loss import SNRL2Loss
from diffengine.registry import MODELS


@MODELS.register_module()
class StableDiffusionXLT2IAdapter(StableDiffusionXL):
    """Stable Diffusion XL T2I Adapter.

    Args:
        adapter_model (str, optional): Path to pretrained adapter model. If
            None, use the default adapter model. Defaults to None.
        adapter_model_channels (List[int]): The channels of adapter.
            Defaults to [320, 640, 1280, 1280].
        adapter_downscale_factor (int): The downscale factor of adapter.
            Defaults to 16.
        lora_config (dict, optional): The LoRA config dict. This should be
            `None` when training ControlNet. Defaults to None.
        finetune_text_encoder (bool, optional): Whether to fine-tune text
            encoder. This should be `False` when training ControlNet.
            Defaults to False.
        data_preprocessor (dict, optional): The pre-process config of
            :class:`SDControlNetDataPreprocessor`.
    """

    def __init__(self,
                 *args,
                 adapter_model: Optional[str] = None,
                 adapter_model_channels: List[int] = [320, 640, 1280, 1280],
                 adapter_downscale_factor: int = 16,
                 lora_config: Optional[dict] = None,
                 finetune_text_encoder: bool = False,
                 data_preprocessor: Optional[Union[dict, nn.Module]] = dict(
                     type='SDXLControlNetDataPreprocessor'),
                 **kwargs):
        assert lora_config is None, \
            '`lora_config` should be None when training ControlNet'
        assert not finetune_text_encoder, \
            '`finetune_text_encoder` should be False when training ControlNet'

        self.adapter_model = adapter_model
        self.adapter_model_channels = adapter_model_channels
        self.adapter_downscale_factor = adapter_downscale_factor

        super().__init__(
            *args,
            lora_config=lora_config,
            finetune_text_encoder=finetune_text_encoder,
            data_preprocessor=data_preprocessor,
            **kwargs)

    def set_lora(self):
        """Set LORA for model."""
        pass

    def prepare_model(self):
        """Prepare model for training.

        Disable gradient for some models.
        """
        if self.adapter_model is not None:
            self.adapter = T2IAdapter.from_pretrained(self.adapter_model)
        else:
            self.adapter = T2IAdapter(
                in_channels=3,
                channels=self.adapter_model_channels,
                num_res_blocks=2,
                downscale_factor=self.adapter_downscale_factor,
                adapter_type='full_adapter_xl',
            )

        if self.gradient_checkpointing:
            self.unet.enable_gradient_checkpointing()

        self.vae.requires_grad_(False)
        print_log('Set VAE untrainable.', 'current')
        self.text_encoder_one.requires_grad_(False)
        self.text_encoder_two.requires_grad_(False)
        print_log('Set Text Encoder untrainable.', 'current')
        self.unet.requires_grad_(False)
        print_log('Set Unet untrainable.', 'current')

    @torch.no_grad()
    def infer(self,
              prompt: List[str],
              condition_image: List[Union[str, Image.Image]],
              negative_prompt: Optional[str] = None,
              height: Optional[int] = None,
              width: Optional[int] = None) -> List[np.ndarray]:
        """Function invoked when calling the pipeline for generation.

        Args:
            prompt (`List[str]`):
                The prompt or prompts to guide the image generation.
            condition_image (`List[Union[str, Image.Image]]`):
                The condition image for ControlNet.
            negative_prompt (`Optional[str]`):
                The prompt or prompts to guide the image generation.
                Defaults to None.
            height (`int`, *optional*, defaults to
                `self.unet.config.sample_size * self.vae_scale_factor`):
                The height in pixels of the generated image.
            width (`int`, *optional*, defaults to
                `self.unet.config.sample_size * self.vae_scale_factor`):
                The width in pixels of the generated image.
        """
        assert len(prompt) == len(condition_image)
        pipeline = StableDiffusionXLAdapterPipeline.from_pretrained(
            self.model,
            vae=self.vae,
            text_encoder_one=self.text_encoder_one,
            text_encoder_two=self.text_encoder_two,
            tokenizer_one=self.tokenizer_one,
            tokenizer_two=self.tokenizer_two,
            unet=self.unet,
            adapter=self.adapter,
            safety_checker=None,
            dtype=torch.float16,
        )
        pipeline.to(self.device)
        pipeline.set_progress_bar_config(disable=True)
        images = []
        for p, img in zip(prompt, condition_image):
            if type(img) == str:
                img = load_image(img)
            img = img.convert('RGB')
            image = pipeline(
                p,
                p,
                img,
                negative_prompt=negative_prompt,
                num_inference_steps=50,
                height=height,
                width=width).images[0]
            images.append(np.array(image))

        del pipeline
        torch.cuda.empty_cache()

        return images

    def forward(self,
                inputs: torch.Tensor,
                data_samples: Optional[list] = None,
                mode: str = 'loss'):
        assert mode == 'loss'
        inputs['text_one'] = self.tokenizer_one(
            inputs['text'],
            max_length=self.tokenizer_one.model_max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt').input_ids.to(self.device)
        inputs['text_two'] = self.tokenizer_two(
            inputs['text'],
            max_length=self.tokenizer_two.model_max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt').input_ids.to(self.device)
        num_batches = len(inputs['img'])
        if 'result_class_image' in inputs:
            # use prior_loss_weight
            weight = torch.cat([
                torch.ones((num_batches // 2, )),
                torch.ones((num_batches // 2, )) * self.prior_loss_weight
            ]).float().reshape(-1, 1, 1, 1)
        else:
            weight = None

        latents = self.vae.encode(inputs['img']).latent_dist.sample()
        latents = latents * self.vae.config.scaling_factor

        noise = torch.randn_like(latents)

        if self.enable_noise_offset:
            noise = noise + self.noise_offset_weight * torch.randn(
                latents.shape[0], latents.shape[1], 1, 1, device=noise.device)

        # Cubic sampling to sample a random time step for each image.
        # For more details about why cubic sampling is used, refer to section
        # 3.4 of https://arxiv.org/abs/2302.08453
        timesteps = torch.rand((num_batches, ), device=self.device)
        timesteps = (1 -
                     timesteps**3) * self.scheduler.config.num_train_timesteps
        timesteps = timesteps.long()
        timesteps = timesteps.clamp(
            0, self.scheduler.config.num_train_timesteps - 1)

        noisy_latents = self.scheduler.add_noise(latents, noise, timesteps)

        prompt_embeds, pooled_prompt_embeds = self.encode_prompt(
            inputs['text_one'], inputs['text_two'])
        unet_added_conditions = {
            'time_ids': inputs['time_ids'],
            'text_embeds': pooled_prompt_embeds
        }

        if self.scheduler.config.prediction_type == 'epsilon':
            gt = noise
        elif self.scheduler.config.prediction_type == 'v_prediction':
            gt = self.scheduler.get_velocity(latents, noise, timesteps)
        else:
            raise ValueError('Unknown prediction type '
                             f'{self.scheduler.config.prediction_type}')

        down_block_additional_residuals = self.adapter(inputs['condition_img'])

        model_pred = self.unet(
            noisy_latents,
            timesteps,
            prompt_embeds,
            added_cond_kwargs=unet_added_conditions,
            down_block_additional_residuals=down_block_additional_residuals
        ).sample

        loss_dict = dict()
        # calculate loss in FP32
        if isinstance(self.loss_module, SNRL2Loss):
            loss = self.loss_module(
                model_pred.float(),
                gt.float(),
                timesteps,
                self.scheduler.alphas_cumprod,
                weight=weight)
        else:
            loss = self.loss_module(
                model_pred.float(), gt.float(), weight=weight)
        loss_dict['loss'] = loss
        return loss_dict
