import os
import json
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = os.getenv("DATA_DIR", "Syngenta_IITM_Hackathon_2026_dataset")


def _csv_path(filename: str) -> str:
    return os.path.join(DATA_DIR, filename)


def _parse_json_column(series: pd.Series) -> pd.Series:
    def _safe_parse(val):
        if pd.isna(val) or val == "":
            return None
        if isinstance(val, (dict, list)):
            return val
        try:
            return json.loads(val)
        except Exception:
            return None
    return series.apply(_safe_parse)


def _validate(df: pd.DataFrame, name: str, required_cols: list[str]) -> pd.DataFrame:
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.warning(f"[data_loader] {name}: missing expected columns {missing}")
    return df


@st.cache_data
def load_growers() -> pd.DataFrame:
    df = pd.read_csv(_csv_path("growers.csv"))
    df["grower_crop_calendar"] = _parse_json_column(df["grower_crop_calendar"])
    df["product_scan_datetime"] = pd.to_datetime(df["product_scan_datetime"], errors="coerce")
    df["campaign_attendance_date"] = pd.to_datetime(df["campaign_attendance_date"], errors="coerce")
    df["product_scan"] = df["product_scan"].fillna(False).astype(bool)
    df["offline_campaign_attended"] = df["offline_campaign_attended"].fillna(False).astype(bool)
    _validate(df, "growers", ["grower_id", "state", "district", "tehsil", "language", "device_type", "grower_crop_calendar"])
    return df


@st.cache_data
def load_whatsapp() -> pd.DataFrame:
    df = pd.read_csv(_csv_path("whatsapp_campaign.csv"))
    df["message_sent_date"] = pd.to_datetime(df["message_sent_date"], errors="coerce")
    df["delivered_status"] = df["delivered_status"].fillna(False).astype(bool)
    df["opened_status"] = df["opened_status"].fillna(False).astype(bool)
    df["clicked_status"] = df["clicked_status"].fillna(False).astype(bool)
    _validate(df, "whatsapp", ["grower_id", "campaign_crop", "campaign_product", "delivered_status", "opened_status", "clicked_status"])
    return df


@st.cache_data
def load_retailers() -> pd.DataFrame:
    df = pd.read_csv(_csv_path("retailers.csv"))
    _validate(df, "retailers", ["retailer_id", "territory_id", "state", "district", "tehsil"])
    return df


@st.cache_data
def load_inventory() -> pd.DataFrame:
    df = pd.read_csv(_csv_path("retailer_inventory_weekly.csv"))
    df["week_end_date"] = pd.to_datetime(df["week_end_date"], errors="coerce")
    df["sku_qty"] = pd.to_numeric(df["sku_qty"], errors="coerce").fillna(0).astype(int)
    _validate(df, "inventory", ["retailer_id", "sku_name", "sku_qty", "week_end_date"])
    return df


@st.cache_data
def load_pos() -> pd.DataFrame:
    df = pd.read_csv(_csv_path("retailer_pos.csv"))
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df["sku_qty"] = pd.to_numeric(df["sku_qty"], errors="coerce").fillna(0).astype(int)
    df["sku_price"] = pd.to_numeric(df["sku_price"], errors="coerce")
    _validate(df, "pos", ["retailer_id", "sku_name", "sku_qty", "transaction_date"])
    return df


@st.cache_data
def load_reps() -> pd.DataFrame:
    df = pd.read_csv(_csv_path("reps_territory.csv"))
    df["tehsil_list"] = _parse_json_column(df["tehsil_list"])
    df["tehsil_list"] = df["tehsil_list"].apply(lambda x: x if isinstance(x, list) else [])
    _validate(df, "reps", ["rep_id", "territory_id", "state", "district", "tehsil_list"])
    return df


@st.cache_data
def load_visits() -> pd.DataFrame:
    df = pd.read_csv(_csv_path("retailer_visit_log.csv"))
    df["visit_date"] = pd.to_datetime(df["visit_date"], errors="coerce")
    _validate(df, "visits", ["rep_id", "visit_date", "territory_id", "visit_tehsil", "visit_type", "product_recommended"])
    return df


@st.cache_data
def load_digital_funnel() -> pd.DataFrame:
    df = pd.read_csv(_csv_path("digital_funnel_weekly.csv"))
    df["week_start_date"] = pd.to_datetime(df["week_start_date"], errors="coerce")
    _validate(df, "digital_funnel", ["campaign_id", "campaign_crop", "campaign_product", "social_post_impression"])
    return df
