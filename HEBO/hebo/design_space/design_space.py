"""Design Space."""

# Copyright (C) 2020. Huawei Technologies Co., Ltd. All rights reserved.

# This program is free software; you can redistribute it and/or modify it under
# the terms of the MIT license.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY

# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the MIT License for more details.

import pandas as pd
import mindspore as ms
import mindspore.numpy as mnp
from mindspore import Tensor

from .numeric_param import NumericPara
from .integer_param import IntegerPara
from .pow_param import PowPara
from .categorical_param import CategoricalPara
from .bool_param import BoolPara
from .pow_integer_param import PowIntegerPara
from .int_exponent_param import IntExponentPara
from .step_int import StepIntPara


class DesignSpace:
    """Design Space."""
    
    def __init__(self):
        self.para_types = {}
        self.register_para_type('num', NumericPara)
        self.register_para_type('pow', PowPara)
        self.register_para_type('pow_int', PowIntegerPara)
        self.register_para_type('int_exponent', IntExponentPara)
        self.register_para_type('int', IntegerPara)
        self.register_para_type('step_int', StepIntPara)
        self.register_para_type('cat', CategoricalPara)
        self.register_para_type('bool', BoolPara)
        self.paras = {}
        self.para_names = []
        self.numeric_names = []
        self.enum_names = []
    
    @property
    def num_paras(self):
        """num_paras of params in design space."""
        return len(self.para_names)
    
    @property
    def num_numeric(self):
        """num_numeric of numeric variables."""
        return len(self.numeric_names)
    
    @property
    def num_categorical(self):
        """num_categorical of categorical."""
        return len(self.enum_names)
    
    def parse(self, rec):
        """Parse input pandas dataframe."""
        self.para_config = rec
        self.paras = {}
        self.para_names = []
        for item in rec:
            assert (item['type'] in self.para_types)
            param = self.para_types[item['type']](item)
            self.paras[param.name] = param
            if param.is_categorical:
                self.enum_names.append(param.name)
            else:
                self.numeric_names.append(param.name)
        self.para_names = self.numeric_names + self.enum_names
        return self
    
    def register_para_type(self, type_name, para_class):
        """User can define their specific parameter type and register the new type.

        using this function.
        """
        self.para_types[type_name] = para_class
    
    def sample(self, num_samples=1):
        """df_suggest: suggested initial points."""
        df = pd.DataFrame(columns=self.para_names)
        for c in df.columns:
            df[c] = self.paras[c].sample(num_samples)
        return df
    
    def transform(self, data: pd.DataFrame) -> (Tensor, Tensor):
        """Transform data to be within [opt_lb, opt_ub].

        input: pandas dataframe
        output: xc and xe
        """
        xc = data[self.numeric_names].values.astype(float).copy()
        xe = data[self.enum_names].values.copy()
        for i, name in enumerate(self.numeric_names):
            xc[:, i] = self.paras[name].transform(xc[:, i])
        for i, name in enumerate(self.enum_names):
            xe[:, i] = self.paras[name].transform(xe[:, i])
        xc = Tensor(
            xc.astype(float), ms.float32) if xc.shape[1] > 0 else mnp.zeros(
            (xc.shape[0], 0))
        xe = Tensor(
            xe.astype(int), ms.int32) if xe.shape[1] > 0 else mnp.zeros(
            (xe.shape[0], 0)).astype(
            ms.int32)
        return xc, xe
    
    def inverse_transform(self, x: Tensor, xe: Tensor) -> pd.DataFrame:
        """Inverse Transform to ub, lb.

        input: x and xe
        output: pandas dataframe
        """
        df_num = pd.DataFrame(columns=self.numeric_names)
        df_cat = pd.DataFrame(columns=self.enum_names)
        for i, name in enumerate(self.numeric_names):
            df_num[name] = self.paras[name].inverse_transform(x.asnumpy()[
                                                              :, i])
        for i, name in enumerate(self.enum_names):
            df_cat[name] = self.paras[name].inverse_transform(
                xe.asnumpy()[:, i])
        df = pd.concat([df_num, df_cat], axis=1)
        df = df[self.para_names]
        return df
    
    @property
    def opt_lb(self):
        """Return optimisation lower bound."""
        lb_numeric = [self.paras[p].opt_lb for p in self.numeric_names]
        lb_enum = [self.paras[p].opt_lb for p in self.enum_names]
        return Tensor(lb_numeric + lb_enum, ms.float32)
    
    @property
    def opt_ub(self):
        """Return optimisation upper bound."""
        ub_numeric = [self.paras[p].opt_ub for p in self.numeric_names]
        ub_enum = [self.paras[p].opt_ub for p in self.enum_names]
        return Tensor(ub_numeric + ub_enum, ms.float32)