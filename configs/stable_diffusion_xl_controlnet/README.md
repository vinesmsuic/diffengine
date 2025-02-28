# Stable Diffusion XL ControlNet

[Adding Conditional Control to Text-to-Image Diffusion Models](https://arxiv.org/abs/2302.05543)

## Abstract

We present a neural network structure, ControlNet, to control pretrained large diffusion models to support additional input conditions. The ControlNet learns task-specific conditions in an end-to-end way, and the learning is robust even when the training dataset is small (\< 50k). Moreover, training a ControlNet is as fast as fine-tuning a diffusion model, and the model can be trained on a personal devices. Alternatively, if powerful computation clusters are available, the model can scale to large amounts (millions to billions) of data. We report that large diffusion models like Stable Diffusion can be augmented with ControlNets to enable conditional inputs like edge maps, segmentation maps, keypoints, etc. This may enrich the methods to control large diffusion models and further facilitate related applications.

<div align=center>
<img src="https://github.com/okotaku/diffengine/assets/24734142/97a5d6b7-90b9-4247-936c-c27e26b47cff"/>
</div>

## Citation

```
@misc{zhang2023adding,
  title={Adding Conditional Control to Text-to-Image Diffusion Models},
  author={Lvmin Zhang and Maneesh Agrawala},
  year={2023},
  eprint={2302.05543},
  archivePrefix={arXiv},
  primaryClass={cs.CV}
}
```

## Run Training

Run Training

```
# single gpu
$ mim train diffengine ${CONFIG_FILE}
# multi gpus
$ mim train diffengine ${CONFIG_FILE} --gpus 2 --launcher pytorch

# Example.
$ mim train diffengine configs/stable_diffusion_xl_controlnet/stable_diffusion_xl_controlnet_fill50k.py
```

## Inference with diffusers

Once you have trained a model, specify the path to where the model is saved, and use it for inference with the `diffusers`.

```py
import torch
from diffusers import StableDiffusionXLControlNetPipeline, ControlNetModel, AutoencoderKL
from diffusers.utils import load_image

checkpoint = 'work_dirs/stable_diffusion_xl_controlnet_fill50k/step25000'
prompt = 'cyan circle with brown floral background'
condition_image = load_image(
    'https://datasets-server.huggingface.co/assets/fusing/fill50k/--/default/train/74/conditioning_image/image.jpg'
).resize((1024, 1024))

controlnet = ControlNetModel.from_pretrained(
        checkpoint, subfolder='controlnet', torch_dtype=torch.float16)

vae = AutoencoderKL.from_pretrained(
    'madebyollin/sdxl-vae-fp16-fix',
    torch_dtype=torch.float16,
)
pipe = StableDiffusionXLControlNetPipeline.from_pretrained(
    'stabilityai/stable-diffusion-xl-base-1.0', controlnet=controlnet, vae=vae, torch_dtype=torch.float16)
pipe.to('cuda')

image = pipe(
    prompt,
    condition_image,
    num_inference_steps=50,
).images[0]
image.save('demo.png')
```

You can see more details on [`docs/source/run_guides/run_controlnet_xl.md`](../../docs/source/run_guides/run_controlnet_xl.md#inference-with-diffusers).

## Results Example

#### stable_diffusion_xl_controlnet_fill50k

![input1](https://datasets-server.huggingface.co/assets/fusing/fill50k/--/default/train/74/conditioning_image/image.jpg)

![example1](https://github.com/okotaku/diffengine/assets/24734142/a331a413-a9e7-4b9a-aa75-72279c4cc77a)

Note that some of the results are not good. We should attempt further tuning.

## Acknowledgement

These experiments are based on [diffusers docs](https://github.com/huggingface/diffusers/blob/main/examples/controlnet/README_sdxl.md). Thank you for the great articles.
