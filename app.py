import streamlit as st
import pandas as pd
import time
import random
import string
import json
import os
import plotly.graph_objects as go
from pybit.unified_trading import HTTP
import firebase_admin
from firebase_admin import (
    credentials, firestore
)
if not firebase_admin._apps:
    fb_json = os.environ.get(
        "firebase_json", None
    )
    if fb_json:
        try:
            fb_dict = (
                json.loads(fb_json)
                if isinstance(fb_json, str)
                else fb_json
            )
            cred = credentials\
                .Certificate(fb_dict)
            firebase_admin\
                .initialize_app(cred)
        except Exception as e:
            st.error(
                f"Sync Error: "
                f"{str(e)}"
            )
            st.stop()
    else:
        if os.path.exists(
            "firebase_key.json"
        ):
            cred = credentials\
                .Certificate(
                    "firebase_key.json"
                )
            firebase_admin\
                .initialize_app(cred)
        else:
            st.error("Missing Config!")
            st.stop()

db = firestore.client()
def db_load(key, default_val):
    try:
        ref = db.collection(
            "scalper_system"
        ).document(key).get()
        if ref.exists:
            return ref.to_dict()\
                .get("data", default_val)
        return default_val
    except:
        return default_val

def db_save(key, val):
    try:
        db.collection(
            "scalper_system"
        ).document(key).set(
            {"data": val}
        )
    except:
        pass
if "init_sync" not in st.session_state:
    st._central_user_creds = \
        db_load("user_creds", {})
    st._central_key_registry = \
        db_load("key_registry", {})
    st._central_blacklist = \
        db_load("blacklist", [])
    st._license_csv_database = \
        db_load("license_csv", [])
    st._global_referral_tree = \
        db_load("referral_tree", {})
    st._global_user_pnl_history = \
        db_load("pnl_history", [])
    st._uid_to_username = \
        db_load("uid_to_user", {})
    st._mlm_bonus_enabled = \
        db_load("mlm_enabled", True)
    st._mlm_deposit_bonus_rate = \
        db_load("dep_rate", 5.18)
    st._mlm_gen_rates = db_load(
        "gen_rates", {
            1: 5.0, 2: 4.0, 3: 3.0,
            4: 2.0, 5: 1.0, 6: 0.5,
            7: 0.5
        }
    )
    st._mlm_id_thresholds = db_load(
        "id_thresh", {
            1: 10, 2: 20, 3: 40,
            4: 80, 5: 160, 6: 320,
            7: 640
        }
    )
    st.session_state.init_sync = True
else:
    st._central_user_creds = \
        db_load("user_creds", {})
    st._central_key_registry = \
        db_load("key_registry", {})
    st._central_blacklist = \
        db_load("blacklist", [])
    st._license_csv_database = \
        db_load("license_csv", [])
    st._global_referral_tree = \
        db_load("referral_tree", {})
    st._global_user_pnl_history = \
        db_load("pnl_history", [])
    st._uid_to_username = \
        db_load("uid_to_user", {})
    st._mlm_bonus_enabled = \
        db_load("mlm_enabled", True)
    st._mlm_deposit_bonus_rate = \
        db_load("dep_rate", 5.18)
    st._mlm_gen_rates = db_load(
        "gen_rates", {}
    )
    st._mlm_id_thresholds = db_load(
        "id_thresh", {}
    )
BYBYT_DATABASE_CORE = {
    "🪙 BTC": {
        "symbol": "BTCUSDT",
        "max_leverage": 100,
        "default_tp": 100.0,
        "default_sl": 150.0,
        "step": 10.0
    },
    "🔷 ETH": {
        "symbol": "ETHUSDT",
        "max_leverage": 100,
        "default_tp": 8.0,
        "default_sl": 15.0,
        "step": 1.0
    },
    "☀️ SOL": {
        "symbol": "SOLUSDT",
        "max_leverage": 50,
        "default_tp": 1.5,
        "default_sl": 3.0,
        "step": 0.1
    },
    "💥 XRP": {
        "symbol": "XRPUSDT",
        "max_leverage": 100,
        "default_tp": 0.015,
        "default_sl": 0.03,
        "step": 0.001
    },
    "🐶 DOGE": {
        "symbol": "DOGEUSDT",
        "max_leverage": 50,
        "default_tp": 0.004,
        "default_sl": 0.01,
        "step": 0.0005
    },
    "🔮 LINK": {
        "symbol": "LINKUSDT",
        "max_leverage": 50,
        "default_tp": 0.25,
        "default_sl": 0.50,
        "step": 0.01
    },
    "🧬 ADA": {
        "symbol": "ADAUSDT",
        "max_leverage": 50,
        "default_tp": 0.01,
        "default_sl": 0.02,
        "step": 0.001
    },
    "PEPE": {
        "symbol": "PEPEUSDT",
        "max_leverage": 20,
        "default_tp": 0.0000001,
        "default_sl": 0.0000003,
        "step": 0.00000001
    },
    "🌀 WIF": {
        "symbol": "WIFUSDT",
        "max_leverage": 20,
        "default_tp": 0.05,
        "default_sl": 0.12,
        "step": 0.01
    },
    "🔥 SHIB": {
        "symbol": "SHIBUSDT",
        "max_leverage": 50,
        "default_tp": 0.0000005,
        "default_sl": 0.000001,
        "step": 0.0000001
    },
    "🪐 DOT": {
        "symbol": "DOTUSDT",
        "max_leverage": 50,
        "default_tp": 0.05,
        "default_sl": 0.12,
        "step": 0.01
    },
    "🔺 AVAX": {
        "symbol": "AVAXUSDT",
        "max_leverage": 50,
        "default_tp": 0.20,
        "default_sl": 0.50,
        "step": 0.01
    },
    "🦄 UNI": {
        "symbol": "UNIUSDT",
        "max_leverage": 50,
        "default_tp": 0.05,
        "default_sl": 0.15,
        "step": 0.01
    }
}
BYBYT_DATABASE_EXT = {
    "⚡ LTC": {
        "symbol": "LTCUSDT",
        "max_leverage": 60,
        "default_tp": 0.50,
        "default_sl": 1.20,
        "step": 0.1
    },
    "🔗 ATOM": {
        "symbol": "ATOMUSDT",
        "max_leverage": 50,
        "default_tp": 0.05,
        "default_sl": 0.15,
        "step": 0.01
    },
    "🌿 XLM": {
        "symbol": "XLMUSDT",
        "max_leverage": 50,
        "default_tp": 0.002,
        "default_sl": 0.005,
        "step": 0.0001
    },
    "🦅 FIL": {
        "symbol": "FILUSDT",
        "max_leverage": 50,
        "default_tp": 0.04,
        "default_sl": 0.10,
        "step": 0.01
    },
    "👻 AAVE": {
        "symbol": "AAVEUSDT",
        "max_leverage": 50,
        "default_tp": 1.0,
        "default_sl": 2.50,
        "step": 0.1
    },
    "📦 NEAR": {
        "symbol": "NEARUSDT",
        "max_leverage": 50,
        "default_tp": 0.04,
        "default_sl": 0.10,
        "step": 0.01
    },
    "🎮 IMX": {
        "symbol": "IMXUSDT",
        "max_leverage": 20,
        "default_tp": 0.02,
        "default_sl": 0.05,
        "step": 0.001
    },
    "🥞 CAKE": {
        "symbol": "CAKEUSDT",
        "max_leverage": 20,
        "default_tp": 0.02,
        "default_sl": 0.05,
        "step": 0.001
    },
    "🚀 SUI": {
        "symbol": "SUIUSDT",
        "max_leverage": 50,
        "default_tp": 0.02,
        "default_sl": 0.06,
        "step": 0.001
    },
    "🌊 APT": {
        "symbol": "APTUSDT",
        "max_leverage": 50,
        "default_tp": 0.05,
        "default_sl": 0.15,
        "step": 0.01
    },
    "🪙 OP": {
        "symbol": "OPUSDT",
        "max_leverage": 50,
        "default_tp": 0.02,
        "default_sl": 0.05,
        "step": 0.001
    },
    "🧱 ARB": {
        "symbol": "ARBUSDT",
        "max_leverage": 50,
        "default_tp": 0.01,
        "default_sl": 0.03,
        "step": 0.001
    }
}
BYBYT_DATABASE_CORE.update(
    BYBYT_DATABASE_EXT
)
YOUR_SECRET_MASTER_CODE = "ADMIN1234"
st.set_page_config(
    page_title="Bybit AI Scalper",
    page_icon="⚡", layout="centered"
)
st.markdown(
    """
    <style>
    html, body, 
    [data-testid="stAppViewContainer"] {
        background: #06090e !important;
        background-image: 
            radial-gradient(
                circle at 50% 20%, 
                #111723 0%, 
                #06090e 80%
            ) !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
        box-sizing: border-box !important;
        touch-action: pan-y !important;
        -webkit-overflow-scrolling: 
            touch !important;
    }
    div[data-testid="stSidebar"] { 
        background-color: 
            #0c1017 !important; 
        border-right: 
            1px solid #1e293b; 
    }
    div.stButton > button:first-child { 
        width: 100%; border-radius: 8px; 
        font-weight: bold; 
        font-size: 16px; height: 46px; 
    }
    iframe { border: none !important; }
    .stExpander { 
        background-color: 
            #0c1017 !important; 
        border: 1px solid 
            #1e293b !important; 
        border-radius: 8px !important; 
    }
    div[data-testid="stMarkdownContainer"] p, 
    span, label, h1, h2, h3, b, code { 
        word-wrap: break-word !important; 
        white-space: normal !important; 
        word-break: break-word !important; 
        max-width: 100% !important; 
    }
    div[data-testid="stDataFrame"], 
    div[data-testid="stTable"], 
    .stTable { 
        max-width: 100% !important; 
        overflow-x: auto !important; 
        display: block !important; 
        box-sizing: border-box !important;
    }
    div[data-testid="stExpander"] p, 
    div[data-testid="stExpander"] label { 
        color: #ffffff !important; 
        font-weight: bold !important; 
        font-size: 13px !important; 
    }
    div[data-testid="stExpander"] h2, 
    div[data-testid="stExpander"] b { 
        color: #38bdf8 !important; 
        font-weight: bold !important; 
    }
    div[data-testid="stSidebar"] p { 
        color: #ffffff !important; 
        font-weight: bold !important; 
    }
    </style>
    """,
    unsafe_allow_html=True
)
if 'demo_balance' not in \
   st.session_state: 
    st.session_state.demo_balance = \
        db_load(
            "state_demo_balance",
            5000.0
        )
if 'bot_active' not in \
   st.session_state:
    st.session_state.bot_active = False
if 'in_position' not in \
   st.session_state:
    st.session_state.in_position = False
if 'buy_price' not in \
   st.session_state:
    st.session_state.buy_price = 0.0
if 'current_side' not in \
   st.session_state:
    st.session_state.current_side = \
        "NONE"
if 'all_trades_history' not in \
   st.session_state:
    st.session_state\
        .all_trades_history = []
if 'win_count' not in \
   st.session_state:
    st.session_state.win_count = \
        db_load("state_win_count", 0)
if 'loss_count' not in \
   st.session_state:
    st.session_state.loss_count = \
        db_load("state_loss_count", 0)
if 'logged_in_user' not in \
   st.session_state:
    if "session_user" in \
       st.query_params:
        st.session_state\
            .logged_in_user = \
            st.query_params[
                "session_user"
            ]
    else:
        st.session_state\
            .logged_in_user = None

if 'my_hardware_signature' not in \
   st.session_state:
    st.session_state\
        .my_hardware_signature = \
        "DEV-" + "".join(
            random.choices(
                string.ascii_uppercase +
                string.digits, k=10
            )
        )

my_signature = \
    st.session_state\
    .my_hardware_signature
if st.session_state.logged_in_user \
   is None:
    st.markdown(
        "<div style='background: "
        "linear-gradient(135deg, "
        "#ff9900 0%, #ffcc00 100%); "
        "padding: 18px; border-radius: "
        "12px; margin-bottom: 25px; "
        "text-align: center;'><h1 "
        "style='margin: 0; color: "
        "#0b0e14; font-size: 26px; "
        "font-weight: bold;'>"
        "BYBIT AI PRO SCALPER</h1>"
        "</div>",
        unsafe_allow_html=True
    )
    st.subheader(
        "🔑 Account Auth Panel"
    )
    auth_mode = st.radio(
        "Choose Layer:", [
            "Secure Login Profile", 
            "Mint New Account ID", 
            "Forget Password Profile"
        ]
    )
    if auth_mode == "Mint New Account ID":
        reg_username = st.text_input(
            "Username:", key="reg_u"
        ).strip()
        reg_password = st.text_input(
            "Password Phrase:", 
            type="password", key="reg_p"
        ).strip()
        reg_email = st.text_input(
            "Google Mail (Gmail ID):", 
            key="reg_e"
        ).strip()
        reg_school = st.text_input(
            "First School Name?", 
            key="reg_sch"
        ).strip()
        reg_sponsor = st.text_input(
            "Sponsor Referral Token:", 
            key="reg_s"
        ).strip()
        if st.button(
            "🚀 Register My Handle", 
            key="reg_submit_btn"
        ):
            st._central_user_creds = \
                db_load("user_creds", {})
            existing_emails = [
                d.get("email") for d \
                in st._central_user_creds\
                .values()
            ]
            if reg_username == "" or \
               reg_password == "" or \
               reg_email == "" or \
               reg_school == "": 
                st.error("Fields blank!")
            elif "@gmail.com" not in \
                 reg_email: 
                st.error("Invalid Gmail!")
            elif reg_email in \
                 existing_emails: 
                st.error("Email active!")
            elif reg_username in \
                 st._central_user_creds: 
                st.error("Handle active!")
            else:
                new_uid = "UID-" + \
                    "".join(
                        random.choices(
                            string.digits, 
                            k=6
                        )
                    )
                st._central_user_creds\
                    [reg_username] = {
                        "password": 
                            reg_password, 
                        "uid": new_uid, 
                        "email": reg_email,
                        "school_answer": 
                            reg_school\
                            .lower(),
                        "sponsor": 
                            reg_sponsor \
                            if reg_sponsor \
                            != "" else 
                            "None"
                    }
                st._uid_to_username\
                    [new_uid] = reg_username
                db_save(
                    "user_creds", 
                    st._central_user_creds
                )
                db_save(
                    "uid_to_user", 
                    st._uid_to_username
                )
                if reg_sponsor != "":
                    st._global_referral_tree = \
                        db_load(
                            "referral_tree", {}
                        )
                    if reg_sponsor not in \
                       st\
                       ._global_referral_tree: 
                        st\
                        ._global_referral_tree\
                        [reg_sponsor] = []
                    if new_uid not in \
                       st\
                       ._global_referral_tree\
                       [reg_sponsor]: 
                        st\
                        ._global_referral_tree\
                        [reg_sponsor]\
                        .append(new_uid)
                    db_save(
                        "referral_tree", 
                        st\
                        ._global_referral_tree
                    )
                st.success(
                    f"Bound! UID: "
                    f"{new_uid}"
                )
        st.stop()
    elif auth_mode == "Forget Password Profile":
        st.markdown(
            "<p style='color:#38bdf8; "
            "font-weight:bold;'>🔐 "
            "Security Recovery Desk:</p>", 
            unsafe_allow_html=True
        )
        forget_uid = st.text_input(
            "Account User UID:", 
            key="forg_uid"
        ).strip()
        forget_email = st.text_input(
            "Registered Gmail:", 
            key="forg_email"
        ).strip()
        forget_school = st.text_input(
            "First School Name?", 
            key="forg_sch"
        ).strip()
        if st.button(
            "🔑 Generate Password", 
            key="forg_sub_btn"
        ):
            st._central_user_creds = \
                db_load("user_creds", {})
            found_user = None
            for uname, data in \
                st._central_user_creds\
                .items():
                if data.get("uid") == \
                   forget_uid and \
                   data.get("email") == \
                   forget_email and \
                   data.get("school_answer") == \
                   forget_school.lower():
                    found_user = uname
                    break
            if found_user:
                generated_pass = \
                    "RESET-" + \
                    "".join(
                        random.choices(
                            string\
                            .ascii_uppercase +
                            string.digits, 
                            k=6
                        )
                    )
                st._central_user_creds\
                    [found_user]\
                    ["password"] = \
                        generated_pass
                db_save(
                    "user_creds", 
                    st._central_user_creds
                )
                st.success(
                    f"Verified! Pass: "
                    f"`{generated_pass}`"
                )
            else: 
                st.error("Mismatch data!")
        st.stop()
    elif auth_mode == "Secure Login Profile":
        login_u = st.text_input(
            "Identity Handle:", 
            key="log_u"
        ).strip()
        login_p = st.text_input(
            "Password Phrase:", 
            type="password", key="log_p"
        ).strip()
        if st.button(
            "🔓 Authenticate In", 
            key="log_submit_btn"
        ):
            st._central_user_creds = \
                db_load("user_creds", {})
            if login_u in \
               st._central_user_creds \
               and st._central_user_creds\
               [login_u]["password"] \
               == login_p:
                st.session_state\
                    .logged_in_user = \
                        login_u
                st.query_params[
                    "session_user"
                ] = login_u
                st.success("Authorized!")
                st.rerun()
            else: 
                st.error("Mismatch credentials!")
        st.stop()
user_data = st._central_user_creds\
    [st.session_state.logged_in_user]
allocated_user_id = user_data["uid"]
my_sponsor_id = user_data["sponsor"]
my_profile_email = user_data.get(
    "email", "Not Set"
)
st.markdown(
    "<div style='background: "
    "linear-gradient(135deg, "
    "#ff9900 0%, #ffcc00 100%); "
    "padding: 18px; border-radius: "
    "12px; margin-bottom: 25px; "
    "text-align: center;'><h1 "
    "style='margin: 0; color: "
    "#0b0e14; font-size: 26px; "
    "font-weight: bold;'>"
    "BYBIT AI PRO SCALPER</h1>"
    "</div>",
    unsafe_allow_html=True
)

with st.sidebar:
    st.markdown(
        "<h2 style='color:#f5a623; "
        "margin-top:0;'>⚙️ Panel</h2>", 
        unsafe_allow_html=True
    )
    st.markdown(f"<p style='color:#e2a826; font-size:13px; margin:0;'>👤 Handle: <b>{st.session_state.logged_in_user}</b></p>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#38bdf8; font-size:13px; margin:4px 0;'>🆔 My Referral ID: <b>{allocated_user_id}</b></p>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#00e676; font-size:12px; margin:0 0 4px 0;'>📧 Email: <b>{my_profile_email}</b></p>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#94a3b8; font-size:12px; margin:0 0 12px 0;'>🔗 Sponsor UID: <b>{my_sponsor_id}</b></p>", unsafe_allow_html=True)
    if st.button("🚪 Logout Account", key="logout_sidebar_btn"): 
        st.session_state.logged_in_user = None
        if "session_user" in st.query_params: del st.query_params["session_user"]
        st.rerun()
with st.sidebar:
    bot_mode = st.radio("Trading Account Mode:", ["Demo Simulation (Virtual Funds)", "Live Exchange (Bybit Mainnet API)"])
    is_real_live = True if "Live" in bot_mode else False
    selected_display_name = st.selectbox("Select Asset Contract:", list(BYBYT_DATABASE_CORE.keys()), index=0)
    coin_config = BYBYT_DATABASE_CORE[selected_display_name]
    target_symbol = coin_config["symbol"]
    ai_decision = st.toggle("AI Smart Crossover Filter", value=True)
    leverage = st.slider(f"Leverage (Max {coin_config['max_leverage']}x):", min_value=1, max_value=coin_config['max_leverage'], value=20)
    trade_amount = st.number_input("Margin Requirement (\$):", min_value=1, max_value=1000, value=20)
    price_jump_target = st.number_input("Take Profit Target (\$):", min_value=0.00000001, max_value=5000.0, value=coin_config["default_tp"], format="%.8f")
    stop_loss_gap = st.number_input("Stop Loss Threshold (\$):", min_value=0.00000001, max_value=5000.0, value=coin_config["default_sl"], format="%.8f")

with st.sidebar:
    api_key, secret_key = "", ""
    if is_real_live:
        st.markdown("<hr style='border:1px solid #1e293b; margin:10px 0;'><div style='background-color:#ff1744; padding:6px; border-radius:5px; text-align:center; margin-bottom:6px;'><b style='color:#ffffff; font-size:11px; letter-spacing:0.5px;'>🚨 LICENSE GATE ACTIVE</b></div>", unsafe_allow_html=True)
        input_license = st.text_input("License Password:", type="password", key="lic_field_sidebar", label_visibility="collapsed").strip()
        if input_license in st._central_key_registry:
            api_key = st.text_input("Bybit API Key:", type="password", key="api_field_sidebar")
            secret_key = st.text_input("Bybit Secret Key:", type="password", key="sec_field_sidebar")

effective_vol = trade_amount * leverage
estimated_fee = effective_vol * 0.0011 
if 'active_coin' not in st.session_state or st.session_state.active_coin != target_symbol:
    st.session_state.in_position = False; st.session_state.buy_price = 0.0; st.session_state.current_side = "NONE"; st.session_state.active_coin = target_symbol
with st.expander("🛠️ Advanced Licensing Cryptographic Hub (Super Admin Panel)"):
    master_input = st.text_input("Input Master Security Override Code Password:", type="password", key="supreme_admin_password_node")
    if master_input == YOUR_SECRET_MASTER_CODE:
        st.success("Supreme Controller Access Verified.")
        st.markdown("<h2>⚙️ Referral Marketing Matrix Controls (7-Gen ROI Mode):</h2>", unsafe_allow_html=True)
        old_val = st._mlm_bonus_enabled
        st._mlm_bonus_enabled = st.toggle("Activate MLM Multi-Generation Incentive Commissions System", value=st._mlm_bonus_enabled, key="adm_mlm_active_toggle")
        if old_val != st._mlm_bonus_enabled: db_save("mlm_enabled", st._mlm_bonus_enabled)
        st._mlm_deposit_bonus_rate = st.number_input("One-Time Bonus Rate on Total Account Deposit (%):", min_value=0.0, max_value=100.0, value=st._mlm_deposit_bonus_rate, key="adm_deposit_bonus_rate_input")
        db_save("dep_rate", st._mlm_deposit_bonus_rate)
        st.markdown("<p style='color:#38bdf8; font-weight:bold;'>🌐 Configure 7-Generation Daily Income ROI Share Rates & Member Limits:</p>", unsafe_allow_html=True)
        c_cols = st.columns(2)
        for g in range(1, 8):
            with c_cols[(g-1)%2]:
                st._mlm_gen_rates[g] = st.number_input(f"Gen {g} Share (%):", min_value=0.0, max_value=100.0, value=st._mlm_gen_rates.get(g, 0.0), key=f"adm_rates_generation_input_g_{g}")
                st._mlm_id_thresholds[g] = st.number_input(f"Gen {g} Cap:", min_value=1, max_value=5000, value=st._mlm_id_thresholds.get(g, 10), key=f"adm_thresholds_generation_input_g_{g}")
        db_save("gen_rates", st._mlm_gen_rates); db_save("id_thresh", st._mlm_id_thresholds)
        if st.button("Mint New Randomized License Token Key", key="adm_mint_token_trigger_btn"):
            random_token = "SCLP-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            st._central_key_registry[random_token] = "FREE_SLOT"
            st._license_csv_database.append({"Date": time.strftime("%Y-%m-%d"), "Time": time.strftime("%H:%M:%S"), "License Key": random_token, "Status": "Active (Unused)"})
            db_save("key_registry", st._central_key_registry); db_save("license_csv", st._license_csv_database); st.code(f"{random_token}", language="text"); st.rerun()
        override_uid = st.text_input("Target User ID (UID) to Hack/Change:", key="adm_override_uid_field").strip()
        override_new_pass = st.text_input("Set Custom New Password Phrase:", key="adm_override_pass_field").strip()
        if st.button("Execute Hard Password Override Ban", key="adm_override_pass_submit_btn"):
            found_account = None
            for uname, data in st._central_user_creds.items():
                if data.get("uid") == override_uid: found_account = uname; break
            if found_account and override_new_pass != "":
                st._central_user_creds[found_account]["password"] = override_new_pass; db_save("user_creds", st._central_user_creds); st.success(f"Success! Handle password changed."); st.rerun()
            else: st.error("Target User UID not found!")
        target_block_key = st.text_input("Paste Target License Token to BAN permanently:", key="adm_ban_token_input_field")
        if st.button("Execute Permanent Revocation Ban", key="adm_ban_token_trigger_btn"):
            if target_block_key in st._central_key_registry:
                st._central_blacklist.append(target_block_key); del st._central_key_registry[target_block_key]
                for row in st._license_csv_database:
                    if row["License Key"] == target_block_key: row["Status"] = "Permanently Banned ❌"
                db_save("blacklist", st._central_blacklist); db_save("key_registry", st._central_key_registry); db_save("license_csv", st._license_csv_database); st.warning(f"Token blocked."); st.rerun()
        if st._license_csv_database: st.dataframe(pd.DataFrame(st._license_csv_database).iloc[::-1], use_container_width=True, height=120)
        all_creds_df = pd.DataFrame.from_dict(st._central_user_creds, orient='index')
        if not all_creds_df.empty: st.dataframe(all_creds_df, use_container_width=True)
        if st._global_referral_tree:
            for parent, children in st._global_referral_tree.items():
                p_user = st._uid_to_username.get(parent, parent); st.markdown(f"👤 <b>Sponsor:</b> `{p_user}` (`{parent}`)", unsafe_allow_html=True)
                for child in children:
                    c_user = st._uid_to_username.get(child, child); st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;└── 📱 <b>Downline Node:</b> `{c_user}` (`{child}`)", unsafe_allow_html=True)
        if st._global_user_pnl_history:
            global_pnl_df = pd.DataFrame(st._global_user_pnl_history)
            target_audit_uid = st.selectbox("Select Target UID to Inspect logs:", global_pnl_df["User ID"].unique(), key="adm_audit_node_selector_dropdown")
            st.dataframe(global_pnl_df[global_pnl_df["User ID"] == target_audit_uid].iloc[::-1], use_container_width=True)
    elif master_input != "": st.error("Administrative override password verification failed.")
st.markdown("<h3 style='color:#f5a623; font-size:16px;'>🌿 My Referral Network Hub</h3>", unsafe_allow_html=True)

def calculate_sub_generations(r_uid, tree):
    g_map = {1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 7: []}
    if r_uid in tree: g_map = tree[r_uid].copy()
    for g in range(2, 8):
        p_layer = g_map[g-1]
        c_accum = []
        for p_uid in p_layer:
            if p_uid in tree:
                for c_uid in tree[p_uid]:
                    if c_uid not in g_map[g]: c_accum.append(c_uid)
        g_map[g] = c_accum
    return g_map
all_downlines_flat_list, downline_display_options = [], {}
mapped_gens = calculate_sub_generations(allocated_user_id, st._global_referral_tree)
if st._mlm_bonus_enabled:
    for g_num in range(1, 8):
        for uid in mapped_gens[g_num]:
            if uid not in all_downlines_flat_list:
                all_downlines_flat_list.append(uid)
                downline_display_options[uid] = f"🔹 [Gen {g_num}] {st._uid_to_username.get(uid, 'Unknown')} ({uid})"
else:
    def pull_all_descendants(r_uid, tree):
        desc = []
        q = tree.get(r_uid, []).copy()
        while q:
            n = q.pop(0)
            if n not in desc: desc.append(n); q.extend(tree.get(n, []))
        return desc
    for idx, uid in enumerate(pull_all_descendants(allocated_user_id, st._global_referral_tree), 1):
        all_downlines_flat_list.append(uid)
        downline_display_options[uid] = f"🔸 [Serial {idx}] {st._uid_to_username.get(uid, 'Unknown')} ({uid})"

st.markdown("<b>🔍 Input Specific Downline UID to Audit Data Records:</b>", unsafe_allow_html=True)
search_uid_input = st.text_input("Enter Target Member UID box input:", value=allocated_user_id, key="custom_uid_search_field_node").strip()
if search_uid_input:
    target_display_title = downline_display_options.get(search_uid_input, f"👤 Target Account: Self Dashboard ({search_uid_input})")
    st.markdown(f"<p style='color:#38bdf8; font-weight:bold;'>{target_display_title}</p>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["Real Production Earnings Gate 🟢", "Demo Sandbox Earnings Gate 🔵"])
    with t1:
        if st._global_user_pnl_history:
            pnl_df = pd.DataFrame(st._global_user_pnl_history)
            child_real_df = pnl_df[(pnl_df["User ID"] == search_uid_input) & (pnl_df["Type"] == "REAL")]
            if not child_real_df.empty: child_real_df["Net P&L ($)"] = pd.to_numeric(child_real_df["Net P&L ($)"]); st.markdown(f"💰 Real Daily Earnings: <b style='color:#00e676;'>${child_real_df['Net P&L ($)'].sum():.2f} USDT</b>", unsafe_allow_html=True); st.dataframe(child_real_df.iloc[::-1], use_container_width=True)
            else: st.info("No live production real funds data records synced yet.")
        else: st.info("Ledger registry is empty.")
    with t2:
        if st._global_user_pnl_history:
            pnl_df = pd.DataFrame(st._global_user_pnl_history)
            child_demo_df = pnl_df[(pnl_df["User ID"] == search_uid_input) & (pnl_df["Type"] == "DEMO")]
            if not child_demo_df.empty: child_demo_df["Net P&L ($)"] = pd.to_numeric(child_demo_df["Net P&L ($)"]); st.markdown(f"💰 Demo Virtual Sandbox Earnings: <b style='color:#29b6f6;'>${child_demo_df['Net P&L ($)'].sum():.2f} USDT</b>", unsafe_allow_html=True); st.dataframe(child_demo_df.iloc[::-1], use_container_width=True)
            else: st.info("No sandbox simulation records synced yet.")
        else: st.info("Ledger registry is empty.")
    st.markdown("<br><b style='color:#f5a623;'>📊 Sub-Downline Network Members Status Grid:</b>", unsafe_allow_html=True)
    t_sub_gens = calculate_sub_generations(search_uid_input, st._global_referral_tree)
    sub_tree_records = []
    for g_idx in range(1, 8):
        for sub_uid in t_sub_gens[g_idx]:
            sub_pnl = 0.0
            if st._global_user_pnl_history:
                pdf = pd.DataFrame(st._global_user_pnl_history); m_df = pdf[pdf["User ID"] == sub_uid]
                if not m_df.empty: sub_pnl = pd.to_numeric(m_df["Net P&L ($)"]).sum()
            label_text = f"Gen {g_idx}" if st._mlm_bonus_enabled else f"Serial {len(sub_tree_records)+1}"
            sub_tree_records.append({"Hierarchy Level": label_text, "User ID": sub_uid, "Username": st._uid_to_username.get(sub_uid, 'Unknown'), "Lifetime Profit/Loss Balance": f"${sub_pnl:.2f} USDT"})
    if sub_tree_records: st.dataframe(pd.DataFrame(sub_tree_records), use_container_width=True)
    else: st.info("No active team network users registered under this target token UID.")
total_trades = (
    st.session_state.win_count + 
    st.session_state.loss_count
)
win_rate = (
    (st.session_state.win_count / total_trades * 100) 
    if total_trades > 0 else 0.0
)
st.markdown(
    "<hr style='border:1px solid #1f2c3f;'>", 
    unsafe_allow_html=True
)
st.markdown(
    f"""<div style="background-color:#141a24; 
    padding:12px; border-radius:10px; 
    margin-bottom:15px; border: 1px solid #1f2c3f; 
    display: flex; justify-content: space-between;">
    <span style="color:#ffffff; font-size:14px; 
    font-weight:bold;">🏆 WON: <b style="color:#00e676;">
    {st.session_state.win_count}</b></span>
    <span style="color:#ffffff; font-size:14px; 
    font-weight:bold;">❌ LOST: <b style="color:#ff1744;">
    {st.session_state.loss_count}</b></span>
    <span style="color:#ffffff; font-size:14px; 
    font-weight:bold;">🎯 WIN RATE: <b style="color:#29b6f6;">
    {win_rate:.1f}%</b></span></div>""", 
    unsafe_allow_html=True
)
live_price, current_rsi, df_kline = 0.0, 50.0, None
if st.session_state.bot_active:
    try:
        public_session = HTTP(testnet=False)
        response = public_session.get_kline(
            category="linear", 
            symbol=target_symbol, 
            interval="5", limit=15
        )
        klines = (
            response.get('result', {})
            .get('list', [])
        )
        if klines:
            df_kline = pd.DataFrame(
                klines, 
                columns=[
                    'time', 'open', 'high', 
                    'low', 'close', 'volume', 
                    'turnover'
                ]
            ).iloc[::-1].reset_index(drop=True)
            for col in [
                'open', 'high', 'low', 'close'
            ]:
                df_kline[col] = (
                    pd.to_numeric(df_kline[col])
                )
            live_price = df_kline['close'].iloc[-1]
            delta = df_kline['close'].diff()
            gain = (
                delta.where(delta > 0, 0)
                .rolling(window=7).mean()
            )
            loss = (
                (-delta.where(delta < 0, 0))
                .rolling(window=7).mean()
            )
            rs = gain / (loss + 1e-10)
            df_kline['RSI'] = (
                100 - (100 / (1 + rs))
            )
            current_rsi = (
                df_kline['RSI'].iloc[-1] 
                if not df_kline['RSI']
                .isnull().iloc[-1] else 50.0
            )
    except:
        pass
floating_pnl, expected_net_profit = 0.0, 0.0
if st.session_state.in_position and live_price > 0:
    is_long_pos = (
        st.session_state.current_side == "LONG"
    )
    if is_long_pos:
        floating_pnl = (
            (live_price - st.session_state.buy_price) * 
            (effective_vol / st.session_state.buy_price)
        )
    else:
        floating_pnl = (
            (st.session_state.buy_price - live_price) * 
            (effective_vol / st.session_state.buy_price)
        )
    expected_net_profit = (
        (price_jump_target * 
         (effective_vol / st.session_state.buy_price)) - 
        estimated_fee
    )

balance_usd_text = f"${(st.session_state.demo_balance + floating_pnl):,.2f}" if not is_real_live else "0.00"
if is_real_live and api_key and secret_key:
    try:
        session = HTTP(
            testnet=False, 
            api_key=api_key, 
            secret_key=secret_key
        )
        wallet_info = session.get_wallet_balance(
            accountType="UNIFIED", coin="USDT"
        )
        member_list = (
            wallet_info.get('result', {})
            .get('list', [])
        )
        if member_list:
            for c in member_list.get('coin', []):
                if c.get('coin') == 'USDT':
                    balance_usd_text = (
                        f"${(float(c.get('walletBalance', 0)) + floating_pnl):,.2f}"
                    )
                    break
    except:
        balance_usd_text = "API Key Error"
position_status = (
    "NO ACTIVE POSITION 💤" 
    if not st.session_state.in_position 
    else f"FUTURE {target_symbol} "
    f"{st.session_state.current_side} CONTRACT"
)
rsi_color = "#ff1744" if current_rsi > 50 else "#00e676"
st.markdown(
    f"""<div style="background-color:#141a24; 
    padding:10px; border-radius:10px; 
    margin-bottom:12px; border-left: 5px solid {rsi_color}; 
    text-align:center; border: 1px solid #1f2c3f;">
    <span style="color:#94a3b8; font-size:12px; 
    font-weight:bold;">📡 LIVE AI RSI (5s FEED):</span>
    <h3 style="margin:2px 0; color:#ffffff; 
    font-size:24px; font-family: monospace;">
    {current_rsi:.2f}</h3></div>
    <div style="background-color:#141a24; 
    padding:15px; border-radius:12px; 
    margin-bottom:12px; border: 1px solid #1f2c3f;">
    <p style="margin:0; font-size:12px; color:#94a3b8; 
    font-weight:bold;">💰 AVAILABLE BALANCE ({bot_mode})</p>
    <h2 style="margin:5px 0; color:#ffffff; 
    font-size:28px; font-family: monospace;">
    {balance_usd_text}</h2>
    <p style="margin:0; font-size:14px; 
    color:{'#00e676' if floating_pnl >= 0 else '#ff1744'}; 
    font-weight:bold;">Live Floating P&L: {floating_pnl:+.2f} USDT</p></div>
    <div style="background-color:#141a24; 
    padding:15px; border-radius:12px; 
    margin-bottom:15px; border: 1px solid #1f2c3f;">
    <p style="margin:0; font-size:12px; color:#94a3b8; 
    font-weight:bold;">📦 MARGIN STATUS EXECUTION</p>
    <h3 style="margin:5px 0; color:#ffffff; 
    font-size:16px; font-weight:bold;">
    {position_status}</h3></div>""", 
    unsafe_allow_html=True
)
if st.session_state.in_position and live_price > 0:
    is_long_pos = (
        st.session_state.current_side == "LONG"
    )
    live_target = (
        (st.session_state.buy_price + price_jump_target) 
        if is_long_pos else 
        (st.session_state.buy_price - price_jump_target)
    )
    live_sl = (
        (st.session_state.buy_price - stop_loss_gap) 
        if is_long_pos else 
        (st.session_state.buy_price + stop_loss_gap)
    )
    st.markdown(
        f"""<div style="background-color:#0b0e14; 
        padding:12px; border-radius:10px; 
        margin-bottom:15px; border: 1px solid #1f2c3f; 
        border-left: 5px solid #29b6f6;">
        <span style="font-size:14px; color:#ffffff; 
        font-weight:bold; font-family: monospace;">
        Entry Price: {st.session_state.buy_price} | 
        Live Index: {live_price}</span><br>
        <span style="font-size:14px; color:#00e676; 
        font-weight:bold; font-family: monospace;">
        Take Profit: {live_target} 
        (Expected Net: +${expected_net_profit:.2f})</span><br>
        <span style="font-size:14px; color:#ff1744; 
        font-weight:bold; font-family: monospace;">
        Stop Loss Boundary: {live_sl}</span></div>""", 
        unsafe_allow_html=True
    )
st.info(
    f"💡 Estimated Execution Trading Fee: "
    f"**${estimated_fee:.3f} USDT**"
)
st.markdown(
    "<h3 style='color:#ffffff; font-size:16px;'>"
    "🎮 Engine Controls</h3>", 
    unsafe_allow_html=True
)
c1, c2 = st.columns(2)
with c1:
    if st.session_state.bot_active:
        if st.button(
            "🔴 STOP ENGINE", key="stop_engine_bot_btn"
        ):
            st.session_state.bot_active = False
            st.rerun()
    else:
        if st.button(
            "🟢 START SCALPER", key="start_engine_bot_btn"
        ):
            st.session_state.bot_active = True
            st.rerun()
with c2:
    if st.session_state.in_position:
        if st.button(
            "🚨 EMERGENCY LIQUIDATE", 
            key="force_sell_engine_btn"
        ):
            net_pnl = floating_pnl - estimated_fee
            if not is_real_live:
                st.session_state.demo_balance += net_pnl
                db_save(
                    "state_demo_balance", 
                    st.session_state.demo_balance
                )
            status_tag = "MANUAL CLOSE 🛑"
            st._global_user_pnl_history.append({
                "Date": time.strftime("%Y-%m-%d"),
                "Time": time.strftime("%H:%M:%S"),
                "User ID": allocated_user_id, 
                "Coin": target_symbol,
                "Action": f"CLOSE {st.session_state.current_side}",
                "Net P&L ($)": f"{net_pnl:.2f}",
                "Type": "REAL" if is_real_live else "DEMO"
            })
            db_save("pnl_history", st._global_user_pnl_history)
            if net_pnl >= 0:
                st.session_state.win_count += 1
                db_save("state_win_count", st.session_state.win_count)
            else:
                st.session_state.loss_count += 1
                db_save("state_loss_count", st.session_state.loss_count)
            if st._mlm_bonus_enabled and my_sponsor_id != "None":
                current_parent = my_sponsor_id
                for gen in range(1, 8):
                    if current_parent in st._central_user_creds:
                        p_user = st._uid_to_username.get(current_parent, current_parent)
                        roi_rate = st._mlm_gen_rates.get(gen, 0.0) / 100.0
                        if net_pnl > 0:
                            bonus_credited = net_pnl * roi_rate
                            st._global_user_pnl_history.append({
                                "Date": time.strftime("%Y-%m-%d"),
                                "Time": time.strftime("%H:%M:%S"),
                                "User ID": current_parent, 
                                "Coin": f"GEN {gen} ROI",
                                "Action": f"COMMISSION FROM {st.session_state.logged_in_user}",
                                "Net P&L ($)": f"{bonus_credited:.2f}",
                                "Type": "REAL" if is_real_live else "DEMO"
                            })
                        current_parent = st._central_user_creds.get(p_user, {}).get("sponsor", "None")
                    else:
                        break
            for idx, trade in enumerate(st.session_state.all_trades_history):
                if trade["Status"] == "RUNNING" and trade["Coin"] == target_symbol:
                    st.session_state.all_trades_history[idx]["Status"] = status_tag
                    st.session_state.all_trades_history[idx]["Net P&L ($)"] = f"{net_pnl:.2f}"
            db_save("pnl_history", st._global_user_pnl_history)
            st.session_state.in_position = False
            st.session_state.buy_price = 0.0
            st.session_state.current_side = "NONE"
            st.rerun()
if st.session_state.bot_active and df_kline is not None:
    try:
        if not st.session_state.in_position:
            decision_side = "NONE"
            if ai_decision:
                decision_side = "BUY" if current_rsi < 45.0 else "SELL" if current_rsi > 55.0 else "NONE"
            else:
                decision_side = "BUY"
            if decision_side != "NONE":
                st.session_state.buy_price = live_price
                st.session_state.in_position = True
                st.session_state.current_side = "LONG" if decision_side == "BUY" else "SHORT"
                st.session_state.all_trades_history.append({
                    "Time": time.strftime("%H:%M:%S"), "Coin": target_symbol,
                    "Action": f"OPEN {st.session_state.current_side}", "Price": live_price,
                    "Target": f"${(live_price + price_jump_target) if decision_side == 'BUY' else (live_price - price_jump_target)}",
                    "Trading Fee ($)": f"-{estimated_fee/2:.3f}", "Net P&L ($)": "0.00", "Status": "RUNNING"
                })
            st.rerun()
        elif st.session_state.in_position:
            is_long_pos = st.session_state.current_side == "LONG"
            is_profit_hit = live_price >= (st.session_state.buy_price + price_jump_target) if is_long_pos else live_price <= (st.session_state.buy_price - price_jump_target)
            is_stop_hit = live_price <= (st.session_state.buy_price - stop_loss_gap) if is_long_pos else live_price >= (st.session_state.buy_price + stop_loss_gap)
            if is_profit_hit or is_stop_hit:
                status_tag = "PROFIT 🟢" if is_profit_hit else "STOPLOSS 🔴"
                net_pnl = floating_pnl - estimated_fee
                st._global_user_pnl_history.append({
                    "Date": time.strftime("%Y-%m-%d"), "Time": time.strftime("%H:%M:%S"),
                    "User ID": allocated_user_id, "Coin": target_symbol,
                    "Action": f"CLOSE {st.session_state.current_side}", "Net P&L ($)": f"{net_pnl:.2f}",
                    "Type": "REAL" if is_real_live else "DEMO"
                })
                if is_profit_hit:
                    st.session_state.win_count += 1
                    db_save("state_win_count", st.session_state.win_count)
                else:
                    st.session_state.loss_count += 1
                    db_save("state_loss_count", st.session_state.loss_count)
                if not is_real_live:
                    st.session_state.demo_balance += net_pnl
                    db_save("state_demo_balance", st.session_state.demo_balance)
                if st._mlm_bonus_enabled and my_sponsor_id != "None":
                    current_parent = my_sponsor_id
                    for gen in range(1, 8):
                        if current_parent in st._central_user_creds:
                            p_user = st._uid_to_username.get(current_parent, current_parent)
                            roi_rate = st._mlm_gen_rates.get(gen, 0.0) / 100.0
                            if net_pnl > 0:
                                bonus_credited = net_pnl * roi_rate
                                st._global_user_pnl_history.append({
                                    "Date": time.strftime("%Y-%m-%d"), "Time": time.strftime("%H:%M:%S"),
                                    "User ID": current_parent, "Coin": f"GEN {gen} ROI",
                                    "Action": f"COMMISSION FROM {st.session_state.logged_in_user}",
                                    "Net P&L ($)": f"{bonus_credited:.2f}", "Type": "REAL" if is_real_live else "DEMO"
                                })
                            current_parent = st._central_user_creds.get(p_user, {}).get("sponsor", "None")
                        else:
                            break
                for idx, trade in enumerate(st.session_state.all_trades_history):
                    if trade["Status"] == "RUNNING" and trade["Coin"] == target_symbol:
                        st.session_state.all_trades_history[idx]["Status"] = status_tag
                        st.session_state.all_trades_history[idx]["Net P&L ($)"] = f"{net_pnl:.2f}"
                db_save("pnl_history", st._global_user_pnl_history)
                st.session_state.in_position = False
                st.session_state.buy_price = 0.0
                st.session_state.current_side = "NONE"
                st.rerun()
        time.sleep(1)
        st.rerun()
    except:
        time.sleep(1)
        st.rerun()
else:
    st.info("Engine Inactive. Invoke green trigger to start loop sequences.")

st.subheader("📋 Permanent Trading Action History")
if st.session_state.all_trades_history:
    st.dataframe(
        pd.DataFrame(st.session_state.all_trades_history).iloc[::-1], 
        use_container_width=True
    )
