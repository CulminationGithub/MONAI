from typing import Callable, Sequence

from abc import ABC

import torch


class CacheMechanism(ABC):
    """
    The interface for caching mechanisms to be used with CachedTransform. This interface provides
    the ability to check whether cached objects are present, test and fetch simultaneously, and
    store items. It makes no other assumptions about the caching mechanism, capacity, cache eviction
    strategies or any other aspect of cache implementation
    """

    def try_fetch(
            self,
            key
    ):
        raise NotImplementedError()

    def store(
            self,
            key,
            value
    ):
        raise NotImplementedError()


class CachedTransform:
    """
    CachedTransform provides the functionality to cache the output of one or more transforms such
    that they only need to be run once. Each time that CachedTransform is run, it checks whether
    a cached entity is present, and if that entity is present, it loads it and returns the
    resulting tensor / tensors as output. If that entity is not present in the cache, it executes
    the transforms in its internal pipeline and caches the result before returning it.
    """

    def __init__(
            self,
            transforms: Callable,
            cache: CacheMechanism
    ):
        """
        Args:
        transforms: A sequence of callable objects
        cache: A caching mechanism that implements the `CacheMechanism` interface
        """
        self.transforms = transforms
        self.cache = cache

    def __call__(
            self,
            key,
            *args,
            **kwargs
    ):
        is_present, value = self.cache.try_fetch(key)

        if is_present:
            return value

        result = self.transforms(*args, **kwargs)
        self.cache.store(key, result)

        return result


class MultiSampleTransform:
    """
    Multi-sample takes the output of a transform that generates multiple samples and executes
    each sample separately in a depth first fashion, gathering the results into an array that
    is finally returned after all samples are processed
    """
    def __init__(
            self,
            multi_sample: Callable,
            transforms: Callable,
    ):
        self.multi_sample = multi_sample
        self.transforms = transforms

    def __call__(
            self,
            t,
            *args,
            **kwargs
    ):
        output = list()
        for mt in self.multi_sample(t):
            mt_out = self.multi_sample(mt)
            if isinstance(mt_out, torch.Tensor):
                output.append(mt_out)
            elif isinstance(mt_out, list):
                output += mt_out
            else:
                raise ValueError(f"self.transform must return a Tensor or list of Tensors, but returned {mt_out}")

        return output
