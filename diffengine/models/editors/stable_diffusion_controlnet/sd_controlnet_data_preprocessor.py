from typing import Union

import torch
from mmengine.model.base_model.data_preprocessor import BaseDataPreprocessor

from diffengine.registry import MODELS


@MODELS.register_module()
class SDControlNetDataPreprocessor(BaseDataPreprocessor):

    def forward(self, data: dict, training: bool = False) -> Union[dict, list]:
        """Preprocesses the data into the model input format.

        After the data pre-processing of :meth:`cast_data`, ``forward``
        will stack the input tensor list to a batch tensor at the first
        dimension.

        Args:
            data (dict): Data returned by dataloader
            training (bool): Whether to enable training time augmentation.

        Returns:
            dict or list: Data in the same format as the model input.
        """
        assert 'result_class_image' not in data['inputs']
        data['inputs']['img'] = torch.stack(data['inputs']['img'])
        data['inputs']['condition_img'] = torch.stack(
            data['inputs']['condition_img'])
        return super().forward(data)  # type: ignore
