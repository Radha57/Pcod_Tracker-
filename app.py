# app.py
# Enhanced PCOD Lifestyle Tracker — with Symptom Tracker added
import os
import tempfile
import shutil
import re
from datetime import date, datetime, timedelta
import pandas as pd
import streamlit as st

# ---------- Config ----------
APP_TITLE = "CR Wellness · PCOD Lifestyle Tracker"
DATA_DIR = "data"
DATA_FILE = os.path.join(DATA_DIR, "pcod_data.csv")
RETRY_SAVE = 2  # retry attempts on write failure

# ---------- Utilities ----------
def ensure_datafile():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=[
            "date","exercise","water_glasses","notes",
            "mood","cramps","bloating","energy_level","saved_at"
        ])
        df.to_csv(DATA_FILE, index=False)

@st.cache_data
def load_data() -> pd.DataFrame:
    """Load CSV and normalize date column. Cached for speed; cleared after save."""
    ensure_datafile()
    try:
        df = pd.read_csv(DATA_FILE, parse_dates=["date","saved_at"])
    except Exception:
        df = pd.DataFrame(columns=[
            "date","exercise","water_glasses","notes",
            "mood","cramps","bloating","energy_level","saved_at"
        ])
    if "date" in df and not df.empty:
        df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    return df

def atomic_write_df(df: pd.DataFrame, path: str):
    """Write df to a temp file and move it to path to avoid partial writes."""
    dirn = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=dirn, prefix="tmp_pcod_")
    os.close(fd)
    try:
        df.to_csv(tmp, index=False)
        shutil.move(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass

def save_entry(entry_date: date, exercise: str, water_glasses: int,
               notes: str, mood: str, cramps: str, bloating: str, energy_level: int) -> dict:
    """Save or update the row for a given date. Returns the saved row dict."""
    ensure_datafile()
    attempts = 0
    while attempts <= RETRY_SAVE:
        try:
            df = load_data().copy()
            entry_date_norm = pd.to_datetime(entry_date).normalize()
            saved_at = pd.to_datetime(datetime.now())
            new_row = {
                "date": entry_date_norm,
                "exercise": exercise.strip(),
                "water_glasses": int(water_glasses),
                "notes": notes.strip(),
                "mood": mood,
                "cramps": cramps,
                "bloating": bloating,
                "energy_level": int(energy_level),
                "saved_at": saved_at
            }
            # if date exists -> update row
            if not df.empty and (df["date"].dt.date == entry_date_norm.date()).any():
                idx = df.index[df["date"].dt.date == entry_date_norm.date()][0]
                for k,v in new_row.items():
                    df.at[idx, k] = v
            else:
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df = df.sort_values("date").reset_index(drop=True)
            atomic_write_df(df, DATA_FILE)
            try:
                load_data.clear()
            except Exception:
                pass
            return new_row
        except Exception as e:
            attempts += 1
            last_exc = e
    raise IOError(f"Failed to save entry after {RETRY_SAVE+1} attempts. Error: {last_exc}")

def get_last_n_days(df: pd.DataFrame, n=7) -> pd.DataFrame:
    if df.empty:
        return df
    cutoff = pd.Timestamp(date.today() - timedelta(days=n-1))
    return df[df["date"] >= cutoff]

def compute_streak(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    days_logged = set(pd.to_datetime(df["date"]).dt.date)
    streak = 0
    cur = date.today()
    while cur in days_logged:
        streak += 1
        cur = cur - timedelta(days=1)
    return streak

def parse_reps(ex_text: str) -> int:
    nums = re.findall(r"\d+", ex_text or "")
    return sum(int(n) for n in nums) if nums else 0

def daily_tip(water: int, exercise_text: str) -> str:
    tips = []
    if water < 8:
        tips.append("Try to reach 8–10 glasses of water today.")
    reps = parse_reps(exercise_text)
    if reps == 0:
        tips.append("Even 10 mins of walk or stretching helps.")
    else:
        tips.append("Nice work — consistency beats intensity.")
    if not tips:
        tips.append("Keep steady — sleep well and reduce stress.")
    return " • ".join(tips)

def award_badges(df: pd.DataFrame) -> list:
    badges = []
    if df.empty:
        return badges
    total = df.shape[0]
    water10 = (df["water_glasses"] >= 10).sum()
    streak = compute_streak(df)
    if total >= 3:
        badges.append("🎯 Habit Starter (3+ days)")
    if water10 >= 3:
        badges.append("💧 Hydration Hero (10+ glasses on 3 days)")
    if streak >= 5:
        badges.append("🔥 5-Day Streak")
    if total >= 14:
        badges.append("🌟 Consistency Champion (14+ logs)")
    return badges

# ---------- Styling ----------
def inject_css():
    st.markdown(
        """
        <style>
        .stApp { 
            max-width: 1000px; 
            margin: 0 auto; 
            font-family: 'Segoe UI', Roboto, sans-serif; 
        }

        /* Hero Section - unchanged layout, only better colors */
        .hero { 
            background: #fff5f8; 
            padding: 20px;  /* same padding as before */
            border-radius: 12px; 
            margin-bottom: 20px; 
            border: 1px solid #f7c6d8; /* soft border */
        }

        .hero h1 {
            color: #d81b60; /* similar pink but deeper */
            font-weight: 700;
            font-size: 2rem; /* same size */
            margin: 0;
        }

        /* Badge Colors */
        .badge-pill { 
            display: inline-block; 
            padding: 6px 12px; 
            border-radius: 20px; 
            background: #ffeaf0; 
            border: 1px solid #f5b1c9; 
            margin-right: 6px; 
            font-size: 0.95rem; 
            color: #ad1457;
            font-weight: 500;
        }

        /* Tip Box */
        .coach { 
            border-left: 4px solid #10b981; 
            background: #f0fdf4; 
            padding: 12px; 
            border-radius: 8px; 
            color: #065f46; 
            font-weight: 500;
            margin-top: 12px;
        }

        .note { 
            color: #555; 
            font-size: 0.95rem; 
            margin-top: 6px; 
        }

        .muted { 
            color: #777; 
            font-size: 0.9rem; 
        }

        .accent-btn > button { 
            background: linear-gradient(90deg,#ff7aa8,#ffb580); 
            color: #fff; 
            font-weight: 600; 
        }
        </style>
        """, unsafe_allow_html=True
    )

# ---------- App UI ----------
st.set_page_config(page_title=APP_TITLE, page_icon="💖", layout="centered")
inject_css()

st.markdown(f'<div class="hero"><h1 style="margin:0">{APP_TITLE}</h1><div class="note">A simple, friendly tracker to help you be consistent — quick to use, easy to maintain.</div></div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("About")
    st.markdown("**Track:** Beginner / Lifestyle\n\n**Built for:** HackSocial 2025")
    df_all = load_data()
    if not df_all.empty:
        st.download_button("⬇️ Download Data (CSV)", df_all.to_csv(index=False).encode("utf-8"), file_name="pcod_data_export.csv")
    if st.button("🧹 Clear All Data"):
        ensure_datafile()
        pd.DataFrame(columns=[
            "date","exercise","water_glasses","notes",
            "mood","cramps","bloating","energy_level","saved_at"
        ]).to_csv(DATA_FILE, index=False)
        load_data.clear()
        st.success("Cleared all data.")

# Input
st.subheader("Today's Entry")
col1, col2 = st.columns([2,1])
with col1:
    entry_date = st.date_input("Date", value=date.today(), max_value=date.today())
    exercise = st.text_input("Exercise (e.g., 10 squats, 2 min butterfly stretch, walk 15m)")
    notes = st.text_area("Notes / Mood (optional)")
with col2:
    water_glasses = st.number_input("Water (glasses)", min_value=0, max_value=20, value=0, step=1)
    st.markdown("<div class='muted'>Use whole numbers for water (glasses).</div>", unsafe_allow_html=True)
    st.write("")  # spacer

# --- Symptom Tracker ---
st.markdown("### Symptom Tracker")
mood = st.selectbox("Mood", ["Good", "Okay", "Bad"])
cramps = st.selectbox("Cramps", ["None", "Mild", "Severe"])
bloating = st.radio("Bloating", ["No", "Yes"])
energy_level = st.slider("Energy Level (1=Low, 5=High)", 1, 5, 3)

# Save action
if st.button("Save Entry", key="save", help="Save today's entry"):
    try:
        saved = save_entry(entry_date, exercise, water_glasses, notes,
                           mood, cramps, bloating, energy_level)
        st.success("Saved! ✅ Your entry was recorded.")
        df_now = load_data()
        streak = compute_streak(df_now)
        if streak in (1,3,5,7,14):
            st.balloons()
            st.success(f"Milestone — {streak}-day streak! Keep going 💪")
        st.markdown("**Last Saved Entry:**")
        display_df = pd.DataFrame([{
            "date": pd.to_datetime(saved["date"]).date(),
            "exercise": saved["exercise"],
            "water_glasses": saved["water_glasses"],
            "mood": saved["mood"],
            "cramps": saved["cramps"],
            "bloating": saved["bloating"],
            "energy_level": saved["energy_level"],
            "notes": saved["notes"],
            "saved_at": pd.to_datetime(saved["saved_at"]).strftime("%Y-%m-%d %H:%M:%S")
        }])
        st.table(display_df)
    except Exception as e:
        st.error(f"Could not save entry: {e}")

# Data & Insights
df = load_data()

st.subheader("Progress • Insights")
if df.empty:
    st.info("No entries yet. Log today's entry to begin your streak!")
else:
    df7 = get_last_n_days(df, n=7)
    if not df7.empty:
        st.markdown("**Last 7 days — Water intake**")
        st.line_chart(df7.set_index("date")["water_glasses"])
    df30 = get_last_n_days(df, n=30)
    if not df30.empty:
        st.markdown("**Last 30 days — Logs (counts)**")
        counts = df30.groupby(df30["date"].dt.date).size().rename("entries")
        st.bar_chart(counts)

# Streaks & Badges
st.subheader("Streaks • Badges • Coach")
streak_val = compute_streak(df)
colA, colB = st.columns(2)
colA.metric("Current Streak", f"{streak_val} day(s)")
colB.metric("Total Logged Days", f"{0 if df.empty else df.shape[0]}")

badges = award_badges(df)
if badges:
    st.markdown("**Badges earned:**")
    st.markdown("".join([f"<span class='badge-pill'>{b}</span>" for b in badges]), unsafe_allow_html=True)

st.markdown(f"<div class='coach'>{daily_tip(water_glasses, exercise)}</div>", unsafe_allow_html=True)

with st.expander("Daily Wellness Suggestions"):
    st.markdown("""
    - Drink warm water in the morning to improve metabolism.
    - Include fiber-rich foods; choose whole grains, lentils, veggies.
    - Keep breakfast protein-rich; avoid long fasting windows.
    - 10 minutes of walking after meals helps digestion and glucose control.
    - Try deep breathing or yoga for stress reduction.
    - Limit sugary drinks and ultra-processed snacks.
    - Aim for 7–8 hours of sleep to support hormonal balance.
    """)

st.caption("Disclaimer: This app is for wellness tracking and educational purposes only — not medical advice.")

