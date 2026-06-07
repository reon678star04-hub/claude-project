import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import pickle
import json
import time
from pathlib import Path
import plotly.graph_objects as go

st.set_page_config(page_title="ネットキャッシュ比率スクリーナー", layout="wide")
st.title("🇯🇵 日本株 ネットキャッシュ比率スクリーナー")
st.caption("ネットキャッシュ = 流動資産 + 投資有価証券×70% − 負債合計　｜　ネットキャッシュ比率 = ネットキャッシュ ÷ 時価総額")

# --- 設定サイドバー ---
st.sidebar.header("設定")
threshold = st.sidebar.slider("ネットキャッシュ比率の閾値", 0.0, 5.0, 1.0, 0.1)
market_options = {
    "全市場（プライム＋スタンダード＋グロース）": None,
    "プライムのみ": ["プライム（内国株式）"],
    "プライム＋スタンダード": ["プライム（内国株式）", "スタンダード（内国株式）"],
}
market_label = st.sidebar.selectbox("対象市場", list(market_options.keys()))
target_markets = market_options[market_label]

sleep_sec = st.sidebar.number_input("リクエスト間隔（秒）", 0.1, 3.0, 0.5, 0.1,
                                     help="小さいほど速いが、レートリミットに引っかかりやすい")

st.sidebar.divider()
st.sidebar.header("テスト・確認")
test_mode = st.sidebar.checkbox("テストモード（少数銘柄のみ取得）")
test_count = st.sidebar.number_input("取得銘柄数", 5, 200, 20, 5, disabled=not test_mode)
show_cached = st.sidebar.button("📂 取得済みデータだけで結果を見る")

JPX_URL = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"
LOCAL_XLS = "data_j.xls"
CACHE_FILE = "net_cash_cache.pkl"
MEMO_FILE = "memo.json"

CURRENT_ASSETS_KEYS = ["Current Assets", "Total Current Assets", "CurrentAssets"]
INVEST_SEC_KEYS = [
    "Available For Sale Securities", "Long Term Investments",
    "Investmentin Financial Assets", "Other Investments",
    "Investment Securities", "Investments And Advances",
]
TOTAL_LIAB_KEYS = [
    "Total Liabilities Net Minority Interest", "Total Liab",
    "Total Liabilities", "TotalLiabilitiesNetMinorityInterest",
]


def get_value(df, candidates):
    for name in candidates:
        if name in df.index:
            val = df.loc[name].iloc[0]
            if pd.notna(val):
                return float(val)
    return None


def get_history(bs, candidates):
    """全年度の値をSeriesで返す（グラフ用）"""
    for name in candidates:
        if name in bs.index:
            row = bs.loc[name]
            if row.notna().any():
                return row.dropna().sort_index()
    return pd.Series(dtype=float)


@st.cache_data(show_spinner="JPX銘柄リストを取得中...")
def load_jpx():
    if not Path(LOCAL_XLS).exists():
        r = requests.get(JPX_URL, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        with open(LOCAL_XLS, "wb") as f:
            f.write(r.content)
    return pd.read_excel(LOCAL_XLS, dtype={"コード": str})


def load_cache():
    if Path(CACHE_FILE).exists():
        with open(CACHE_FILE, "rb") as f:
            return pickle.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(cache, f)


def load_memo():
    if Path(MEMO_FILE).exists():
        with open(MEMO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_memo(memo):
    with open(MEMO_FILE, "w", encoding="utf-8") as f:
        json.dump(memo, f, ensure_ascii=False, indent=2)


def fetch_one(ticker):
    try:
        stock = yf.Ticker(ticker)
        bs = stock.balance_sheet
        if bs is None or bs.empty:
            return None
        info = stock.info
        market_cap = info.get("marketCap") or info.get("market_cap")
        if not market_cap:
            return None
        current_assets = get_value(bs, CURRENT_ASSETS_KEYS)
        invest_sec = get_value(bs, INVEST_SEC_KEYS) or 0.0
        total_liab = get_value(bs, TOTAL_LIAB_KEYS)
        if current_assets is None or total_liab is None:
            return None
        return {
            "current_assets": current_assets,
            "investment_securities": invest_sec,
            "total_liabilities": total_liab,
            "market_cap": float(market_cap),
        }
    except Exception:
        return None


def show_detail_section(result_df, ticker_info, memo):
    """財務推移グラフ＋メモセクション"""
    st.divider()
    st.subheader("🔍 銘柄詳細調査")

    options = [
        f"{row['コード']} {row['銘柄名']}"
        for _, row in result_df.reset_index().iterrows()
        if '銘柄名' in result_df.columns or '銘柄名' in result_df.reset_index().columns
    ]
    if not options:
        return

    selected_label = st.selectbox("調査する銘柄を選択", options)
    selected_code = selected_label.split(" ")[0]
    selected_ticker = selected_code.zfill(4) + ".T"
    selected_name = selected_label.split(" ", 1)[1] if " " in selected_label else ""

    col_graph, col_memo = st.columns([3, 2])

    with col_graph:
        st.markdown(f"**📊 財務推移: {selected_label}**")
        with st.spinner("財務データを取得中..."):
            try:
                stock = yf.Ticker(selected_ticker)
                bs = stock.balance_sheet
                if bs is not None and not bs.empty:
                    ca_hist = get_history(bs, CURRENT_ASSETS_KEYS) / 1e8
                    is_hist = get_history(bs, INVEST_SEC_KEYS) / 1e8
                    tl_hist = get_history(bs, TOTAL_LIAB_KEYS) / 1e8

                    years = sorted(set(ca_hist.index) | set(tl_hist.index))
                    year_labels = [str(y.year) + "年" for y in years]

                    fig = go.Figure()
                    if not ca_hist.empty:
                        fig.add_trace(go.Bar(
                            x=year_labels,
                            y=[ca_hist.get(y, 0) for y in years],
                            name="流動資産",
                            marker_color="#4C9BE8",
                        ))
                    if not is_hist.empty:
                        fig.add_trace(go.Bar(
                            x=year_labels,
                            y=[is_hist.get(y, 0) for y in years],
                            name="投資有価証券",
                            marker_color="#82C4A0",
                        ))
                    if not tl_hist.empty:
                        fig.add_trace(go.Bar(
                            x=year_labels,
                            y=[tl_hist.get(y, 0) for y in years],
                            name="負債合計",
                            marker_color="#E87C4C",
                        ))

                    # NC比率の折れ線
                    nc_vals = []
                    info = stock.info
                    mc = info.get("marketCap", 0)
                    for y in years:
                        ca = ca_hist.get(y, None)
                        is_ = is_hist.get(y, 0)
                        tl = tl_hist.get(y, None)
                        if ca is not None and tl is not None and mc:
                            nc_ratio = (ca + is_ * 0.7 - tl) * 1e8 / mc
                            nc_vals.append(nc_ratio)
                        else:
                            nc_vals.append(None)

                    fig.add_trace(go.Scatter(
                        x=year_labels,
                        y=nc_vals,
                        name="NC比率",
                        yaxis="y2",
                        mode="lines+markers",
                        line=dict(color="#9B59B6", width=2),
                    ))

                    fig.update_layout(
                        barmode="group",
                        yaxis=dict(title="金額（億円）"),
                        yaxis2=dict(title="NC比率", overlaying="y", side="right"),
                        legend=dict(orientation="h", y=-0.2),
                        height=400,
                        margin=dict(t=20, b=60),
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("財務データを取得できませんでした。")
            except Exception as e:
                st.warning(f"グラフ表示エラー: {e}")

    with col_memo:
        st.markdown(f"**📝 メモ: {selected_label}**")
        current = memo.get(selected_ticker, {"rating": "未評価", "memo": ""})

        ratings = ["未評価", "◎", "○", "△", "×"]
        current_rating = current.get("rating", "未評価")
        rating_idx = ratings.index(current_rating) if current_rating in ratings else 0

        new_rating = st.radio("評価", ratings, index=rating_idx, horizontal=True)
        new_memo = st.text_area("メモ", value=current.get("memo", ""), height=180,
                                placeholder="気になる点、調査結果など...")

        if st.button("💾 保存", type="primary"):
            memo[selected_ticker] = {"rating": new_rating, "memo": new_memo}
            save_memo(memo)
            st.success("保存しました。")


def show_results(cache, tickers, ticker_info, threshold, market_col, memo):
    rows = [{"ticker": t, **d} for t, d in cache.items() if t in set(tickers)]
    if not rows:
        st.warning("表示できるデータがありません。")
        return
    df = pd.DataFrame(rows).set_index("ticker")
    df["net_cash"] = df["current_assets"] + df["investment_securities"] * 0.7 - df["total_liabilities"]
    df["net_cash_ratio"] = df["net_cash"] / df["market_cap"]
    df = df.join(ticker_info, how="left")
    result = df[df["net_cash_ratio"] > threshold].sort_values("net_cash_ratio", ascending=False)
    st.subheader(f"結果: ネットキャッシュ比率 > {threshold} の銘柄　{len(result)} 社　（集計対象: {len(df)} 社）")

    def fmt_oku(v):
        return f"{v/1e8:,.1f}" if pd.notna(v) else "-"

    show = result.reset_index()[[
        "コード", "銘柄名", market_col, "33業種区分",
        "current_assets", "investment_securities", "total_liabilities",
        "net_cash", "market_cap", "net_cash_ratio"
    ]].rename(columns={
        market_col: "市場",
        "33業種区分": "業種",
        "current_assets": "流動資産(億)",
        "investment_securities": "投資有価証券(億)",
        "total_liabilities": "負債合計(億)",
        "net_cash": "ネットキャッシュ(億)",
        "market_cap": "時価総額(億)",
        "net_cash_ratio": "NC比率",
    })
    for col in ["流動資産(億)", "投資有価証券(億)", "負債合計(億)", "ネットキャッシュ(億)", "時価総額(億)"]:
        show[col] = show[col].apply(fmt_oku)
    show["NC比率"] = show["NC比率"].apply(lambda x: f"{x:.2f}")

    # メモ・評価列を追加
    show["評価"] = show["コード"].apply(
        lambda c: memo.get(c.zfill(4) + ".T", {}).get("rating", "")
    )
    show["メモ"] = show["コード"].apply(
        lambda c: memo.get(c.zfill(4) + ".T", {}).get("memo", "")
    )

    st.dataframe(show, use_container_width=True, hide_index=True)
    csv = result.reset_index().to_csv(index=False, encoding="utf-8-sig")
    st.download_button("📥 CSVでダウンロード", csv, "net_cash_result.csv", "text/csv")

    show_detail_section(result, ticker_info, memo)


# --- メイン ---
jpx_df = load_jpx()
market_col = "市場・商品区分"

if target_markets:
    filtered = jpx_df[jpx_df[market_col].isin(target_markets)].copy()
else:
    filtered = jpx_df[jpx_df[market_col].str.contains("内国株式", na=False)].copy()

filtered["ticker"] = filtered["コード"].str.zfill(4) + ".T"
tickers = filtered["ticker"].tolist()
ticker_info = filtered.set_index("ticker")[["コード", "銘柄名", market_col, "33業種区分"]].copy()

cache = load_cache()
memo = load_memo()
st.info(f"対象銘柄数: **{len(tickers)}** 社　｜　キャッシュ済み: **{len(cache)}** 社")

# 取得済みデータだけで結果表示
if show_cached:
    show_results(cache, tickers, ticker_info, threshold, market_col, memo)

elif st.button("🔍 スクリーニング開始", type="primary"):
    remaining = [t for t in tickers if t not in cache]
    if test_mode:
        remaining = remaining[:int(test_count)]
        st.info(f"テストモード: {len(remaining)} 社のみ取得します")

    if remaining:
        st.warning(f"未取得の銘柄が {len(remaining)} 社あります。取得中...（中断しても途中から再開できます）")
        progress = st.progress(0, text="取得中...")
        status = st.empty()
        failed = []

        for i, ticker in enumerate(remaining):
            result = fetch_one(ticker)
            if result:
                cache[ticker] = result
            else:
                failed.append(ticker)

            time.sleep(sleep_sec)

            pct = (i + 1) / len(remaining)
            progress.progress(pct, text=f"{i+1}/{len(remaining)} 取得中: {ticker}")

            if (i + 1) % 100 == 0:
                save_cache(cache)

        save_cache(cache)
        status.success(f"取得完了！成功: {len(cache)} 社 / 失敗: {len(failed)} 社")
    else:
        st.success("全銘柄がキャッシュ済みです。")

    show_results(cache, tickers, ticker_info, threshold, market_col, memo)
