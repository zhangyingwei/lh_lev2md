#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
import lev2mdapi

Front_Address = "tcp://10.0.1.101:6900"
Multicast_Address = "udp://224.224.224.234:7889"
Multicast_Address2 = "udp://224.224.224.234:7890"
Local_Interface_Address = "10.0.1.24"
Sender_Interface_Address = "10.0.1.101"

g_SubMarketData = True;
g_SubTransaction = True;
g_SubOrderDetail = True;
g_SubXTSTick = True;
g_SubXTSMarketData = True;
g_SubNGTSTick = True;
g_SubBondMarketData = True;
g_SubBondTransaction = True;
g_SubBondOrderDetail = True;

SH_Securities = [b"600035", b"510050", b"600000" ];
SH_XTS_Securities = [ b"018003", b"113565" ];

SZ_Securities = [b"000001", b"128048", b"128125" ];
SZ_Bond_Securities = [b"100303", b"109559", b"112617"];

class Lev2MdSpi(lev2mdapi.CTORATstpLev2MdSpi):
	def __init__(self,api):
		lev2mdapi.CTORATstpLev2MdSpi.__init__(self)
		self.__api=api

	def OnFrontConnected(self):
		print("OnFrontConnected")
		#请求登录
		login_req = lev2mdapi.CTORATstpReqUserLoginField()
		self.__api.ReqUserLogin(login_req,1)

	def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast):
		print("OnRspUserLogin: ErrorID[%d] ErrorMsg[%s] RequestID[%d] IsLast[%d]" % (pRspInfo['ErrorID'], pRspInfo['ErrorMsg'], nRequestID, bIsLast))
		if pRspInfo['ErrorID'] == 0:
			if g_SubMarketData:
				self.__api.SubscribeMarketData(SH_Securities,lev2mdapi.TORA_TSTP_EXD_SSE);
				self.__api.SubscribeMarketData(SZ_Securities, lev2mdapi.TORA_TSTP_EXD_SZSE);

			if g_SubTransaction:
				self.__api.SubscribeTransaction(SH_Securities, lev2mdapi.TORA_TSTP_EXD_SSE);
				self.__api.SubscribeTransaction(SZ_Securities, lev2mdapi.TORA_TSTP_EXD_SZSE);

			if g_SubOrderDetail:
				self.__api.SubscribeOrderDetail(SH_Securities, lev2mdapi.TORA_TSTP_EXD_SSE);
				self.__api.SubscribeOrderDetail(SZ_Securities, lev2mdapi.TORA_TSTP_EXD_SZSE);

			if g_SubXTSTick:
				self.__api.SubscribeXTSTick(SH_XTS_Securities, lev2mdapi.TORA_TSTP_EXD_SSE);

			if g_SubXTSMarketData:
				self.__api.SubscribeXTSMarketData(SH_XTS_Securities, lev2mdapi.TORA_TSTP_EXD_SSE);

			if g_SubBondMarketData:
				self.__api.SubscribeBondMarketData(SZ_Bond_Securities, lev2mdapi.TORA_TSTP_EXD_SZSE);

			if g_SubBondTransaction:
				self.__api.SubscribeBondTransaction(SZ_Bond_Securities, lev2mdapi.TORA_TSTP_EXD_SZSE);

			if g_SubBondOrderDetail:
				self.__api.SubscribeBondOrderDetail(SZ_Bond_Securities, lev2mdapi.TORA_TSTP_EXD_SZSE);
			#4.0.5版本接口
			if g_SubNGTSTick:
				self.__api.SubscribeNGTSTick(SH_Securities, lev2mdapi.TORA_TSTP_EXD_SSE);



	def OnRspSubMarketData(self, pSpecificSecurity, pRspInfo, nRequestID, bIsLast):
		print("OnRspSubMarketData")

	def OnRspSubIndex(self, pSpecificSecurity, pRspInfo, nRequestID, bIsLast):
		print("OnRspSubIndex")

	def OnRspSubTransaction(self, pSpecificSecurity, pRspInfo, nRequestID, bIsLast):
		print("OnRspSubTransaction")

	def OnRspSubOrderDetail(self, pSpecificSecurity, pRspInfo, nRequestID, bIsLast):
		print("OnRspSubOrderDetail")

	def OnRspSubBondMarketData(self, pSpecificSecurity, pRspInfo, nRequestID, bIsLast):
		print("OnRspSubBondMarketData")

	def OnRspSubBondTransaction(self, pSpecificSecurity, pRspInfo, nRequestID, bIsLast):
		print("OnRspSubBondTransaction")

	def OnRspSubBondOrderDetail(self, pSpecificSecurity, pRspInfo, nRequestID, bIsLast):
		print("OnRspSubBondOrderDetail")

	def OnRspSubXTSMarketData(self, pSpecificSecurity, pRspInfo, nRequestID, bIsLast):
		print("OnRspSubXTSMarketData")

	def OnRspSubXTSTick(self, pSpecificSecurity, pRspInfo, nRequestID, bIsLast):
		print("OnRspSubXTSTick")

	# 4.0.5版本接口
	def OnRspSubNGTSTick(self, pSpecificSecurity, pRspInfo, nRequestID, bIsLast):
		print("OnRspSubNGTSTick")



	def OnRtnMarketData(self, pDepthMarketData, FirstLevelBuyNum, FirstLevelBuyOrderVolumes, FirstLevelSellNum, FirstLevelSellOrderVolumes):
		#输出行情快照数据
		print("OnRtnMarketData SecurityID[%s] LastPrice[%.2f] TotalVolumeTrade[%d] TotalValueTrade[%.2f] BidPrice1[%.2f] BidVolume1[%d] AskPrice1[%.2f] AskVolume1[%d]" % (pDepthMarketData['SecurityID'],
																																												pDepthMarketData['LastPrice'],
																																												pDepthMarketData['TotalValueTrade'],
																																												pDepthMarketData['TotalValueTrade'],
																																												pDepthMarketData['BidPrice1'],
																																												pDepthMarketData['BidVolume1'],
																																												pDepthMarketData['AskPrice1'],
																																												pDepthMarketData['AskVolume1']))
		#输出一档价位买队列前50笔委托数量
		for buy_index in range(0, FirstLevelBuyNum):
			print("first level buy  [%d] : [%d]" % (buy_index, FirstLevelBuyOrderVolumes[buy_index]))

		#输出一档价位卖队列前50笔委托数量
		for sell_index in range(0, FirstLevelSellNum):
			print("first level sell [%d] : [%d]" % (sell_index, FirstLevelSellOrderVolumes[sell_index]))

	def OnRtnIndex(self, pIndex):
		#输出指数行情数据
		print("OnRtnIndex SecurityID[%s] LastIndex[%.2f] LowIndex[%.2f] HighIndex[%.2f] TotalVolumeTraded[%d] Turnover[%.2f]" %(pIndex['SecurityID'],
																													 pIndex['LastIndex'],
																													 pIndex['LowIndex'],
																													 pIndex['HighIndex'],
																													 pIndex['TotalVolumeTraded'],
																													 pIndex['Turnover']))

	def OnRtnTransaction(self, pTransaction):
		#输出逐笔成交数据
		print("OnRtnTransaction SecurityID[%s] TradePrice[%.2f] TradeVolume[%d] TradeTime[%d] MainSeq[%d] SubSeq[%d] BuyNo[%d] SellNo[%d]" % (pTransaction['SecurityID'],
																																			  pTransaction['TradePrice'],
																																			  pTransaction['TradeVolume'],
																																			  pTransaction['TradeTime'],
																																			  pTransaction['MainSeq'],
																																			  pTransaction['SubSeq'],
																																			  pTransaction['BuyNo'],
																																			  pTransaction['SellNo']))

	def OnRtnOrderDetail(self, pOrderDetail):
		#输出逐笔委托数据
		print("OnRtnOrderDetail SecurityID[%s] Price[%.2f] Volume[%d] Side[%s] OrderType[%s] OrderTime[%d] MainSeq[%d] SubSeq[%d]" % (pOrderDetail['SecurityID'],
																																	  pOrderDetail['Price'],
																																	  pOrderDetail['Volume'],
																																	  pOrderDetail['Side'],
																																	  pOrderDetail['OrderType'],
																																	  pOrderDetail['OrderTime'],
																																	  pOrderDetail['MainSeq'],
																																	  pOrderDetail['SubSeq']))


	def OnRtnBondMarketData(self, pDepthMarketData, FirstLevelBuyNum, FirstLevelBuyOrderVolumes, FirstLevelSellNum,
						FirstLevelSellOrderVolumes):
		# 输出行情快照数据
		print(
			"OnRtnBondMarketData SecurityID[%s] LastPrice[%.2f] TotalVolumeTrade[%d] TotalValueTrade[%.2f] BidPrice1[%.2f] BidVolume1[%d] AskPrice1[%.2f] AskVolume1[%d]" % (
																																		pDepthMarketData['SecurityID'],
																																		pDepthMarketData['LastPrice'],
																																		pDepthMarketData['TotalValueTrade'],
																																		pDepthMarketData['TotalValueTrade'],
																																		pDepthMarketData['BidPrice1'],
																																		pDepthMarketData['BidVolume1'],
																																		pDepthMarketData['AskPrice1'],
																																		pDepthMarketData['AskVolume1']))

		# 输出一档价位买队列前50笔委托数量
		for buy_index in range(0, FirstLevelBuyNum):
			print("first level buy  [%d] : [%d]" % (buy_index, FirstLevelBuyOrderVolumes[buy_index]))

		# 输出一档价位卖队列前50笔委托数量
		for sell_index in range(0, FirstLevelSellNum):
			print("first level sell [%d] : [%d]" % (sell_index, FirstLevelSellOrderVolumes[sell_index]))

	def OnRtnBondTransaction(self, pTransaction):
		# 输出逐笔成交数据
		print(
			"OnRtnBondTransaction SecurityID[%s] TradePrice[%.2f] TradeVolume[%d] TradeTime[%d] MainSeq[%d] SubSeq[%d] BuyNo[%d] SellNo[%d]" % (
			pTransaction['SecurityID'],
			pTransaction['TradePrice'],
			pTransaction['TradeVolume'],
			pTransaction['TradeTime'],
			pTransaction['MainSeq'],
			pTransaction['SubSeq'],
			pTransaction['BuyNo'],
			pTransaction['SellNo']))

	def OnRtnBondOrderDetail(self, pOrderDetail):
		# 输出逐笔委托数据
		print(
			"OnRtnBondOrderDetail SecurityID[%s] Price[%.2f] Volume[%d] Side[%s] OrderType[%s] OrderTime[%d] MainSeq[%d] SubSeq[%d]" % (
			pOrderDetail['SecurityID'],
			pOrderDetail['Price'],
			pOrderDetail['Volume'],
			pOrderDetail['Side'],
			pOrderDetail['OrderType'],
			pOrderDetail['OrderTime'],
			pOrderDetail['MainSeq'],
			pOrderDetail['SubSeq']))


	def OnRtnXTSMarketData(self, pDepthMarketData, FirstLevelBuyNum, FirstLevelBuyOrderVolumes, FirstLevelSellNum,
							FirstLevelSellOrderVolumes):
		# 输出行情快照数据
		print(
			"OnRtnXTSMarketData SecurityID[%s] LastPrice[%.2f] TotalVolumeTrade[%d] TotalValueTrade[%.2f] BidPrice1[%.2f] BidVolume1[%d] AskPrice1[%.2f] AskVolume1[%d]" % (
																																	pDepthMarketData['SecurityID'],
																																	pDepthMarketData['LastPrice'],
																																	pDepthMarketData['TotalValueTrade'],
																																	pDepthMarketData['TotalValueTrade'],
																																	pDepthMarketData['BidPrice1'],
																																	pDepthMarketData['BidVolume1'],
																																	pDepthMarketData['AskPrice1'],
																																	pDepthMarketData['AskVolume1']))

		# 输出一档价位买队列前50笔委托数量
		for buy_index in range(0, FirstLevelBuyNum):
			print("first level buy  [%d] : [%d]" % (buy_index, FirstLevelBuyOrderVolumes[buy_index]))

		# 输出一档价位卖队列前50笔委托数量
		for sell_index in range(0, FirstLevelSellNum):
			print("first level sell [%d] : [%d]" % (sell_index, FirstLevelSellOrderVolumes[sell_index]))

	def OnRtnXTSTick(self, pTick):
		# 输出上海债券逐笔数据’
		print(
			"OnXTSTick TickType[%s] SecurityID[%s] Price[%.2f] Volume[%d] TickTime[%d] MainSeq[%d] SubSeq[%d] BuyNo[%d] SellNo[%d]" % (
				pTick['TickType'],
				pTick['SecurityID'],
				pTick['Price'],
				pTick['Volume'],
				pTick['TickTime'],
				pTick['MainSeq'],
				pTick['SubSeq'],
				pTick['BuyNo'],
				pTick['SellNo']))


	def OnRtnNGTSTick(self, pTick):
		# 输出上海股基逐笔数据’
		print(
			"OnRtnNGTSTick TickType[%s] SecurityID[%s] Price[%.2f] Volume[%d] TickTime[%d] MainSeq[%d] SubSeq[%d] BuyNo[%d] SellNo[%d]" % (
			pTick['TickType'],
			pTick['SecurityID'],
			pTick['Price'],
			pTick['Volume'],
			pTick['TickTime'],
			pTick['MainSeq'],
			pTick['SubSeq'],
			pTick['BuyNo'],
	    	pTick['SellNo']))


if __name__ == "__main__":
	print(lev2mdapi.CTORATstpLev2MdApi_GetApiVersion())
	#case 1: Tcp方式
	g_SubMode=lev2mdapi.TORA_TSTP_MST_TCP
	#case 2: 组播方式
	#g_SubMode = lev2mdapi.TORA_TSTP_MST_MCAST

	#case 1缓存模式
	api = lev2mdapi.CTORATstpLev2MdApi_CreateTstpLev2MdApi(g_SubMode,True)
	#case 2非缓存模式
	#api = lev2mdapi.CTORATstpLev2MdApi_CreateTstpLev2MdApi(g_SubMode, False)

	spi = Lev2MdSpi(api)
	api.RegisterSpi(spi)

	if g_SubMode != lev2mdapi.TORA_TSTP_MST_MCAST:
		api.RegisterFront(Front_Address)
	else:
		#case 1 从一个组播地址收取行情
		api.RegisterMulticast(Multicast_Address, Local_Interface_Address, Sender_Interface_Address)

		#case 2:注册多个组播地址同时收行情
		#api.RegisterMulticast(Multicast_Address, Local_Interface_Address, Sender_Interface_Address);
		#api.RegisterMulticast(Multicast_Address2, Local_Interface_Address, Sender_Interface_Address);

		#case 3:efvi模式收行情
		#api.RegisterMulticast(Multicast_Address, Local_Interface_Address, Sender_Interface_Address, "enp101s0f0",4096, True);

	#case 1 不绑核运行
	api.Init()
	#case 2 绑核运行
	#api.Init("2,17")
	str = input("\n")