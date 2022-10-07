from typing import Any, Optional, Sequence, Tuple, Union

import numpy as np

import torch

from monai.config import DtypeLike, NdarrayOrTensor
from monai.data import MetaTensor

from monai.transforms import InvertibleTransform, RandomizableTransform

from monai.transforms.atmostonce.apply import apply
from monai.transforms.atmostonce.functional import resize, rotate, zoom, spacing, croppad, translate, rotate90, flip
from monai.transforms.atmostonce.lazy_transform import LazyTransform
from monai.transforms.atmostonce.utils import value_to_tuple_range

from monai.utils import (GridSampleMode, GridSamplePadMode,
                         InterpolateMode, NumpyPadMode, PytorchPadMode)
from monai.utils.mapping_stack import MetaMatrix
from monai.utils.misc import ensure_tuple


# TODO: these transforms are intended to replace array transforms once development is done

# spatial
# =======

# TODO: why doesn't Spacing have antialiasing options?
class Spacing(LazyTransform, InvertibleTransform):

    def __init__(
            self,
            pixdim: Union[Sequence[float], float, np.ndarray],
            src_pixdim: Optional[Union[Sequence[float], float, np.ndarray]],
            diagonal: Optional[bool] = False,
            mode: Optional[Union[GridSampleMode, str]] = GridSampleMode.BILINEAR,
            padding_mode: Optional[Union[GridSamplePadMode, str]] = GridSamplePadMode.BORDER,
            align_corners: Optional[bool] = False,
            dtype: Optional[DtypeLike] = np.float64,
            lazy_evaluation: Optional[bool] = False,
            shape_override: Optional[Sequence] = None
    ):
        LazyTransform.__init__(self, lazy_evaluation)
        self.pixdim = pixdim
        self.src_pixdim = src_pixdim
        self.diagonal = diagonal
        self.mode = mode
        self.padding_mode = padding_mode
        self.align_corners = align_corners
        self.dtype = dtype

    def __call__(
        self,
        img: NdarrayOrTensor,
        mode: Optional[Union[GridSampleMode, str]] = None,
        padding_mode: Optional[Union[GridSamplePadMode, str]] = None,
        align_corners: Optional[bool] = None,
        dtype: DtypeLike = None,
        shape_override: Optional[Sequence] = None
    ):

        mode_ = mode or self.mode
        padding_mode_ = padding_mode or self.padding_mode
        align_corners_ = align_corners or self.align_corners
        dtype_ = dtype or self.dtype

        shape_override_ = shape_override
        if shape_override_ is None and isinstance(img, MetaTensor) and img.has_pending_transforms():
            shape_override_ = img.peek_pending_transform().metadata.get("shape_override", None)

        img_t, transform, metadata = spacing(img, self.pixdim, self.src_pixdim, self.diagonal,
                                             mode_, padding_mode_, align_corners_, dtype_,
                                             shape_override_)

        # TODO: candidate for refactoring into a LazyTransform method
        img_t.push_pending_transform(MetaMatrix(transform, metadata))
        if not self.lazy_evaluation:
            img_t = apply(img_t)

        return img_t

    def inverse(self, data):
        raise NotImplementedError()


class Flip(LazyTransform, InvertibleTransform):

    def __init__(
            self,
            spatial_axis: Optional[Union[Sequence[int], int]] = None,
            lazy_evaluation: Optional[bool] = True
    ) -> None:
        LazyTransform.__init__(self, lazy_evaluation)
        self.spatial_axis = spatial_axis

    def __call__(
            self,
            img: NdarrayOrTensor,
            spatial_axis: Optional[Union[Sequence[int], int]] = None,
            shape_override: Optional[Sequence] = None
    ):
        spatial_axis_ = self.spatial_axis = spatial_axis
        shape_override_ = shape_override
        if (shape_override_ is None and
           isinstance(img, MetaTensor) and img.has_pending_transforms()):
            shape_override_ = img.peek_pending_transform().metadata.get("shape_override", None)

        img_t, transform, metadata = flip(img, spatial_axis_, shape_override_)

        # TODO: candidate for refactoring into a LazyTransform method
        img_t.push_pending_transform(MetaMatrix(transform, metadata))
        if not self.lazy_evaluation:
            img_t = apply(img_t)

        return img_t


class Resize(LazyTransform, InvertibleTransform):

    def __init__(
            self,
            spatial_size: Union[Sequence[int], int],
            size_mode: Optional[str] = "all",
            mode: Union[InterpolateMode, str] = InterpolateMode.AREA,
            align_corners: Optional[bool] = False,
            anti_aliasing: Optional[bool] = False,
            anti_aliasing_sigma: Optional[Union[Sequence[float], float, None]] = None,
            dtype: Optional[Union[DtypeLike, torch.dtype]] = np.float32,
            lazy_evaluation: Optional[bool] = False
    ):
        LazyTransform.__init__(self, lazy_evaluation)
        self.spatial_size = spatial_size
        self.size_mode = size_mode
        self.mode = mode,
        self.align_corners = align_corners
        self.anti_aliasing = anti_aliasing
        self.anti_aliasing_sigma = anti_aliasing_sigma
        self.dtype = dtype

    def __call__(
        self,
        img: NdarrayOrTensor,
        mode: Optional[Union[InterpolateMode, str]] = None,
        align_corners: Optional[bool] = None,
        anti_aliasing: Optional[bool] = None,
        anti_aliasing_sigma: Union[Sequence[float], float, None] = None,
        shape_override: Optional[Sequence] = None
    ) -> NdarrayOrTensor:
        mode_ = mode or self.mode
        align_corners_ = align_corners or self.align_corners
        anti_aliasing_ = anti_aliasing or self.anti_aliasing
        anti_aliasing_sigma_ = anti_aliasing_sigma or self.anti_aliasing_sigma

        shape_override_ = shape_override
        if shape_override_ is None and isinstance(img, MetaTensor) and img.has_pending_transforms():
            shape_override_ = img.peek_pending_transform().metadata.get("shape_override", None)

        img_t, transform, metadata = resize(img, self.spatial_size, self.size_mode, mode_,
                                            align_corners_, anti_aliasing_, anti_aliasing_sigma_,
                                            self.dtype, shape_override_)

        # TODO: candidate for refactoring into a LazyTransform method
        img_t.push_pending_transform(MetaMatrix(transform, metadata))
        if not self.lazy_evaluation:
            img_t = apply(img_t)

        return img_t


class Rotate(LazyTransform, InvertibleTransform):

    def __init__(
            self,
            angle: Union[Sequence[float], float],
            keep_size: bool = True,
            mode: Union[GridSampleMode, str] = GridSampleMode.BILINEAR,
            padding_mode: Union[GridSamplePadMode, str] = GridSamplePadMode.BORDER,
            align_corners: bool = False,
            dtype: Union[DtypeLike, torch.dtype] = np.float32,
            lazy_evaluation: Optional[bool] = False
    ):
        LazyTransform.__init__(self, lazy_evaluation)
        self.angle = angle
        self.keep_size = keep_size
        self.mode = mode
        self.padding_mode = padding_mode
        self.align_corners = align_corners
        self.dtype = dtype

    def __call__(
        self,
        img: NdarrayOrTensor,
        angle: Optional[Union[Sequence[float], float]] = None,
        mode: Optional[Union[InterpolateMode, str]] = None,
        padding_mode: Optional[Union[NumpyPadMode, PytorchPadMode, str]] = None,
        align_corners: Optional[bool] = None,
        shape_override: Optional[Sequence] = None
    ) -> NdarrayOrTensor:
        angle = self.angle
        mode = mode or self.mode
        padding_mode = padding_mode or self.padding_mode
        align_corners = align_corners or self.align_corners
        keep_size = self.keep_size
        dtype = self.dtype

        shape_override_ = shape_override
        if shape_override_ is None and isinstance(img, MetaTensor) and img.has_pending_transforms():
            shape_override_ = img.peek_pending_transform().metadata.get("shape_override", None)

        img_t, transform, metadata = rotate(img, angle, keep_size, mode, padding_mode,
                                            align_corners, dtype, shape_override_)

        # TODO: candidate for refactoring into a LazyTransform method
        img_t.push_pending_transform(MetaMatrix(transform, metadata))
        if not self.lazy_evaluation:
            img_t = apply(img_t)

        return img_t

    def inverse(self, data):
        raise NotImplementedError()


class Zoom(LazyTransform, InvertibleTransform):
    """
    Zoom into / out of the image applying the `zoom` factor as a scalar, or if `zoom` is a tuple of
    values, apply each zoom factor to the appropriate dimension.
    """

    def __init__(
            self,
            factor: Union[Sequence[float], float],
            mode: Union[InterpolateMode, str] = InterpolateMode.BILINEAR,
            padding_mode: Union[NumpyPadMode, PytorchPadMode, str] = NumpyPadMode.EDGE,
            align_corners: Optional[bool] = None,
            keep_size: Optional[bool] = True,
            dtype: Union[DtypeLike, torch.dtype] = np.float32,
            lazy_evaluation: Optional[bool] = True,
            **kwargs
    ):
        LazyTransform.__init__(self, lazy_evaluation)
        self.factor = factor
        self.mode: InterpolateMode = InterpolateMode(mode)
        self.padding_mode = padding_mode
        self.align_corners = align_corners
        self.keep_size = keep_size
        self.dtype = dtype
        self.kwargs = kwargs
        print("mode =", self.mode)

    def __call__(
        self,
        img: NdarrayOrTensor,
        factor: Optional[Union[Sequence[float], float]] = None,
        mode: Optional[Union[InterpolateMode, str]] = None,
        padding_mode: Optional[Union[NumpyPadMode, PytorchPadMode, str]] = None,
        align_corners: Optional[bool] = None,
        shape_override: Optional[Sequence] = None
    ) -> NdarrayOrTensor:

        factor = self.factor if factor is None else factor
        mode = self.mode if mode is None else mode
        padding_mode = self.padding_mode if padding_mode is None else padding_mode
        align_corners = self.align_corners if align_corners is None else align_corners
        keep_size = self.keep_size
        dtype = self.dtype

        shape_override_ = shape_override
        if shape_override_ is None and isinstance(img, MetaTensor) and img.has_pending_transforms():
            shape_override_ = img.peek_pending_transform().metadata.get("shape_override", None)
        print("mode =", mode)
        img_t, transform, metadata = zoom(img, factor, mode, padding_mode, align_corners,
                                          keep_size, dtype, shape_override_)

        # TODO: candidate for refactoring into a LazyTransform method
        img_t.push_pending_transform(MetaMatrix(transform, metadata))
        if not self.lazy_evaluation:
            img_t = apply(img_t)

        return img_t

    def inverse(self, data):
        raise NotImplementedError()


class Rotate90(InvertibleTransform, LazyTransform):

    def __init__(
            self,
            k: Optional[int] = 1,
            spatial_axes: Optional[Tuple[int, int]] = (0, 1),
            lazy_evaluation: Optional[bool] = True,
    ) -> None:
        LazyTransform.__init__(self, lazy_evaluation)
        self.k = k
        self.spatial_axes = spatial_axes

    def __call__(
            self,
            img: torch.Tensor,
            k: Optional[int] = None,
            spatial_axes: Optional[Tuple[int, int]] = None,
            shape_override: Optional[Sequence[int]] = None
    ) -> torch.Tensor:
        k_ = k or self.k
        spatial_axes_ = spatial_axes or self.spatial_axes

        shape_override_ = shape_override
        if (shape_override_ is None and
            isinstance(img, MetaTensor) and img.has_pending_transforms()):
            shape_override_ = img.peek_pending_transform().metadata.get("shape_override", None)

        img_t, transform, metadata = rotate90(img, k_, spatial_axes_, shape_override_)

        # TODO: candidate for refactoring into a LazyTransform method
        img_t.push_pending_transform(MetaMatrix(transform, metadata))
        if not self.lazy_evaluation:
            img_t = apply(img_t)

        return img_t


class RandRotate90(RandomizableTransform, InvertibleTransform, LazyTransform):

    def __init__(
            self,
            prob: float = 0.1,
            max_k: int = 3,
            spatial_axes: Tuple[int, int] = (0, 1),
            lazy_evaluation: Optional[bool] = True
    ) -> None:
        RandomizableTransform.__init__(self, prob)
        self.max_k = max_k
        self.spatial_axes = spatial_axes

        self.k = 0

        self.op = Rotate90(0, spatial_axes, lazy_evaluation)

    def randomize(self, data: Optional[Any] = None) -> None:
        super().randomize(None)
        if not self._do_transform:
            return None
        self.k = self.R.randint(self.max_k) + 1

    def __call__(
            self,
            img: torch.Tensor,
            randomize: bool = True,
            shape_override: Optional[Sequence] = None
    ) -> torch.Tensor:

        if randomize:
            self.randomize()

        k = self.k if self._do_transform else 0

        return self.op(img, k, shape_override=shape_override)

    def inverse(
            self,
            data: NdarrayOrTensor,
    ):
        raise NotImplementedError()


class RandRotate(RandomizableTransform, InvertibleTransform, LazyTransform):

    def __init__(
            self,
            range_x: Optional[Union[Tuple[float, float], float]] = 0.0,
            range_y: Optional[Union[Tuple[float, float], float]] = 0.0,
            range_z: Optional[Union[Tuple[float, float], float]] = 0.0,
            prob: Optional[float] = 0.1,
            keep_size: Optional[bool] = True,
            mode: Optional[Union[GridSampleMode, str]] = GridSampleMode.BILINEAR,
            padding_mode: Optional[Union[GridSamplePadMode, str]] = GridSamplePadMode.BORDER,
            align_corners: Optional[bool] = False,
            dtype: Optional[Union[DtypeLike, torch.dtype]] = np.float32,
            lazy_evaluation: Optional[bool] = True
    ):
        RandomizableTransform.__init__(self, prob)
        self.range_x = value_to_tuple_range(range_x)
        self.range_y = value_to_tuple_range(range_y)
        self.range_z = value_to_tuple_range(range_z)

        self.x, self.y, self.z = 0.0, 0.0, 0.0

        self.op = Rotate(0, keep_size, mode, padding_mode, align_corners, dtype, lazy_evaluation)

    def randomize(self, data: Optional[Any] = None) -> None:
        super().randomize(None)

        self.x, self.y, self.z = 0.0, 0.0, 0.0

        if self._do_transform:
            self.x = self.R.uniform(low=self.range_x[0], high=self.range_x[1])
            self.y = self.R.uniform(low=self.range_y[0], high=self.range_y[1])
            self.z = self.R.uniform(low=self.range_z[0], high=self.range_z[1])

    def __call__(
            self,
            img: NdarrayOrTensor,
            mode: Optional[Union[InterpolateMode, str]] = None,
            padding_mode: Optional[Union[NumpyPadMode, PytorchPadMode, str]] = None,
            align_corners: Optional[bool] = None,
            dtype: Optional[Union[DtypeLike, torch.dtype]] = None,
            randomize: Optional[bool] = True,
            shape_override: Optional[Sequence] = None
    ) -> NdarrayOrTensor:

        if randomize:
            self.randomize()

        img_dims = len(img.shape) - 1
        if self._do_transform:
            angle = self.x if img_dims == 2 else (self.x, self.y, self.z)
        else:
            angle = 0 if img_dims == 2 else (0, 0, 0)

        return self.op(img, angle, mode, padding_mode, align_corners, shape_override)

    def inverse(
            self,
            data: NdarrayOrTensor,
    ):
        raise NotImplementedError()


class RandFlip(RandomizableTransform, InvertibleTransform, LazyTransform):

    def __init__(
            self,
            prob: float = 0.1,
            spatial_axis: Optional[Union[Sequence[int], int]] = None
    ) -> None:
        RandomizableTransform.__init__(self, prob)
        self.spatial_axis = spatial_axis

        self.op = Flip(0, spatial_axis)


# class RandRotateOld(RandomizableTransform, InvertibleTransform, LazyTransform):
#
#     def __init__(
#             self,
#             range_x: Optional[Union[Tuple[float, float], float]] = 0.0,
#             range_y: Optional[Union[Tuple[float, float], float]] = 0.0,
#             range_z: Optional[Union[Tuple[float, float], float]] = 0.0,
#             prob: Optional[float] = 0.1,
#             keep_size: bool = True,
#             mode: Union[GridSampleMode, str] = GridSampleMode.BILINEAR,
#             padding_mode: Union[GridSamplePadMode, str] = GridSamplePadMode.BORDER,
#             align_corners: bool = False,
#             dtype: Union[DtypeLike, torch.dtype] = np.float32
#     ):
#         RandomizableTransform.__init__(self, prob)
#         self.range_x = ensure_tuple(range_x)
#         if len(self.range_x) == 1:
#             self.range_x = tuple(sorted([-self.range_x[0], self.range_x[0]]))
#         self.range_y = ensure_tuple(range_y)
#         if len(self.range_y) == 1:
#             self.range_y = tuple(sorted([-self.range_y[0], self.range_y[0]]))
#         self.range_z = ensure_tuple(range_z)
#         if len(self.range_z) == 1:
#             self.range_z = tuple(sorted([-self.range_z[0], self.range_z[0]]))
#
#         self.keep_size = keep_size
#         self.mode = mode
#         self.padding_mode = padding_mode
#         self.align_corners = align_corners
#         self.dtype = dtype
#
#         self.x = 0.0
#         self.y = 0.0
#         self.z = 0.0
#
#     def randomize(self, data: Optional[Any] = None) -> None:
#         super().randomize(None)
#         if not self._do_transform:
#             return None
#         self.x = self.R.uniform(low=self.range_x[0], high=self.range_x[1])
#         self.y = self.R.uniform(low=self.range_y[0], high=self.range_y[1])
#         self.z = self.R.uniform(low=self.range_z[0], high=self.range_z[1])
#
#     def __call__(
#             self,
#             img: NdarrayOrTensor,
#             mode: Optional[Union[InterpolateMode, str]] = None,
#             padding_mode: Optional[Union[NumpyPadMode, PytorchPadMode, str]] = None,
#             align_corners: Optional[bool] = None,
#             dtype: Optional[Union[DtypeLike, torch.dtype]] = None,
#             randomize: Optional[bool] = True,
#             get_matrix: Optional[bool] = False,
#             shape_override: Optional[Sequence] = None
#     ) -> NdarrayOrTensor:
#
#         if randomize:
#             self.randomize()
#
#         img_dims = len(img.shape) - 1
#         if self._do_transform:
#             angle = self.x if img_dims == 2 else (self.x, self.y, self.z)
#         else:
#             angle = 0 if img_dims == 2 else (0, 0, 0)
#
#         mode = self.mode or mode
#         padding_mode = self.padding_mode or padding_mode
#         align_corners = self.align_corners or align_corners
#         keep_size = self.keep_size
#         dtype = self.dtype
#
#         shape_override_ = shape_override
#         if shape_override_ is None and isinstance(img, MetaTensor) and img.has_pending_transforms():
#             shape_override_ = img.peek_pending_transform().metadata.get("shape_override", None)
#
#         img_t, transform, metadata = rotate(img, angle, keep_size, mode, padding_mode,
#                                             align_corners, dtype, shape_override_)
#
#         # TODO: candidate for refactoring into a LazyTransform method
#         img_t.push_pending_transform(MetaMatrix(transform, metadata))
#         if not self.lazy_evaluation:
#             img_t = apply(img_t)
#
#         return img_t
#
#     def inverse(
#             self,
#             data: NdarrayOrTensor,
#     ):
#         raise NotImplementedError()


class Translate(LazyTransform, InvertibleTransform):
    def __init__(
            self,
            translation: Union[Sequence[float], float],
            mode: Union[InterpolateMode, str] = InterpolateMode.AREA,
            padding_mode: Union[NumpyPadMode, PytorchPadMode, str] = NumpyPadMode.EDGE,
            dtype: Union[DtypeLike, torch.dtype] = np.float32,
            lazy_evaluation: Optional[bool] = True,
            **kwargs
    ):
        LazyTransform.__init__(self, lazy_evaluation)
        self.translation = translation
        self.mode: InterpolateMode = InterpolateMode(mode)
        self.padding_mode = padding_mode
        self.dtype = dtype
        self.kwargs = kwargs

    def __call__(
            self,
            img: NdarrayOrTensor,
            mode: Optional[Union[InterpolateMode, str]] = None,
            padding_mode: Optional[Union[NumpyPadMode, PytorchPadMode, str]] = None,
            shape_override: Optional[Sequence] = None
    ) -> NdarrayOrTensor:
        mode = self.mode or mode
        padding_mode = self.padding_mode or padding_mode
        dtype = self.dtype

        shape_override_ = shape_override
        if shape_override_ is None and isinstance(img, MetaTensor) and img.has_pending_transforms():
            shape_override_ = img.peek_pending_transform().metadata.get("shape_override", None)

        img_t, transform, metadata = translate(img, self.translation,
                                               mode, padding_mode, dtype, shape_override_)

        # TODO: candidate for refactoring into a LazyTransform method
        img_t.push_pending_transform(MetaMatrix(transform, metadata))
        if not self.lazy_evaluation:
            img_t = apply(img_t)

        return img_t

    def inverse(self, data):
        raise NotImplementedError()


# croppad
# =======

class CropPad(LazyTransform, InvertibleTransform):

    def __init__(
            self,
            slices: Optional[Sequence[slice]] = None,
            padding_mode: Optional[Union[GridSamplePadMode, str]] = GridSamplePadMode.BORDER,
            lazy_evaluation: Optional[bool] = True,
    ):
        LazyTransform.__init__(self, lazy_evaluation)
        self.slices = slices
        self.padding_mode = padding_mode

    def __call__(
            self,
            img: NdarrayOrTensor,
            slices: Optional[Sequence[slice]] = None,
            shape_override: Optional[Sequence] = None
    ):
        slices_ = slices if self.slices is None else self.slices

        shape_override_ = shape_override
        if shape_override_ is None and isinstance(img, MetaTensor) and img.has_pending_transforms():
            shape_override_ = img.peek_pending_transform().metadata.get("shape_override", None)

        img_t, transform, metadata = croppad(img, slices_, self.padding_mode, shape_override_)

        # TODO: candidate for refactoring into a LazyTransform method
        img_t.push_pending_transform(MetaMatrix(transform, metadata))
        if not self.lazy_evaluation:
            img_t = apply(img_t)

        return img_t

    def inverse(
            self,
            data: NdarrayOrTensor
    ):
        raise NotImplementedError()
