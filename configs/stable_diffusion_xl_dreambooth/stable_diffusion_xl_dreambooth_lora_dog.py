_base_ = [
    '../_base_/models/stable_diffusion_xl_lora.py',
    '../_base_/datasets/dog_dreambooth_xl.py',
    '../_base_/schedules/stable_diffusion_500.py',
    '../_base_/default_runtime.py'
]

train_dataloader = dict(
    dataset=dict(class_image_config=dict(model={{_base_.model.model}}, )), )
