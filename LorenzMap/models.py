# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import numpy as np
import mxnet as mx
from mxnet import gluon

np.random.seed(1234)
ctx = mx.cpu()


class Lorenz(gluon.nn.Block):
    def __init__(self, in_channels=1, L=4, k=2, M=1):
        super(Lorenz, self).__init__()
        self.L = L
        self.dilations = [2 ** i for i in range(L)]

        # initial causal convolution
        self.from_input = gluon.nn.Conv1D(in_channels=in_channels, kernel_size=1, channels=M)

        # dilated, residual, skip
        self.conv = gluon.nn.Sequential()
        self.residual = gluon.nn.Sequential()
        self.skips = gluon.nn.Sequential()

        for d in self.dilations:
            self.conv.add(gluon.nn.Conv1D(in_channels=M, kernel_size=k, channels=M, dilation=d, activation='relu'))
            self.residual.add(gluon.nn.Conv1D(in_channels=M, kernel_size=1, channels=M, dilation=d))
            self.skips.add(gluon.nn.Conv1D(in_channels=M, kernel_size=1, channels=M, dilation=d))

        # final 1x1 output layer
        self.conv_post1 = gluon.nn.Conv1D(in_channels=M, kernel_size=1, channels=1)
        self.conv_post2 = gluon.nn.Flatten()

    def forward(self, x):
        output = self.preprocess(x)
        skip_connections = []

        for s, res, skip in zip(self.conv, self.residual, self.skips):
            output, skips = self.residue_forward(output, s, res, skip)
            skip_connections.append(skips)

        # sum up all layers skips for output layer
        output = sum([s[:,:,-output.shape[2]:] for s in skip_connections])
        output = self.postprocess(output)
        return output

    def preprocess(self, x):
        output = self.from_input(x)
        return output

    def postprocess(self, x):
        output = self.conv_post1(x)
        output = self.conv_post2(output)
        return output

    def residue_forward(self, x, conv, residual, skips):
        output = x
        output = conv(output)
        output = residual(output)
        skips = skips(output)
        # add residual layer with matching shape
        output = output + x[:, :, -output.shape[2]:]
        return output, skips
