_base_ = [
    '../../configs/_base_/models/stable_diffusion_xl_lora.py',
    '_base_/face_expression_xl_dataset.py',
    '../../configs/_base_/schedules/stable_diffusion_50e.py',
    '../../configs/_base_/default_runtime.py'
]

train_dataloader = dict(batch_size=2)

optim_wrapper = dict(optimizer=dict(lr=1e-4), accumulative_counts=2)

model = dict(model='gsdf/CounterfeitXL', lora_config=dict(rank=32))

train_cfg = dict(by_epoch=True, max_epochs=50)
