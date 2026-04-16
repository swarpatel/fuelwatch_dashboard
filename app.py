import streamlit as st
import feedparser
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
import datetime
import pytz

st.set_page_config(layout="wide", page_title="WA Fuel Dashboard")

# Hide Streamlit UI elements
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .block-container {
                padding-top: 1rem;
                padding-bottom: 1rem;
                padding-left: 1rem;
                padding-right: 1rem;
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)
                

# Initialize session state for the radius and ZIP
if "radius_km" not in st.session_state:
    st.session_state.radius_km = None
if "zip_input" not in st.session_state:
    st.session_state.zip_input = ""

# Handle dynamic ZIP changes
def handle_zip_change():
    if st.session_state.zip_input and st.session_state.radius_km is None:
        st.session_state.radius_km = 5
    elif not st.session_state.zip_input:
        st.session_state.radius_km = None

# Clear ZIP and radius
def clear_zip():
    st.session_state.zip_input = ""
    st.session_state.radius_km = None

@st.cache_data(ttl=3600)
def fetch_fuel_data(product_id=1, river_side="All", day="today"):
    # Append the &Day parameter to the native FuelWatch URLs
    if river_side == "North":
        url = f"https://www.fuelwatch.wa.gov.au/fuelwatch/fuelWatchRSS?Product={product_id}&Region=25&Day={day}"
    elif river_side == "South":
        url = f"https://www.fuelwatch.wa.gov.au/fuelwatch/fuelWatchRSS?Product={product_id}&Region=26&Day={day}"
    else:
        url = f"https://www.fuelwatch.wa.gov.au/fuelwatch/fuelWatchRSS?Product={product_id}&StateRegion=98&Day={day}"
        
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
    # Added "Australia" to improve ZIP code accuracy
    location = geolocator.geocode(f"{suburb}, Western Australia, Australia")
    return (location.latitude, location.longitude) if location else None

st.sidebar.header("Filters")
fuel_options = {
    "ULP": 1, 
    "PULP": 2, 
    "Diesel": 4,
    "Brand Diesel": 11,
    "LPG": 5,
    "98 RON": 6,
    "E85": 10
}
fuel_type = st.sidebar.selectbox("Fuel Type", fuel_options.items(), format_func=lambda x: x[0])
river_side = st.sidebar.radio("River Side", ["All", "North", "South"])

df = fetch_fuel_data(fuel_type[1], river_side)
brands = st.sidebar.multiselect("Brand", df["brand"].unique())

zip_col, btn_col = st.sidebar.columns([5, 1])

with zip_col:
    suburb_input = st.text_input(
        "Suburb ZIP (for radius)", 
        key="zip_input",
        on_change=handle_zip_change
    )

with btn_col:
    st.write("<br>", unsafe_allow_html=True)
    st.button("✖", help="Clear ZIP", on_click=clear_zip)

radius_km = st.sidebar.selectbox(
    "Radius", 
    [None, 5, 10, 20], 
    format_func=lambda x: f"{x} KM" if x else "None",
    key="radius_km"
)

filtered_df = df.copy()

if brands:
    filtered_df = filtered_df[filtered_df["brand"].isin(brands)]

# Initialize center variable early so the map can use it later
center = None

if suburb_input:
    center = get_coordinates(suburb_input)
    if center and st.session_state.radius_km:
        filtered_df["distance"] = filtered_df.apply(
            lambda row: geodesic(center, (row["latitude"], row["longitude"])).km, axis=1
        )
        filtered_df = filtered_df[filtered_df["distance"] <= st.session_state.radius_km]

# Perth is in the AWST timezone
perth_tz = pytz.timezone('Australia/Perth')
current_time = datetime.datetime.now(perth_tz)
publish_time = current_time.replace(hour=14, minute=30, second=0, microsecond=0) # FuelWatch publishes tomorrow's prices at 2:30 PM

# Only run this logic if it is past 2:30 PM in Perth
if current_time >= publish_time:
    df_tomorrow = fetch_fuel_data(fuel_type[1], river_side, day="tomorrow")
    
    if not df_tomorrow.empty and not filtered_df.empty:
        # Merge tomorrow's price into the main dataframe
        tomorrow_subset = df_tomorrow[['brand', 'address', 'price']].rename(columns={'price': 'price_tomorrow'})
        filtered_df = pd.merge(filtered_df, tomorrow_subset, on=['brand', 'address'], how='left')

        # Create filtered dataframe for tomorrow to find the true lowest
        filtered_tomorrow = df_tomorrow.copy()

        if brands:
            filtered_tomorrow = filtered_tomorrow[filtered_tomorrow["brand"].isin(brands)]
            
        if center and st.session_state.radius_km:
            filtered_tomorrow["distance"] = filtered_tomorrow.apply(
                lambda row: geodesic(center, (row["latitude"], row["longitude"])).km, axis=1
            )
            filtered_tomorrow = filtered_tomorrow[filtered_tomorrow["distance"] <= st.session_state.radius_km]
            
        if not filtered_tomorrow.empty:
            today_min = filtered_df['price'].min()
            
            # Find the exact station with the lowest price tomorrow
            tomorrow_min_idx = filtered_tomorrow['price'].idxmin()
            best_tomorrow = filtered_tomorrow.loc[tomorrow_min_idx]
            tomorrow_min = best_tomorrow['price']
            
            diff = round(tomorrow_min - today_min, 1)
            station_info = f"**{best_tomorrow['brand']} - {best_tomorrow['location']}** ({tomorrow_min} c/L)"
            
            if diff > 0:
                st.error(f"🚨 **FILL UP TODAY!** The cheapest price tomorrow will jump to {station_info}, an increase of {diff} c/L.")
            elif diff < 0:
                st.success(f"⏳ **WAIT!** The cheapest price tomorrow will drop to {station_info}, a saving of {abs(diff)} c/L.")
            else:
                st.info(f"⚖️ **PRICES STABLE:** The cheapest price tomorrow remains {station_info}.")
                
col1, col2 = st.columns([1, 2])
selected_station = None

with col1:
    st.subheader("Lowest Price")
    if not filtered_df.empty:
        min_idx = filtered_df['price'].idxmin()
        best = filtered_df.loc[min_idx]
        st.metric(label=f"{best['brand']} - {best['location']}", value=f"{best['price']} c/L")
        
        st.caption("💡 **Tip:** Check the box on the far left of any row to view that station on the map.")
        
        display_df = filtered_df.sort_values("price").reset_index(drop=True)
        
        # Dynamically build the columns list based on whether tomorrow's data exists
        display_cols = ["brand", "price"]
        if "price_tomorrow" in display_df.columns:
            display_cols.append("price_tomorrow")
        display_cols.extend(["location", "address"])
        
        event = st.dataframe(
            display_df[display_cols], # Use the dynamic columns list
            use_container_width=True, 
            height=500,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )
        
        if event.selection.rows:
            selected_row_idx = event.selection.rows[0]
            selected_station = display_df.iloc[selected_row_idx]
            
            st.divider()
            st.markdown("### ⛽ Selected Station")
            st.write(f"**{selected_station['brand']} - {selected_station['location']}**")
            st.write(f"**Price:** {selected_station['price']} c/L")
            
            full_address = f"{selected_station['address']} {selected_station['location']}"
            
            # USED ST.CODE TO CREATE A NATIVE CLICK-TO-COPY BUTTON FOR THE ADDRESS
            st.caption("Address (Hover to copy to clipboard):")
            st.code(full_address, language=None)
            
            maps_url = f"https://www.google.com/maps/search/?api=1&query={selected_station['latitude']},{selected_station['longitude']}"
            st.link_button("🗺️ Get Directions on Google Maps", maps_url)

    else:
        st.warning("No stations found matching filters.")

with col2:
    st.subheader("Map View")
    if not filtered_df.empty:
        # Default view averages the filtered stations
        center_lat = filtered_df["latitude"].mean()
        center_lon = filtered_df["longitude"].mean()
        zoom = 11

        # Level 1 Override: Zoom to ZIP code if entered
        if center is not None:
            center_lat, center_lon = center
            zoom = 13 

        # Level 2 Override: Zoom tightly to clicked station
        if selected_station is not None:
            center_lat = selected_station['latitude']
            center_lon = selected_station['longitude']
            zoom = 15 
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom)
        
        for _, row in filtered_df.iterrows():
            is_selected = selected_station is not None and row['latitude'] == selected_station['latitude'] and row['longitude'] == selected_station['longitude']
            color = 'red' if is_selected else 'blue'

            maps_url = f"https://www.google.com/maps/search/?api=1&query={row['latitude']},{row['longitude']}"
            
            popup_html = f"""
            <div style="min-width: 220px; font-family: sans-serif;">
                <b>{row['brand']}</b><br>
                <span style="font-size: 1.2em; font-weight: bold;">{row['price']} c/L</span><br>
                <span style="color: gray; font-size: 0.9em;">{row['address']}</span><br><br>
                <a href="{maps_url}" target="_blank" style="background-color: #4CAF50; color: white; padding: 8px 12px; text-decoration: none; border-radius: 4px; display: inline-block; text-align: center; width: 100%; box-sizing: border-box;">
                    🗺️ Open in Google Maps
                </a>
            </div>
            """

            folium.Marker(
                [row["latitude"], row["longitude"]],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"{row['price']}c",
                icon=folium.Icon(color=color)
            ).add_to(m)
            
        st_folium(m, use_container_width=True, height=950, returned_objects=[])