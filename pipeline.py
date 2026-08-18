import os
import re
import pandas as pd
import numpy as np

def load_and_clean_turbines(filepath="wind_turbine_20220114.csv"):
    """
    Loads and cleans the turbine dataset:
    - Reads CSV with latin-1 encoding
    - Keeps specified columns (handling duplicate column names if present)
    - Replaces -9999 sentinel values with NaN
    - Reports percentage of turbines with missing eia_id
    """
    print(f"Loading turbine data from {filepath}...")
    df = pd.read_csv(filepath, encoding='latin-1', low_memory=False)
    
    desired_cols = [
        'case_id', 'eia_id', 't_state', 't_county', 'p_name', 'p_year', 
        'p_tnum', 'p_cap', 't_manu', 't_model', 't_cap', 't_hh', 't_rd', 
        't_ttlh', 'retrofit', 'retrofit_year', 't_conf_atr', 't_conf_loc', 
        'xlong', 'ylat'
    ]
    
    col_indices = []
    for col in desired_cols:
        for idx, c in enumerate(df.columns):
            if c == col and idx not in col_indices:
                col_indices.append(idx)
                break
                
    df_turb = df.iloc[:, col_indices].copy()

    # Replace -9999 with NaN
    df_turb = df_turb.replace(-9999, np.nan)

    # Report % of turbines with missing eia_id
    missing_eia_pct = df_turb['eia_id'].isna().mean() * 100
    print(f"Turbine dataset loaded. Missing eia_id: {missing_eia_pct:.2f}%")

    return df_turb


def load_eia923_year(filepath, year):
    """
    Loads and cleans EIA-923 generation and fuel data for a given year:
    - Reads 'Page 1 Generation and Fuel Data' with header=5
    - Normalizes column names (strip \n, collapse whitespace)
    - Selects and renames relevant columns to snake_case
    - Sets year column explicitly from argument
    - Filters to prime_mover == 'WT' only
    - Strips whitespace from operator_name and plant_name
    - Coerces net_gen_mwh to numeric (errors='coerce')
    - Prints warning for any expected column not found
    """
    sheet_name = 'Page 1 Generation and Fuel Data'
    print(f"Loading EIA-923 data for year {year} from {filepath}...")
    
    try:
        df = pd.read_excel(filepath, sheet_name=sheet_name, header=5)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        raise e

    # Normalize column names: replace newlines with spaces and collapse multiple spaces
    normalized_cols = {}
    for col in df.columns:
        norm_col = re.sub(r'\s+', ' ', str(col)).strip()
        normalized_cols[col] = norm_col
    df = df.rename(columns=normalized_cols)

    column_mapping = {
        'Plant Id': 'plant_id',
        'Plant Name': 'plant_name',
        'Operator Name': 'operator_name',
        'Operator Id': 'operator_id',
        'Plant State': 'plant_state',
        'Census Region': 'census_region',
        'NERC Region': 'nerc_region',
        'Sector Name': 'sector_name',
        'NAICS Code': 'naics_code',
        'Reported Prime Mover': 'prime_mover',
        'Net Generation (Megawatthours)': 'net_gen_mwh'
    }

    for expected_col in column_mapping.keys():
        if expected_col not in df.columns:
            print(f"WARNING [{year}]: Expected column '{expected_col}' not found in file!")

    available_cols = [col for col in column_mapping.keys() if col in df.columns]
    df_sub = df[available_cols].rename(columns=column_mapping).copy()

    for orig_col, target_col in column_mapping.items():
        if target_col not in df_sub.columns:
            df_sub[target_col] = np.nan

    df_sub['year'] = year

    if 'prime_mover' in df_sub.columns:
        df_sub = df_sub[df_sub['prime_mover'].astype(str).str.strip() == 'WT'].copy()

    if 'operator_name' in df_sub.columns:
        df_sub['operator_name'] = df_sub['operator_name'].astype(str).str.strip().replace('nan', np.nan)
    if 'plant_name' in df_sub.columns:
        df_sub['plant_name'] = df_sub['plant_name'].astype(str).str.strip().replace('nan', np.nan)

    if 'net_gen_mwh' in df_sub.columns:
        df_sub['net_gen_mwh'] = pd.to_numeric(df_sub['net_gen_mwh'], errors='coerce')

    return df_sub


def build_combined_eia923(file_mapping):
    """
    Loops load_eia923_year over all EIA-923 files, skips and logs failures,
    and concats results into one combined multi-year EIA-923 dataframe.
    """
    frames = []
    for year, filepath in file_mapping.items():
        if not os.path.exists(filepath):
            print(f"LOG: File for year {year} not found at {filepath}. Skipping.")
            continue
        try:
            df_year = load_eia923_year(filepath, year)
            frames.append(df_year)
        except Exception as e:
            print(f"LOG: Failed to load EIA-923 data for year {year} from {filepath}. Error: {e}. Skipping.")
    
    if not frames:
        raise ValueError("No EIA-923 files were successfully loaded.")
    
    combined_eia = pd.concat(frames, ignore_index=True)
    return combined_eia


def check_duplicates(df_eia):
    """
    Checks for duplicate plant_id + year combinations in the combined EIA-923 dataset.
    """
    print("Checking for duplicates on (plant_id, year)...")
    duplicates = df_eia[df_eia.duplicated(subset=['plant_id', 'year'], keep=False)]
    if not duplicates.empty:
        dup_counts = df_eia.groupby(['plant_id', 'year']).size().reset_index(name='count')
        multi_counts = dup_counts[dup_counts['count'] > 1]
        print(f"WARNING: Found {len(multi_counts)} plant_id + year combinations with multiple rows:")
        print(multi_counts.head(10))
    else:
        print("No duplicate plant_id + year combinations found.")
    return duplicates


def main():
    # 1. Load and clean turbine data
    df_turb = load_and_clean_turbines("wind_turbine_20220114.csv")

    # Save standalone cleaned turbine dataset (both Excel and CSV for convenience)
    turbine_excel_path = "turbines_cleaned.xlsx"
    turbine_csv_path = "turbines_cleaned.csv"
    print(f"Saving standalone cleaned turbine dataset to {turbine_excel_path} and {turbine_csv_path}...")
    df_turb.to_excel(turbine_excel_path, index=False)
    df_turb.to_csv(turbine_csv_path, index=False)

    print("\n--- Turbine Table Inspection ---")
    print("Shape:", df_turb.shape)
    print("Head:")
    print(df_turb.head())

    # 2 & 3. Define file mapping for EIA-923 (2020-2024) and build combined dataset
    file_mapping = {
        2020: "EIA923_Schedules_2_3_4_5_M_12_2020_Final_Revision.xlsx",
        2021: "EIA923_Schedules_2_3_4_5_M_12_2021_Final_Revision.xlsx",
        2022: "EIA923_Schedules_2_3_4_5_M_12_2022_Final_Revision.xlsx",
        2023: "EIA923_Schedules_2_3_4_5_M_12_2023_Final_Revision.xlsx",
        2024: "EIA923_Schedules_2_3_4_5_M_12_2024_Final.xlsx"
    }

    df_eia_combined = build_combined_eia923(file_mapping)
    print(f"\nCombined multi-year EIA-923 shape: {df_eia_combined.shape}")

    # 4. Check for duplicates
    check_duplicates(df_eia_combined)

    # Save standalone combined EIA-923 dataset (both Excel and CSV)
    eia_excel_path = "eia923_2020_2024_cleaned.xlsx"
    eia_csv_path = "eia923_2020_2024_cleaned.csv"
    print(f"Saving standalone combined EIA-923 dataset to {eia_excel_path} and {eia_csv_path}...")
    df_eia_combined.to_excel(eia_excel_path, index=False)
    df_eia_combined.to_csv(eia_csv_path, index=False)

    print("\n--- EIA-923 Combined Table Inspection ---")
    print("Shape:", df_eia_combined.shape)
    print("Head:")
    print(df_eia_combined.head())

    print("\nPipeline completed successfully! Tables are kept separate (no merge).")


if __name__ == "__main__":
    main()
