optim_wrapper = dict(
    type='AmpOptimWrapper',
    dtype='float16',
    optimizer=dict(type='AdamW', lr=1e-4, weight_decay=1e-2),
    clip_grad=dict(max_norm=1.0))

# train, val, test setting
train_cfg = dict(by_epoch=True, max_epochs=1)
val_cfg = None
test_cfg = None

default_hooks = dict(
    checkpoint=dict(
        type='CheckpointHook',
        interval=1,
        max_keep_ckpts=3,
    ), )
