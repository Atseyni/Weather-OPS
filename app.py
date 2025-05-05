import streamlit as st
import requests
from datetime import datetime
import pandas as pd

API_KEY = st.secrets["API_KEY"]
AVWX_TOKEN = st.secrets["AVWX_TOKEN"]

@st.cache_data(show_spinner=False)
def get_weather(city):
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric&lang=fr"
    r = requests.get(url)
    data = r.json()
    if 'main' in data and 'weather' in data:
        temp = data['main']['temp']
        desc = data['weather'][0]['description']
        icon = data['weather'][0]['icon']
        wind = data['wind']['speed']
        pressure = data['main']['pressure']
        return {
            "temp": temp,
            "desc": desc,
            "icon": f"http://openweathermap.org/img/wn/{icon}@2x.png",
            "wind": round(wind * 1.94384, 1),
            "pressure": pressure,
            "city": city
        }
    return None

@st.cache_data(show_spinner=False)
def get_metar(icao):
    url = f"https://avwx.rest/api/metar/{icao}?token={AVWX_TOKEN}&format=json"
    r = requests.get(url)
    if r.status_code == 200:
        data = r.json()
        return data.get("raw", ""), data.get("sanitized", "")
    return None, None

@st.cache_data(show_spinner=False)
def get_taf(icao):
    url = f"https://avwx.rest/api/taf/{icao}?token={AVWX_TOKEN}&format=json"
    r = requests.get(url)
    if r.status_code == 200:
        data = r.json()
        return data.get("raw", ""), data.get("sanitized", "")
    return None, None

@st.cache_data(show_spinner=False)
def get_station_name(icao):
    url = f"https://avwx.rest/api/station/{icao}?token={AVWX_TOKEN}"
    r = requests.get(url)
    if r.status_code == 200:
        data = r.json()
        return data.get("name", "Unknown name"), data.get("latitude"), data.get("longitude")
    return "Unknown name", None, None

@st.cache_data(show_spinner=False)
def get_flight_rules(visibility_m, ceiling_ft):
    if visibility_m is None or ceiling_ft is None:
        return "Insufficient data"
    if visibility_m >= 5000 and ceiling_ft >= 1500:
        return "VFR (Visual Flight Rules)"
    elif visibility_m >= 3000 and ceiling_ft >= 1000:
        return "MVFR (Marginal VFR)"
    elif visibility_m >= 1600 and ceiling_ft >= 500:
        return "IFR (Instrument Flight Rules)"
    else:
        return "LIFR (Low IFR)"

st.set_page_config(page_title="Weather OPS", layout="centered")
st.title("🛫 Weather OPS – Live METAR / TAF")

st.markdown("""
<div style='font-size:18px; line-height:1.6;'>
Welcome to <b>Weather OPS</b>, your aviation weather assistant.<br>
Enter an <b>ICAO airport code</b> to get live data:<br>
✅ Latest <b>METAR</b><br>
✅ Latest <b>TAF</b><br>
✅ <b>Map location</b><br>
✅ Auto-analysis of <b>VFR / IFR</b> conditions<br>
</div>
""", unsafe_allow_html=True)

with st.form(key="icao_form", clear_on_submit=False):
    icao_input = st.text_input("Enter ICAO code (e.g. LFPG, KLAX, EGLL):", label_visibility="collapsed").upper()
    submit = st.form_submit_button(label="Submit")

if submit and icao_input:
    try:
        metar_raw, metar_text = get_metar(icao_input)
        taf_raw, taf_text = get_taf(icao_input)
        station_name, lat, lon = get_station_name(icao_input)

        st.subheader(f"📍 {station_name} ({icao_input})")

        if lat and lon:
            df_map = pd.DataFrame({"lat": [lat], "lon": [lon]})
            st.map(df_map, zoom=6)

        with st.expander("📄 METAR (Current observation)"):
            try:
                raw_url = f"https://avwx.rest/api/metar/{icao_input}?token={AVWX_TOKEN}&format=json"
                r = requests.get(raw_url)
                data = r.json()
                vis_raw = data.get("visibility", {}).get("meters_float")
                vis = float(vis_raw) if vis_raw else None
                ceiling = None
                for cloud in data.get("clouds", []):
                    if cloud.get("base_feet_agl"):
                        ceiling = int(cloud["base_feet_agl"])
                        break

                if "CAVOK" in metar_raw.upper():
                    vis = 10000
                    ceiling = 5000

                st.markdown(f"<small>🔎 Visibility: {vis} m — Ceiling: {ceiling} ft</small>", unsafe_allow_html=True)

                rules = get_flight_rules(vis, ceiling)
                color = "green" if "VFR" in rules else "orange" if "MVFR" in rules else "red" if "IFR" in rules else "#8B0000"
                st.markdown(f"""
                <div style='padding:10px; border-radius:8px; background-color:{color}; color:white; font-weight:bold;'>
                🛫 Flight conditions: {rules}
                </div>
                """, unsafe_allow_html=True)
            except:
                st.info("Unable to analyze VFR/IFR conditions.")

            if metar_raw:
                st.code(metar_raw, language="text")
                st.caption(metar_text)
            else:
                st.warning("METAR data unavailable.")

        with st.expander("🗓️ TAF (Aeronautical forecast)"):
            if taf_raw:
                st.code(taf_raw, language="text")
                st.caption(taf_text)
            else:
                st.warning("TAF data unavailable.")

        st.markdown("""
    <small>
    <b>Flight rules legend:</b><br>
    🟢 <b>VFR</b> = Good visual conditions (>1500 ft & >5000 m)<br>
    🟠 <b>MVFR</b> = Marginal visual flight<br>
    🔴 <b>IFR</b> = Instrument flight required<br>
    🟥 <b>LIFR</b> = Low visibility / low ceiling conditions
    </small>
    """, unsafe_allow_html=True)

        st.divider()

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("🛩️ Enter a valid ICAO code to display weather data.")

st.markdown("<small>Powered by OpenWeather, AVWX & Streamlit</small>", unsafe_allow_html=True)
