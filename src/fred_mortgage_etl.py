import os
import json
import requests
import pandas as pd
from dotenv import load_dotenv

def extract_mortgage_rates():

    load_dotenv()
    fred_api_key=os.getenv("FRED_API_KEY")
    url="https://api.stlouisfed.org/fred/series/observations"
    params = {
    "series_id": "MORTGAGE30US",
    "api_key" : fred_api_key,
    "file_type" : "json"
    }
    response = requests.get(url,params = params)
    response.raise_for_status()
    data = response.json()

    return data

def transform_fred_mortgage_rate(data):
    df_weekly= pd.DataFrame(data["observations"])

    df_weekly=df_weekly.rename(columns= {"value" : "mortgage_rate"})
    df_weekly=df_weekly.drop(columns={"realtime_start","realtime_end"})

    df_weekly["date"]= pd.to_datetime(df_weekly["date"])
    df_weekly["mortgage_rate"]=pd.to_numeric(df_weekly["mortgage_rate"])

    df_monthly = df_weekly.copy()
    df_monthly["month"] = df_monthly["date"].dt.to_period("M")

    df_monthly=(df_monthly.groupby("month")["mortgage_rate"].mean())
    df_monthly = df_monthly.round(2)

    df_monthly=pd.DataFrame(df_monthly)
    df_monthly = df_monthly.reset_index()

    df_monthly["month"]= df_monthly["month"].dt.to_timestamp()

    return df_weekly,df_monthly

def validate_fred_mortgage_rate(df_weekly,df_monthly):
    assert df_weekly["date"].isnull().sum() == 0,"Missing weekly dates detected"
    assert df_weekly["date"].is_unique,"Duplicate weekly dates detected"
    assert df_weekly["mortgage_rate"].isnull().sum() == 0, \
    "Missing weekly mortgage rates detected"    
    assert (df_weekly["mortgage_rate"] > 0).all(), \
    "Invalid weekly mortgage rates detected"

    assert df_monthly["month"].isnull().sum() == 0,"Missing monthly dates detected"
    assert df_monthly["month"].is_unique,"Duplicate monthly dates detected"
    assert df_monthly["mortgage_rate"].isnull().sum() == 0, \
    "Missing monthly mortgage rates detected"    
    assert (df_monthly["mortgage_rate"] > 0).all(), \
    "Invalid monthly mortgage rates detected"
    return True
def load_fred_mortgage_rate(data, df_weekly, df_monthly):
    with open("data/raw/fred_mortgage_rate.json", "w") as file:
        json.dump(data, file, indent=4)

    df_weekly.to_csv("data/processed/fred_weekly_mortgage_rate.csv",index=False)
    df_monthly.to_csv("data/processed/fred_monthly_mortgage_rate.csv",index=False)

def main():
    data=extract_mortgage_rates()
    df_weekly, df_monthly = transform_fred_mortgage_rate(data)
    validate_fred_mortgage_rate(df_weekly,df_monthly)

    load_fred_mortgage_rate(data,df_weekly,df_monthly)



if __name__ == "__main__":
    main()