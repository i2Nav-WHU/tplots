# -*- coding: utf-8 -*-

"""
@File     :   tplots.py
@Software :   tplots
@Time     :   2020-04-30
@Author   :   hailiang
@Contact  :   thl@whu.edu.cn
@Version  :   v1.0: 2020-05-01
              v1.1: 2020-05-03 add support for configuration file
"""

import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from ruamel.yaml import YAML

from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QFileDialog, QComboBox
from PyQt5.QtGui import QIntValidator, QFont
from PyQt5.QtCore import Qt

import tplots_gui

# 加载预配置的参数文件
import matplotlib
from pathlib import Path

rcfile = Path(os.path.dirname(os.path.realpath(__file__))) / 'res' / 'matplotlibrc'
matplotlib.rc_file(str(rcfile))


class Tplots(QMainWindow):

    def __init__(self, **kwds):
        super().__init__(**kwds)

        # 配置列表
        self.figsize = ([8, 6], [10, 7.5], [12, 9])
        self.linestyle = ('-', '--', '-.', ':')
        self.markerstyle = ('o', '^', 's', 'p', '*', 'x', '+', 'd')
        self.delimiter = ('\\s+', ' *, *', ' *; *')
        self.filetype = (None, np.double, np.float32, np.int)
        self.legendloc = ('best', 'upper right', 'upper left', 'lower right', 'lower left')

        # 数据
        self.plot_data = None
        self.plot_file = None
        self.data_columns = None
        self.figure_items = {}
        self.plot_items = {}
        self.isneedreload = False

        # 配置
        self.figure_options = dict()
        self.plot_options = [dict(), dict(), dict()]
        self.file_options = dict()
        self.yaml = YAML()

        self.gui = tplots_gui.Ui_MainWindow()
        self.gui.setupUi(self)

        # 配置GUI控件
        self.set_gui()

        # 设置信号槽函数
        self.set_signal()

    def show_plots(self):
        if self.plot_data is None or self.isneedreload:
            if not self.load_data():
                self.show_log(u'绘图失败')
                return False

        # 获取GUI配置
        self.get_options()

        # 检查数据有效区间
        for k in range(3):
            if (self.plot_options[k]['line'] or self.plot_options[k]['marker']) \
                    and self.plot_options[k]['yindex'] >= self.data_columns:
                self.show_log(u'数据超出范围, 请检查数据列号')
                return False

        # 横轴数据检查
        isxaxiscnt = self.figure_options['xaxiscnt']
        istxoffset = False
        txoffset = 0
        if isxaxiscnt:
            tx = np.arange(len(self.plot_data))
        else:
            col = self.figure_options['xaxiscol']
            tx = self.plot_data[:, col]

            istxoffset = tx[0] > 99999
            txoffset = int(tx[0] / 1000) * 1000

        # 关闭重复窗口
        plt.close(self.figure_options['figure'])

        # 建立窗口
        plt.figure(self.figure_options['figure'], figsize=self.figure_options['figsize'])

        # 先绘制marker
        legend = []
        for k in range(3):
            if self.plot_options[k]['marker']:
                if self.plot_options[0]['ismarkercolor']:
                    # 自定义颜色
                    plt.plot(
                        tx,
                        self.plot_data[:, self.plot_options[k]['yindex']],
                        marker=self.plot_options[k]['markerstyle'],
                        markersize=self.plot_options[k]['markersize'],
                        linestyle='',
                        color=self.plot_options[k]['markercolor']
                    )
                else:
                    plt.plot(
                        tx,
                        self.plot_data[:, self.plot_options[k]['yindex']],
                        marker=self.plot_options[k]['markerstyle'],
                        markersize=self.plot_options[k]['markersize'],
                        linestyle='')
                if self.figure_options['legend']:
                    legend.append(self.plot_options[k]['legend'])

        # 绘制曲线
        for k in range(3):
            if self.plot_options[k]['line']:
                if self.plot_options[0]['islinecolor']:
                    # 自定义颜色
                    plt.plot(
                        tx,
                        self.plot_data[:, self.plot_options[k]['yindex']],
                        linestyle=self.plot_options[k]['linestyle'],
                        linewidth=self.plot_options[k]['linewidth'],
                        color=self.plot_options[k]['linecolor'])
                else:
                    plt.plot(
                        tx,
                        self.plot_data[:, self.plot_options[k]['yindex']],
                        linestyle=self.plot_options[k]['linestyle'],
                        linewidth=self.plot_options[k]['linewidth'])
                if self.figure_options['legendall']:
                    legend.append(self.plot_options[k]['legend'])

        # 横轴数据数值较大, 使用偏移
        if istxoffset:
            plt.ticklabel_format(axis='x', style='plain', useOffset=txoffset)

        # 添加文本
        for k in range(3):
            if self.plot_options[k]['text']:
                plt.text(self.plot_options[k]['textcoordx'],
                         self.plot_options[k]['textcoordy'],
                         self.plot_options[k]['textstr'],
                         fontsize=self.plot_options[k]['textsize'],
                         color=self.plot_options[k]['textcolor'])

        # 窗口属性
        plt.title(self.figure_options['title'], fontsize=self.figure_options['fontsize'])
        plt.xlabel(self.figure_options['xlabel'], fontsize=self.figure_options['fontsize'])
        plt.ylabel(self.figure_options['ylabel'], fontsize=self.figure_options['fontsize'])

        # 图例
        if self.figure_options['legend']:
            plt.legend(legend, loc=self.figure_options['legendloc'])
        # 栅格
        if self.figure_options['grid']:
            plt.grid()

        plt.tight_layout()

        # 显示绘图
        plt.show()

        self.show_log(u'显示绘图  ' + self.figure_options['figure'])

        return True

    def close_plots(self):
        plt.close('all')
        self.show_log(u'关闭绘图')

    def load_data(self):
        if self.plot_file is None:
            self.show_log(u'请先导入有效数据文件')
            return False

        file_type = self.filetype[self.gui.cbfileformat.currentIndex()]
        delimiter = self.delimiter[self.gui.cbdelimiter.currentIndex()]

        try:
            # 数据列数量
            columns = int(self.gui.editdatacols.text())

            # 加载数据
            if file_type is None:
                skipfooter = 0
                if self.figure_items['passheader'].checkState(1) == Qt.Checked:
                    skipfooter = int(self.figure_items['passheader'].text(1))
                df = pd.read_csv(self.plot_file,
                                 delimiter=delimiter,
                                 engine='python',
                                 header=None,
                                 skiprows=list(range(skipfooter)))
                self.plot_data = np.array(df)
            else:
                self.plot_data = np.fromfile(self.plot_file, dtype=file_type).reshape(-1, columns)

            # 显示数据加载情况
            msg = u'数据加载成功  [%d, %d]' % (self.plot_data.shape[0], self.plot_data.shape[1])
            self.gui.editdatacols.setText(str(self.plot_data.shape[1]))
            self.data_columns = self.plot_data.shape[1]
            self.show_log(msg)

            # 更新文本默认坐标
            isxaxiscnt = self.figure_items['xaxiscnt'].checkState(1) == Qt.Checked
            col = int(self.figure_items['xaxiscol'].text(1))
            for k in range(1, 4):
                if isxaxiscnt:
                    self.plot_items['textcoordx'].setText(k, '0')
                else:
                    self.plot_items['textcoordx'].setText(k, str(self.plot_data[0, col]))

            self.isneedreload = False
            return True
        except ValueError:
            self.show_log(u'数据加载失败, 请检查文件内容')
        except TypeError:
            self.show_log(u'数据加载失败, 请检查文件格式配置')
            return False

    def import_file(self):
        filename, suffix = QFileDialog.getOpenFileName()
        self.gui.editdatafile.setText(filename)

    def update_file_state(self):
        self.plot_file = self.gui.editdatafile.text()
        if os.path.isfile(self.plot_file) and os.path.exists(self.plot_file):
            self.show_log(u'导入新数据')

            self.gui.treeplot.setEnabled(True)
            self.gui.treefigure.setEnabled(True)
        else:
            self.plot_file = None
            self.show_log(u'数据文件无效')

        self.plot_data = None

    def clear_log(self):
        self.gui.listlog.clear()

    def show_log(self, msg):
        stamp = datetime.now().strftime('%H:%M:%S : ')
        item = stamp + msg
        self.gui.listlog.addItem(item)

    def about_tplots(self):
        QMessageBox.about(self,
                          'About tplots',
                          '<p style="font-weight:bold; font-size:20pt;">'
                          'A novel GUI plot tool'
                          '</p>'
                          '<body style="font-size:12pt;">'
                          '<p style="font-weight:bold">Version: 1.1</p>'
                          '<p>'
                          '<div style="font-weight:bold">Development:</div>'
                          '<div>'
                          'hailiang, thl@whu.edu.cn<br/>'
                          'linfeng, linfeng_bao@outlook.com</div>'
                          '</p>'
                          '<p>'
                          '<div style="font-weight:bold">Test:</div>'
                          '<div >ruonan, grn213331@163.com</div>'
                          '</p>'
                          '</body>')

    def about_qt(self):
        QMessageBox.aboutQt(self, '关于Qt')

    def closeEvent(self, event):
        if self.plot_file is None:
            event.accept()
            return

        msgbox = QMessageBox()
        msgbox.setWindowTitle('Confirm Save')
        msgbox.setText('The document has been modified.')
        msgbox.setInformativeText('Do you want to save your changes?')
        msgbox.setStandardButtons(QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        msgbox.setDefaultButton(QMessageBox.Save)

        ret = msgbox.exec()
        if ret == QMessageBox.Save:
            self.save_config()
            event.accept()

            self.close_plots()
        elif ret == QMessageBox.Discard:
            event.accept()

            self.close_plots()
        elif ret == QMessageBox.Cancel:
            event.ignore()

    def figure_option_changed(self, item, column):
        if item == self.figure_items['xaxiscnt'] or item == self.figure_items['xaxiscol']:
            isusecnt = self.figure_items['xaxiscnt'].checkState(1)
            config = self.gui.treefigure.topLevelItem(2)
            if isusecnt == Qt.Checked:
                config.setText(1, u'计数索引')
            else:
                col = int(self.figure_items['xaxiscol'].text(1))
                label = u'指定数据列  [%d]' % col
                config.setText(1, label)
        elif item == self.figure_items['legendall']:
            state = Qt.Unchecked if self.figure_items['legendall'].checkState(1) == Qt.Checked else Qt.Checked
            self.figure_items['legendmarker'].setCheckState(1, state)
        elif item == self.figure_items['legendmarker']:
            state = Qt.Unchecked if self.figure_items['legendmarker'].checkState(1) == Qt.Checked else Qt.Checked
            self.figure_items['legendall'].setCheckState(1, state)
        elif item == self.figure_items['passheader']:
            self.isneedreload = True

    def plot_option_changed(self, item, column):

        if item == self.plot_items['textcoordx'] or item == self.plot_items['textcoordy']:
            # 文本坐标
            x = float(self.plot_items['textcoordx'].text(column))
            y = float(self.plot_items['textcoordy'].text(column))
            text = '[%g, %g]' % (x, y)
            self.plot_items['textcoord'].setText(column, text)

    def set_signal(self):
        self.gui.acexit.triggered.connect(self.close)
        self.gui.acopen.triggered.connect(self.load_config)
        self.gui.acsave.triggered.connect(self.save_config)

        self.gui.acabout.triggered.connect(self.about_tplots)
        self.gui.acaboutqt.triggered.connect(self.about_qt)

        self.gui.pbclearlog.clicked.connect(self.clear_log)
        self.gui.pbimport.clicked.connect(self.import_file)
        self.gui.pbloaddata.clicked.connect(self.load_data)
        self.gui.pbcloseplots.clicked.connect(self.close_plots)
        self.gui.pbshowplots.clicked.connect(self.show_plots)

        self.gui.editdatafile.textChanged.connect(self.update_file_state)

        self.gui.treefigure.itemChanged.connect(self.figure_option_changed)
        self.gui.treeplot.itemChanged.connect(self.plot_option_changed)

    def set_gui(self):
        # 缓存所有的tree指针
        self.figure_items['figure'] = self.gui.treefigure.topLevelItem(0)
        self.figure_items['figsize'] = self.gui.treefigure.topLevelItem(1)
        self.figure_items['xaxis'] = self.gui.treefigure.topLevelItem(2)
        self.figure_items['xaxiscol'] = self.gui.treefigure.topLevelItem(2).child(0)
        self.figure_items['xaxiscnt'] = self.gui.treefigure.topLevelItem(2).child(1)
        self.figure_items['title'] = self.gui.treefigure.topLevelItem(3)
        self.figure_items['xlabel'] = self.gui.treefigure.topLevelItem(4)
        self.figure_items['ylabel'] = self.gui.treefigure.topLevelItem(5)
        self.figure_items['fontsize'] = self.gui.treefigure.topLevelItem(6)
        self.figure_items['grid'] = self.gui.treefigure.topLevelItem(7)
        self.figure_items['legend'] = self.gui.treefigure.topLevelItem(8)
        self.figure_items['legendall'] = self.gui.treefigure.topLevelItem(8).child(0)
        self.figure_items['legendmarker'] = self.gui.treefigure.topLevelItem(8).child(1)
        self.figure_items['legendloc'] = self.gui.treefigure.topLevelItem(8).child(2)
        self.figure_items['passheader'] = self.gui.treefigure.topLevelItem(9)

        self.plot_items['yindex'] = self.gui.treeplot.topLevelItem(0)
        self.plot_items['legend'] = self.gui.treeplot.topLevelItem(1)
        self.plot_items['line'] = self.gui.treeplot.topLevelItem(2)
        self.plot_items['linestyle'] = self.gui.treeplot.topLevelItem(2).child(0)
        self.plot_items['linewidth'] = self.gui.treeplot.topLevelItem(2).child(1)
        self.plot_items['islinecolor'] = self.gui.treeplot.topLevelItem(2).child(2)
        self.plot_items['linecolor'] = self.gui.treeplot.topLevelItem(2).child(2).child(0)
        self.plot_items['marker'] = self.gui.treeplot.topLevelItem(3)
        self.plot_items['markerstyle'] = self.gui.treeplot.topLevelItem(3).child(0)
        self.plot_items['markersize'] = self.gui.treeplot.topLevelItem(3).child(1)
        self.plot_items['ismarkercolor'] = self.gui.treeplot.topLevelItem(3).child(2)
        self.plot_items['markercolor'] = self.gui.treeplot.topLevelItem(3).child(2).child(0)
        self.plot_items['text'] = self.gui.treeplot.topLevelItem(4)
        self.plot_items['textstr'] = self.gui.treeplot.topLevelItem(4).child(0)
        self.plot_items['textcoord'] = self.gui.treeplot.topLevelItem(4).child(1)
        self.plot_items['textcoordx'] = self.gui.treeplot.topLevelItem(4).child(1).child(0)
        self.plot_items['textcoordy'] = self.gui.treeplot.topLevelItem(4).child(1).child(1)
        self.plot_items['textsize'] = self.gui.treeplot.topLevelItem(4).child(2)
        self.plot_items['textcolor'] = self.gui.treeplot.topLevelItem(4).child(3)

        # figure size
        combo = QComboBox()
        combo.addItem('[8, 6]')
        combo.addItem('[10, 7.5]')
        combo.addItem('[12, 9]')
        combo.setCurrentIndex(1)
        self.gui.treefigure.setItemWidget(self.figure_items['figsize'], 1, combo)

        # legend location
        combo = QComboBox()
        combo.addItem('自动')
        combo.addItem('右上')
        combo.addItem('左上')
        combo.addItem('右下')
        combo.addItem('左下')
        self.gui.treefigure.setItemWidget(self.figure_items['legendloc'], 1, combo)

        # line style
        combo = QComboBox()
        combo.addItem(u'-  实线')
        combo.addItem(u'-- 虚线')
        combo.addItem(u'-. 点划线')
        combo.addItem(u':  点线')
        self.gui.treeplot.setItemWidget(self.plot_items['linestyle'], 1, combo)

        combo = QComboBox()
        combo.addItem(u'-  实线')
        combo.addItem(u'-- 虚线')
        combo.addItem(u'-. 点划线')
        combo.addItem(u':  点线')
        self.gui.treeplot.setItemWidget(self.plot_items['linestyle'], 2, combo)

        combo = QComboBox()
        combo.addItem(u'-  实线')
        combo.addItem(u'-- 虚线')
        combo.addItem(u'-. 点划线')
        combo.addItem(u':  点线')
        self.gui.treeplot.setItemWidget(self.plot_items['linestyle'], 3, combo)

        # marker style
        combo = QComboBox()
        combo.addItem(u'o 圆圈')
        combo.addItem(u'^ 三角形')
        combo.addItem(u's 方形')
        combo.addItem(u'p 五边形')
        combo.addItem(u'* 星形')
        combo.addItem(u'x 叉形')
        combo.addItem(u'+ 十字形')
        combo.addItem(u'd 菱形')
        self.gui.treeplot.setItemWidget(self.plot_items['markerstyle'], 1, combo)

        combo = QComboBox()
        combo.addItem(u'o 圆圈')
        combo.addItem(u'^ 三角形')
        combo.addItem(u's 方形')
        combo.addItem(u'p 五边形')
        combo.addItem(u'* 星形')
        combo.addItem(u'x 叉形')
        combo.addItem(u'+ 十字形')
        combo.addItem(u'd 菱形')
        self.gui.treeplot.setItemWidget(self.plot_items['markerstyle'], 2, combo)

        combo = QComboBox()
        combo.addItem(u'o 圆圈')
        combo.addItem(u'^ 三角形')
        combo.addItem(u's 方形')
        combo.addItem(u'p 五边形')
        combo.addItem(u'* 星形')
        combo.addItem(u'x 叉形')
        combo.addItem(u'+ 十字形')
        combo.addItem(u'd 菱形')
        self.gui.treeplot.setItemWidget(self.plot_items['markerstyle'], 3, combo)

        # 限制输入格式
        validator = QIntValidator(0, 9999)
        self.gui.editdatacols.setValidator(validator)

        # 禁用
        self.gui.treefigure.setEnabled(False)
        self.gui.treeplot.setEnabled(False)

        # 设置宽度
        self.gui.treefigure.setColumnWidth(0, 200)
        self.gui.treeplot.setColumnWidth(0, 150)
        self.gui.treeplot.setColumnWidth(1, 120)
        self.gui.treeplot.setColumnWidth(2, 120)

        # 窗口字体大小
        font = QFont()
        font.setPointSize(11)
        self.setFont(font)

        # 窗口标题
        self.setWindowTitle('tplots')

        # 初始位置
        self.move(0, 0)

    def get_options(self):
        # 文件属性
        self.file_options['filename'] = self.gui.editdatafile.text()
        self.file_options['filetype'] = self.gui.cbfileformat.currentIndex()
        self.file_options['delimiter'] = self.gui.cbdelimiter.currentIndex()
        self.file_options['columns'] = int(self.gui.editdatacols.text())

        # 窗口属性
        self.figure_options['figure'] = self.figure_items['figure'].text(1)
        self.figure_options['figsize'] = self.figsize[
            self.gui.treefigure.itemWidget(self.figure_items['figsize'], 1).currentIndex()]

        self.figure_options['xaxiscol'] = int(self.figure_items['xaxiscol'].text(1))
        self.figure_options['xaxiscnt'] = self.figure_items['xaxiscnt'].checkState(1) == Qt.Checked
        self.figure_options['title'] = self.figure_items['title'].text(1)
        self.figure_options['xlabel'] = self.figure_items['xlabel'].text(1)
        self.figure_options['ylabel'] = self.figure_items['ylabel'].text(1)
        self.figure_options['fontsize'] = int(self.figure_items['fontsize'].text(1))
        self.figure_options['grid'] = self.figure_items['grid'].checkState(1) == Qt.Checked
        self.figure_options['legend'] = self.figure_items['legend'].checkState(1) == Qt.Checked
        self.figure_options['legendall'] = self.figure_items['legendall'].checkState(1) == Qt.Checked
        self.figure_options['legendmarker'] = self.figure_items['legendmarker'].checkState(1) == Qt.Checked
        self.figure_options['legendloc'] = self.legendloc[
            self.gui.treefigure.itemWidget(self.figure_items['legendloc'], 1).currentIndex()]

        # 绘图属性
        self.plot_options[0]['islinecolor'] = self.plot_items['islinecolor'].checkState(1) == Qt.Checked
        self.plot_options[0]['ismarkercolor'] = self.plot_items['ismarkercolor'].checkState(1) == Qt.Checked
        for k in range(3):
            axis = k + 1
            self.plot_options[k]['yindex'] = int(self.plot_items['yindex'].text(axis))
            self.plot_options[k]['legend'] = self.plot_items['legend'].text(axis)
            self.plot_options[k]['line'] = self.plot_items['line'].checkState(axis) == Qt.Checked
            self.plot_options[k]['linestyle'] = self.linestyle[
                self.gui.treeplot.itemWidget(self.plot_items['linestyle'], 1).currentIndex()]
            self.plot_options[k]['linewidth'] = float(self.plot_items['linewidth'].text(axis))
            self.plot_options[k]['linecolor'] = self.plot_items['linecolor'].text(axis)
            self.plot_options[k]['marker'] = self.plot_items['marker'].checkState(axis) == Qt.Checked
            self.plot_options[k]['markerstyle'] = self.markerstyle[
                self.gui.treeplot.itemWidget(self.plot_items['markerstyle'], axis).currentIndex()]
            self.plot_options[k]['markersize'] = float(self.plot_items['markersize'].text(axis))
            self.plot_options[k]['markercolor'] = self.plot_items['markercolor'].text(axis)
            self.plot_options[k]['text'] = self.plot_items['text'].checkState(axis) == Qt.Checked
            self.plot_options[k]['textstr'] = self.plot_items['textstr'].text(axis)
            self.plot_options[k]['textcolor'] = self.plot_items['textcolor'].text(axis)
            self.plot_options[k]['textsize'] = self.plot_items['textsize'].text(axis)
            self.plot_options[k]['textcoordx'] = float(self.plot_items['textcoordx'].text(axis))
            self.plot_options[k]['textcoordy'] = float(self.plot_items['textcoordy'].text(axis))

        return True

    def update_gui(self):
        # 刷新GUI

        # 文件属性
        self.gui.editdatafile.setText(self.file_options['filename'])
        self.gui.cbfileformat.setCurrentIndex(self.file_options['filetype'])
        self.gui.cbdelimiter.setCurrentIndex(self.file_options['delimiter'])
        self.gui.editdatacols.setText(str(self.file_options['columns']))

        # 窗口
        self.figure_items['figure'].setText(1, self.figure_options['figure'])
        index = self.figsize.index(self.figure_options['figsize'])
        self.gui.treefigure.itemWidget(self.figure_items['figsize'], 1).setCurrentIndex(index)
        self.figure_items['xaxiscnt'].setCheckState(1, Qt.Checked if self.figure_options['xaxiscnt'] else Qt.Unchecked)
        self.figure_items['xaxiscol'].setText(1, str(self.figure_options['xaxiscol']))

        self.figure_items['title'].setText(1, self.figure_options['title'])
        self.figure_items['xlabel'].setText(1, self.figure_options['xlabel'])
        self.figure_items['ylabel'].setText(1, self.figure_options['ylabel'])
        self.figure_items['fontsize'].setText(1, str(self.figure_options['fontsize']))

        self.figure_items['grid'].setCheckState(1, Qt.Checked if self.figure_options['grid'] else Qt.Unchecked)
        self.figure_items['legend'].setCheckState(1, Qt.Checked if self.figure_options['legend'] else Qt.Unchecked)
        self.figure_items['legendall'].setCheckState(1,
                                                     Qt.Checked if self.figure_options['legendall'] else Qt.Unchecked)
        self.figure_items['legendmarker'].setCheckState(1, Qt.Checked if self.figure_options[
            'legendmarker'] else Qt.Unchecked)
        self.figure_items['legendloc'].setText(1, self.figure_options['legendloc'])

        # 绘图
        self.plot_items['islinecolor'].setCheckState(1, Qt.Checked if self.plot_options[0][
            'islinecolor'] else Qt.Unchecked)
        for k in range(3):
            self.plot_items['yindex'].setText(k + 1, str(self.plot_options[k]['yindex']))
            self.plot_items['legend'].setText(k + 1, self.plot_options[k]['legend'])
            self.plot_items['line'].setCheckState(k + 1, Qt.Checked if self.plot_options[k]['line'] else Qt.Unchecked)
            self.plot_items['linestyle'].setText(k + 1, self.plot_options[k]['linestyle'])
            self.plot_items['linewidth'].setText(k + 1, str(self.plot_options[k]['linewidth']))
            self.plot_items['linecolor'].setText(k + 1, self.plot_options[k]['linecolor'])
            self.plot_items['marker'].setCheckState(k + 1,
                                                    Qt.Checked if self.plot_options[k]['marker'] else Qt.Unchecked)
            self.plot_items['markerstyle'].setText(k + 1, self.plot_options[k]['markerstyle'])
            self.plot_items['markersize'].setText(k + 1, str(self.plot_options[k]['markersize']))
            self.plot_items['markercolor'].setText(k + 1, self.plot_options[k]['markercolor'])
            self.plot_items['textstr'].setText(k + 1, self.plot_options[k]['textstr'])
            self.plot_items['textsize'].setText(k + 1, self.plot_options[k]['textsize'])
            self.plot_items['textsize'].setText(k + 1, self.plot_options[k]['textsize'])
            self.plot_items['textcoordy'].setText(k + 1, str(self.plot_options[k]['textcoordy']))

        return True

    def save_config(self):
        if self.plot_file is None:
            self.show_log(u'配置未更改')
            return False

        # 获取配置
        self.get_options()
        config_dict = {"figure_options": self.figure_options,
                       "plot_options": self.plot_options,
                       "file_options": self.file_options}

        if self.plot_file is not None:
            directory = str(Path(self.plot_file).parent / 'tplots.yaml')
        else:
            directory = 'tplots.yaml'
        filename, suffix = QFileDialog.getSaveFileName(directory=directory, filter='YAML (*.yaml)')
        if filename != '':
            with open(filename, 'w') as fp:
                self.yaml.dump(config_dict, fp)
                self.show_log(u"配置保存成功")

    def load_config(self):
        directory = os.path.dirname(self.plot_file) if self.plot_file is not None else ''
        filename, suffix = QFileDialog.getOpenFileName(directory=directory, filter='*.yaml')

        if filename != '':
            try:
                with open(filename, 'r') as fp:
                    config = self.yaml.load(fp)

                self.plot_options = config['plot_options']
                self.figure_options = config['figure_options']
                self.file_options = config['file_options']

                self.update_gui()

                self.show_log(u"配置加载成功")
            except Exception:
                self.show_log(u"配置文件格式错误")
                return False


if __name__ == '__main__':
    app = QApplication(sys.argv)

    tplots = Tplots()
    tplots.show()

    sys.exit(app.exec())
