import pandas as pd


def extract_redfin_housing():
    df = pd.read_csv("data/raw/redfin_housing_market_monthly_all_metros_2015_Jan_to_2026_Jul.csv")

    return df


def transform_redfin_housing(df):
    df = df.copy()

    df = df.drop(columns=[
        "LAST UPDATED",
        "FREQUENCY",
        "REGION TYPE",
        "HOMES SOLD YOY (%)",
        "MEDIAN SALE PRICE NSA YOY (%)",
        "AVERAGE SALE TO LIST RATIO YOY (PPTS)",
        "SHARE SOLD ABOVE ORIGINAL LIST (%)",
        "SHARE SOLD ABOVE ORIGINAL LIST YOY (PPTS)",
        "NEW LISTINGS YOY (%)",
        "ACTIVE LISTINGS YOY (%)",
        "INVENTORY YOY (%)",
        "PENDING SALES YOY (%)",
        "MEDIAN NEW LISTING PRICE YOY (%)",
        "MEDIAN NEW LISTING PRICE PER SQ.FT. YOY (%)",
        "MEDIAN SALE PRICE PER SQ.FT. YOY (%)",
        "MONTHS OF SUPPLY YOY (%)",
        "PERCENT OFF MARKET IN TWO WEEKS YOY (PPTS)MEDIAN DAYS ON MARKET YOY (%)",
        "Unnamed: 12",
        "PERIOD END"
    ])

    df = df.rename(columns={
        "PERIOD BEGIN": "period_begin",
        "REGION ID": "redfin_region_id",
        "REGION NAME": "region_name",
        "HOMES SOLD": "homes_sold",
        "MEDIAN SALE PRICE NSA ($)": "median_sale_price",
        "MEDIAN DAYS ON MARKET (DAYS)": "median_days_on_market",
        "AVERAGE SALE TO LIST RATIO (%)": "avg_sale_to_list_ratio",
        "NEW LISTINGS": "new_listings",
        "ACTIVE LISTINGS": "active_listings",
        "INVENTORY": "inventory",
        "PENDING SALES": "pending_sales",
        "MEDIAN NEW LISTING PRICE ($)": "median_new_listing_price",
        "MEDIAN NEW LISTING PRICE PER SQ.FT. ($)": "median_new_listing_price_per_sqft",
        "MEDIAN SALE PRICE PER SQ.FT. ($)": "median_sale_price_per_sqft",
        "MONTHS OF SUPPLY": "months_of_supply",
        "PERCENT OFF MARKET IN TWO WEEKS (%)": "percent_off_market_two_weeks"
    })

    # Core field required for affordability analysis
    df = df.dropna(subset=["median_sale_price"]).copy()

    # Datatypes
    df["period_begin"] = pd.to_datetime(df["period_begin"])
    df["redfin_region_id"] = df["redfin_region_id"].astype(str)

    df["homes_sold"] = df["homes_sold"].astype(int)

    df["median_days_on_market"] = pd.to_numeric(df["median_days_on_market"],errors="coerce")

    df["median_days_on_market"] = (df["median_days_on_market"].astype("Int64"))
    
    # Replace impossible negative new listing count with missing value
    df.loc[df["new_listings"] < 0, "new_listings"] = pd.NA

    # Organize rows
    df = (df.sort_values(["redfin_region_id", "period_begin"]).reset_index(drop=True))

    invalid_percent = ((df["percent_off_market_two_weeks"] < 0)|(df["percent_off_market_two_weeks"] > 100))
    df.loc[invalid_percent,"percent_off_market_two_weeks"] = pd.NA
    print("Negative percent after transform:",(df["percent_off_market_two_weeks"] < 0).sum())

    print("Missing percent after transform:",df["percent_off_market_two_weeks"].isna().sum())

    

    return df

def validate_redfin_housing(df):

    # Core columns cannot be missing
    assert df["period_begin"].isnull().sum() == 0, \
        "Missing period_begin values detected"

    assert df["redfin_region_id"].isnull().sum() == 0, \
        "Missing Redfin region IDs detected"

    assert df["region_name"].isnull().sum() == 0, \
        "Missing region names detected"

    assert df["median_sale_price"].isnull().sum() == 0, \
        "Missing median sale prices detected"

    assert df["homes_sold"].isnull().sum() == 0, \
        "Missing homes sold values detected"


    # One region should only have one row per month
    assert not df.duplicated(
        subset=["redfin_region_id", "period_begin"]
    ).any(), "Duplicate region-month combinations detected"


    # Core numeric values must make sense
    assert (df["median_sale_price"] > 0).all(), \
        "Invalid median sale prices detected"

    assert (df["homes_sold"] > 0).all(), \
        "Invalid homes sold values detected"

    valid_percent = (df["percent_off_market_two_weeks"].dropna().between(0, 100).all())

    assert valid_percent, \
        "Invalid percent_off_market_two_weeks values detected"


    # NaN is allowed, but existing values cannot be negative
    optional_nonnegative = [
        "median_days_on_market",
        "new_listings",
        "active_listings",
        "inventory",
        "pending_sales",
        "median_new_listing_price",
        "median_new_listing_price_per_sqft",
        "median_sale_price_per_sqft",
        "months_of_supply"
    ]


    for column in optional_nonnegative:
        assert (df[column].dropna() >= 0).all(), \
            f"Invalid negative values detected in {column}"
        

    return True


def load_redfin_housing(df):
    df.to_csv("data/processed/redfin_monthly_housing.csv",index=False)


def main():
    df=extract_redfin_housing()
    df=transform_redfin_housing(df)
    validate_redfin_housing(df)
    load_redfin_housing(df)

    



if __name__ == "__main__":
    main()