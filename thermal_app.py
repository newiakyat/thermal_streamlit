import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import io

# --- PAGE CONFIG ---
st.set_page_config(page_title="Thermal Analysis Dashboard", layout="wide", page_icon="🌡️")

# Initialize session state for IP addresses
if 'ips' not in st.session_state:
    st.session_state.ips = ['10.x.x.x']
    
# new
if 'selections' not in st.session_state:
    st.session_state.selections = {}  # Store {ip_index: {'date': ..., 'mdw': ..., 'msn': ...}}

st.title("Thermal Data Analysis Dashboard")
st.markdown("Navigate through the network directory to analyze `AmPsI2I.csv` logs.")

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("Network Settings")



# Add new IP button
if st.sidebar.button("➕ Add IP"):
    st.session_state.ips.append(f"Address {len(st.session_state.ips)+1}")

    # st.rerun()


for i, ip in enumerate(st.session_state.ips):
    # st.text(f"value of i: {i}, value of ip: {ip}")
    col1, col2 = st.sidebar.columns([3, 1])
    with col1:
        st.session_state.ips[i] = st.text_input(f"IP Address {i+1}", value=ip, key=f"ip_{i}")

    with col2:
        if st.button("➖", key=f"remove_{i}") and len(st.session_state.ips) >= 1:
            st.session_state.ips.pop(i)
            st.rerun()


# --- HELPER FUNCTIONS ---
def get_subfolders(path):
    """Safely list directories in a path."""
    try:
        if os.path.exists(path):
            return [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
        return []
    except Exception as e:
        st.error(f"Access Error: {e}")
        return []

def prepare_data(df):
    """Applies the logic from ThermalVisualization.py"""
    # Calculate backdiff: absolute difference between previous and current Servo Track
    df['backdiff'] = abs(df['FTC Servo Track'].shift(1) - df['FTC Servo Track'])
    df['backdiff'] = df['backdiff'].fillna(0)
    
    ordered_columns = ['Spiral Count', 'Spiral Number', 'LastFindTrackCenterPosition', 
        'FTC Servo Track', 'PID Posn Error', 'backdiff', 
        'mS FTC time', 'PWupdate', 'nS LastIndex2SIM', 
        'nS diffInx2SIM', 'AvgChangeInIndexToSIM', 'ns Time Correction']
    
    for col in ordered_columns:
        if col not in df.columns:
            df[col] = np.nan
            
    prepared_df = df[ordered_columns].copy()
    
    # Convert 'Spiral Count' to consecutive integers starting from 1
    prepared_df['Spiral Count'] = range(1, len(prepared_df) + 1)
    
    # Find second occurrence where Spiral Number is 0
    zero_spiral_indices = prepared_df.index[prepared_df['Spiral Number'] == 0].tolist()
    zero_spiral = zero_spiral_indices[1]+1 if len(zero_spiral_indices) > 1 else -1
    
    return prepared_df, zero_spiral

def plot_thermal_graphs(df, msn_name):
    """Generates the 4 graphs using matplotlib for Streamlit."""
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle(f'Thermal Analysis: {msn_name}', fontsize=20, fontweight='bold')
    for ax in axes.flat:
        ax.axvline(x=zero_spiral, color='red', linestyle='--', linewidth=1)

    # Color palette
    colors = ['#1f77b4', '#2ca02c', '#d62728', '#9467bd']

    # 1. FTC Servo Track
    axes[0, 0].plot(df['Spiral Count'], df['FTC Servo Track'], color=colors[0])
    axes[0, 0].set_title('FTC Servo Track vs Spiral Count', fontsize=14)
    axes[0, 0].set_ylabel('Servo Track')
    axes[0, 0].grid(True, linestyle='--', alpha=0.6)

    # 2. mS FTC time
    axes[0, 1].plot(df['Spiral Count'], df['mS FTC time'], color=colors[1])
    axes[0, 1].set_title('mS FTC Time vs Spiral Count', fontsize=14)
    axes[0, 1].set_ylabel('Time (ms)')
    axes[0, 1].grid(True, linestyle='--', alpha=0.6)

    # 3. Backdiff
    axes[1, 0].plot(df['Spiral Count'], df['backdiff'], color=colors[2])
    axes[1, 0].set_title('Backdiff vs Spiral Count', fontsize=14)
    axes[1, 0].set_xlabel('Spiral Count')
    axes[1, 0].set_ylabel('Difference')
    axes[1, 0].grid(True, linestyle='--', alpha=0.6)

    # 4. PWupdate
    axes[1, 1].plot(df['Spiral Count'], df['PWupdate'], color=colors[3])
    axes[1, 1].set_title('PWupdate vs Spiral Count', fontsize=14)
    axes[1, 1].set_xlabel('Spiral Count')
    axes[1, 1].set_ylabel('Value')
    axes[1, 1].grid(True, linestyle='--', alpha=0.6)

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    return fig

# --- DYNAMIC NAVIGATION UI ---
if st.session_state.ips:
    # Create tabs for each IP
    tab_names = [f"IP: {ip.strip()}" if ip.strip() else f"IP {i+1}" for i, ip in enumerate(st.session_state.ips)]
    tabs = st.tabs(tab_names)
    
    for i, (tab, ip) in enumerate(zip(tabs, st.session_state.ips)):
        with tab:
            ip = ip.strip()
            if ip:
                base_dir = rf"\\{ip}\c\data\ammonite"
                
                if i not in st.session_state.selections:
                    st.session_state.selections[i] = {'date': "-- Select --", 'mdw': "-- Select --", 'msn': "-- Select --"}
                
                # 1. Select Date
                dates = get_subfolders(base_dir)
                # st.text(f"value of dates: {dates}")
                if dates:
                    date_options = ["-- Select --"] + sorted(dates, reverse=True)
                    date_index = date_options.index(st.session_state.selections[i]['date']) if st.session_state.selections[i]['date'] in date_options else 0
                    selected_date = st.selectbox("📅 Select Date", options=date_options, 
                                                key=f"date_{i}",
                                                index=date_index)
                    st.session_state.selections[i]['date'] = selected_date                    
                     
                    
                    if selected_date != "-- Select --":
                        # 2. Select MDW and Cell
                        date_path = os.path.join(base_dir, st.session_state.selections[i]['date']) if st.session_state.selections[i]['date'] != "-- Select --" else base_dir
                        mdws = get_subfolders(date_path)
                        mdw_options = ["-- Select --"] + sorted(mdws)
                        mdw_index = mdw_options.index(st.session_state.selections[i]['mdw']) if st.session_state.selections[i]['mdw'] in mdw_options else 0
                        selected_mdw = st.selectbox("🏭 Select MDW and Cell", options=mdw_options, 
                                                    key=f"mdw_{i}",
                                                    index=mdw_index)
                        st.session_state.selections[i]['mdw'] = selected_mdw                         
                        
                        if selected_mdw != "-- Select --":
                            # 3. Select MSN
                            mdw_path = os.path.join(date_path, selected_mdw)
                            msns = get_subfolders(mdw_path)
                            msn_options = ["-- Select --"] + sorted(msns)
                            msn_index = msn_options.index(st.session_state.selections[i]['msn']) if st.session_state.selections[i]['msn'] in msn_options else 0
                            selected_msn = st.selectbox("🆔 Select MSN", options=msn_options, 
                                                        key=f"msn_{i}",
                                                        index=msn_index)
                            st.session_state.selections[i]['msn'] = selected_msn                   
                            
                            if selected_msn != "-- Select --":
                                # Construct Final Path
                                target_file = os.path.join(mdw_path, selected_msn, "thermal_data", "AmPsI2I.csv")
                                
                                st.divider()
                                
                                if os.path.exists(target_file):
                                    st.success(f"File Found: `{target_file}`")
                                    
                                    # Data Loading & Processing
                                    try:
                                        raw_df = pd.read_csv(target_file)
                                        processed_df, zero_spiral = prepare_data(raw_df)
                                        
                                        # Layout for Metrics
                                        col1, col2, col3, col4, col5 = st.columns(5)
                                        col1.metric("Max FTC Servo Track", f"{processed_df['FTC Servo Track'].max():.3f}")
                                        col2.metric("Max mS FTC time", f"{processed_df['mS FTC time'].max():.3f}")
                                        col3.metric("Max Backdiff", f"{processed_df['backdiff'].max():.6f}")
                                        col4.metric("Min PWupdate", f"{processed_df['PWupdate'].min():.3f}")
                                        col5.metric("0_Spiral", f"{zero_spiral}")

                                        # Plotting
                                        st.subheader("Visual Analysis")
                                        fig = plot_thermal_graphs(processed_df, selected_msn)
                                        st.pyplot(fig)
                                        
                                        buf = io.BytesIO()
                                        fig.savefig(buf, format="png", dpi=150, bbox_inches='tight')
                                        buf.seek(0)
                                        st.download_button(
                                            label="📥 Download as PNG",
                                            data=buf,
                                            file_name=f"thermal_analysis_{selected_msn}.png",
                                            mime="image/png",
                                            key=f"download_{i}"
                                        )
                                        
                                        # Option to view/download data
                                        # with st.expander("View Raw Data Table"):
                                        #     st.dataframe(processed_df)
                                            
                                    except Exception as e:
                                        st.error(f"Error processing CSV: {e}")
                                else:
                                    st.warning(f"Expected file not found at: `{target_file}`")
                else:
                    st.warning("No folders found. Check IP or Permissions.")
            else:
                st.info("Please enter a valid IP address in the sidebar to start.")
else:
    st.info("Please add at least one IP address in the sidebar.")