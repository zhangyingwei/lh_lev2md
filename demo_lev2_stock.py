#!/usr/bin/python3
# -*- coding: UTF-8 -*-

"""
股票Level2行情数据接收演示程序

功能说明：
1. 连接股票Level2行情服务器（支持TCP和UDP组播两种方式）
2. 登录并订阅各种类型的行情数据
3. 接收并处理实时行情推送数据

支持的行情数据类型：
- 快照行情（3秒频率）
- 指数行情
- 逐笔成交数据（仅深圳）
- 逐笔委托数据（仅深圳）
- 上海XTS新债数据
- 上海NGTS合流逐笔数据

作者：TORA API团队
版本：v4.0.7
"""

# from asyncio.windows_events import NULL #仅适用于Windows
import sys
import lev2mdapi
''' 注意: 如果提示找不到_lev2mdapi 且已发布的库文件不一致时,可自行重命名为_lev2mdapi.so (Windows下为_lev2mdapi.pyd)'''

class MdSpi(lev2mdapi.CTORATstpLev2MdSpi):
    """
    行情数据回调处理类

    继承自CTORATstpLev2MdSpi，实现各种行情数据的回调处理方法
    包括连接状态、登录响应、订阅响应和实时行情数据推送的处理
    """

    def __init__(self, api):
        """
        初始化回调处理对象

        Args:
            api: Level2行情API实例
        """
        lev2mdapi.CTORATstpLev2MdSpi.__init__(self)
        self.__api = api  # 保存API实例的引用

    def OnFrontConnected(self):
        """
        前置连接成功回调

        当与行情服务器建立连接后会触发此回调
        在此方法中进行用户登录操作
        """
        print("OnFrontConnected")

        # 创建登录请求结构体
        login_req = lev2mdapi.CTORATstpReqUserLoginField()
        # 使用组播方式接收行情时，Login请求域可置空，不必填写校验信息
        # 当使用TCP方式接收行情时，则必须填写校验信息：LogInAccount,Password和LogInAccountType
        '''
        LogInAccount为申请的手机号
        Password为该手机号在N视界网站的登陆密码。
        LogInAccountType = TORA_TSTP_LACT_UnifiedUserID
        若填入的手机号尚未登记会提示ErrorID[439]
        '''
        login_req.LogInAccount='13811112222' # n-sight.com.cn网站注册手机号
        login_req.Password='123456' # n-sight.com.cn网站登陆密码
        login_req.LogInAccountType = lev2mdapi.TORA_TSTP_LACT_UnifiedUserID # 统一标识登陆，level2用户校验指定类型

        # 发送登录请求，请求ID为1
        self.__api.ReqUserLogin(login_req, 1)

    def OnRspUserLogin(self, pRspUserLoginField, pRspInfo, nRequestID, bIsLast):
        """
        用户登录响应回调

        Args:
            pRspUserLoginField: 登录响应信息（本例中未使用）
            pRspInfo: 响应信息，包含错误码和错误信息
            nRequestID: 请求ID
            bIsLast: 是否为最后一条响应（本例中未使用）
        """
        if pRspInfo['ErrorID'] == 0:
            print('Login success! [%d]' % nRequestID)

            #########以下为逐笔数据订阅######
            # 定义各种证券代码集合，用于订阅不同类型的行情数据
            Securities = [b'00000000']                               #全部合约(通配符)
            Securities_startwith_sh = [b'6*****']                    #通配符方式
            Securities_stock_sh = [b'600621']                        #上海股票
            # Securities_stock_sh = [b'6*****']                        #上海股票
            Securities_index_sh = [b'000905',b'000852']              #上海指数
            Securities_cbond_sh = [b'110038',b'110043',b'113537']    #上海可转债

            Securities_stock_sz = [b'000001',b'000650',b'300750']    #深圳股票
            Securities_stock_sz = [b'30****']              #深圳股票
            Securities_startwith_sz = [b'000***',b'3*****']          #通配符方式
            Securities_index_sz = [b'399001']                        #深圳指数
            Securities_cbond_sz = [b'123013']                        #深圳可转债
            Securities_sz = [b'300750',b'123013']                    #深圳股票+可转债

            '''
            订阅快照行情
            当sub_arr中只有一个"00000000"的合约且ExchangeID填TORA_TSTP_EXD_SSE或TORA_TSTP_EXD_SZSE时,订阅单市场所有合约行情
			当sub_arr中只有一个"00000000"的合约且ExchangeID填TORA_TSTP_EXD_COMM时,订阅全市场所有合约行情
            支持类似 600*** 通配符,不支持 6*****1 类型通配符。
			其它情况,订阅sub_arr集合中的合约行情
            '''
            if 0: #3s快照订阅，不含上海可转债(XTS新债)
                # 订阅股票快照行情（3秒频率更新）
                ret_md = self.__api.SubscribeMarketData(Securities_stock_sh, lev2mdapi.TORA_TSTP_EXD_SSE) #上海股票
                # ret_md = self.__api.SubscribeMarketData(Securities_startwith_sz, lev2mdapi.TORA_TSTP_EXD_SZSE) #深圳股票通配符查询举例
                # ret_md = self.__api.SubscribeMarketData(Securities_sz, lev2mdapi.TORA_TSTP_EXD_SZSE) #深圳股票+可转债
                # ret_md = self.__api.SubscribeMarketData(Securities, lev2mdapi.TORA_TSTP_EXD_COMM)  #沪深全市场订阅，不含上海可转债
                if ret_md != 0:
                    print('SubscribeMarketData fail, ret[%d]' % ret_md)
                else:
                    print('SubscribeMarketData success, ret[%d]' % ret_md)

            if 0: #指数快照订阅
                # 订阅指数快照行情
                ret_i = self.__api.SubscribeIndex(Securities_index_sh, lev2mdapi.TORA_TSTP_EXD_SSE) #订阅上海指数
                # ret_i = self.__api.SubscribeIndex(Securities_index_sz, lev2mdapi.TORA_TSTP_EXD_SZSE)  #订阅深圳指数
                # ret_i = self.__api.SubscribeIndex(Securities, lev2mdapi.TORA_TSTP_EXD_COMM) #全市场指数订阅
                if (ret_i == 0):
                    print("SubscribeIndex:::Success,ret=%d" % ret_i)
                else:
                    print("SubscribeIndex:::Failed,ret=%d)" % ret_i)

            if 1: #逐笔成交订阅（仅深圳有效，且不含深圳普通债券）
                # 订阅逐笔成交数据（仅深圳市场支持）
                ret_t = self.__api.SubscribeTransaction(Securities_sz, lev2mdapi.TORA_TSTP_EXD_SZSE)  #订阅深圳股票+可转债
                # ret_t = self.__api.SubscribeTransaction(Securities, lev2mdapi.TORA_TSTP_EXD_COMM) #全市场订阅
                if (ret_t == 0):
                    print("SubscribeTransaction:::Success,ret=%d" % ret_t)
                else:
                    print("SubscribeTransaction:::Failed,ret=%d)" % ret_t)

            if 1: #逐笔委托订阅（仅深圳有效，且不含深圳普通债券）
                # 订阅逐笔委托数据（仅深圳市场支持）
                ret_od = self.__api.SubscribeOrderDetail(Securities_stock_sz, lev2mdapi.TORA_TSTP_EXD_SZSE)  #订阅深圳股票+转债
                # ret_od = self.__api.SubscribeOrderDetail(Securities_sz, lev2mdapi.TORA_TSTP_EXD_SZSE)  #订阅深圳股票+转债
                # ret_od = self.__api.SubscribeOrderDetail(Securities, lev2mdapi.TORA_TSTP_EXD_COMM) #全市场指数订阅
                if (ret_od == 0):
                    print("SubscribeOrderDetail:::Success,ret=%d" % ret_od)
                else:
                    print("SubscribeOrderDetail:::Failed,ret=%d)" % ret_od)

            if 0: #上海XTS新债快照订阅
                # 订阅上海XTS新债快照行情
                ret_xts_md = self.__api.SubscribeXTSMarketData(Securities_cbond_sh, lev2mdapi.TORA_TSTP_EXD_SSE) #订阅上海可转债
                if (ret_xts_md == 0):
                    print("SubscribeXTSMarketData:::Success,ret=%d" % ret_xts_md)
                else:
                    print("SubscribeXTSMarketData:::Failed,ret=%d)" % ret_xts_md)

            if 0:  #上海XTS新债逐笔委托和逐笔成交订阅
                # 订阅上海XTS新债逐笔数据（包括委托和成交）
                ret_xts_tick = self.__api.SubscribeXTSTick(Securities_cbond_sh, lev2mdapi.TORA_TSTP_EXD_SSE) #订阅上海可转债(XTS新债)
                if (ret_xts_tick == 0):
                    print("SubscribeXTSTick:::Success,ret=%d" % ret_xts_tick)
                else:
                    print("SubscribeXTSTick:::Failed,ret=%d)" % ret_xts_tick)

            if 1: #上海逐笔合并订阅
                # 订阅上海NGTS合流逐笔数据（合并的委托和成交数据）
                ret_xts_md = self.__api.SubscribeNGTSTick(Securities_stock_sh, lev2mdapi.TORA_TSTP_EXD_SSE) #订阅上海NGTS合流逐笔
                if (ret_xts_md == 0):
                    print("SubscribeNGTSTick:::Success,ret=%d" % ret_xts_md)
                else:
                    print("SubscribeNGTSTick:::Failed,ret=%d)" % ret_xts_md)

        else: #login
            # 登录失败处理
            print('Login fail!!! [%d] [%d] [%s]'
                %(nRequestID, pRspInfo['ErrorID'], pRspInfo['ErrorMsg']))

    ######以下为行情订阅响应########

    def OnRspSubMarketData(self, pSpecificSecurityField, pRspInfo, nRequestID, bIsLast):
        """
        订阅股票快照行情响应回调

        Args:
            pSpecificSecurityField: 特定证券信息（本例中未使用）
            pRspInfo: 响应信息，包含错误码和错误信息
            nRequestID: 请求ID（本例中未使用）
            bIsLast: 是否为最后一条响应（本例中未使用）
        """
        if pRspInfo['ErrorID'] == 0:
            print('OnRspSubMarketData: OK!')
        else:
            print('OnRspSubMarketData: Error! [%d] [%s]'
                %(pRspInfo['ErrorID'], pRspInfo['ErrorMsg']))

    def OnRspUnSubMarketData(self, pSpecificSecurityField, pRspInfo, nRequestID, bIsLast):
        """
        取消订阅股票快照行情响应回调

        Args:
            pSpecificSecurityField: 特定证券信息（本例中未使用）
            pRspInfo: 响应信息，包含错误码和错误信息
            nRequestID: 请求ID（本例中未使用）
            bIsLast: 是否为最后一条响应（本例中未使用）
        """
        if pRspInfo.ErrorID == 0:
            print('OnRspUnSubMarketData: OK!')
        else:
            print('OnRspUnSubMarketData: Error! [%d] [%s]'
                %(pRspInfo['ErrorID'], pRspInfo['ErrorMsg']))

    def OnRspSubIndex(self, pSpecificSecurityField, pRspInfo,nRequestID, bIsLast):
        """
        订阅指数行情响应回调

        Args:
            pSpecificSecurityField: 特定证券信息（本例中未使用）
            pRspInfo: 响应信息，包含错误码和错误信息
            nRequestID: 请求ID（本例中未使用）
            bIsLast: 是否为最后一条响应（本例中未使用）
        """
        if pRspInfo['ErrorID'] == 0:
            print('OnRspSubIndex: OK!')
        else:
            print('OnRspSubIndex: Error! [%d] [%s]'
                %(pRspInfo['ErrorID'], pRspInfo['ErrorMsg']))

    def OnRspSubTransaction(self, pSpecificSecurity, pRspInfo, nRequestID, bIsLast):
        """
        订阅逐笔成交响应回调

        Args:
            pSpecificSecurity: 特定证券信息（本例中未使用）
            pRspInfo: 响应信息，包含错误码和错误信息
            nRequestID: 请求ID（本例中未使用）
            bIsLast: 是否为最后一条响应（本例中未使用）
        """
        if pRspInfo['ErrorID'] == 0:
            print('OnRspSubTransaction: OK!')
        else:
            print('OnRspSubTransaction: Error! [%d] [%s]'
                %(pRspInfo['ErrorID'], pRspInfo['ErrorMsg']))

    def OnRspSubOrderDetail(self, pSpecificSecurity, pRspInfo, nRequestID, bIsLast):
        """
        订阅逐笔委托响应回调

        Args:
            pSpecificSecurity: 特定证券信息（本例中未使用）
            pRspInfo: 响应信息，包含错误码和错误信息
            nRequestID: 请求ID（本例中未使用）
            bIsLast: 是否为最后一条响应（本例中未使用）
        """
        if pRspInfo['ErrorID'] == 0:
            print('OnRspSubOrderDetail: OK!')
        else:
            print('OnRspSubOrderDetail: Error! [%d] [%s]'
                %(pRspInfo['ErrorID'], pRspInfo['ErrorMsg']))

    def OnRspSubXTSMarketData(self, pSpecificSecurity, pRspInfo, nRequestID, bIsLast):
        """
        订阅上海XTS新债快照行情响应回调

        Args:
            pSpecificSecurity: 特定证券信息（本例中未使用）
            pRspInfo: 响应信息，包含错误码和错误信息
            nRequestID: 请求ID（本例中未使用）
            bIsLast: 是否为最后一条响应（本例中未使用）
        """
        if pRspInfo['ErrorID'] == 0:
            print('OnRspSubXTSMarketData: OK!')
        else:
            print('OnRspSubXTSMarketData: Error! [%d] [%s]'
                %(pRspInfo['ErrorID'], pRspInfo['ErrorMsg']))

    def OnRspSubXTSTick(self, pSpecificSecurity, pRspInfo, nRequestID, bIsLast):
        """
        订阅上海XTS新债逐笔数据响应回调

        Args:
            pSpecificSecurity: 特定证券信息（本例中未使用）
            pRspInfo: 响应信息，包含错误码和错误信息
            nRequestID: 请求ID（本例中未使用）
            bIsLast: 是否为最后一条响应（本例中未使用）
        """
        if pRspInfo['ErrorID'] == 0:
            print('OnRspSubXTSTick: OK!')
        else:
            print('OnRspSubXTSTick: Error! [%d] [%s]'
                % (pRspInfo['ErrorID'], pRspInfo['ErrorMsg']))

    def OnRspSubNGTSTick(self, pSpecificSecurity, pRspInfo, nRequestID, bIsLast):
        """
        订阅上海NGTS合流逐笔数据响应回调

        Args:
            pSpecificSecurity: 特定证券信息（本例中未使用）
            pRspInfo: 响应信息，包含错误码和错误信息
            nRequestID: 请求ID（本例中未使用）
            bIsLast: 是否为最后一条响应（本例中未使用）
        """
        if pRspInfo['ErrorID'] == 0:
            print('OnRspSubNGTSTick: OK!')
        else:
            print('OnRspSubNGTSTick: Error! [%d] [%s]'
                % (pRspInfo['ErrorID'], pRspInfo['ErrorMsg']))

    # #####以下为行情推送的回报########

    # 普通快照行情回报
    def OnRtnMarketData(self, pMarketData, FirstLevelBuyNum, FirstLevelBuyOrderVolumes, FirstLevelSellNum, FirstLevelSellOrderVolumes):
        """
        股票快照行情数据推送回调

        接收实时的股票快照行情数据，包含价格、成交量、买卖盘等信息

        Args:
            pMarketData: 行情数据结构体，包含股票的各种价格和成交信息
            FirstLevelBuyNum: 第一档买单数量（本例中未使用）
            FirstLevelBuyOrderVolumes: 第一档买单委托量（本例中未使用）
            FirstLevelSellNum: 第一档卖单数量（本例中未使用）
            FirstLevelSellOrderVolumes: 第一档卖单委托量（本例中未使用）
        """
        print("OnRtnMarketData TimeStamp[%d] SecurityName[%s] ExchangeID[%s] \n\tPreClosePrice[%.4f] LowestPrice[%.4f] HighestPrice[%.4f] OpenPrice[%.4f] LastPrice[%.4f] \n\tBidPrice{[%.4f] [%.4f] [%.4f] [%.4f] [%.4f] [%.4f] [%.4f] [%.4f] [%.4f] [%.4f]} \n\tAskPrice{[%.4f] [%.4f] [%.4f] [%.4f] [%.4f] [%.4f] [%.4f] [%.4f] [%.4f] [%.4f]} \n\tBidVolume{[%ld] [%ld] [%ld] [%ld] [%ld] [%ld] [%ld] [%ld] [%ld] [%ld]} \n\tAskVolume{[%ld] [%ld] [%ld] [%ld] [%ld] [%ld] [%ld] [%ld] [%ld] [%ld]}\n" %
			(pMarketData['DataTimeStamp'],pMarketData['SecurityID'],pMarketData['ExchangeID'],
            pMarketData['PreClosePrice'], pMarketData['LowestPrice'],
			pMarketData['HighestPrice'], pMarketData['OpenPrice'],pMarketData['LastPrice'],
			pMarketData['BidPrice1'], pMarketData['BidPrice2'], pMarketData['BidPrice3'],
			pMarketData['BidPrice4'], pMarketData['BidPrice5'], pMarketData['BidPrice6'],
			pMarketData['BidPrice7'], pMarketData['BidPrice8'], pMarketData['BidPrice9'], pMarketData['BidPrice10'],
			pMarketData['AskPrice1'], pMarketData['AskPrice2'], pMarketData['AskPrice3'],
			pMarketData['AskPrice4'], pMarketData['AskPrice5'], pMarketData['AskPrice6'],
			pMarketData['AskPrice7'], pMarketData['AskPrice8'], pMarketData['AskPrice9'], pMarketData['AskPrice10'],
			pMarketData['BidVolume1'], pMarketData['BidVolume2'], pMarketData['BidVolume3'],
			pMarketData['BidVolume4'], pMarketData['BidVolume5'], pMarketData['BidVolume6'],
			pMarketData['BidVolume7'], pMarketData['BidVolume8'], pMarketData['BidVolume9'], pMarketData['BidVolume10'],
			pMarketData['AskVolume1'], pMarketData['AskVolume2'], pMarketData['AskVolume3'],
			pMarketData['AskVolume4'], pMarketData['AskVolume5'], pMarketData['AskVolume6'],
			pMarketData['AskVolume7'], pMarketData['AskVolume8'], pMarketData['AskVolume9'], pMarketData['AskVolume10']))

    # 指数快照行情通知
    def OnRtnIndex(self, pIndex):
        """
        指数行情数据推送回调

        接收实时的指数行情数据，包含指数点位、涨跌幅等信息

        Args:
            pIndex: 指数数据结构体，包含指数的各种信息
        """
        print("OnRtnIndex DataTimeStamp[%d] SecurityID[%s] ExchangeID[%s] LastIndex[%.4f] PreCloseIndex[%.4f] OpenIndex[%.4f] LowIndex[%.4f] HighIndex[%.4f] CloseIndex[%.4f] Turnover[%.4f] TotalVolumeTraded[%ld]" %
        (pIndex['DataTimeStamp'], # 精确到秒，上海指数5秒一笔，深圳3秒一笔
        pIndex['SecurityID'],
        pIndex['ExchangeID'],
        pIndex['LastIndex'],
        pIndex['PreCloseIndex'],
        pIndex['OpenIndex'],
        pIndex['LowIndex'],
        pIndex['HighIndex'],
        pIndex['CloseIndex'],
        pIndex['Turnover'],
        pIndex['TotalVolumeTraded']))

    # 逐笔成交通知
    def OnRtnTransaction(self, pTransaction):
        """
        逐笔成交数据推送回调（仅深圳市场）

        接收实时的逐笔成交数据，包含每笔成交的详细信息

        Args:
            pTransaction: 逐笔成交数据结构体，包含成交价格、数量、时间等信息
        """
        print("OnRtnTransaction SecurityID[%s] " % pTransaction['SecurityID'],end="")
        print("ExchangeID[%s] " % pTransaction['ExchangeID'],end="")
        # 深圳逐笔成交，TradeTime的格式为【时分秒毫秒】例如例如100221530，表示10:02:21.530;
		# 上海逐笔成交，TradeTime的格式为【时分秒百分之秒】例如10022153，表示10:02:21.53;
        print("TradeTime[%d] " % pTransaction['TradeTime'],end="")
        print("TradePrice[%.4f] " % pTransaction['TradePrice'],end="")
        print("TradeVolume[%ld] " % pTransaction['TradeVolume'],end="")
        print("ExecType[%s] " % pTransaction['ExecType'],end="") # 上海逐笔成交没有这个字段，只有深圳有。值2表示撤单成交，BuyNo和SellNo只有一个是非0值，以该非0序号去查找到的逐笔委托即为被撤单的委托。
        print("MainSeq[%d] " % pTransaction['MainSeq'],end="")
        print("SubSeq[%ld] " % pTransaction['SubSeq'],end="")
        print("BuyNo[%ld] " % pTransaction['BuyNo'],end="")
        print("SellNo[%ld] " % pTransaction['SellNo'],end="")
        print("TradeBSFlag[%s] " % pTransaction['TradeBSFlag'],end="")
        print("Info1[%ld] " % pTransaction['Info1'],end="")
        print("Info2[%ld] " % pTransaction['Info2'],end="")
        print("Info3[%ld] " % pTransaction['Info3'])

    # 逐笔委托通知
    def OnRtnOrderDetail(self, pOrderDetail):
        """
        逐笔委托数据推送回调（仅深圳市场）

        接收实时的逐笔委托数据，包含每笔委托的详细信息

        Args:
            pOrderDetail: 逐笔委托数据结构体，包含委托价格、数量、方向等信息
        """
        print("OnRtnOrderDetail SecurityID[%s] " % pOrderDetail['SecurityID'], end="")
        print("ExchangeID[%s] " % pOrderDetail['ExchangeID'], end="")
        print("OrderTime[%d] " % pOrderDetail['OrderTime'], end="")
        print("Price[%.4f] " % pOrderDetail['Price'], end="")
        print("Volume[%ld] " % pOrderDetail['Volume'], end="")
        print("OrderType[%s] " % pOrderDetail['OrderType'], end="")
        print("MainSeq[%d] " % pOrderDetail['MainSeq'], end="")
        print("SubSeq[%d] " % pOrderDetail['SubSeq'], end="")
        print("Side[%s] " % pOrderDetail['Side'], end="")
        print("Info1[%d] " % pOrderDetail['Info1'], end="")
        print("Info2[%d] " % pOrderDetail['Info2'], end="")
        print("Info3[%d] " % pOrderDetail['Info3'])

    def OnRtnXTSMarketData(self, pMarketData, FirstLevelBuyNum, FirstLevelBuyOrderVolumes, FirstLevelSellNum, FirstLevelSellOrderVolumes):
        """
        上海XTS新债快照行情数据推送回调

        接收上海XTS新债的快照行情数据

        Args:
            pMarketData: XTS新债行情数据结构体
            FirstLevelBuyNum: 第一档买单数量（本例中未使用）
            FirstLevelBuyOrderVolumes: 第一档买单委托量（本例中未使用）
            FirstLevelSellNum: 第一档卖单数量（本例中未使用）
            FirstLevelSellOrderVolumes: 第一档卖单委托量（本例中未使用）
        """
        if(pMarketData):
            print("OnRtnXTSMarketData SecurityID[%s] " % pMarketData['SecurityID'], end="")
            print("ExchangeID[%s] " % pMarketData['ExchangeID'], end="")
            print("DataTimeStamp[%d] " % pMarketData['DataTimeStamp'], end="")
            print("PreClosePrice[%.4f] " % pMarketData['PreClosePrice'], end="")
            print("OpenPrice[%.4f] " % pMarketData['OpenPrice'], end="")
            print("NumTrades[%ld] " % pMarketData['NumTrades'], end="")
            print("TotalVolumeTrade[%ld] " % pMarketData['TotalVolumeTrade'], end="")
            print("HighestPrice[%.4f] " % pMarketData['HighestPrice'], end="")
            print("LowestPrice[%.4f] " % pMarketData['LowestPrice'], end="")
            print("LastPrice[%.4f] " % pMarketData['LastPrice'], end="")
            print("BidPrice1[%.4f] " % pMarketData['BidPrice1'], end="")
            print("BidVolume1[%ld] " % pMarketData['BidVolume1'], end="")
            print("AskPrice1[%.4f] " % pMarketData['AskPrice1'], end="")
            print("AskVolume1[%ld] " % pMarketData['AskVolume1'], end="")
            print("MDSecurityStat[%s] " % pMarketData['MDSecurityStat'])

    def OnRtnNGTSTick(self, pNGTSTick):
        """
        上海NGTS合流逐笔数据推送回调

        接收上海NGTS合流的逐笔数据，包含委托和成交的合并信息

        Args:
            pNGTSTick: NGTS逐笔数据结构体，包含逐笔委托和成交的合并信息
        """
        if(pNGTSTick):
            print("OnRtnNGTSTick SecurityID[%s] " % pNGTSTick['SecurityID'], end="")
            print("ExchangeID[%s] " % pNGTSTick['ExchangeID'], end="")
            print("MainSeq[%d] " % pNGTSTick['MainSeq'], end="")
            print("SubSeq[%ld] " % pNGTSTick['SubSeq'], end="")
            print("TickTime[%d] " % pNGTSTick['TickTime'], end="")
            print("TickType[%s] " % pNGTSTick['TickType'], end="")
            print("BuyNo[%ld] " % pNGTSTick['BuyNo'], end="")
            print("SellNo[%ld] " % pNGTSTick['SellNo'], end="")
            print("Price[%.4f] " % pNGTSTick['Price'], end="")
            print("Volume[%ld] " % pNGTSTick['Volume'], end="")
            print("TradeMoney[%.4f] " % pNGTSTick['TradeMoney'], end="")
            print("Side[%s] " % pNGTSTick['Side'], end="")
            print("TradeBSFlag[%s] " % pNGTSTick['TradeBSFlag'], end="")
            print("MDSecurityStat[%s] " % pNGTSTick['MDSecurityStat'], end="")
            print("Info1[%d] " % pNGTSTick['Info1'], end="")
            print("Info2[%d] " % pNGTSTick['Info2'], end="")
            print("Info3[%d] " % pNGTSTick['Info3'])


    #上海可转债XTS债券逐笔数据通知
    def OnRtnXTSTick(self, pTick):
        """
        上海XTS新债逐笔数据推送回调

        接收上海XTS新债的逐笔委托和成交数据

        Args:
            pTick: XTS逐笔数据结构体，包含逐笔委托和成交信息
        """
        print("OnRtnXTSTick SecurityID[%s] " % pTick['SecurityID'],end="")
        print("ExchangeID[%s] " % pTick['ExchangeID'],end="")
        print("MainSeq[%d] " % pTick['MainSeq'],end="")
        print("SubSeq[%ld] " % pTick['SubSeq'],end="")
        print("TickTime[%d] " % pTick['TickTime'],end="")
        print("TickType[%s] " % pTick['TickType'],end="")
        print("BuyNo[%ld] " % pTick['BuyNo'],end="")
        print("SellNo[%ld] " % pTick['SellNo'],end="")
        print("Price[%.4f] " % pTick['Price'],end="")
        print("Volume[%ld] " % pTick['Volume'],end="")
        print("TradeMoney[%.4f] " % pTick['TradeMoney'],end="")
        print("Side[%s] " % pTick['Side'],end="")
        print("TradeBSFlag[%s] " % pTick['TradeBSFlag'],end="")
        print("MDSecurityStat[%s] " % pTick['MDSecurityStat'],end="")
        print("Info1[%d] " % pTick['Info1'],end="")
        print("Info2[%d] " % pTick['Info2'],end="")
        print("Info3[%d] " % pTick['Info3'])

    def OnRtnBondMarketData(self, pMarketData, FirstLevelBuyNum, FirstLevelBuyOrderVolumes, FirstLevelSellNum, FirstLevelSellOrderVolumes):
        """
        深圳普通债券快照行情数据推送回调（不包括可转债）

        Args:
            pMarketData: 债券行情数据结构体（本例中未使用）
            FirstLevelBuyNum: 第一档买单数量（本例中未使用）
            FirstLevelBuyOrderVolumes: 第一档买单委托量（本例中未使用）
            FirstLevelSellNum: 第一档卖单数量（本例中未使用）
            FirstLevelSellOrderVolumes: 第一档卖单委托量（本例中未使用）
        """
        print("OnRtnBondMarketData::深圳普通债券（不包括可转债）快照行情")

    def OnRtnBondTransaction(self, pTransaction):
        """
        深圳普通债券逐笔成交数据推送回调（不包括可转债）

        Args:
            pTransaction: 债券逐笔成交数据结构体（本例中未使用）
        """
        print("OnRtnBondTransaction::深圳普通债券（不包括可转债）逐笔成交")

    def OnRtnBondOrderDetail(self, pOrderDetail):
        """
        深圳普通债券逐笔委托数据推送回调（不包括可转债）

        Args:
            pOrderDetail: 债券逐笔委托数据结构体（本例中未使用）
        """
        print("OnRtnBondOrderDetail::深圳普通债券（不包括可转债）逐笔委托")


if __name__ == "__main__":
    """
    主程序入口

    功能：
    1. 解析命令行参数，支持TCP和UDP两种连接方式
    2. 创建API实例并配置连接参数
    3. 注册回调处理对象
    4. 启动行情接收服务
    """
    # 打印接口版本号
    print("LEV2MDAPI版本号::"+lev2mdapi.CTORATstpLev2MdApi_GetApiVersion())
    argc=len(sys.argv)

    if argc==1 : #默认TCP连接仿真环境
        # LEV2MD_TCP_FrontAddress ="tcp://210.14.72.17:16900" #上海测试桩 合并流
        # LEV2MD_TCP_FrontAddress ="tcp://210.14.72.17:36900" #上海测试桩 非合并流
        LEV2MD_TCP_FrontAddress ="tcp://210.14.72.17:6900" #深圳测试桩

    elif argc == 3 and sys.argv[1]=="tcp" :   #普通TCP方式
        # 通过命令行参数指定TCP连接地址
        LEV2MD_TCP_FrontAddress=sys.argv[2]
    elif argc == 4 and sys.argv[1]=="udp" :   #UDP 组播
        # 通过命令行参数指定UDP组播地址和接收网卡IP
        LEV2MD_MCAST_FrontAddress=sys.argv[2]	#组播地址
        LEV2MD_MCAST_InterfaceIP=sys.argv[3]	#组播接收地址
    else:
        # 参数错误，显示使用说明
        print("/*********************************************demo运行说明************************************\n")
        print("* argv[1]: tcp udp\t\t\t\t=[%s]" % (sys.argv[1]))
        print("* argv[2]: tcp::FrontIP udp::MCAST_IP\t\t=[%s]" % (sys.argv[2] if argc>2 else ""))
        print("* argv[3]: udp::InterfaceIP\t=[%s]" % (sys.argv[3] if argc>3 else ""))
        print("* Usage:")
        print("* 默认连上海测试桩:	python3 lev2mddemo.py")
        print("* 指定TCP地址:		python3 lev2mddemo.py tcp tcp://210.14.72.17:16900")
        print("* 指定组播地址:		python3 lev2mddemo.py udp udp://224.224.224.15:7889 10.168.9.46")
        print("* 上述x.x.x.x使用托管服务器中接收LEV2MD行情的网口IP地址")
        print("* ******************************************************************************************/")
        exit(-1)

    '''*************************创建实例 注册服务*****************'''
    if argc==1 or sys.argv[1]=="tcp" :   #默认或TCP方式
        print("************* LEV2MD TCP *************")
        # TCP订阅lv2行情，前置Front和FENS方式都用默认构造
        api = lev2mdapi.CTORATstpLev2MdApi_CreateTstpLev2MdApi()
        #默认 api = lev2mdapi.CTORATstpLev2MdApi_CreateTstpLev2MdApi(lev2mdapi.TORA_TSTP_MST_TCP)
        '''
        非缓存模式: lev2mdapi.CTORATstpLev2MdApi_CreateTstpLev2MdApi(lev2mdapi.TORA_TSTP_MST_TCP,false)
        缓存模式：  lev2mdapi.CTORATstpLev2MdApi_CreateTstpLev2MdApi(lev2mdapi.TORA_TSTP_MST_TCP,true)
        非缓存模式相比缓存模式处理效率更高,但回调处理逻辑耗时长可能导致连接中断时,建议使用缓存模式
        '''

        # 注册TCP前置服务器地址
        api.RegisterFront(LEV2MD_TCP_FrontAddress)
        # 注册多个行情前置服务地址，用逗号隔开
        # 例如:api.RegisterFront("tcp://10.0.1.101:6402,tcp://10.0.1.101:16402")
        print("LEV2MD_TCP_FrontAddress[TCP]::%s" % LEV2MD_TCP_FrontAddress)

    elif sys.argv[1]=="udp"  :  #组播普通行情
        print("************* LEV2MD UDP *************")
        # LEV2MD组播订阅lv2行情，默认非缓存模式
        api = lev2mdapi.CTORATstpLev2MdApi_CreateTstpLev2MdApi(lev2mdapi.TORA_TSTP_MST_MCAST)
        '''
        非缓存模式: lev2mdapi.CTORATstpLev2MdApi_CreateTstpLev2MdApi(lev2mdapi.TORA_TSTP_MST_MCAST,false)
        缓存模式：  lev2mdapi.CTORATstpLev2MdApi_CreateTstpLev2MdApi(lev2mdapi.TORA_TSTP_MST_MCAST,true)
        非缓存模式相比缓存模式处理效率更高,但回调处理逻辑耗时长可能导致不能完整及时处理数据时,建议使用缓存模式
        '''
        # 注册UDP组播地址和接收网卡IP
        api.RegisterMulticast(LEV2MD_MCAST_FrontAddress, LEV2MD_MCAST_InterfaceIP, "")
        print("LEV2MD_MCAST_FrontAddress[UDP]::%s" % LEV2MD_MCAST_FrontAddress)
        print("LEV2MD_MCAST_InterfaceIP::%s" % LEV2MD_MCAST_InterfaceIP)

    else:
        # 参数错误，显示使用说明并退出
        print("/*********************************************demo运行说明************************************\n")
        print("* argv[1]: tcp udp\t\t\t\t=[%s]" % (sys.argv[1]))
        print("* argv[2]: tcp::FrontIP udp::MCAST_IP\t\t=[%s]" % (sys.argv[2] if argc>2 else ""))
        print("* argv[3]: udp::InterfaceIP\t=[%s]" % (sys.argv[3] if argc>3 else ""))
        print("* Usage:")
        print("* 默认连上海测试桩:	python3 lev2mddemo.py")
        print("* 指定TCP地址:		python3 lev2mddemo.py tcp tcp://210.14.72.17:16900")
        print("* 指定组播地址:		python3 lev2mddemo.py udp udp://224.224.224.15:7889 10.168.9.46")
        print("* 上述x.x.x.x使用托管服务器中接收LEV2MD行情的网口IP地址")
        print("* ******************************************************************************************/")
        sys.exit(-2)

    # 创建回调对象，用于处理各种行情数据推送
    spi = MdSpi(api)

    # 注册回调接口，将回调对象与API实例关联
    api.RegisterSpi(spi)

    # 启动接口,不输入参数时为不绑核运行
    api.Init()
    # 绑核运行需要输入核心编号.
    # TCP模式收取行情时，非缓存模式1个线程,缓存模式2个线程,相应绑几个核心即可
    # 组播模式收取行情时，需要传递的核的数目= 注册的组播地址数目+[缓存模式? 1: 0]
    # 平台服务器PROXY模式时,线程数2,绑定不低于2个核心
    #api.Init("2,17")


    # 等待程序结束（按回车键退出）
    input()

    # 释放接口对象，清理资源
    api.Release()
