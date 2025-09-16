import streamlit as st
from datetime import datetime, date
import db_supabase as db

# --- ページ設定 ---
st.set_page_config(page_title="割り勘アプリ", page_icon="💸", layout="wide")

# --- カスタムCSS ---
st.markdown("""
<style>
    .result-box {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 1.5rem;
        margin-top: 1rem;
        border-left: 6px solid #4CAF50;
    }
    .result-text {
        font-size: 1.5rem;
        font-weight: bold;
        color: #333;
    }
</style>
""", unsafe_allow_html=True)

# --- 関数定義 ---
def calculate_warikan(items):
    """立替額と負担額を計算する関数"""
    tatekae_yu = 0
    tatekae_mi = 0
    futan_yu = 0
    futan_mi = 0

    for item in items:
        price = item['price']
        payer = item.get('payer') # DBにpayerがない古いデータも考慮
        paid_by_yu = bool(item['paid_by_yu'])
        paid_by_mi = bool(item['paid_by_mi'])

        # 立替額を計算
        if payer == 'ゆー':
            tatekae_yu += price
        elif payer == 'みー':
            tatekae_mi += price

        # 負担額を計算
        if paid_by_yu and paid_by_mi:
            futan_yu += price / 2
            futan_mi += price / 2
        elif paid_by_yu:
            futan_yu += price
        elif paid_by_mi:
            futan_mi += price
            
    return tatekae_yu, tatekae_mi, futan_yu, futan_mi

def display_seisan_result(futan_yu, tatekae_yu, futan_mi, tatekae_mi, context_text=""):
    """精算結果を表示する関数"""
    seisan_yu = futan_yu - tatekae_yu
    seisan_mi = futan_mi - tatekae_mi

    if seisan_mi > 0:
        amount = round(seisan_mi)
        st.info(f"{context_text}みー は ゆー に ¥{amount:,} 支払います。")
    elif seisan_yu > 0:
        amount = round(seisan_yu)
        st.info(f"{context_text}ゆー は みー に ¥{amount:,} 支払います。")
    else:
        st.info(f"{context_text}支払いはありません。")

# --- ヘッダー ---
st.title("💸 割り勘アプリ")
st.markdown("---")

# --- 明細入力フォーム ---
entry_date = st.date_input("📅 日付", datetime.now().date())
with st.form("item_form", clear_on_submit=True):
    payer = st.radio("実際に支払った人", ("ゆー", "みー"), horizontal=True)
    col1, col2 = st.columns([2, 1])
    with col1:
        item_name = st.text_input("項目名", placeholder="例: ランチ")
    with col2:
        item_price = st.number_input("金額", min_value=0, step=100)
    
    submitted = st.form_submit_button("項目を追加")
    if submitted and item_name and item_price > 0:
        db.add_item(entry_date, item_name, item_price, payer)
        st.experimental_rerun()

# --- 期間を指定して集計 ---
st.markdown("### 🗓️ 期間を指定して集計")
all_items_for_range = db.get_all_items()
if all_items_for_range:
    try:
        min_date = min([datetime.strptime(item['entry_date'], '%Y-%m-%d').date() for item in all_items_for_range])
        max_date = max([datetime.strptime(item['entry_date'], '%Y-%m-%d').date() for item in all_items_for_range])

        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("開始日", min_date, min_value=min_date, max_value=max_date)
        with col2:
            end_date = st.date_input("終了日", max_date, min_value=min_date, max_value=max_date)

        if st.button("この期間で集計"):
            range_items = db.get_items_by_date_range(start_date, end_date)
            if range_items:
                t_yu, t_mi, f_yu, f_mi = calculate_warikan(range_items)
                st.markdown(f"**{start_date}〜{end_date}の集計**")
                st.write(f"ゆー: 立替 ¥{t_yu:,.0f}, 負担 ¥{f_yu:,.0f}")
                st.write(f"みー: 立替 ¥{t_mi:,.0f}, 負担 ¥{f_mi:,.0f}")
                display_seisan_result(f_yu, t_yu, f_mi, t_mi, context_text="この期間では、")
            else:
                st.warning("指定された期間にデータはありませんでした。")
    except (ValueError, TypeError):
        st.info("まだ履歴データがありません。")

# --- 履歴リスト ---
all_items = db.get_all_items()
if all_items:
    st.markdown("### 📝 履歴リスト")
    items_by_date = {}
    for item in all_items:
        date_str = item['entry_date']
        if date_str not in items_by_date:
            items_by_date[date_str] = []
        items_by_date[date_str].append(item)

    for date_str, items_in_date in sorted(items_by_date.items(), reverse=True):
        with st.expander(f"**{date_str}** の明細", expanded=True):
            for item in items_in_date:
                item_id = item['id']
                paid_by_yu = bool(item['paid_by_yu'])
                paid_by_mi = bool(item['paid_by_mi'])
                payer_text = f" (支払: {item.get('payer', '不明')})"

                col1, col2, col3, col4, col5 = st.columns([3, 2, 1, 1, 1])
                with col1:
                    st.write(f"**{item['name']}**{payer_text}")
                with col2:
                    st.write(f"¥{item['price']:,}")
                with col3:
                    new_paid_by_yu = st.checkbox("ゆー", value=paid_by_yu, key=f"yu_{item_id}")
                with col4:
                    new_paid_by_mi = st.checkbox("みー", value=paid_by_mi, key=f"mi_{item_id}")
                with col5:
                    if st.button("削除", key=f"del_{item_id}"):
                        db.delete_item(item_id)
                        st.experimental_rerun()

                if new_paid_by_yu != paid_by_yu or new_paid_by_mi != paid_by_mi:
                    db.update_payment(item_id, new_paid_by_yu, new_paid_by_mi)
                    st.experimental_rerun()

# --- 全体の合計と清算 ---
if all_items:
    st.markdown("---")
    st.markdown("### 💰 全体合計と清算")

    tatekae_yu_all, tatekae_mi_all, futan_yu_all, futan_mi_all = calculate_warikan(all_items)

    st.markdown('<div class="result-box">', unsafe_allow_html=True)
    seisan_yu_all = futan_yu_all - tatekae_yu_all
    seisan_mi_all = futan_mi_all - tatekae_mi_all

    if seisan_mi_all > 0:
        amount = round(seisan_mi_all)
        st.markdown(f'<p class="result-text">みー は ゆー に ¥{amount:,} 支払います。</p>', unsafe_allow_html=True)
    elif seisan_yu_all > 0:
        amount = round(seisan_yu_all)
        st.markdown(f'<p class="result-text">ゆー は みー に ¥{amount:,} 支払います。</p>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="result-text">支払いはありません。</p>', unsafe_allow_html=True)
    
    st.write(f"ゆー: 立替総額 ¥{tatekae_yu_all:,.0f}, 負担総額 ¥{futan_yu_all:,.0f}")
    st.write(f"みー: 立替総額 ¥{tatekae_mi_all:,.0f}, 負担総額 ¥{futan_mi_all:,.0f}")
    st.markdown('</div>', unsafe_allow_html=True)