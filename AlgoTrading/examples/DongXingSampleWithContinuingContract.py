# -*- coding: utf-8 -*-
u"""
Created on 2016-4-25

@author: cheng.li
"""

import datetime as dt
import numpy as np
from AlgoTrading.api import Strategy
from AlgoTrading.api import strategyRunner
from AlgoTrading.api import DataSource
from AlgoTrading.api import PortfolioType
from PyFin.Analysis.SeriesValues import SeriesValues
from PyFin.api import CLOSE
from PyFin.api import OPEN
from PyFin.api import LOW
from PyFin.api import HIGH
from PyFin.api import LAST


def sign(x):
    if x > 0:
        return 1
    else:
        return -1


class MovingAverageCrossStrategy(Strategy):
    def __init__(self):

        self.closes = CLOSE()
        self.mul = LAST('multiplier')
        self.preMul = LAST('multiplier').shift(1)
        self.preCloses = CLOSE().shift(1)
        self.openes = OPEN()
        self.lowes = LOW()
        self.highes = HIGH()

        # 计算指数的备用指标
        self.closeDLastClose = self.closes / self.preCloses - 1.
        self.closeDOpen = self.closes / self.openes - 1.
        self.closeDLow = self.closes / self.lowes - 1.
        self.highDClose = 1. - self.highes / self.closes

        self.ih_amount = 28
        self.if_amount = 42
        self.ic_amount = 12

        # 定义指数的权重
        names = ['000016.zicn', '000300.zicn', '000905.zicn']
        self.indexWeights = SeriesValues(np.array([1., -2., 1.]),
                                         index=dict(zip(names, range(len(names)))))

    def handle_data(self):

        if '000016.zicn' not in self.closeDLastClose.value or np.isnan(self.closeDLastClose['000016.zicn']):
            return

        if self.current_datetime.hour == 9 and self.current_datetime.minute < 30:
            return

        ihc, ifc, icc = 'ih.ccfx', 'if.ccfx', 'ic.ccfx'

        # 计算指数指标得分
        closeDLastCloseScore = self.closeDLastClose.value_by_names(['000016.zicn', '000300.zicn', '000905.zicn']).dot(
            self.indexWeights)
        closeDOpenScore = self.closeDOpen.value_by_names(['000016.zicn', '000300.zicn', '000905.zicn']).dot(
            self.indexWeights)
        closeDLowScore = self.closeDLow.value_by_names(['000016.zicn', '000300.zicn', '000905.zicn']).dot(
            self.indexWeights)
        highDCloseScore = self.highDClose.value_by_names(['000016.zicn', '000300.zicn', '000905.zicn']).dot(
            self.indexWeights)

        # 定义基差
        ihBasis = self.closes[ihc] / self.closes['000016.zicn'] / self.mul[ihc] - 1.
        ihPreBasis = self.preCloses[ihc] / self.preCloses['000016.zicn'] / self.preMul[ihc] - 1.

        ifBasis = self.closes[ifc] / self.closes['000300.zicn'] / self.mul[ifc] - 1.
        ifPreBasis = self.preCloses[ifc] / self.preCloses['000300.zicn'] / self.preMul[ifc] - 1.

        icBasis = self.closes[icc] / self.closes['000905.zicn'] / self.mul[icc] - 1.
        icPreBasis = self.preCloses[icc] / self.preCloses['000905.zicn'] / self.preMul[icc] - 1.

        # 计算基差得分
        ihBasisDiff = ihPreBasis - ihBasis
        ifBasisDiff = ifPreBasis - ifBasis
        icBasisDiff = icPreBasis - icBasis

        basis = ihBasis - 2. * ifBasis + icBasis
        basisScore = ihBasisDiff - 2. * ifBasisDiff + icBasisDiff

        # 5个信号合并产生开平仓信号
        elects = 0
        for signal in [closeDLastCloseScore, closeDOpenScore, closeDLowScore, highDCloseScore, basisScore]:
            if basis < 0. < signal:
                elects += 1
            elif signal < 0. < basis:
                elects -= 1

        # 开平仓逻辑

        if elects > 0:
            # 多头信号
            self.order_to(ihc, 1, self.ih_amount)
            self.order_to(ifc, -1, self.if_amount)
            self.order_to(icc, 1, self.ic_amount)
        elif elects < 0:
            # 空头信号
            self.order_to(ihc, -1, self.ih_amount)
            self.order_to(ifc, 1, self.if_amount)
            self.order_to(icc, -1, self.ic_amount)
        else:
            # 平仓信号
            self.order_to(ihc, 1, 0)
            self.order_to(ifc, 1, 0)
            self.order_to(icc, 1, 0)

        # 记录必要的信息，供回测后查看

        # 指数价格信息
        self.keep("000016.zicn_open", self.openes['000016.zicn'])
        self.keep("000016.zicn_high", self.highes['000016.zicn'])
        self.keep("000016.zicn_low", self.lowes['000016.zicn'])
        self.keep("000016.zicn_close", self.closes['000016.zicn'])
        self.keep("000016.zicn_pre_close", self.preCloses['000016.zicn'])

        self.keep("000300.zicn_open", self.openes['000300.zicn'])
        self.keep("000300.zicn_high", self.highes['000300.zicn'])
        self.keep("000300.zicn_low", self.lowes['000300.zicn'])
        self.keep("000300.zicn_close", self.closes['000300.zicn'])
        self.keep("000300.zicn_pre_close", self.preCloses['000300.zicn'])

        self.keep("000905.zicn_open", self.openes['000905.zicn'])
        self.keep("000905.zicn_high", self.highes['000905.zicn'])
        self.keep("000905.zicn_low", self.lowes['000905.zicn'])
        self.keep("000905.zicn_close", self.closes['000905.zicn'])
        self.keep("000905.zicn_pre_close", self.preCloses['000905.zicn'])

        # 期货价格信息
        self.keep("IH_ID", ihc)
        self.keep("IH_CLOSER", self.closes[ihc])
        self.keep("IF_ID", ifc)
        self.keep("IF_CLOSER", self.closes[ifc])
        self.keep("IC_ID", icc)
        self.keep("IC_CLOSER", self.closes[icc])

        self.keep("IH_PRE_CLOSER", self.preCloses[ihc])
        self.keep("IF_PRE_CLOSER", self.preCloses[ifc])
        self.keep("IC_PRE_CLOSER", self.preCloses[icc])

        self.keep("IH_MUL", self.mul[ihc])
        self.keep("IF_MUL", self.mul[ifc])
        self.keep("IC_MUL", self.mul[icc])

        self.keep("IH_PRE_MUL", self.preMul[ihc])
        self.keep("IF_PRE_MUL", self.preMul[ifc])
        self.keep("IC_PRE_MUL", self.preMul[icc])

        # 因子信息
        self.keep("C/LC-1", closeDLastCloseScore)
        self.keep("C/O-1", closeDOpenScore)
        self.keep("C/L-1", closeDLowScore)
        self.keep("1-H/C", highDCloseScore)

        # 基差信息
        self.keep("BASIS_Score", basisScore)

        # 开平仓方向信号
        self.keep("POSITION_SIGNAL", elects)
        self.keep("Released_PnL", self.realizedHoldings['pnl'])
        self.keep("PnL", self.holdings['pnl'])


def run_example():
    indexes = ['000016.zicn', '000300.zicn', '000905.zicn']

    # futures to trade
    ihs = ['ih.ccfx']
    ifs = ['if.ccfx']
    ics = ['ic.ccfx']

    futures = ihs + ifs + ics

    universe = indexes + futures
    startDate = dt.datetime(2015, 5, 1)
    endDate = dt.datetime(2017, 2, 13)

    strategyRunner(userStrategy=MovingAverageCrossStrategy,
                   initialCapital=100000,
                   symbolList=universe,
                   startDate=startDate,
                   endDate=endDate,
                   dataSource=DataSource.DXDataCenter,
                   portfolioType=PortfolioType.CashManageable,
                   freq=0,
                   saveFile=True,
                   plot=True,
                   benchmark='000905.zicn',
                   logLevel='info')


if __name__ == "__main__":
    startTime = dt.datetime.now()
    print("Start: %s" % startTime)
    run_example()
    endTime = dt.datetime.now()
    print("End : %s" % endTime)
    print("Elapsed: %s" % (endTime - startTime))
