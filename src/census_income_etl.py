import os
import json
import requests
import pandas as pd

from dotenv import load_dotenv
YEAR = 2024

DIVISION_PARENT_METROS = [
    "31080",
    "33100",
    "19820",
    "47900",
    "41860",
    "19100",
    "14460",
    "16980",
    "37980",
    "35620",
    "42660"
]

def extract_census_metros():
    load_dotenv()

    census_api_key = os.getenv("CENSUS_API_KEY")

    url = f"https://api.census.gov/data/{YEAR}/acs/acs5"

    params = {
        "get": "NAME,B19013_001E",
        "for": "metropolitan statistical area/micropolitan statistical area:*",
        "key": census_api_key
    }

    response = requests.get(url, params=params)

    response.raise_for_status()

    data = response.json()

    return data

def extract_census_divisions():
    load_dotenv()

    census_api_key = os.getenv("CENSUS_API_KEY")

    url = "https://api.census.gov/data/2024/acs/acs5"

    all_divisions = []
    division_columns = None

    for metro_code in DIVISION_PARENT_METROS:

        params = {
            "get": "NAME,B19013_001E",
            "for": "metropolitan division:*",
            "in": f"metropolitan statistical area/micropolitan statistical area:{metro_code}",
            "key": census_api_key
        }

        response = requests.get(url, params=params)
        response.raise_for_status()

        division_data = response.json()

        if division_columns is None:
            division_columns = division_data[0]

        all_divisions.extend(division_data[1:])

    return all_divisions, division_columns


def transform_census_metros(data):

    df_metros = pd.DataFrame(data[1:],columns=data[0])

    df_metros = df_metros.rename(columns={
        "NAME": "geo_name",
        "B19013_001E": "median_household_income",
        "metropolitan statistical area/micropolitan statistical area": "geo_id"
    })

    # Keep only metropolitan areas, not micropolitan areas
    df_metros = df_metros[df_metros["geo_name"].str.contains("Metro Area")].copy()

    # Clean metro names
    df_metros["geo_name"] = (df_metros["geo_name"].str.replace(" Metro Area", "", regex=False))

    # Convert datatypes
    df_metros["median_household_income"] = pd.to_numeric(df_metros["median_household_income"],errors="coerce")

    df_metros["geo_id"] = df_metros["geo_id"].astype(str)

    # Identify geography type
    df_metros["geography_type"] = "metro"

    # Normal metros do not have a parent metro
    df_metros["parent_metro_code"] = pd.NA

    # Same column order as metropolitan divisions
    df_metros = df_metros[
        [
            "geo_id",
            "geo_name",
            "geography_type",
            "parent_metro_code",
            "median_household_income"
        ]
    ]

    return df_metros

def transform_census_divisions(data, columns):

    df_divisions = pd.DataFrame(data,columns=columns)

    df_divisions = df_divisions.rename(columns={
        "NAME": "geo_name",
        "B19013_001E": "median_household_income",
        "metropolitan statistical area/micropolitan statistical area": "parent_metro_code",
        "metropolitan division": "geo_id"
    })

    df_divisions["median_household_income"] = pd.to_numeric(df_divisions["median_household_income"],errors="coerce")

    df_divisions["geo_id"] = df_divisions["geo_id"].astype(str)
    df_divisions["parent_metro_code"] = (df_divisions["parent_metro_code"].astype(str))

    df_divisions["geography_type"] = "division"

    df_divisions["geo_name"] = (
        df_divisions["geo_name"]
        .str.split(" Metro Division;", n=1)
        .str[0]
    )

    df_divisions = df_divisions[
        [
            "geo_id",
            "geo_name",
            "geography_type",
            "parent_metro_code",
            "median_household_income"
        ]
    ]

    return df_divisions



def combine_census_geographies(df_metros, df_divisions):

    df_census = pd.concat([df_metros, df_divisions],ignore_index=True)

    df_census["year"] = YEAR

    df_census = (df_census.sort_values("geo_id").reset_index(drop=True))

    return df_census

def validate_census_income(df):

    # Core fields cannot be missing
    assert df["geo_id"].notna().all(), \
        "Missing geographic IDs detected"

    assert df["geo_name"].notna().all(), \
        "Missing geographic names detected"

    assert df["median_household_income"].notna().all(), \
        "Missing household income values detected"

    # Every geography should appear only once
    assert df["geo_id"].is_unique, \
        "Duplicate geographic IDs detected"

    # Income must be positive
    assert (df["median_household_income"] > 0).all(), \
        "Invalid household income values detected"

    # geography_type should contain only the two types we created
    assert df["geography_type"].isin(["metro", "division"]).all(), "Invalid geography types detected"

    # Regular metros should NOT have a parent metro code
    metro_rows = df["geography_type"] == "metro"

    assert df.loc[metro_rows,"parent_metro_code"].isna().all(), \
        "Metro rows unexpectedly contain parent metro codes"

    # Metropolitan divisions MUST have a parent metro code
    division_rows = df["geography_type"] == "division"

    assert df.loc[division_rows,"parent_metro_code"].notna().all(), \
        "Metropolitan divisions missing parent metro codes"

def load_census_income(metro_data,division_data,division_columns,df_census):

    with open(f"data/raw/census_metro_income_{YEAR}.json","w") as file:json.dump(metro_data, file, indent=4)

    division_raw = [division_columns] + division_data

    with open(f"data/raw/census_division_income_{YEAR}.json","w") as file:json.dump(division_raw, file, indent=4)

    df_census.to_csv(f"data/processed/census_geography_income_{YEAR}.csv",index=False)


def main():

    metro_data = extract_census_metros()

    division_data, division_columns = extract_census_divisions()

    df_metros = transform_census_metros(metro_data)

    df_divisions = transform_census_divisions(division_data,division_columns)

    df_census = combine_census_geographies(df_metros,df_divisions)
    validate_census_income(df_census)

    load_census_income(metro_data,division_data,division_columns,df_census)

    print("Census income ETL completed successfully")





if __name__ == "__main__":
    main()