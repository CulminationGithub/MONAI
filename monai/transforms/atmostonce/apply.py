from typing import Optional, Sequence, Union

import itertools as it

import numpy as np

import torch

from monai.config import DtypeLike
from monai.data import MetaTensor
from monai.transforms import Affine
from monai.transforms.inverse import InvertibleTransform
from monai.transforms.transform import MapTransform
from monai.utils import GridSampleMode, GridSamplePadMode
from monai.utils.misc import get_backend_from_data, get_device_from_data
from monai.utils.mapping_stack import MatrixFactory

# TODO: This should move to a common place to be shared with dictionary
GridSampleModeSequence = Union[Sequence[Union[GridSampleMode, str]], GridSampleMode, str]
GridSamplePadModeSequence = Union[Sequence[Union[GridSamplePadMode, str]], GridSamplePadMode, str]
DtypeSequence = Union[Sequence[DtypeLike], DtypeLike]


# TODO: move to mapping_stack.py
def extents_from_shape(shape):
    extents = [[0, shape[i]] for i in range(1, len(shape))]

    extents = it.product(*extents)
    return list(np.asarray(e + (1,)) for e in extents)


# TODO: move to mapping_stack.py
def shape_from_extents(
        src_shape: Sequence,
        extents: Union[Sequence[np.ndarray], Sequence[torch.Tensor], np.ndarray, torch.Tensor]
):
    if isinstance(extents, (list, tuple)):
        if isinstance(extents[0], np.ndarray):
            aextents = np.asarray(extents)
            aextents = torch.from_numpy(aextents)
        else:
            aextents = torch.stack(extents)
    else:
        if isinstance(extents, np.ndarray):
            aextents = torch.from_numpy(extents)
        else:
            aextents = extents

    mins = aextents.min(axis=0)[0]
    maxes = aextents.max(axis=0)[0]
    values = torch.ceil(maxes - mins).type(torch.IntTensor)[:-1]
    return torch.cat((torch.as_tensor([src_shape[0]]), values))

    # return [src_shape[0]] + np.ceil(maxes - mins)[:-1].astype(int).tolist()


def metadata_is_compatible(value_1, value_2):
    if value_1 is None:
        return True
    else:
        if value_2 is None:
            return True
        return value_1 == value_2


def starting_matrix_and_extents(matrix_factory, data):
    # set up the identity matrix and metadata
    cumulative_matrix = matrix_factory.identity()
    cumulative_extents = extents_from_shape(data.shape)

    # pre-translate origin to centre of image
    translate_to_centre = matrix_factory.translate([d / 2 for d in data.shape[1:]])
    cumulative_matrix = translate_to_centre @ cumulative_matrix
    cumulative_extents = [e @ translate_to_centre.matrix.matrix for e in cumulative_extents]
    return cumulative_matrix, cumulative_extents


def prepare_args_dict_for_apply(cur_mode, cur_padding_mode, cur_device, cur_dtype):
    kwargs = {}
    if cur_mode is not None:
        kwargs['mode'] = cur_mode
    if cur_padding_mode is not None:
        kwargs['padding_mode'] = cur_padding_mode
    if cur_device is not None:
        kwargs['device'] = cur_device
    if cur_dtype is not None:
        kwargs['dtype'] = cur_dtype

    return kwargs


def apply(data: Union[torch.Tensor, MetaTensor],
          pending: Optional[dict] = None):
    pending_ = pending
    pending_ = data.pending_transforms

    if len(pending) == 0:
        return data

    dim_count = len(data.shape) - 1
    matrix_factory = MatrixFactory(dim_count,
                                   get_backend_from_data(data),
                                   get_device_from_data(data))

    # # set up the identity matrix and metadata
    # cumulative_matrix = matrix_factory.identity()
    # cumulative_extents = extents_from_shape(data.shape)
    #
    # # pre-translate origin to centre of image
    # translate_to_centre = matrix_factory.translate([d / 2 for d in data.shape[1:]])
    # cumulative_matrix = translate_to_centre @ cumulative_matrix
    # cumulative_extents = [e @ translate_to_centre.matrix.matrix for e in cumulative_extents]
    cumulative_matrix, cumulative_extents = starting_matrix_and_extents(matrix_factory, data)

    # set the various resampling parameters to an initial state
    cur_mode = None
    cur_padding_mode = None
    cur_device = None
    cur_dtype = None

    for meta_matrix in pending_:
        next_matrix = meta_matrix.matrix
        cumulative_matrix = next_matrix @ cumulative_matrix
        # cumulative_extents = [e @ translate_to_centre.matrix.matrix for e in cumulative_extents]
        cumulative_extents = [e @ cumulative_matrix.matrix.matrix for e in cumulative_extents]

        new_mode = meta_matrix.metadata.get('mode', None)
        new_padding_mode = meta_matrix.metadata.get('padding_mode', None)
        new_device = meta_matrix.metadata.get('device', None)
        new_dtype = meta_matrix.metadata.get('dtype', None)

        mode_compat = metadata_is_compatible(cur_mode, new_mode)
        padding_mode_compat = metadata_is_compatible(cur_padding_mode, new_padding_mode)
        device_compat = metadata_is_compatible(cur_device, new_device)
        dtype_compat = metadata_is_compatible(cur_dtype, new_dtype)

        if (mode_compat is False or padding_mode_compat is False or
            device_compat is False or dtype_compat is False):
            print("intermediate apply required")
            # carry out an intermediate resample here due to incompatibility between arguments
            # kwargs = {}
            # if cur_mode is not None:
            #     kwargs['mode'] = cur_mode
            # if cur_padding_mode is not None:
            #     kwargs['padding_mode'] = cur_padding_mode
            # if cur_device is not None:
            #     kwargs['device'] = cur_device
            # if cur_dtype is not None:
            #     kwargs['dtype'] = cur_dtype
            kwargs = prepare_args_dict_for_apply(cur_mode, cur_padding_mode, cur_device, cur_dtype)

            a = Affine(norm_coords=False,
                       affine=cumulative_matrix.matrix.matrix,
                       **kwargs)
            data = a(img=data)

            cur_mode = new_mode
            cur_padding_mode = new_padding_mode
            cur_device = new_device
            cur_dtype = new_dtype

    # TODO: figure out how to propagate extents properly
    # TODO: resampling strategy: augment resample or perform multiple stages if necessary
    # TODO: resampling strategy - antialiasing: can resample just be augmented?

    a = Affine(norm_coords=False,
               affine=cumulative_matrix.matrix.matrix,
               # spatial_size=cur_spatial_size,
               **kwargs)
    data = a(img=data)

    data.clear_pending_transforms()


class Apply(InvertibleTransform):

    def __init__(self):
        super().__init__()


class Applyd(MapTransform, InvertibleTransform):

    def __init__(self):
        super().__init__()

# class Applyd(MapTransform, InvertibleTransform):
#
#     def __init__(self,
#                  keys: KeysCollection,
#                  modes: GridSampleModeSequence,
#                  padding_modes: GridSamplePadModeSequence,
#                  normalized: bool = False,
#                  device: Optional[torch.device] = None,
#                  dtypes: Optional[DtypeSequence] = np.float32):
#         self.keys = keys
#         self.modes = modes
#         self.padding_modes = padding_modes
#         self.device = device
#         self.dtypes = dtypes
#         self.resamplers = dict()
#
#         if isinstance(dtypes, (list, tuple)):
#             if len(keys) != len(dtypes):
#                 raise ValueError("'keys' and 'dtypes' must be the same length if 'dtypes' is a sequence")
#
#             # create a resampler for each output data type
#             unique_resamplers = dict()
#             for d in dtypes:
#                 if d not in unique_resamplers:
#                     unique_resamplers[d] = Resample(norm_coords=not normalized, device=device, dtype=d)
#
#             # assign each named data input the appropriate resampler for that data type
#             for k, d in zip(keys, dtypes):
#                 if k not in self.resamplers:
#                     self.resamplers[k] = unique_resamplers[d]
#
#         else:
#             # share the resampler across all named data inputs
#             resampler = Resample(norm_coords=not normalized, device=device, dtype=dtypes)
#             for k in keys:
#                 self.resamplers[k] = resampler
#
#     def __call__(self,
#                  data: Mapping[Hashable, NdarrayOrTensor],
#                  allow_missing_keys: bool = False) -> Dict[Hashable, NdarrayOrTensor]:
#         d = dict(data)
#         mapping_stack = d["mappings"]
#         keys = d.keys()
#         for key_tuple in self.key_iterator(d,
#                                            expand_scalar_to_tuple(self.modes, len(keys)),
#                                            expand_scalar_to_tuple(self.padding_modes, len(keys)),
#                                            expand_scalar_to_tuple(self.dtypes, len(keys))):
#             key, mode, padding_mode, dtype = key_tuple
#             affine = mapping_stack[key].transform()
#             data = d[key]
#             spatial_size = data.shape[1:]
#             grid = create_grid(spatial_size, device=self.device, backend="torch", dtype=dtype)
#             _device = grid.device
#
#             _b = TransformBackends.TORCH if isinstance(grid, torch.Tensor) else TransformBackends.NUMPY
#
#             grid, *_ = convert_data_type(grid, torch.Tensor, device=_device, dtype=grid.dtype)
#             affine, *_ = convert_to_dst_type(affine, grid)
#             d[key] = self.resamplers[key](data, grid=grid, mode=mode, padding_mode=padding_mode)
#
#         return d
