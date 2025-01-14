model = dict(
    type='StableDiffusionXL',
    model='stabilityai/stable-diffusion-xl-base-1.0',
    vae_model='madebyollin/sdxl-vae-fp16-fix',
    lora_config=dict(rank=8))
