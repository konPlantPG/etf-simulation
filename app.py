from datetime import datetime, timedelta

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf



def remove_all_zero_col(df):
    """全て0の列を削除"""
    df = df.copy()
    for col in df.columns:
        if (df[col] == 0).all():
            df.drop(col, axis=1, inplace=True)
    return df


def get_data(months, tickers, column):
    df = pd.DataFrame()
    for company in tickers.keys():
        tkr = yf.Ticker(tickers[company])
        hist = tkr.history(period=f'{months}mo')
        hist = hist[[column]]
        hist.columns = [company]
        hist = hist.T
        hist.index.name ='Name'
        df = pd.concat([df, hist])
    return df


def calc_value(data, data_income, companies):

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        option1 = st.selectbox(
            label="年",
                options=data['Date'].dt.year.drop_duplicates().sort_values(ascending=False))
    with col2:
        option2 = st.selectbox(
            label="月",
                options=data['Date'].dt.month.drop_duplicates())
    with col3:
        option3 = st.selectbox(
            label="日",
                options=data['Date'].dt.day.drop_duplicates().sort_values())
    with col4:
        option4 = st.selectbox(
            label="ETF",
                options=companies
        )
    with col5:
        option5 = st.selectbox(
            label="個数",
                options=list(range(1,1000+1))
        )

    
    #日付計算
    date_str = str(option1)+"-"+str(option2)+"-"+str(option3)
    datetime_type = datetime.strptime(date_str, '%Y-%m-%d')

    #配当金の計算
    data_div = data_income[data_income["Date"].dt.date>datetime_type.date()]
    data_div = data_div[data_div["Name"]==option4]
    data_div= data_div['Dividend(USD)'].sum()*option5

    
    #投資した時の価値の計算
    data_dt = data[data["Date"].dt.date==datetime_type.date()]
    dt_prices= data_dt[data_dt["Name"]==option4]['Prices(USD)']
    investment = dt_prices.iloc[0]*option5

    #現在の価値の計算
    today = datetime.strptime((datetime.now() - timedelta(1)).strftime('%Y-%m-%d'), '%Y-%m-%d').date()
    data_today = data[data["Date"].dt.date==today]
    dt_prices_today= data_today[data_today["Name"]==option4]['Prices(USD)']
   

    if dt_prices_today.empty:
        today = datetime.strptime((datetime.now() - timedelta(2)).strftime('%Y-%m-%d'), '%Y-%m-%d').date()
        data_today = data[data["Date"].dt.date==today]
        dt_prices_today= data_today[data_today["Name"]==option4]['Prices(USD)']
        
        if dt_prices_today.empty:
            today = datetime.strptime((datetime.now() - timedelta(3)).strftime('%Y-%m-%d'), '%Y-%m-%d').date()
            data_today = data[data["Date"].dt.date==today]
            dt_prices_today= data_today[data_today["Name"]==option4]['Prices(USD)']

    investment_today = dt_prices_today.iloc[0]* option5

    income = investment_today - investment

    
    return income, data_div



def main():
    st.title('米国ETF価格表示&シミュレーションアプリ')

    st.sidebar.write("""
    # ETF価格表示範囲
    このwebアプリはETFシミュレーションツールです。以下のオプションから日数を指定してください。
    """)

    months=st.sidebar.slider('月数', 1, 200, 60)

    st.write(f"""
    ### 過去　**{months}ヶ月の** ETFの価格
    """)

    st.sidebar.write("""
    ## ETFの価格範囲
    """)
    ymin, ymax= st.sidebar.slider(
        '範囲を指定してください',
        0.0, 600.0, (0.0, 600.0)
    )

    st.sidebar.write("""
    ## ETFの分配金範囲
    """)

    ymin_income, ymax_income= st.sidebar.slider(
        '範囲を指定してください',
        0.0, 5.0, (0.0, 5.0)
    )

    #会社の株価混ぜるかもなので、一旦キーとvaluse同じもの
    tickers={
        'VT':'VT',
        'VOO': 'VOO',
        'VTI': 'VTI',
        'QQQ': 'QQQ',
        'VYM': 'VYM',
        'HDV': 'HDV',
        'SPYD': 'SPYD'
    }

    df = get_data(months, tickers, "Close")
    companies=st.multiselect(
        'ETFを選択してください',
        list(df.index),
        ['VT', 'VOO', 'VYM']
    )

    if not companies:
        st.error('少なくとも1つETFを選択してください')
    else:
        data = df.loc[companies]
        st.write("### 価格(USD)", data.sort_index())

        #データの整形
        data = data.T.reset_index()
        data = pd.melt(data, id_vars=['Date']).rename(
            columns={'value': 'Prices(USD)'}
        )

        chart = (
            alt.Chart(data)
            .mark_line(opacity=0.8, clip=True)
            .encode(
                x="Date:T",
                y=alt.Y("Prices(USD):Q", stack=None, scale=alt.Scale(domain=[ymin, ymax])),
                color='Name:N'
            )
        )

        st.altair_chart(chart, use_container_width=True)

        #ETFの分配金
        
        df_income = get_data(months, tickers, "Dividends")
        data_income = df_income.loc[companies]
        data_income = remove_all_zero_col(data_income)
        
        st.write("### 分配金(USD)", data_income.sort_index())

        #データの整形
        data_income = data_income.T.reset_index()
        data_income = pd.melt(data_income, id_vars=['Date']).rename(
            columns={'value': 'Dividend(USD)'}
        )

        chart2 = (
            alt.Chart(data_income)
            .mark_bar(opacity=0.8, clip=True)
            .encode(
                x="Date:T",
                y=alt.Y("Dividend(USD):Q", stack=None, scale=alt.Scale(domain=[ymin_income, ymax_income])),
                color='Name:N'
            )
        )
        st.altair_chart(chart2, use_container_width=True)

        #シミュレーション部分
        st.write("### シミュレーション")
        st.write("過去にETFを購入した時現在までにいくら収益があるかの計算ができます。")
        try:
            income, div = calc_value(data, data_income, companies)

            income = round(income, 2)
            div = round(div, 2)

            st.write(f"""
            ### 今日までに
            キャピタルゲイン{income} ドルと　分配金 {div}ドルが得られます
            """)
        
        except:
            st.write("内部でエラーがおきました。過去の日付や土日・休場日を避けて入力してくださると幸いです")


        st.write("### 作者のブログ")
        link = '[工場勤務Pythonプログラマー](https://plantprogramer.com/)'
        st.markdown(link, unsafe_allow_html=True)
        

        
        

            
    

if __name__=="__main__":
    main()
