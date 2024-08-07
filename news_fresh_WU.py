# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import chinese_calendar as calendar
import fitter
import scipy.stats as st
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
import seaborn as sns
import datetime
import sys

# 添加其他文件夹路径的脚本到系统临时路径，不会保留在环境变量中，每次重新append即可
sys.path.append(r"D:/Work info/Repositories/regression_evaluation_main/")
import regression_evaluation_def as ref

pd.set_option("display.max_columns", None)
pd.set_option("display.min_rows", 20)
plt.rcParams["font.sans-serif"] = ["SimHei"]  # 用来正常显示中文标签
plt.rcParams["axes.unicode_minus"] = False  # 用来正常显示负号
"""
中文字体	    说明
‘SimHei’	中文黑体
‘Kaiti’	    中文楷体
‘LiSu’	    中文隶书
‘FangSong’	中文仿宋
‘YouYuan’	中文幼圆
’STSong‘    华文宋体
"""


organ = "HLJ"
decim = 2
multiplier = 100
process_type = 20

if process_type == 1:
    truncated = 10

    process_type = "fundamental sheets process"
    if truncated == 1:
        truncated = "keep rest days"
    elif truncated == 2:
        truncated = "delete rest days"
    else:
        truncated = "no delete"

elif process_type == 2:
    run_pri_range = 10  # %
    process_type = "running"

else:
    code_processed = 1
    seg_day = datetime.datetime(2022, 8, 1)
    acct_pri_range = 10  # %
    acct_ppfx_range = 10  # %

    process_type = "forecasting and newsvendor comparison"
    if code_processed == 1:
        code_processed = True
    else:
        code_processed = False


def adjust_box_widths(g, fac=0.8):
    """
    Adjust the withs of a seaborn-generated boxplot.
    """
    # iterating through Axes instances
    for ax in g.axes:
        # iterating through axes artists:
        for c in ax.get_children():
            # searching for PathPatches
            if isinstance(c, PathPatch):
                # getting current width of box:
                p = c.get_path()
                verts = p.vertices
                verts_sub = verts[:-1]
                xmin = np.min(verts_sub[:, 0])
                xmax = np.max(verts_sub[:, 0])
                xmid = 0.5 * (xmin + xmax)
                xhalf = 0.5 * (xmax - xmin)

                # setting new width of box
                xmin_new = xmid - fac * xhalf
                xmax_new = xmid + fac * xhalf
                verts_sub[verts_sub[:, 0] == xmin, 0] = xmin_new
                verts_sub[verts_sub[:, 0] == xmax, 0] = xmax_new

                # setting new width of median line
                for l in ax.lines:
                    if np.all(l.get_xdata() == [xmin, xmax]):
                        l.set_xdata([xmin_new, xmax_new])


match process_type:
    case "fundamental sheets process":
        cv, n = 1 / 1, 365 / 2
        account = pd.read_csv(
            f"D:\Work info\WestUnion\data\origin\\{organ}\\account.csv",
            parse_dates=["busdate"],
            infer_datetime_format=True,
            dtype={"code": str},
        )
        print(
            f"\naccount\n\nshape: {account.shape}\n\ndtypes:\n{account.dtypes}\n\nisnull-columns:\n{account.isnull().any()}"
            f"\n\nisnull-rows:\n{sum(account.isnull().T.any())}\n"
        )
        commodity = pd.read_csv(
            f"D:\Work info\WestUnion\data\origin\\{organ}\\commodity.csv",
            dtype={"code": str, "sm_sort": str, "md_sort": str, "bg_sort": str},
        )
        print(
            f"\ncommodity\n\nshape: {commodity.shape}\n\ndtypes:\n{commodity.dtypes}\n\nisnull-columns:\n"
            f"{commodity.isnull().any()}\n\nisnull-rows:\n{sum(commodity.isnull().T.any())}\n"
        )
        stock = pd.read_csv(
            f"D:\Work info\WestUnion\data\origin\\{organ}\\stock.csv",
            parse_dates=["busdate"],
            infer_datetime_format=True,
            dtype={"code": str},
        )
        print(
            f"\nstock\n\nshape: {stock.shape}\n\ndtypes:\n{stock.dtypes}\n\nisnull-columns:\n"
            f"{stock.isnull().any()}\n\nisnull-rows:\n{sum(stock.isnull().T.any())}\n"
        )

        account["weekday"] = account["busdate"].apply(
            lambda x: x.weekday() + 1
        )  # the label of Monday is 0, so +1
        df = pd.DataFrame(
            list(account["busdate"].apply(lambda x: calendar.get_holiday_detail(x))),
            columns=["is_holiday", "hol_type"],
        )  # (True, None) is weekend, (False, 某节日)是指当天因某日调休而补班
        print(
            f"\ndf\n\nshape: {df.shape}\n\ndtypes:\n{df.dtypes}\n\nisnull-columns:\n{df.isnull().any()}"
            f"\n\nisnull-rows, i.e. the number of rows of non-holiday:\n{sum(df.isnull().T.any())}\n"
        )
        if sum(df.isnull().T.any()) > 0:
            df.loc[df.isnull().T.any(), "hol_type"] = "0"  # 将非节假日标为0
            print(
                f"\ndf\n\nshape: {df.shape}\n\ndtypes:\n{df.dtypes}\n\nisnull-columns:\n{df.isnull().any()}"
                f"\n\nisnull-rows, i.e. the number of rows of non-holiday:\n{sum(df.isnull().T.any())}\n"
            )
        account = pd.concat([account, df], axis=1)
        # pandas为了防止漏掉共同属性（特征、维度），两个df中所有相同的列必须on在一起，否则相同的列会出现多余的_x,_y
        acct_comty = pd.merge(account, commodity, how="left", on=["class", "code"])
        print(
            f"\nacct_comty\n\nshape: {acct_comty.shape}\n\ndtypes:\n{acct_comty.dtypes}\n\nisnull-columns:\n"
            f"{acct_comty.isnull().any()}\n\nisnull-rows:\n{sum(acct_comty.isnull().T.any())}\n"
        )
        acct_comty_stk = pd.merge(
            acct_comty, stock, how="left", on=["organ", "class", "code", "busdate"]
        )
        print(
            f"\nacct_comty_stk\n\nshape: {acct_comty_stk.shape}\n\ndtypes:\n{acct_comty_stk.dtypes}\n\nisnull-columns:\n"
            f"{acct_comty_stk.isnull().any()}\n\nisnull-rows:\n{sum(acct_comty_stk.isnull().T.any())}\n"
        )
        if sum(acct_comty_stk.isnull().T.any()) > 0:
            acct_comty_stk.drop(
                index=acct_comty_stk[acct_comty_stk.isnull().T.any()].index,
                inplace=True,
            )
        print(
            f"\nacct_comty_stk\n\nshape: {acct_comty_stk.shape}\n\ndtypes:\n{acct_comty_stk.dtypes}\n\nisnull-columns:\n"
            f"{acct_comty_stk.isnull().any()}\n\nisnull-rows:\n{sum(acct_comty_stk.isnull().T.any())}\n"
        )
        cloumns = [
            "organ",
            "code",
            "name",
            "busdate",
            "weekday",
            "is_holiday",
            "hol_type",
            "class",
            "bg_sort",
            "bg_sort_name",
            "md_sort",
            "md_sort_name",
            "sm_sort",
            "sm_sort_name",
            "amount",
            "sum_price",
            "sum_cost",
            "sum_disc",
            "amou_stock",
            "sum_stock",
            "costprice",
        ]
        acct_comty_stk = acct_comty_stk[cloumns]

        match truncated:
            case "keep rest days":
                acct_comty_stk = acct_comty_stk[
                    (acct_comty_stk["amou_stock"] == 0)
                    & (acct_comty_stk["sum_disc"] == 0)
                ]

            case "delete rest days":
                acct_comty_stk = acct_comty_stk[
                    (acct_comty_stk["amou_stock"] == 0)
                    & (acct_comty_stk["sum_disc"] == 0)
                    & (~acct_comty_stk["is_holiday"])
                ]
            case _:
                acct_comty_stk.to_csv(
                    f"D:\Work info\WestUnion\data\processed\\{organ}\\merge-sheets-no-truncated-no-screen.csv",
                    encoding="utf_8_sig",
                    index=False,
                )
                # sys.exit()

        print(f"acct_comty_stk truncated {acct_comty_stk.shape}")
        codes_group = acct_comty_stk.groupby(["organ", "code"])
        codes_cv = codes_group["amount"].agg(np.std) / codes_group["amount"].agg(
            np.mean
        )
        codes_cv.sort_values(inplace=True)
        codes_filter = codes_cv[
            (codes_cv > 0).values & (codes_cv <= cv).values
        ].index.values
        print(f"经变异系数cv筛选后剩余单品数：{len(codes_filter)}")
        df = pd.DataFrame()
        for _ in range(len(codes_filter)):
            df = pd.concat([df, codes_group.get_group(codes_filter[_])])
        print(f"经变异系数cv筛选后剩余单品的历史销售总天数：{len(df)}")
        codes_filter_longer = (
            df.groupby(["organ", "code"])
            .agg("count")[(df.groupby(["organ", "code"]).agg("count") >= n)["amount"]]
            .index.values
        )
        print(f"经变异系数cv且销售天数n筛选后的单品数：{len(codes_filter_longer)}")
        account_filter = pd.DataFrame()
        for _ in range(len(codes_filter_longer)):
            account_filter = pd.concat(
                [
                    account_filter,
                    acct_comty_stk[
                        (
                            np.sum(
                                acct_comty_stk[["organ", "code"]].values
                                == codes_filter_longer[_],
                                axis=1,
                            )
                            == 2
                        )
                    ],
                ]
            )
        print(
            f"经变异系数cv且销售天数n筛选后剩余单品的历史销售总天数：{len(account_filter)}"
        )
        account_filter.index.name = "account_original_index"
        account_filter.to_csv(
            f"D:\Work info\WestUnion\data\processed\\{organ}\\merge-sheets-truncated-{truncated}--"
            f"cv-{cv:.2f}--len-{round(n)}.csv",
            encoding="utf_8_sig",
        )
        print(f"acct_comty_stk truncated finally {account_filter.shape}")

    case "running":
        running = pd.read_csv(
            f"D:\Work info\WestUnion\data\origin\\{organ}\\running.csv",
            parse_dates=["selldate"],
            dtype={"code": str},
        )
        running["selltime"] = running["selltime"].apply(lambda x: x[:8])  # 截取出时分秒
        running["selltime"] = pd.to_datetime(running["selltime"], format="%H:%M:%S")
        running["selltime"] = running[
            "selltime"
        ].dt.time  # 去掉to_datetime自动生成的年月日
        print(
            f"\n对流水表每笔小票中，单品的平均销售单价进行验证:\n"
            f"np.average(abs(running['sum_sell'] / running['amount'] - running['price'])): "
            f"\n{np.average(abs(running['sum_sell'] / running['amount'] - running['price']))}\n"
        )
        price_mode = (
            running.groupby(["organ", "code", "selldate"])["price"]
            .agg(lambda x: np.mean(pd.Series.mode(x)))
            .reset_index()
        )
        price_mode["price_hb"], price_mode["price_lb"] = price_mode["price"] * (
            1 + run_pri_range / 100
        ), price_mode["price"] * (1 - run_pri_range / 100)
        run_pri_bnd = pd.merge(
            running, price_mode, how="left", on=["organ", "code", "selldate"]
        )
        run_pri_bnd.rename(
            columns={"price_x": "price", "selldate": "busdate"}, inplace=True
        )
        run_pri_seg = run_pri_bnd[
            (run_pri_bnd["price"] <= run_pri_bnd["price_hb"])
            & (run_pri_bnd["price"] >= run_pri_bnd["price_lb"])
            & (run_pri_bnd["type"] == "单品销售")
        ]
        run_grp = (
            run_pri_seg.groupby(["organ", "class", "code", "busdate"])[
                ["amount", "sum_sell", "sum_disc"]
            ]
            .sum()
            .reset_index()
        )
        run_grp["price"] = run_grp["sum_sell"] / run_grp["amount"]
        run_grp.to_csv(
            f"D:\Work info\WestUnion\data\processed\\{organ}\\run_grp.csv",
            index=False,
            encoding="utf_8_sig",
        )

    case "forecasting and newsvendor comparison":
        account_ori = pd.read_csv(
            f"D:\Work info\WestUnion\data\origin\\{organ}\\account.csv",
            parse_dates=["busdate"],
            infer_datetime_format=True,
            dtype={"code": str},
        )
        account_ori["price"] = account_ori["sum_price"] / account_ori["amount"]
        account_ori["ppfx_acct"] = (
            account_ori["sum_price"] - account_ori["sum_cost"]
        ) / account_ori["sum_price"]
        pri_ppfx_avg = (
            account_ori.groupby(["organ", "class", "code"])["price", "ppfx_acct"]
            .median()
            .reset_index()
        )
        pri_ppfx_avg.rename(
            columns={"price": "price_code", "ppfx_acct": "ppfx_code"}, inplace=True
        )
        pri_ppfx_avg[["price_code_mean", "ppfx_code_mean"]] = (
            account_ori.groupby(["organ", "class", "code"])["price", "ppfx_acct"]
            .mean()
            .reset_index()[["price", "ppfx_acct"]]
        )
        pri_ppfx_avg["price_code"] = (
            pri_ppfx_avg["price_code_mean"] + 2 * pri_ppfx_avg["price_code"]
        ) / 3
        pri_ppfx_avg["ppfx_code"] = (
            pri_ppfx_avg["ppfx_code_mean"] + 2 * pri_ppfx_avg["ppfx_code"]
        ) / 3
        pri_ppfx_avg.drop(columns=["price_code_mean", "ppfx_code_mean"], inplace=True)
        pri_ppfx_avg["price_hb"], pri_ppfx_avg["price_lb"] = pri_ppfx_avg[
            "price_code"
        ] * (1 + acct_pri_range / 100), pri_ppfx_avg["price_code"] * (
            1 - acct_pri_range / 100
        )
        pri_ppfx_avg["ppfx_hb"], pri_ppfx_avg["ppfx_lb"] = pri_ppfx_avg["ppfx_code"] * (
            1 + acct_ppfx_range / 100
        ), pri_ppfx_avg["ppfx_code"] * (1 - acct_ppfx_range / 100)
        account = pd.merge(
            account_ori, pri_ppfx_avg, how="left", on=["organ", "class", "code"]
        )
        acct_seg = account[
            (account["price"] <= account["price_hb"])
            & (account["price"] >= account["price_lb"])
            & (account["ppfx_acct"] <= account["ppfx_hb"])
            & (account["ppfx_acct"] >= account["ppfx_lb"])
        ]
        commodity = pd.read_csv(
            f"D:\Work info\WestUnion\data\origin\\{organ}\\commodity.csv",
            dtype={"code": str, "sm_sort": str, "md_sort": str, "bg_sort": str},
        )
        stock = pd.read_csv(
            f"D:\Work info\WestUnion\data\origin\\{organ}\\stock.csv",
            parse_dates=["busdate"],
            infer_datetime_format=True,
            dtype={"code": str},
        )
        acct_comty = pd.merge(acct_seg, commodity, how="left", on=["class", "code"])
        acct_comty_stk = pd.merge(
            acct_comty, stock, how="left", on=["organ", "class", "code", "busdate"]
        )
        print(
            f"\n三种平均成本单价（即平均进价）对比：\n"
            f"\n由账表得到的成本单价(account['sum_cost'] / account['amount']):\n"
            f"{round(acct_comty_stk['sum_cost'] / acct_comty_stk['amount'], decim)}\n"
            f"\n由库存得到的成本单价(stock['sum_stock'] / stock['amou_stock']):\n"
            f"{round(acct_comty_stk['sum_stock'] / acct_comty_stk['amou_stock'], decim)}\n"
            f"\nstock['costprice']:\n"
            f"{acct_comty_stk['costprice']}\n"
        )
        if sum(acct_comty_stk.isnull().T.any()) > 0:
            acct_comty_stk.drop(
                index=acct_comty_stk[acct_comty_stk.isnull().T.any()].index,
                inplace=True,
            )
        # screen out the rows whose stock were still remaining and no discount in one day's selling
        acct_comty_stk = acct_comty_stk[
            (acct_comty_stk["amou_stock"] != 0) & (acct_comty_stk["sum_disc"] == 0)
        ]
        pred = pd.read_csv(
            f"D:\Work info\WestUnion\data\origin\\{organ}\\fresh-forecast-order.csv",
            parse_dates=["busdate"],
            infer_datetime_format=True,
            dtype={"bg_sort": str, "md_sort": str, "sm_sort": str, "code": str},
            names=[
                "Unnamed",
                "organ",
                "class",
                "bg_sort",
                "bg_sort_name",
                "md_sort",
                "md_sort_name",
                "sm_sort",
                "sm_sort_name",
                "code",
                "name",
                "busdate",
                "theory_sale",
                "real_sale",
                "predict",
                "advise_order",
                "real_order",
            ],
            header=0,
        )
        print(
            f"\npred:\n\nshape: {pred.shape}\n\ndtypes:\n{pred.dtypes}\n\nisnull-columns:\n"
            f"{pred.isnull().sum()}\n\nisnull-rows-ratio-avg(%):"
            f"\n{round(sum(pred.isnull().sum()) / (len(pred) * max(1, sum(pred.isnull().any()))) * multiplier, decim)}\n"
        )
        pred.drop(columns=["Unnamed"], inplace=True)
        # 将predict列中含有空值的行删除，保证所有行同时有销售值和预测值
        pred.dropna(inplace=True, subset=["predict"])
        pred_acct_comty_stk = pd.merge(
            pred,
            acct_comty_stk,
            how="right",
            on=[
                "organ",
                "code",
                "name",
                "busdate",
                "class",
                "bg_sort",
                "bg_sort_name",
                "md_sort",
                "md_sort_name",
                "sm_sort",
                "sm_sort_name",
            ],
        )
        print(
            f"\npred_acct_comty_stk:\n\nshape: {pred_acct_comty_stk.shape}\n\ndtypes:\n{pred_acct_comty_stk.dtypes}\n\nisnull-columns:\n"
            f"{pred_acct_comty_stk.isnull().sum()}\n\nisnull-rows-ratio-avg(%):"
            f"\n{round(sum(pred_acct_comty_stk.isnull().sum()) / (len(pred_acct_comty_stk) * max(1, sum(pred_acct_comty_stk.isnull().any()))) * multiplier, decim)}\n"
        )

        pred_acct_comty_stk["organ"].replace(
            to_replace=["门店B", "门店C", "门店D"], value=["B", "C", "D"], inplace=True
        )
        # smape = 2 * abs((pred_acct_comty_stk['predict'] - pred_acct_comty_stk['theory_sale'])
        #                 / (pred_acct_comty_stk['predict'] + pred_acct_comty_stk['theory_sale']))
        # pred_acct_comty_stk = pred_acct_comty_stk[(smape < 1) | pd.isnull(pred_acct_comty_stk['predict']) | pd.isnull(pred_acct_comty_stk['theory_sale'])]
        pred_acct_comty_stk.sort_values(
            by=["organ", "class", "bg_sort", "md_sort", "sm_sort", "code", "busdate"],
            ascending=True,
            inplace=True,
        )

        # obtain validation set.
        print("\nvalidation set:")
        # forecast is not started among 2022 spring festival
        pred_acct_comty_stk_valid = pred_acct_comty_stk[
            pred_acct_comty_stk["busdate"] >= seg_day
        ]
        # 注意，print(f’‘)里{}外不能带:,{}内带:表示设置数值类型
        pred_acct_comty_stk_valid.to_csv(
            f"D:\Work info\WestUnion\data\processed\\{organ}\\process_type-{process_type}-"
            f"pred_acct_comty_stk_valid.csv",
            index=False,
            encoding="utf_8_sig",
        )

        # profit = (售价 - 进价) / 进价
        group_organ_valid = pred_acct_comty_stk_valid.groupby(["organ"], as_index=False)
        profit_organ_valid = pd.DataFrame(
            round(
                (
                    group_organ_valid["sum_price"].sum()["sum_price"]
                    - group_organ_valid["sum_cost"].sum()["sum_cost"]
                )
                / group_organ_valid["sum_cost"].sum()["sum_cost"]
                * multiplier,
                decim,
            ),
            columns=["GrossMargin(%)"],
        )
        profit_organ_valid["organ"] = group_organ_valid["sum_price"].sum()["organ"]
        group_class_valid = pred_acct_comty_stk_valid.groupby(
            ["organ", "class"], as_index=False
        )
        profit_class_valid = pd.DataFrame(
            round(
                (
                    group_class_valid["sum_price"].sum()["sum_price"]
                    - group_class_valid["sum_cost"].sum()["sum_cost"]
                )
                / group_class_valid["sum_cost"].sum()["sum_cost"]
                * multiplier,
                decim,
            ),
            columns=["GrossMargin(%)"],
        )
        profit_class_valid[["organ", "class"]] = group_class_valid["sum_price"].sum()[
            ["organ", "class"]
        ]
        group_big_valid = pred_acct_comty_stk_valid.groupby(
            ["organ", "class", "bg_sort", "bg_sort_name"], as_index=False
        )
        profit_big_valid = pd.DataFrame(
            round(
                (
                    group_big_valid["sum_price"].sum()["sum_price"]
                    - group_big_valid["sum_cost"].sum()["sum_cost"]
                )
                / group_big_valid["sum_cost"].sum()["sum_cost"]
                * multiplier,
                decim,
            ),
            columns=["GrossMargin(%)"],
        )
        profit_big_valid[["organ", "class", "bg_sort", "bg_sort_name"]] = (
            group_big_valid["sum_price"].sum()[
                ["organ", "class", "bg_sort", "bg_sort_name"]
            ]
        )
        group_mid_valid = pred_acct_comty_stk_valid.groupby(
            ["organ", "class", "bg_sort", "bg_sort_name", "md_sort", "md_sort_name"],
            as_index=False,
        )
        profit_mid_valid = pd.DataFrame(
            round(
                (
                    group_mid_valid["sum_price"].sum()["sum_price"]
                    - group_mid_valid["sum_cost"].sum()["sum_cost"]
                )
                / group_mid_valid["sum_cost"].sum()["sum_cost"]
                * multiplier,
                decim,
            ),
            columns=["GrossMargin(%)"],
        )
        profit_mid_valid[
            ["organ", "class", "bg_sort", "bg_sort_name", "md_sort", "md_sort_name"]
        ] = group_mid_valid["sum_price"].sum()[
            ["organ", "class", "bg_sort", "bg_sort_name", "md_sort", "md_sort_name"]
        ]
        group_small_valid = pred_acct_comty_stk_valid.groupby(
            [
                "organ",
                "class",
                "bg_sort",
                "bg_sort_name",
                "md_sort",
                "md_sort_name",
                "sm_sort",
                "sm_sort_name",
            ],
            as_index=False,
        )
        profit_small_valid = pd.DataFrame(
            round(
                (
                    group_small_valid["sum_price"].sum()["sum_price"]
                    - group_small_valid["sum_cost"].sum()["sum_cost"]
                )
                / group_small_valid["sum_cost"].sum()["sum_cost"]
                * multiplier,
                decim,
            ),
            columns=["GrossMargin(%)"],
        )
        profit_small_valid[
            [
                "organ",
                "class",
                "bg_sort",
                "bg_sort_name",
                "md_sort",
                "md_sort_name",
                "sm_sort",
                "sm_sort_name",
            ]
        ] = group_small_valid["sum_price"].sum()[
            [
                "organ",
                "class",
                "bg_sort",
                "bg_sort_name",
                "md_sort",
                "md_sort_name",
                "sm_sort",
                "sm_sort_name",
            ]
        ]
        group_code_valid = pred_acct_comty_stk_valid.groupby(
            [
                "organ",
                "class",
                "bg_sort",
                "bg_sort_name",
                "md_sort",
                "md_sort_name",
                "sm_sort",
                "sm_sort_name",
                "code",
                "name",
            ],
            as_index=False,
        )
        profit_code_valid = pd.DataFrame(
            round(
                (
                    group_code_valid["sum_price"].sum()["sum_price"]
                    - group_code_valid["sum_cost"].sum()["sum_cost"]
                )
                / group_code_valid["sum_cost"].sum()["sum_cost"]
                * multiplier,
                decim,
            ),
            columns=["GrossMargin(%)"],
        )
        profit_code_valid[
            [
                "organ",
                "class",
                "bg_sort",
                "bg_sort_name",
                "md_sort",
                "md_sort_name",
                "sm_sort",
                "sm_sort_name",
                "code",
                "name",
            ]
        ] = group_code_valid["sum_price"].sum()[
            [
                "organ",
                "class",
                "bg_sort",
                "bg_sort_name",
                "md_sort",
                "md_sort_name",
                "sm_sort",
                "sm_sort_name",
                "code",
                "name",
            ]
        ]
        profit_ori_valid = pd.concat(
            [
                profit_organ_valid,
                profit_class_valid,
                profit_big_valid,
                profit_mid_valid,
                profit_small_valid,
                profit_code_valid,
            ],
            ignore_index=True,
        )
        # profit_ori.to_csv(f'D:\Work info\WestUnion\data\processed\\{organ}\\profit_ori.csv', encoding='utf_8_sig')
        # 说明：因为后面不是用profit_ori作为自变量来算newsvendor的最优解，而是用分位点ppfx作为自变量利润，
        # 所以是否对profit_ori做筛选不影响后续newsvendor的最优解的计算。

        # ppfx = (售价 - 进价) / 售价
        ppfx_organ_valid = pd.DataFrame(
            round(
                (
                    group_organ_valid["sum_price"].sum()["sum_price"]
                    - group_organ_valid["sum_cost"].sum()["sum_cost"]
                )
                / group_organ_valid["sum_price"].sum()["sum_price"],
                decim,
            ),
            columns=["ppfx"],
        )
        ppfx_class_valid = pd.DataFrame(
            round(
                (
                    group_class_valid["sum_price"].sum()["sum_price"]
                    - group_class_valid["sum_cost"].sum()["sum_cost"]
                )
                / group_class_valid["sum_price"].sum()["sum_price"],
                decim,
            ),
            columns=["ppfx"],
        )
        ppfx_big_valid = pd.DataFrame(
            round(
                (
                    group_big_valid["sum_price"].sum()["sum_price"]
                    - group_big_valid["sum_cost"].sum()["sum_cost"]
                )
                / group_big_valid["sum_price"].sum()["sum_price"],
                decim,
            ),
            columns=["ppfx"],
        )
        ppfx_mid_valid = pd.DataFrame(
            round(
                (
                    group_mid_valid["sum_price"].sum()["sum_price"]
                    - group_mid_valid["sum_cost"].sum()["sum_cost"]
                )
                / group_mid_valid["sum_price"].sum()["sum_price"],
                decim,
            ),
            columns=["ppfx"],
        )
        ppfx_small_valid = pd.DataFrame(
            round(
                (
                    group_small_valid["sum_price"].sum()["sum_price"]
                    - group_small_valid["sum_cost"].sum()["sum_cost"]
                )
                / group_small_valid["sum_price"].sum()["sum_price"],
                decim,
            ),
            columns=["ppfx"],
        )
        ppfx_code_valid = pd.DataFrame(
            round(
                (
                    group_code_valid["sum_price"].sum()["sum_price"]
                    - group_code_valid["sum_cost"].sum()["sum_cost"]
                )
                / group_code_valid["sum_price"].sum()["sum_price"],
                decim,
            ),
            columns=["ppfx"],
        )
        ppfx_ori_valid = pd.concat(
            [
                ppfx_organ_valid,
                ppfx_class_valid,
                ppfx_big_valid,
                ppfx_mid_valid,
                ppfx_small_valid,
                ppfx_code_valid,
            ],
            ignore_index=True,
        )
        ppfx_all_valid = pd.concat([ppfx_ori_valid, profit_ori_valid], axis=1)
        # 特别重要：因为此处的ppfx_all中每一行的顺序，要与后面（org_sale_valid，org_pred按organ做groupby后），
        # 再按行append（org_cls_sale_valid，org_cls_pred按organ，class做groupby后），
        # 再按行append（org_cls_bg_sale_valid，org_cls_bg_pred按organ，class, bg_sort做groupby后）,
        # 再按行append（org_cls_bg_md_sale_valid，org_cls_bg_md_pred按organ，class, bg_sort, md_sort做groupby后）,
        # 再按行append（org_cls_bg_md_sm_sale_valid，org_cls_bg_md_sm_pred按organ，class, bg_sort, md_sort, sm_sort做groupby后）,
        # 再按行append（org_cls_bg_md_sm_cd_sale_valid，org_cls_bg_md_sm_cd_pred按organ，class, bg_sort, md_sort, sm_sort, code做groupby后）,
        # 的顺序完全一致，一一匹配，最后得到的df中，alpha才是与ppfx和GrossMargin(%)一一对应的。
        # 如果在此处先按条件筛选ppfx_all，则最后得到的df里，中间有些行会对错，则后面的行会全部匹配错。因为这里删除了ppfx_all的某些行，
        # 而对alpha做append时是没有删除行的。所以只能在最后的df里将ppfx <= 0和ppfx == 1的异常行删除，其他行里面的alpha、ppfx、GrossMargin(%)等字段才不会对应错。

        # obtain six hierarchy's sum of 'theory_sale' and 'predict'
        grp_org_dt_valid = pred_acct_comty_stk_valid.groupby(
            ["organ", "busdate"], as_index=False
        )
        org_sale_valid = grp_org_dt_valid["theory_sale"].mean()
        org_pred_valid = grp_org_dt_valid["predict"].mean()
        print(
            f"\nconcerning case ppfx, the number of group organ is: {len(ppfx_organ_valid)}\n"
            f"the length of organ_busdate is: {len(org_sale_valid)}\n"
        )
        grp_org_cls_dt_valid = pred_acct_comty_stk_valid.groupby(
            ["organ", "class", "busdate"], as_index=False
        )
        org_cls_sale_valid = grp_org_cls_dt_valid["theory_sale"].mean()
        org_cls_pred_valid = grp_org_cls_dt_valid["predict"].mean()
        print(
            f"concerning case ppfx, the number of group organ_cls is: {len(ppfx_class_valid)}\n"
            f"the length of organ_class_busdate is: {len(org_cls_sale_valid)}\n"
        )
        grp_org_cls_bg_dt_valid = pred_acct_comty_stk_valid.groupby(
            ["organ", "class", "bg_sort", "busdate"], as_index=False
        )
        org_cls_bg_sale_valid = grp_org_cls_bg_dt_valid["theory_sale"].mean()
        org_cls_bg_pred_valid = grp_org_cls_bg_dt_valid["predict"].mean()
        print(
            f"concerning case ppfx, the number of group organ_cls_bg is: {len(ppfx_big_valid)}\n"
            f"the length of organ_class_bg_busdate is: {len(org_cls_bg_sale_valid)}\n"
        )
        grp_org_cls_bg_md_dt_valid = pred_acct_comty_stk_valid.groupby(
            ["organ", "class", "bg_sort", "md_sort", "busdate"], as_index=False
        )
        org_cls_bg_md_sale_valid = grp_org_cls_bg_md_dt_valid["theory_sale"].mean()
        org_cls_bg_md_pred_valid = grp_org_cls_bg_md_dt_valid["predict"].mean()
        print(
            f"concerning case ppfx, the number of group organ_cls_bg_md is: {len(ppfx_mid_valid)}\n"
            f"the length of organ_class_bg_md_busdate is: {len(org_cls_bg_md_sale_valid)}\n"
        )
        grp_org_cls_bg_md_sm_dt_valid = pred_acct_comty_stk_valid.groupby(
            ["organ", "class", "bg_sort", "md_sort", "sm_sort", "busdate"],
            as_index=False,
        )
        org_cls_bg_md_sm_sale_valid = grp_org_cls_bg_md_sm_dt_valid[
            "theory_sale"
        ].mean()
        org_cls_bg_md_sm_pred_valid = grp_org_cls_bg_md_sm_dt_valid["predict"].mean()
        print(
            f"concerning case ppfx, the number of group organ_cls_bg_md_sm is: {len(ppfx_small_valid)}\n"
            f"the length of organ_class_bg_md_sm_busdate is: {len(org_cls_bg_md_sm_sale_valid)}\n"
        )
        grp_org_cls_bg_md_sm_cd_dt_valid = pred_acct_comty_stk_valid.groupby(
            ["organ", "class", "bg_sort", "md_sort", "sm_sort", "code", "busdate"],
            as_index=False,
        )
        org_cls_bg_md_sm_cd_sale_valid = grp_org_cls_bg_md_sm_cd_dt_valid[
            "theory_sale"
        ].mean()
        org_cls_bg_md_sm_cd_pred_valid = grp_org_cls_bg_md_sm_cd_dt_valid[
            "predict"
        ].mean()
        print(
            f"concerning case ppfx, the number of group organ_cls_bg_md_sm_cd is: {len(ppfx_code_valid)}\n"
            f"the length of organ_class_bg_md_sm_cd_busdate is: {len(org_cls_bg_md_sm_cd_sale_valid)}\n"
        )

        # obtain train set.
        print("\ntrain set:")
        pred_acct_comty_stk_train = pred_acct_comty_stk[
            ~(pred_acct_comty_stk["busdate"] >= seg_day)
        ]
        pred_acct_comty_stk_train.to_csv(
            f"D:\Work info\WestUnion\data\processed\\{organ}\\process_type-{process_type}-"
            f"pred_acct_comty_stk_train.csv",
            index=False,
            encoding="utf_8_sig",
        )

        group_organ_train = pred_acct_comty_stk_train.groupby(["organ"], as_index=False)
        profit_organ_train = pd.DataFrame(
            round(
                (
                    group_organ_train["sum_price"].sum()["sum_price"]
                    - group_organ_train["sum_cost"].sum()["sum_cost"]
                )
                / group_organ_train["sum_cost"].sum()["sum_cost"]
                * multiplier,
                decim,
            ),
            columns=["GrossMargin(%)"],
        )
        profit_organ_train["organ"] = group_organ_train["sum_price"].sum()["organ"]
        group_class_train = pred_acct_comty_stk_train.groupby(
            ["organ", "class"], as_index=False
        )
        profit_class_train = pd.DataFrame(
            round(
                (
                    group_class_train["sum_price"].sum()["sum_price"]
                    - group_class_train["sum_cost"].sum()["sum_cost"]
                )
                / group_class_train["sum_cost"].sum()["sum_cost"]
                * multiplier,
                decim,
            ),
            columns=["GrossMargin(%)"],
        )
        profit_class_train[["organ", "class"]] = group_class_train["sum_price"].sum()[
            ["organ", "class"]
        ]
        group_big_train = pred_acct_comty_stk_train.groupby(
            ["organ", "class", "bg_sort", "bg_sort_name"], as_index=False
        )
        profit_big_train = pd.DataFrame(
            round(
                (
                    group_big_train["sum_price"].sum()["sum_price"]
                    - group_big_train["sum_cost"].sum()["sum_cost"]
                )
                / group_big_train["sum_cost"].sum()["sum_cost"]
                * multiplier,
                decim,
            ),
            columns=["GrossMargin(%)"],
        )
        profit_big_train[["organ", "class", "bg_sort", "bg_sort_name"]] = (
            group_big_train["sum_price"].sum()[
                ["organ", "class", "bg_sort", "bg_sort_name"]
            ]
        )
        group_mid_train = pred_acct_comty_stk_train.groupby(
            ["organ", "class", "bg_sort", "bg_sort_name", "md_sort", "md_sort_name"],
            as_index=False,
        )
        profit_mid_train = pd.DataFrame(
            round(
                (
                    group_mid_train["sum_price"].sum()["sum_price"]
                    - group_mid_train["sum_cost"].sum()["sum_cost"]
                )
                / group_mid_train["sum_cost"].sum()["sum_cost"]
                * multiplier,
                decim,
            ),
            columns=["GrossMargin(%)"],
        )
        profit_mid_train[
            ["organ", "class", "bg_sort", "bg_sort_name", "md_sort", "md_sort_name"]
        ] = group_mid_train["sum_price"].sum()[
            ["organ", "class", "bg_sort", "bg_sort_name", "md_sort", "md_sort_name"]
        ]
        group_small_train = pred_acct_comty_stk_train.groupby(
            [
                "organ",
                "class",
                "bg_sort",
                "bg_sort_name",
                "md_sort",
                "md_sort_name",
                "sm_sort",
                "sm_sort_name",
            ],
            as_index=False,
        )
        profit_small_train = pd.DataFrame(
            round(
                (
                    group_small_train["sum_price"].sum()["sum_price"]
                    - group_small_train["sum_cost"].sum()["sum_cost"]
                )
                / group_small_train["sum_cost"].sum()["sum_cost"]
                * multiplier,
                decim,
            ),
            columns=["GrossMargin(%)"],
        )
        profit_small_train[
            [
                "organ",
                "class",
                "bg_sort",
                "bg_sort_name",
                "md_sort",
                "md_sort_name",
                "sm_sort",
                "sm_sort_name",
            ]
        ] = group_small_train["sum_price"].sum()[
            [
                "organ",
                "class",
                "bg_sort",
                "bg_sort_name",
                "md_sort",
                "md_sort_name",
                "sm_sort",
                "sm_sort_name",
            ]
        ]
        group_code_train = pred_acct_comty_stk_train.groupby(
            [
                "organ",
                "class",
                "bg_sort",
                "bg_sort_name",
                "md_sort",
                "md_sort_name",
                "sm_sort",
                "sm_sort_name",
                "code",
                "name",
            ],
            as_index=False,
        )
        profit_code_train = pd.DataFrame(
            round(
                (
                    group_code_train["sum_price"].sum()["sum_price"]
                    - group_code_train["sum_cost"].sum()["sum_cost"]
                )
                / group_code_train["sum_cost"].sum()["sum_cost"]
                * multiplier,
                decim,
            ),
            columns=["GrossMargin(%)"],
        )
        profit_code_train[
            [
                "organ",
                "class",
                "bg_sort",
                "bg_sort_name",
                "md_sort",
                "md_sort_name",
                "sm_sort",
                "sm_sort_name",
                "code",
                "name",
            ]
        ] = group_code_train["sum_price"].sum()[
            [
                "organ",
                "class",
                "bg_sort",
                "bg_sort_name",
                "md_sort",
                "md_sort_name",
                "sm_sort",
                "sm_sort_name",
                "code",
                "name",
            ]
        ]
        profit_ori_train = pd.concat(
            [
                profit_organ_train,
                profit_class_train,
                profit_big_train,
                profit_mid_train,
                profit_small_train,
                profit_code_train,
            ],
            ignore_index=True,
        )

        ppfx_organ_train = pd.DataFrame(
            round(
                (
                    group_organ_train["sum_price"].sum()["sum_price"]
                    - group_organ_train["sum_cost"].sum()["sum_cost"]
                )
                / group_organ_train["sum_price"].sum()["sum_price"],
                decim,
            ),
            columns=["ppfx"],
        )
        ppfx_class_train = pd.DataFrame(
            round(
                (
                    group_class_train["sum_price"].sum()["sum_price"]
                    - group_class_train["sum_cost"].sum()["sum_cost"]
                )
                / group_class_train["sum_price"].sum()["sum_price"],
                decim,
            ),
            columns=["ppfx"],
        )
        ppfx_big_train = pd.DataFrame(
            round(
                (
                    group_big_train["sum_price"].sum()["sum_price"]
                    - group_big_train["sum_cost"].sum()["sum_cost"]
                )
                / group_big_train["sum_price"].sum()["sum_price"],
                decim,
            ),
            columns=["ppfx"],
        )
        ppfx_mid_train = pd.DataFrame(
            round(
                (
                    group_mid_train["sum_price"].sum()["sum_price"]
                    - group_mid_train["sum_cost"].sum()["sum_cost"]
                )
                / group_mid_train["sum_price"].sum()["sum_price"],
                decim,
            ),
            columns=["ppfx"],
        )
        ppfx_small_train = pd.DataFrame(
            round(
                (
                    group_small_train["sum_price"].sum()["sum_price"]
                    - group_small_train["sum_cost"].sum()["sum_cost"]
                )
                / group_small_train["sum_price"].sum()["sum_price"],
                decim,
            ),
            columns=["ppfx"],
        )
        ppfx_code_train = pd.DataFrame(
            round(
                (
                    group_code_train["sum_price"].sum()["sum_price"]
                    - group_code_train["sum_cost"].sum()["sum_cost"]
                )
                / group_code_train["sum_price"].sum()["sum_price"],
                decim,
            ),
            columns=["ppfx"],
        )
        ppfx_ori_train = pd.concat(
            [
                ppfx_organ_train,
                ppfx_class_train,
                ppfx_big_train,
                ppfx_mid_train,
                ppfx_small_train,
                ppfx_code_train,
            ],
            ignore_index=True,
        )
        ppfx_all_train = pd.concat([ppfx_ori_train, profit_ori_train], axis=1)

        grp_org_dt_train = pred_acct_comty_stk_train.groupby(
            ["organ", "busdate"], as_index=False
        )
        org_sale_train = grp_org_dt_train["amount"].mean()
        print(
            f"\nconcerning case ppfx, the number of group organ is: {len(ppfx_organ_train)}\n"
            f"the length of organ_busdate is: {len(org_sale_train)}\n"
        )
        grp_org_cls_dt_train = pred_acct_comty_stk_train.groupby(
            ["organ", "class", "busdate"], as_index=False
        )
        org_cls_sale_train = grp_org_cls_dt_train["amount"].mean()
        print(
            f"concerning case ppfx, the number of group organ_cls is: {len(ppfx_class_train)}\n"
            f"the length of organ_class_busdate is: {len(org_cls_sale_train)}\n"
        )
        grp_org_cls_bg_dt_train = pred_acct_comty_stk_train.groupby(
            ["organ", "class", "bg_sort", "busdate"], as_index=False
        )
        org_cls_bg_sale_train = grp_org_cls_bg_dt_train["amount"].mean()
        print(
            f"concerning case ppfx, the number of group organ_cls_bg is: {len(ppfx_big_train)}\n"
            f"the length of organ_class_bg_busdate is: {len(org_cls_bg_sale_train)}\n"
        )
        grp_org_cls_bg_md_dt_train = pred_acct_comty_stk_train.groupby(
            ["organ", "class", "bg_sort", "md_sort", "busdate"], as_index=False
        )
        org_cls_bg_md_sale_train = grp_org_cls_bg_md_dt_train["amount"].mean()
        print(
            f"concerning case ppfx, the number of group organ_cls_bg_md is: {len(ppfx_mid_train)}\n"
            f"the length of organ_class_bg_md_busdate is: {len(org_cls_bg_md_sale_train)}\n"
        )
        grp_org_cls_bg_md_sm_dt_train = pred_acct_comty_stk_train.groupby(
            ["organ", "class", "bg_sort", "md_sort", "sm_sort", "busdate"],
            as_index=False,
        )
        org_cls_bg_md_sm_sale_train = grp_org_cls_bg_md_sm_dt_train["amount"].mean()
        print(
            f"concerning case ppfx, the number of group organ_cls_bg_md_sm is: {len(ppfx_small_train)}\n"
            f"the length of organ_class_bg_md_sm_busdate is: {len(org_cls_bg_md_sm_sale_train)}\n"
        )
        grp_org_cls_bg_md_sm_cd_dt_train = pred_acct_comty_stk_train.groupby(
            ["organ", "class", "bg_sort", "md_sort", "sm_sort", "code", "busdate"],
            as_index=False,
        )
        org_cls_bg_md_sm_cd_sale_train = grp_org_cls_bg_md_sm_cd_dt_train[
            "amount"
        ].mean()
        print(
            f"concerning case ppfx, the number of group organ_cls_bg_md_sm_cd is: {len(ppfx_code_train)}\n"
            f"the length of organ_class_bg_md_sm_cd_busdate is: {len(org_cls_bg_md_sm_cd_sale_train)}\n"
        )

        eval_metr = pd.DataFrame()
        if code_processed is False:
            for _ in range(len(org_sale_valid.groupby("organ").groups.keys())):
                # 注意：org_sale_train[['organ']]切出df，org_sale_train['organ']切出serise；即df[['']]切出df，df['']切出series.
                org_sale_train_each = org_sale_train[
                    (
                        org_sale_train[["organ"]]
                        == list(org_sale_valid.groupby(["organ"]).groups.keys())[_]
                    ).sum(axis=1)
                    == len(["organ"])
                ]["amount"]
                org_sale_valid_each = org_sale_valid[
                    (
                        org_sale_valid[["organ"]]
                        == list(org_sale_valid.groupby(["organ"]).groups.keys())[_]
                    ).sum(axis=1)
                    == len(["organ"])
                ]["theory_sale"]
                org_pred_each = org_pred_valid[
                    (
                        org_pred_valid[["organ"]]
                        == list(org_pred_valid.groupby(["organ"]).groups.keys())[_]
                    ).sum(axis=1)
                    == len(["organ"])
                ]["predict"]
                try:
                    # obtain the ralative accuracy (alpha) of 'organ'
                    f = fitter.Fitter(org_sale_train_each, distributions="gamma")
                    f.fit()
                    org_news_each = st.gamma.ppf(
                        ppfx_all_valid["ppfx"][_], *f.fitted_param["gamma"]
                    )
                    # 注意：若series中有空值，使用np.median(series)或np.percentile(series,50)时，返回空；
                    # 使用series.median()则返回除空值外的中位数。
                    alpha = (
                        (org_pred_each - org_news_each)
                        / (org_sale_valid_each - org_news_each)
                    ).median()
                    # calculate evaluation metrics between predict and theory_sale
                    res = ref.regression_evaluation_single(
                        y_true=org_sale_valid_each, y_pred=org_pred_each
                    )
                    accu_sin = ref.accuracy_single(
                        y_true=org_sale_valid_each, y_pred=org_pred_each
                    )
                    df = round(
                        pd.DataFrame(
                            list([alpha]) + list([accu_sin]) + list(res[:-2])
                        ).T,
                        decim,
                    )
                    eval_metr = eval_metr.append(df)
                except:
                    print(
                        f"\nin loop {_}, the length of 'org_sale_train_each' is {len(org_sale_train_each)}\n"
                    )
                    df = pd.DataFrame(
                        list([np.nan]) * max(len(eval_metr.columns), 21)
                    ).T
                    eval_metr = eval_metr.append(df)
            print(
                f"\nppfx(i.e. gross margin ratio):"
                f"\n{ppfx_all_valid['ppfx'].loc[:len(org_sale_valid.groupby('organ').groups.keys())-1]}\n"
                f"\neval_metr:\n{eval_metr}"
            )

            for _ in range(
                len(org_cls_sale_valid.groupby(["organ", "class"]).groups.keys())
            ):
                org_cls_sale_train_each = org_cls_sale_train[
                    (
                        org_cls_sale_train[["organ", "class"]]
                        == list(
                            org_cls_sale_valid.groupby(["organ", "class"]).groups.keys()
                        )[_]
                    ).sum(axis=1)
                    == len(["organ", "class"])
                ]["amount"]
                org_cls_sale_valid_each = org_cls_sale_valid[
                    (
                        org_cls_sale_valid[["organ", "class"]]
                        == list(
                            org_cls_sale_valid.groupby(["organ", "class"]).groups.keys()
                        )[_]
                    ).sum(axis=1)
                    == len(["organ", "class"])
                ]["theory_sale"]
                org_cls_pred_each = org_cls_pred_valid[
                    (
                        org_cls_pred_valid[["organ", "class"]]
                        == list(
                            org_cls_pred_valid.groupby(["organ", "class"]).groups.keys()
                        )[_]
                    ).sum(axis=1)
                    == len(["organ", "class"])
                ]["predict"]
                try:
                    # obtain the ralative accuracy (alpha) of ['organ', 'class']
                    f = fitter.Fitter(org_cls_sale_train_each, distributions="gamma")
                    f.fit()
                    org_cls_news_each = st.gamma.ppf(
                        ppfx_all_valid["ppfx"][
                            len(org_sale_valid.groupby("organ").groups.keys()) + _
                        ],
                        *f.fitted_param["gamma"],
                    )
                    alpha = (
                        (org_cls_pred_each - org_cls_news_each)
                        / (org_cls_sale_valid_each - org_cls_news_each)
                    ).median()
                    # calculate evaluation metrics between predict and theory_sale
                    res = ref.regression_evaluation_single(
                        y_true=org_cls_sale_valid_each, y_pred=org_cls_pred_each
                    )
                    accu_sin = ref.accuracy_single(
                        y_true=org_cls_sale_valid_each, y_pred=org_cls_pred_each
                    )
                    df = round(
                        pd.DataFrame(
                            list([alpha]) + list([accu_sin]) + list(res[:-2])
                        ).T,
                        decim,
                    )
                    eval_metr = eval_metr.append(df)
                except:
                    print(
                        f"\nin loop {_}, the length of 'org_cls_sale_train_each' is {len(org_cls_sale_train_each)}\n"
                    )
                    df = pd.DataFrame(
                        list([np.nan]) * max(len(eval_metr.columns), 21)
                    ).T
                    eval_metr = eval_metr.append(df)
            print(
                f"\nppfx(i.e. gross margin ratio):"
                f"\n{ppfx_all_valid['ppfx'].loc[:len(org_cls_sale_valid.groupby(['organ', 'class']).groups.keys()) - 1]}\n"
                f"\neval_metr:\n{eval_metr}"
            )

            for _ in range(
                len(
                    org_cls_bg_sale_valid.groupby(
                        ["organ", "class", "bg_sort"]
                    ).groups.keys()
                )
            ):
                org_cls_bg_sale_train_each = org_cls_bg_sale_train[
                    (
                        org_cls_bg_sale_train[["organ", "class", "bg_sort"]]
                        == list(
                            org_cls_bg_sale_valid.groupby(
                                ["organ", "class", "bg_sort"]
                            ).groups.keys()
                        )[_]
                    ).sum(axis=1)
                    == len(["organ", "class", "bg_sort"])
                ]["amount"]
                org_cls_bg_sale_valid_each = org_cls_bg_sale_valid[
                    (
                        org_cls_bg_sale_valid[["organ", "class", "bg_sort"]]
                        == list(
                            org_cls_bg_sale_valid.groupby(
                                ["organ", "class", "bg_sort"]
                            ).groups.keys()
                        )[_]
                    ).sum(axis=1)
                    == len(["organ", "class", "bg_sort"])
                ]["theory_sale"]
                org_cls_bg_pred_each = org_cls_bg_pred_valid[
                    (
                        org_cls_bg_pred_valid[["organ", "class", "bg_sort"]]
                        == list(
                            org_cls_bg_pred_valid.groupby(
                                ["organ", "class", "bg_sort"]
                            ).groups.keys()
                        )[_]
                    ).sum(axis=1)
                    == len(["organ", "class", "bg_sort"])
                ]["predict"]
                try:
                    # obtain the ralative accuracy of ['organ', 'class', 'bg_sort']
                    f = fitter.Fitter(org_cls_bg_sale_train_each, distributions="gamma")
                    f.fit()
                    org_cls_bg_news_each = st.gamma.ppf(
                        ppfx_all_valid["ppfx"][
                            len(org_sale_valid.groupby("organ").groups.keys())
                            + len(
                                org_cls_sale_valid.groupby(
                                    ["organ", "class"]
                                ).groups.keys()
                            )
                            + _
                        ],
                        *f.fitted_param["gamma"],
                    )
                    alpha = (
                        (org_cls_bg_pred_each - org_cls_bg_news_each)
                        / (org_cls_bg_sale_valid_each - org_cls_bg_news_each)
                    ).median()
                    # calculate evaluation metrics between predict and theory_sale
                    res = ref.regression_evaluation_single(
                        y_true=org_cls_bg_sale_valid_each, y_pred=org_cls_bg_pred_each
                    )
                    accu_sin = ref.accuracy_single(
                        y_true=org_cls_bg_sale_valid_each, y_pred=org_cls_bg_pred_each
                    )
                    df = round(
                        pd.DataFrame(
                            list([alpha]) + list([accu_sin]) + list(res[:-2])
                        ).T,
                        decim,
                    )
                    eval_metr = eval_metr.append(df)
                except:
                    print(
                        f"\nin loop {_}, the length of 'org_cls_bg_sale_train_each' is {len(org_cls_bg_sale_train_each)}\n"
                    )
                    df = pd.DataFrame(
                        list([np.nan]) * max(len(eval_metr.columns), 21)
                    ).T
                    eval_metr = eval_metr.append(df)
            print(
                f"\nppfx(i.e. gross margin ratio):"
                f"\n{ppfx_all_valid['ppfx'].loc[:len(org_cls_bg_sale_valid.groupby(['organ', 'class', 'bg_sort']).groups.keys()) - 1]}\n"
                f"\neval_metr:\n{eval_metr}"
            )

            for _ in range(
                len(
                    org_cls_bg_md_sale_valid.groupby(
                        ["organ", "class", "bg_sort", "md_sort"]
                    ).groups.keys()
                )
            ):
                org_cls_bg_md_sale_train_each = org_cls_bg_md_sale_train[
                    (
                        org_cls_bg_md_sale_train[
                            ["organ", "class", "bg_sort", "md_sort"]
                        ]
                        == list(
                            org_cls_bg_md_sale_valid.groupby(
                                ["organ", "class", "bg_sort", "md_sort"]
                            ).groups.keys()
                        )[_]
                    ).sum(axis=1)
                    == len(["organ", "class", "bg_sort", "md_sort"])
                ]["amount"]
                org_cls_bg_md_sale_valid_each = org_cls_bg_md_sale_valid[
                    (
                        org_cls_bg_md_sale_valid[
                            ["organ", "class", "bg_sort", "md_sort"]
                        ]
                        == list(
                            org_cls_bg_md_sale_valid.groupby(
                                ["organ", "class", "bg_sort", "md_sort"]
                            ).groups.keys()
                        )[_]
                    ).sum(axis=1)
                    == len(["organ", "class", "bg_sort", "md_sort"])
                ]["theory_sale"]
                org_cls_bg_md_pred_each = org_cls_bg_md_pred_valid[
                    (
                        org_cls_bg_md_pred_valid[
                            ["organ", "class", "bg_sort", "md_sort"]
                        ]
                        == list(
                            org_cls_bg_md_pred_valid.groupby(
                                ["organ", "class", "bg_sort", "md_sort"]
                            ).groups.keys()
                        )[_]
                    ).sum(axis=1)
                    == len(["organ", "class", "bg_sort", "md_sort"])
                ]["predict"]
                try:
                    # obtain the ralative accuracy of ['organ', 'class', 'bg_sort', 'md_sort']
                    f = fitter.Fitter(
                        org_cls_bg_md_sale_train_each, distributions="gamma"
                    )
                    f.fit()
                    org_cls_bg_md_news_each = st.gamma.ppf(
                        ppfx_all_valid["ppfx"][
                            len(org_sale_valid.groupby("organ").groups.keys())
                            + len(
                                org_cls_sale_valid.groupby(
                                    ["organ", "class"]
                                ).groups.keys()
                            )
                            + len(
                                org_cls_bg_sale_valid.groupby(
                                    ["organ", "class", "bg_sort"]
                                ).groups.keys()
                            )
                            + _
                        ],
                        *f.fitted_param["gamma"],
                    )
                    alpha = (
                        (org_cls_bg_md_pred_each - org_cls_bg_md_news_each)
                        / (org_cls_bg_md_sale_valid_each - org_cls_bg_md_news_each)
                    ).median()
                    # calculate evaluation metrics between predict and theory_sale
                    res = ref.regression_evaluation_single(
                        y_true=org_cls_bg_md_sale_valid_each,
                        y_pred=org_cls_bg_md_pred_each,
                    )
                    accu_sin = ref.accuracy_single(
                        y_true=org_cls_bg_md_sale_valid_each,
                        y_pred=org_cls_bg_md_pred_each,
                    )
                    df = round(
                        pd.DataFrame(
                            list([alpha]) + list([accu_sin]) + list(res[:-2])
                        ).T,
                        decim,
                    )
                    eval_metr = eval_metr.append(df)
                except:
                    print(
                        f"\nin loop {_}, the length of 'org_cls_bg_md_sale_train_each' is {len(org_cls_bg_md_sale_train_each)}\n"
                    )
                    df = pd.DataFrame(
                        list([np.nan]) * max(len(eval_metr.columns), 21)
                    ).T
                    eval_metr = eval_metr.append(df)
            print(
                f"\nppfx(i.e. gross margin ratio):"
                f"\n{ppfx_all_valid['ppfx'].loc[:len(org_cls_bg_md_sale_valid.groupby(['organ', 'class', 'bg_sort', 'md_sort']).groups.keys()) - 1]}\n"
                f"\neval_metr:\n{eval_metr}"
            )

            for _ in range(
                len(
                    org_cls_bg_md_sm_sale_valid.groupby(
                        ["organ", "class", "bg_sort", "md_sort", "sm_sort"]
                    ).groups.keys()
                )
            ):
                org_cls_bg_md_sm_sale_train_each = org_cls_bg_md_sm_sale_train[
                    (
                        org_cls_bg_md_sm_sale_train[
                            ["organ", "class", "bg_sort", "md_sort", "sm_sort"]
                        ]
                        == list(
                            org_cls_bg_md_sm_sale_valid.groupby(
                                ["organ", "class", "bg_sort", "md_sort", "sm_sort"]
                            ).groups.keys()
                        )[_]
                    ).sum(axis=1)
                    == len(["organ", "class", "bg_sort", "md_sort", "sm_sort"])
                ]["amount"]
                org_cls_bg_md_sm_sale_valid_each = org_cls_bg_md_sm_sale_valid[
                    (
                        org_cls_bg_md_sm_sale_valid[
                            ["organ", "class", "bg_sort", "md_sort", "sm_sort"]
                        ]
                        == list(
                            org_cls_bg_md_sm_sale_valid.groupby(
                                ["organ", "class", "bg_sort", "md_sort", "sm_sort"]
                            ).groups.keys()
                        )[_]
                    ).sum(axis=1)
                    == len(["organ", "class", "bg_sort", "md_sort", "sm_sort"])
                ]["theory_sale"]
                org_cls_bg_md_sm_pred_each = org_cls_bg_md_sm_pred_valid[
                    (
                        org_cls_bg_md_sm_pred_valid[
                            ["organ", "class", "bg_sort", "md_sort", "sm_sort"]
                        ]
                        == list(
                            org_cls_bg_md_sm_pred_valid.groupby(
                                ["organ", "class", "bg_sort", "md_sort", "sm_sort"]
                            ).groups.keys()
                        )[_]
                    ).sum(axis=1)
                    == len(["organ", "class", "bg_sort", "md_sort", "sm_sort"])
                ]["predict"]
                try:
                    # obtain the ralative accuracy of ['organ', 'class', 'bg_sort', 'md_sort', 'sm_sort']
                    f = fitter.Fitter(
                        org_cls_bg_md_sm_sale_train_each, distributions="gamma"
                    )
                    f.fit()
                    org_cls_bg_md_sm_news_each = st.gamma.ppf(
                        ppfx_all_valid["ppfx"][
                            len(org_sale_valid.groupby("organ").groups.keys())
                            + len(
                                org_cls_sale_valid.groupby(
                                    ["organ", "class"]
                                ).groups.keys()
                            )
                            + len(
                                org_cls_bg_sale_valid.groupby(
                                    ["organ", "class", "bg_sort"]
                                ).groups.keys()
                            )
                            + len(
                                org_cls_bg_md_sale_valid.groupby(
                                    ["organ", "class", "bg_sort", "md_sort"]
                                ).groups.keys()
                            )
                            + _
                        ],
                        *f.fitted_param["gamma"],
                    )
                    alpha = (
                        (org_cls_bg_md_sm_pred_each - org_cls_bg_md_sm_news_each)
                        / (
                            org_cls_bg_md_sm_sale_valid_each
                            - org_cls_bg_md_sm_news_each
                        )
                    ).median()
                    # calculate evaluation metrics between predict and theory_sale
                    res = ref.regression_evaluation_single(
                        y_true=org_cls_bg_md_sm_sale_valid_each,
                        y_pred=org_cls_bg_md_sm_pred_each,
                    )
                    accu_sin = ref.accuracy_single(
                        y_true=org_cls_bg_md_sm_sale_valid_each,
                        y_pred=org_cls_bg_md_sm_pred_each,
                    )
                    df = round(
                        pd.DataFrame(
                            list([alpha]) + list([accu_sin]) + list(res[:-2])
                        ).T,
                        decim,
                    )
                    eval_metr = eval_metr.append(df)
                except:
                    print(
                        f"\nin loop {_}, the length of 'org_cls_bg_md_sm_sale_train_each' is {len(org_cls_bg_md_sm_sale_train_each)}\n"
                    )
                    df = pd.DataFrame(
                        list([np.nan]) * max(len(eval_metr.columns), 21)
                    ).T
                    eval_metr = eval_metr.append(df)
            print(
                f"\nppfx(i.e. gross margin ratio):"
                f"\n{ppfx_all_valid['ppfx'].loc[:len(org_cls_bg_md_sm_sale_valid.groupby(['organ', 'class', 'bg_sort', 'md_sort', 'sm_sort']).groups.keys()) - 1]}\n"
                f"\neval_metr:\n{eval_metr}"
            )

            # 注意 df.columns=[] 与 df.reindex 的区别，前者是重新赋列名，后者是改变列的顺序。
            eval_metr.columns = [
                "alpha(%)",
                "AA(%)",
                "MAPE",
                "SMAPE",
                "RMSPE",
                "MTD_p2",
                "EMLAE",
                "MALE",
                "MAE",
                "RMSE",
                "MedAE",
                "MTD_p1",
                "MSE",
                "MSLE",
                "VAR",
                "R2",
                "PR",
                "SR",
                "KT",
                "WT",
                "MGC",
            ]
            # eval_metr.index = np.arange(len(eval_metr))
            eval_metr.index = ppfx_all_valid[: len(eval_metr)].index
            eval_ppfx_all = pd.concat(
                [eval_metr, ppfx_all_valid[: len(eval_metr)]], axis=1, join="inner"
            )
            eval_ppfx_all = eval_ppfx_all.reindex(
                columns=list(eval_ppfx_all.columns[:2])
                + list(eval_ppfx_all.columns[-12:])
                + list(eval_ppfx_all.columns[2:-12])
            )
            eval_ppfx_all.rename(columns={"ppfx": "ppfx(%)"}, inplace=True)
            eval_ppfx_all["class"].replace(
                to_replace=["蔬菜课", "肉课", "水果课", "面包课", "水产课"],
                value=["Vegetable", "Meat", "Fruit", "Bread", "Aquatic"],
                inplace=True,
            )
            eval_ppfx_all[["alpha(%)", "AA(%)", "ppfx(%)"]] = (
                eval_ppfx_all[["alpha(%)", "AA(%)", "ppfx(%)"]] * multiplier
            )
            eval_ppfx_all["GrossMargin(%)"] = eval_ppfx_all["GrossMargin(%)"].round(0)
            eval_ppfx_all_seg = eval_ppfx_all[
                (eval_ppfx_all["ppfx(%)"] >= -10 * multiplier)
                & (eval_ppfx_all["ppfx(%)"] <= 10 * multiplier)
                & (eval_ppfx_all["alpha(%)"] >= -100 * multiplier)
                & (eval_ppfx_all["alpha(%)"] <= 100 * multiplier)
            ]  # to overlap upper samples in 'alpha'
            eval_ppfx_all_seg_no = eval_ppfx_all_seg.drop(
                columns=["bg_sort_name", "md_sort_name", "sm_sort_name", "name"]
            )

        else:
            for _ in range(
                len(
                    org_cls_bg_md_sm_cd_sale_valid.groupby(
                        ["organ", "class", "bg_sort", "md_sort", "sm_sort", "code"]
                    ).groups.keys()
                )
            ):
                org_cls_bg_md_sm_cd_sale_train_each = org_cls_bg_md_sm_cd_sale_train[
                    (
                        org_cls_bg_md_sm_cd_sale_train[
                            ["organ", "class", "bg_sort", "md_sort", "sm_sort", "code"]
                        ]
                        == list(
                            org_cls_bg_md_sm_cd_sale_valid.groupby(
                                [
                                    "organ",
                                    "class",
                                    "bg_sort",
                                    "md_sort",
                                    "sm_sort",
                                    "code",
                                ]
                            ).groups.keys()
                        )[_]
                    ).sum(axis=1)
                    == len(["organ", "class", "bg_sort", "md_sort", "sm_sort", "code"])
                ]["amount"]
                org_cls_bg_md_sm_cd_sale_valid_each = org_cls_bg_md_sm_cd_sale_valid[
                    (
                        org_cls_bg_md_sm_cd_sale_valid[
                            ["organ", "class", "bg_sort", "md_sort", "sm_sort", "code"]
                        ]
                        == list(
                            org_cls_bg_md_sm_cd_sale_valid.groupby(
                                [
                                    "organ",
                                    "class",
                                    "bg_sort",
                                    "md_sort",
                                    "sm_sort",
                                    "code",
                                ]
                            ).groups.keys()
                        )[_]
                    ).sum(axis=1)
                    == len(["organ", "class", "bg_sort", "md_sort", "sm_sort", "code"])
                ]["theory_sale"]
                org_cls_bg_md_sm_cd_pred_each = org_cls_bg_md_sm_cd_pred_valid[
                    (
                        org_cls_bg_md_sm_cd_pred_valid[
                            ["organ", "class", "bg_sort", "md_sort", "sm_sort", "code"]
                        ]
                        == list(
                            org_cls_bg_md_sm_cd_pred_valid.groupby(
                                [
                                    "organ",
                                    "class",
                                    "bg_sort",
                                    "md_sort",
                                    "sm_sort",
                                    "code",
                                ]
                            ).groups.keys()
                        )[_]
                    ).sum(axis=1)
                    == len(["organ", "class", "bg_sort", "md_sort", "sm_sort", "code"])
                ]["predict"]

                try:
                    # obtain the ralative accuracy of ['organ', 'class', 'bg_sort', 'md_sort', 'sm_sort', , 'code']
                    f = fitter.Fitter(
                        org_cls_bg_md_sm_cd_sale_train_each,
                        distributions="gamma",
                        timeout=10,
                    )
                    f.fit()
                    ppfx_train = ppfx_all_train[
                        np.sum(
                            ppfx_all_train[["organ", "code"]]
                            == ppfx_all_valid[
                                ppfx_all_valid.index
                                == len(org_sale_valid.groupby("organ").groups.keys())
                                + len(
                                    org_cls_sale_valid.groupby(
                                        ["organ", "class"]
                                    ).groups.keys()
                                )
                                + len(
                                    org_cls_bg_sale_valid.groupby(
                                        ["organ", "class", "bg_sort"]
                                    ).groups.keys()
                                )
                                + len(
                                    org_cls_bg_md_sale_valid.groupby(
                                        ["organ", "class", "bg_sort", "md_sort"]
                                    ).groups.keys()
                                )
                                + len(
                                    org_cls_bg_md_sm_sale_valid.groupby(
                                        [
                                            "organ",
                                            "class",
                                            "bg_sort",
                                            "md_sort",
                                            "sm_sort",
                                        ]
                                    ).groups.keys()
                                )
                                + _
                            ][["organ", "code"]].values,
                            axis=1,
                        )
                        == 2
                    ]["ppfx"]
                    org_cls_bg_md_sm_cd_news_each = st.gamma.ppf(
                        ppfx_train, *f.fitted_param["gamma"]
                    )
                    alpha = (
                        (org_cls_bg_md_sm_cd_pred_each - org_cls_bg_md_sm_cd_news_each)
                        / (
                            org_cls_bg_md_sm_cd_sale_valid_each
                            - org_cls_bg_md_sm_cd_news_each
                        )
                    ).median()
                    # calculate evaluation metrics between predict and theory_sale
                    res = ref.regression_evaluation_single(
                        y_true=org_cls_bg_md_sm_cd_sale_valid_each,
                        y_pred=org_cls_bg_md_sm_cd_pred_each,
                    )
                    accu_sin = ref.accuracy_single(
                        y_true=org_cls_bg_md_sm_cd_sale_valid_each,
                        y_pred=org_cls_bg_md_sm_cd_pred_each,
                    )
                    df = round(
                        pd.DataFrame(
                            list([alpha]) + list([accu_sin]) + list(res[:-2])
                        ).T,
                        decim,
                    )
                    eval_metr = eval_metr.append(df)
                except:
                    print(
                        f"\nin loop {_}, the length of 'org_cls_bg_md_sm_cd_sale_train_each' is {len(org_cls_bg_md_sm_cd_sale_train_each)}\n"
                    )
                    df = pd.DataFrame(
                        list([np.nan]) * max(len(eval_metr.columns), 21)
                    ).T
                    eval_metr = eval_metr.append(df)

            print(
                f"\nppfx(i.e. gross margin ratio):"
                f"\n{ppfx_all_valid['ppfx'].loc[:len(org_cls_bg_md_sm_cd_sale_valid.groupby(['organ', 'class', 'bg_sort', 'md_sort', 'sm_sort', 'code']).groups.keys()) - 1]}\n"
                f"\neval_metr:\n{eval_metr}"
            )

            eval_metr.columns = [
                "alpha(%)",
                "AA(%)",
                "MAPE",
                "SMAPE",
                "RMSPE",
                "MTD_p2",
                "EMLAE",
                "MALE",
                "MAE",
                "RMSE",
                "MedAE",
                "MTD_p1",
                "MSE",
                "MSLE",
                "VAR",
                "R2",
                "PR",
                "SR",
                "KT",
                "WT",
                "MGC",
            ]
            eval_metr.index = ppfx_all_valid[-len(eval_metr) :].index
            # pd.concat execute join by the same index, if axis=1
            eval_ppfx_all_cd = pd.concat(
                [eval_metr, ppfx_all_valid[-len(eval_metr) :]], axis=1, join="inner"
            )
            eval_ppfx_all_cd = eval_ppfx_all_cd.reindex(
                columns=list(eval_ppfx_all_cd.columns[:2])
                + list(eval_ppfx_all_cd.columns[-12:])
                + list(eval_ppfx_all_cd.columns[2:-12])
            )
            eval_ppfx_all_cd.rename(columns={"ppfx": "ppfx(%)"}, inplace=True)
            eval_ppfx_all_cd["class"].replace(
                to_replace=["蔬菜课", "肉课", "水果课", "面包课", "水产课"],
                value=["Vegetable", "Meat", "Fruit", "Bread", "Aquatic"],
                inplace=True,
            )
            eval_ppfx_all_cd[["alpha(%)", "AA(%)", "ppfx(%)"]] = (
                eval_ppfx_all_cd[["alpha(%)", "AA(%)", "ppfx(%)"]] * multiplier
            )
            eval_ppfx_all_cd["GrossMargin(%)"] = eval_ppfx_all_cd[
                "GrossMargin(%)"
            ].round(0)

            i = 4  # '4' means the 4th index of eval_ppfx_all_cd.columns, i.e. 'organ'
            column_name = list()
            df = pd.DataFrame()
            for _ in range(
                5
            ):  # '5' means 5 hierarchies which are: 'organ', 'class', 'bg_sort', 'md_sort', 'sm_sort'
                column_name.append(eval_ppfx_all_cd.columns[i])
                df = df.append(
                    eval_ppfx_all_cd.groupby(column_name, as_index=False).median()
                )
                if i < 6:
                    i += 1
                else:
                    i += 2
            df = df.append(eval_ppfx_all_cd)
            eval_ppfx_all = df
            eval_ppfx_all = eval_ppfx_all.reindex(
                columns=[
                    "alpha(%)",
                    "AA(%)",
                    "ppfx(%)",
                    "GrossMargin(%)",
                    "organ",
                    "class",
                    "bg_sort",
                    "bg_sort_name",
                    "md_sort",
                    "md_sort_name",
                    "sm_sort",
                    "sm_sort_name",
                    "code",
                    "name",
                    "MAPE",
                    "SMAPE",
                    "RMSPE",
                    "MTD_p2",
                    "EMLAE",
                    "MALE",
                    "MAE",
                    "RMSE",
                    "MedAE",
                    "MTD_p1",
                    "MSE",
                    "MSLE",
                    "VAR",
                    "R2",
                    "PR",
                    "SR",
                    "KT",
                    "WT",
                    "MGC",
                ]
            )

            eval_ppfx_all.to_csv(
                f"D:\Work info\WestUnion\data\processed\\{organ}\\"
                f"eval_ppfx_all__code_processed_{code_processed}_range{acct_pri_range}_{datetime.date.today()}.csv",
                encoding="utf_8_sig",
            )
            eval_ppfx_all_seg = eval_ppfx_all[
                (eval_ppfx_all["ppfx(%)"] >= -10 * multiplier)
                & (eval_ppfx_all["ppfx(%)"] <= 10 * multiplier)
                & (eval_ppfx_all["alpha(%)"] >= -100 * multiplier)
                & (eval_ppfx_all["alpha(%)"] <= 100 * multiplier)
            ]
            if len(eval_ppfx_all) != len(ppfx_all_valid):
                raise Exception(
                    "alpha中元素的顺序与ppfx_all中行的顺序不匹配，即alpha与ppfx,GrossMargin(%)的对应关系错误，结果不可用"
                )
            eval_ppfx_all_seg_no = eval_ppfx_all_seg.drop(
                columns=["bg_sort_name", "md_sort_name", "sm_sort_name", "name"]
            )
            eval_ppfx_all_seg_no.to_excel(
                f"D:\Work info\WestUnion\data\processed\\{organ}\\"
                f"eval_ppfx_all_seg_no__code_processed_{code_processed}_range{acct_pri_range}_{datetime.date.today()}.xlsx",
                encoding="utf_8_sig",
                sheet_name="Metrics",
                index_label="index",
            )

        # 按顺序分别观察4个指标：alpha(%), AA(%), ppfx(%), profit(%) 的分布
        for _ in range(4):
            f = fitter.Fitter(
                eval_ppfx_all_seg[eval_ppfx_all_seg.columns[_]], distributions="common"
            )
            f.fit()
            print(f"\n{f.summary()}\n")
            name = list(f.get_best().keys())[0]
            print(f"最接近的分布: {name}" "\n")
            f.plot_pdf()
            plt.xlabel(f"{eval_ppfx_all_seg.columns[_]}")
            plt.ylabel("概率")
            plt.title("常见分布对真实值的拟合")
            plt.show()
            plt.plot(f.x, f.y, "b-.", label="真实值")
            plt.plot(f.x, f.fitted_pdf[name], "r-", label="概率密度函数的拟合值")
            plt.xlabel(f"{eval_ppfx_all_seg.columns[_]}")
            plt.ylabel("概率")
            plt.title(name)
            plt.legend()
            plt.show()

        # sparate the infomation of six hirarchies
        ppfx_org = eval_ppfx_all_seg[pd.isnull(eval_ppfx_all_seg["class"])].dropna(
            axis=1
        )
        ppfx_cls = eval_ppfx_all_seg[
            pd.notnull(eval_ppfx_all_seg["class"])
            & pd.isnull(eval_ppfx_all_seg["bg_sort"])
        ].dropna(axis=1)
        ppfx_bg = eval_ppfx_all_seg[
            pd.notnull(eval_ppfx_all_seg["bg_sort"])
            & pd.isnull(eval_ppfx_all_seg["md_sort"])
        ].dropna(axis=1)
        ppfx_md = eval_ppfx_all_seg[
            pd.notnull(eval_ppfx_all_seg["md_sort"])
            & pd.isnull(eval_ppfx_all_seg["sm_sort"])
        ].dropna(axis=1)
        ppfx_sm = eval_ppfx_all_seg[
            pd.notnull(eval_ppfx_all_seg["sm_sort"])
            & pd.isnull(eval_ppfx_all_seg["code"])
        ].dropna(axis=1)
        ppfx_cd = eval_ppfx_all_seg[pd.notnull(eval_ppfx_all_seg["code"])].dropna(
            axis=1
        )
        ppfx_scater = pd.concat(
            [
                ppfx_org[["alpha(%)", "GrossMargin(%)"]],
                ppfx_cls[["alpha(%)", "GrossMargin(%)"]],
                ppfx_bg[["alpha(%)", "GrossMargin(%)"]],
                ppfx_md[["alpha(%)", "GrossMargin(%)"]],
                ppfx_sm[["alpha(%)", "GrossMargin(%)"]],
                ppfx_cd[["alpha(%)", "GrossMargin(%)"]],
            ],
            axis=1,
        )

        # plot the scatter of 'ppfx' and 'alpha' within six hierarchies
        i = 4
        for _ in range(0, len(ppfx_scater.columns), 2):
            if _ != len(ppfx_scater.columns) - 2:
                plt.scatter(x=ppfx_scater.iloc[:, _ + 1], y=ppfx_scater.iloc[:, _])
                plt.xlim(0, multiplier * 1.1)
                if (ppfx_scater.iloc[:, _].max() < multiplier) & (
                    ppfx_scater.iloc[:, _].min() > 0
                ):
                    plt.ylim(0, multiplier)
                    plt.yticks(
                        np.arange(0, multiplier + 1, step=10)
                    )  # 以每10间隔显示y坐标
                else:
                    plt.yticks(
                        np.arange(
                            np.floor(ppfx_scater.iloc[:, _].min()),
                            np.ceil(ppfx_scater.iloc[:, _].max()),
                            step=20,
                        )
                    )  # 以每20间隔显示y坐标
                plt.xlabel("Gross Margin: 毛利率(%)")
                plt.ylabel("Relative Accuracy: 相对权重(%)")
                plt.title(f"{eval_ppfx_all_seg_no.columns[i]}", fontsize=14)
                i += 1
                ax = plt.gca()  # 获得坐标轴的句柄
                ax.xaxis.set_major_locator(
                    plt.MultipleLocator(multiplier / 10)
                )  # 以每10间隔显示x坐标
                plt.show()
            else:
                plt.scatter(x=ppfx_scater.iloc[:, _ + 1], y=ppfx_scater.iloc[:, _])
                plt.xlim(0, multiplier * 1.5)
                if (ppfx_scater.iloc[:, _].max() < multiplier) & (
                    ppfx_scater.iloc[:, _].min() > 0
                ):
                    plt.ylim(0, multiplier)
                    plt.yticks(
                        np.arange(0, multiplier + 1, step=10)
                    )  # 以每10间隔显示y坐标
                else:
                    plt.yticks(
                        np.arange(
                            np.floor(ppfx_scater.iloc[:, _].min()),
                            np.ceil(ppfx_scater.iloc[:, _].max()),
                            step=50,
                        )
                    )  # 以每50间隔显示y坐标
                plt.xlabel("Gross Margin: 毛利率(%)")
                plt.ylabel("Relative Accuracy: 相对权重(%)")
                plt.title(f"{eval_ppfx_all_seg_no.columns[i]}", fontsize=14)
                i += 1
                ax = plt.gca()  # 获得坐标轴的句柄
                ax.xaxis.set_major_locator(
                    plt.MultipleLocator(multiplier / 10)
                )  # 以每10间隔显示x坐标
                plt.show()

        fig = plt.figure()
        df_box = ppfx_org[["alpha(%)", "GrossMargin(%)", "organ", "AA(%)"]]
        df_box = df_box.melt(id_vars="organ")
        bp = sns.boxplot(
            data=df_box,
            x="variable",
            y="value",
            hue="organ",
            hue_order=["B", "C", "D"],
            order=["GrossMargin(%)", "alpha(%)", "AA(%)"],
            showfliers=False,
            fliersize=4.5,
            flierprops={
                "marker": "o",  # 异常值形状
            },
            whiskerprops={"linestyle": "--", "color": "black"},  # 设置上下须属性
            showmeans=True,  # 箱图显示均值，
            meanprops={"marker": "D", "markerfacecolor": "red"},  # 设置均值属性
        )
        plt.xticks(
            [0, 1, 2], ["毛利率(%)", "相对权重(%)", "绝对精度(%)"]
        )  # 按位置顺序0,1,2给x轴的变量命名
        plt.title("门店层级")
        ax = plt.gca()
        ax.yaxis.set_major_locator(
            plt.MultipleLocator(multiplier / 10)
        )  # 以每(multiplier / 10)间隔显示
        bp.set(xlabel=None)
        bp.set(ylabel=None)
        adjust_box_widths(fig)
        f = plt.gcf()
        fmt = ["svg", "png", "pdf"]
        for _ in range(len(fmt)):
            f.savefig(
                f"D:\Work info\WestUnion\data\processed\\{organ}\\boxplot_md.{fmt[_]}"
            )
        plt.show()
        f.clear()

        hierachy = [ppfx_cls, ppfx_bg, ppfx_md, ppfx_sm, ppfx_cd]
        title = ["课别", "大分类", "中分类", "小分类", "单品"]
        for _ in range(len(hierachy)):
            fig = plt.figure()
            # df_box = ppfx_cd[(ppfx_cd['class'] == 'Fruit') | (ppfx_cd['class'] == 'Vegetable')][['alpha(%)', 'ppfx(%)', 'class']]
            df_box = hierachy[_][["alpha(%)", "GrossMargin(%)", "class", "AA(%)"]]
            df_box = df_box.melt(id_vars="class")
            bp = sns.boxplot(
                data=df_box,
                x="variable",
                y="value",
                hue="class",
                hue_order=["Vegetable", "Fruit", "Aquatic"],
                order=["GrossMargin(%)", "alpha(%)", "AA(%)"],
                showfliers=False,
                fliersize=4.5,
                # palette=palettable.tableau.TrafficLight_9.mpl_colors,
                flierprops={
                    "marker": "o",  # 异常值形状
                    # 'markerfacecolor': 'red',  # 形状填充色
                },
                whiskerprops={"linestyle": "--", "color": "black"},  # 设置上下须属性
                showmeans=True,  # 箱图显示均值，
                meanprops={"marker": "D", "markerfacecolor": "red"},  # 设置均值属性
            )
            plt.xticks(
                [0, 1, 2], ["毛利率(%)", "相对权重(%)", "绝对精度(%)"]
            )  # 按位置顺序0,1,2给x轴的变量命名
            # if code_processed is True:
            #     plt.ylim(0, multiplier)
            plt.title(f"{title[_]}层级")
            ax = plt.gca()  # 获得坐标轴的句柄
            ax.yaxis.set_major_locator(
                plt.MultipleLocator(multiplier / 5)
            )  # 以每(multiplier / 5)间隔显示
            bp.set(xlabel=None)
            bp.set(ylabel=None)
            adjust_box_widths(fig)
            f = plt.gcf()  # 获取当前图像
            fmt = ["svg", "png", "pdf"]
            for _ in range(len(fmt)):
                f.savefig(
                    f"D:\Work info\WestUnion\data\processed\\{organ}\\boxplot_cd.{fmt[_]}"
                )
            plt.show()
            f.clear()  # 先画图plt.show，再释放内存
