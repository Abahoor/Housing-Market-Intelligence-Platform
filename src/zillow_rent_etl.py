import pandas as pd

def extract_zillow_rent():
    df=pd.read_csv("data/raw/Metro_zori_uc_sfrcondomfr_sm_month.csv")

    return df

def transform_zillow_rent(df):

    # Keep only metro-level Zillow records
    df = df[df["RegionType"] == "msa"].copy()


    id_columns = [
    "RegionID",
    "SizeRank",
    "RegionName",
    "RegionType",
    "StateName"
    ]

    # Convert wide monthly columns into long format
    df_long=df.melt(
    id_vars=id_columns,
    var_name="date",
    value_name="rent"
    )

    # Convert date strings into datetime
    df_long["date"] = pd.to_datetime(df_long["date"])

    # Standardize every monthly date to the first day of the month
    df_long["date"] = (df_long["date"].dt.to_period("M").dt.to_timestamp())

    # Convert rent to numeric.
    # Unexpected non-numeric values become NaN.
    df_long["rent"] = pd.to_numeric(df_long["rent"],errors="coerce")

    # Zillow has incomplete historical coverage.
    # Do not invent rents; keep only real observations.
    df_long = df_long.dropna(subset=["rent"]).copy()

    # Remove columns that are no longer useful
    df_long = df_long.drop(columns=["SizeRank", "RegionType"])

    # Clean column names
    df_long = df_long.rename(columns={
        "RegionID": "zillow_region_id",
        "RegionName": "region_name",
        "StateName": "state_name"
    })

    # IDs are identifiers, not quantities
    df_long["zillow_region_id"] = (
        df_long["zillow_region_id"].astype(str)
    )

    # Cleaner dollar values
    df_long["rent"] = df_long["rent"].round(2)

    # Organize final output
    df_long = (
        df_long
        .sort_values(["zillow_region_id", "date"])
        .reset_index(drop=True)
    )

    return df_long

def validate_zillow_rent(df):
    assert df["zillow_region_id"].notna().all(), \
        "Missing Zillow region IDs detected"

    assert df["region_name"].notna().all(), \
        "Missing region names detected"

    assert df["date"].notna().all(), \
        "Missing dates detected"

    assert df["rent"].notna().all(), \
        "Missing rent values detected"

    assert (df["rent"] > 0).all(), \
        "Invalid rent values detected"

    assert not df.duplicated(
        subset=["zillow_region_id", "date"]
    ).any(), \
        "Duplicate Zillow region-date records detected"

def load_zillow_rent(df):
    df.to_csv("data/processed/zillow_monthly_rent.csv",index=False)


def main():
    df=extract_zillow_rent()
    df=transform_zillow_rent(df)
    validate_zillow_rent(df)
    load_zillow_rent(df)




if __name__=="__main__":
    main()
