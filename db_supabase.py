import streamlit as st
from supabase import create_client, Client
from datetime import date

def get_db_connection() -> Client:
    """Supabaseへの接続クライアントを取得します。"""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def add_item(entry_date: date, name: str, price: int, payer: str):
    """新しい明細をSupabaseに追加します。"""
    supabase = get_db_connection()
    supabase.table("items").insert({
        "entry_date": entry_date.strftime("%Y-%m-%d"),
        "name": name,
        "price": price,
        "payer": payer,
        "paid_by_yu": True, # 負担者はデフォルトで両方チェック
        "paid_by_mi": True
    }).execute()

def get_all_items():
    """すべての明細をSupabaseから取得します。"""
    supabase = get_db_connection()
    response = supabase.table("items").select("*").order("entry_date", desc=True).order("id", desc=True).execute()
    return response.data

def update_payment(item_id: int, paid_by_yu: bool, paid_by_mi: bool):
    """支払い担当者の情報を更新します。"""
    supabase = get_db_connection()
    supabase.table("items").update({
        "paid_by_yu": paid_by_yu,
        "paid_by_mi": paid_by_mi
    }).eq("id", item_id).execute()

def delete_item(item_id: int):
    """指定されたIDの明細を削除します。"""
    supabase = get_db_connection()
    supabase.table("items").delete().eq("id", item_id).execute()

def get_items_by_date_range(start_date: date, end_date: date):
    """指定された期間内のすべての明細を取得します。"""
    supabase = get_db_connection()
    response = supabase.table("items").select("*") \
        .gte("entry_date", start_date.strftime("%Y-%m-%d")) \
        .lte("entry_date", end_date.strftime("%Y-%m-%d")) \
        .execute()
    return response.data