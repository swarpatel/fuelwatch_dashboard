import streamlit as st
import feedparser
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic
from geopy.geocoders import Nominatim

# 1. Page Config MUST be the first Streamlit command
st.set_page_config(layout="wide", page_title="WA Fuel Dashboard")

# 2. Inject Custom CSS to hide Streamlit UI and maximize screen space
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            /* Reduce whitespace at the top and sides */
            .block-container {
                padding-top: 1rem;
                padding-bottom: 1rem;
                padding-left: 1rem;
                padding-right: 1rem;
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def fetch_fuel_data(product_id=1, river_side="All"):
    if river_side == "North":
        url = f"https://www.fuelwatch.wa.gov.au/fuelwatch/fuelWatchRSS?Product={product_id}&Region=25"
    elif river_side == "South":
        url = f"https://www.fuelwatch.wa.gov.au/fuelwatch/fuelWatchRSS?Product={product_id}&Region=26"
    else:
        url = f"https://www.fuelwatch.wa.gov.au/fuelwatch/fuelWatchRSS?Product={product_id}&StateRegion=98"
        
    feed = feedparser.parse(url)
    
    data = []
    for entry in feed.entries:
        data.append({
            "brand": entry.get("brand", "Unknown"),
            "price": float(entry.get("price", 0)),
            "location": entry.get("location", ""),
            "address": entry.get("address", ""),
            "latitude": float(entry.get("latitude", 0)),
            "longitude": float(entry.get("longitude", 0)),
        })
    return pd.DataFrame(data)

def get_coordinates(suburb):
    geolocator = Nominatim(user_agent="fuel_dash")
    location = geolocator.geocode(f"{suburb}, Western Australia")
    return (location.latitude, location.longitude) if location else None

# Sidebar Filters (Automatically collapses into a menu on mobile)
st.sidebar.header("Filters")
fuel_type = st.sidebar.selectbox("Fuel Type", {"ULP": 1, "PULP": 2, "Diesel": 4}.items(), format_func=lambda x: x[0])
river_side = st.sidebar.radio("River Side", ["All", "North", "South"])

df = fetch_fuel_data(fuel_type[1], river_side)

brands = st.sidebar.multiselect("Brand", df["brand"].unique())
suburb_input = st.sidebar.text_input("Suburb (for radius)")
radius_km = st.sidebar.selectbox("Radius", [None, 5, 10, 20], format_func=lambda x: f"{x} KM" if x else "None")

filtered_df = df.copy()

if brands:
    filtered_df = filtered_df[filtered_df["brand"].isin(brands)]

if suburb_input and radius_km:
    center = get_coordinates(suburb_input)
    if center:
        filtered_df["distance"] = filtered_df.apply(
            lambda row: geodesic(center, (row["latitude"], row["longitude"])).km, axis=1
        )
        filtered_df = filtered_df[filtered_df["distance"] <= radius_km]

# 3. Layout: Streamlit stacks these on mobile, but keeps them side-by-side on desktop
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Lowest Price")
    if not filtered_df.empty:
        min_idx = filtered_df['price'].idxmin()
        best = filtered_df.loc[min_idx]
        st.metric(label=f"{best['brand']} - {best['location']}", value=f"{best['price']} c/L")
        
        # Increase height and use container width to maximize space
        st.dataframe(
            filtered_df[["brand", "price", "location"]].sort_values("price"), 
            use_container_width=True, 
            height=700,
            hide_index=True # Cleaner look
        )
    else:
        st.warning("No stations found matching filters.")

with col2:
    st.subheader("Map View")
    if not filtered_df.empty:
        m = folium.Map(location=[filtered_df["latitude"].mean(), filtered_df["longitude"].mean()], zoom_start=11)
        
        for _, row in filtered_df.iterrows():
            folium.Marker(
                [row["latitude"], row["longitude"]],
                popup=f"{row['brand']}: {row['price']}c",
                tooltip=f"{row['price']}c"
            ).add_to(m)
            
        # Make the map completely responsive to the column width
        st_folium(m, use_container_width=True, height=700, returned_objects=[])