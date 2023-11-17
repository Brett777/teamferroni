import streamlit as st
import pandas as pd
pd.set_option('display.max_columns', 100)
pd.set_option('display.max_rows', 1000)
import http.client
import io
import json
import datarobot as dr
import datetime
import warnings
import hmac
warnings.simplefilter(action='ignore', category=FutureWarning)
st.set_page_config(layout="wide")

key = st.secrets["key"]
drKey = st.secrets["drKey"]

def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    # Return True if the passward is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show input for password.
    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False


if not check_password():
    st.stop()  # Do not continue if check_password is not True.



def getData(key, boardId):
    #key = "5bxU25LFJn6pXAHHbJdEfTHZBJPhuU"
    #boardId = "19"

    conn = http.client.HTTPSConnection("api.repliers.io")
    payload = "{}"
    headers = {'repliers-api-key': str(key)}


    df = pd.DataFrame()
    conn = http.client.HTTPSConnection("api.repliers.io")
    conn.request("GET", "/listings?boardId=" + str(boardId) + "&agent=1063204&sortBy=createdOnDesc&pageNum=1&type=sale&status=A&status=U", payload, headers)
    res = conn.getresponse()
    data = res.read()
    json_string = json.loads(data.decode("utf-8"))
    container1 = st.container()
    col1, col2 = container1.columns([1,3])
    progressBar = st.progress(0, text="")


    # for i in range(1, (json_string["numPages"] + 1)):
    for i in range(1, (2 + 1)):
        with col1:
            progressBar.progress(value=i/(json_string["numPages"] + 1), text="Getting historical sales data... " +str(i))
        conn = http.client.HTTPSConnection("api.repliers.io")
        payload = "{}"
        headers = {'repliers-api-key': str(key)}
        conn.request("GET", "/listings?" + str(boardId) + "&agent=1063204&sortBy=createdOnDesc&pageNum=" + str(
            i) + "&type=sale&status=A&status=U", payload, headers)
        res = conn.getresponse()
        data = res.read()
        json_string = json.loads(data.decode("utf-8"))
        dfPage = pd.json_normalize(json_string["listings"])
        df = pd.concat([df, dfPage])
        # df = df.append(dfPage).reset_index(drop=True)
        print(str(i) + " out of " + str(json_string["numPages"]))
    progressBar.empty()
    try:
        if len(df) > 0:
            df = df.drop_duplicates("mlsNumber")
            df = df.loc[df["class"] != "CommercialProperty"]
            df.sort_values("soldDate", ascending=False, inplace=True)
            df.reset_index(inplace=True, drop=True)
            rooms = df.columns[df.columns.str.startswith('rooms')]
            df.drop(rooms, axis=1, inplace=True)
            df.drop("resource", axis=1, inplace=True)
            df.drop("updatedOn", axis=1, inplace=True)
            df.drop("timestamps.expiryDate", axis=1, inplace=True)
            df.drop("timestamps.terminatedDate", axis=1, inplace=True)
            df.drop("timestamps.listingEntryDate", axis=1, inplace=True)
            df.drop("timestamps.closedDate", axis=1, inplace=True)
            df.drop("timestamps.possessionDate", axis=1, inplace=True)
            df.drop("timestamps.idxUpdated", axis=1, inplace=True)
            df.drop("timestamps.conditionalExpiryDate", axis=1, inplace=True)
            df.drop("timestamps.listingUpdated", axis=1, inplace=True)
            df.drop("timestamps.photosUpdated", axis=1, inplace=True)
            df.drop("timestamps.suspendedDate", axis=1, inplace=True)
            df.drop("timestamps.extensionEntryDate", axis=1, inplace=True)
            df.drop("timestamps.unavailableDate", axis=1, inplace=True)
            # df.drop("duplicates", axis=1, inplace=True)
            df.drop("details.waterSource", axis=1, inplace=True)

            commercial = df.columns[df.columns.str.startswith('commercial')]
            df.drop(commercial, axis=1, inplace=True)
            df["listDate"] = pd.to_datetime(df["listDate"], format='%Y-%m-%d', utc=None).dt.tz_localize(None)
            df["soldDate"] = pd.to_datetime(df["soldDate"], format='%Y-%m-%d').dt.tz_localize(None)
            if boardId != "19":
                df["details.sqft"] = df["details.sqft"].str.replace('5000+', '5000-6000')
                df["details.sqft"] = df["details.sqft"].str.replace('6000+', '6000-7000')
                df["details.sqft"] = df["details.sqft"].str.replace('< 700', '0-700')
                df[["SQFT lower range", "SQFT upper range", "drop me1", "drop me2"]] = df["details.sqft"].str.split('-',
                                                                                                                    expand=True)
                df.drop(["drop me1", "drop me2"], axis="columns", inplace=True)
                df["SQFT upper range"] = pd.to_numeric(df["SQFT upper range"], errors="coerce")
                df["SQFT lower range"] = pd.to_numeric(df["SQFT lower range"], errors="coerce")
                df["details.sqft"] = df[["SQFT upper range", "SQFT lower range"]].median(axis="columns", skipna=True)
            df["taxes.annualAmount"] = pd.to_numeric(df["taxes.annualAmount"], errors="coerce")
            df["details.sqft"] = pd.to_numeric(df["details.sqft"], errors="coerce")
            df["Tax per SQFT"] = df["taxes.annualAmount"] / df["details.sqft"]
            df["Postal FSA"] = df["address.zip"].str[:3]
            df["lot.width"] = pd.to_numeric(df["lot.width"], errors="coerce")
            df["lot.depth"] = pd.to_numeric(df["lot.depth"], errors="coerce")
            df["Lot Area"] = df["lot.width"] * df["lot.depth"]

            df["condominium.pets"] = df["condominium.pets"].str.replace("R", "Restrict")
            df["condominium.pets"] = df["condominium.pets"].str.replace("Restricted", "Restrict")
            df["condominium.pets"] = df["condominium.pets"].str.replace("Restrictestrict", "Restrict")
            df["condominium.pets"] = df["condominium.pets"].str.replace("Restrictestricted", "Restrict")
            df["condominium.pets"] = df["condominium.pets"].str.replace("Yes", "Y")
            df["condominium.pets"] = df["condominium.pets"].str.replace("No", "N")
            df["condominium.pets"] = df["condominium.pets"].str.replace("1", "Restrict")

            df.loc[df["condominium.parkingType"].str[0] == "O", "condominium.parkingType"] = "Owned"
            df.loc[df["condominium.parkingType"].str[0] == "E", "condominium.parkingType"] = "Exclusive"
            df.loc[df["condominium.parkingType"].str[0] == "U", "condominium.parkingType"] = "Common"

            if boardId != "19":
                df.loc[(datetime.date.today() - pd.to_numeric(df["details.yearBuilt"],
                                                              errors="coerce")) / 365 >= 100, "details.yearBuilt"] = "100+"
                df.loc[(datetime.date.today() - pd.to_numeric(df["details.yearBuilt"],
                                                              errors="coerce")) / 365 < 100, "details.yearBuilt"] = "51-99"
                df.loc[(datetime.date.today() - pd.to_numeric(df["details.yearBuilt"],
                                                              errors="coerce")) / 365 < 51, "details.yearBuilt"] = "31-50"
                df.loc[(datetime.date.today() - pd.to_numeric(df["details.yearBuilt"],
                                                              errors="coerce")) / 365 < 31, "details.yearBuilt"] = "16-30"
                df.loc[(datetime.date.today() - pd.to_numeric(df["details.yearBuilt"],
                                                              errors="coerce")) / 365 < 16, "details.yearBuilt"] = "6-15"
                df.loc[(datetime.date.today() - pd.to_numeric(df["details.yearBuilt"],
                                                              errors="coerce")) / 365 < 6, "details.yearBuilt"] = "0-5"
                df.loc[(datetime.date.today() - pd.to_numeric(df["details.yearBuilt"],
                                                              errors="coerce")) / 365 <= 1, "details.yearBuilt"] = "New"

            df["details.propertyType"] = df["details.propertyType"].str.replace("Apartment Unit", "Condo Apt")
            df["details.style"] = df["details.style"].str.replace("2 Storey", "2-Storey")
            df["details.style"] = df["details.style"].str.replace("1 Storey/Apartment Style", "Apartment")
            df["details.style"] = df["details.style"].str.replace("3 Storey", "3-Storey")
            df["details.style"] = df["details.style"].str.replace("Bungalow Raised", "Bungalow-Raised")
            df["details.style"] = df["details.style"].str.replace("4 Level Backsplit", "Backsplit 4")
            df["details.style"] = df["details.style"].str.replace("4 Level Sidesplit", "Sidesplit 4")
            df["details.style"] = df["details.style"].str.replace("3 Level Backsplit", "Backsplit 3")
            df["details.style"] = df["details.style"].str.replace("3 Level Sidesplit", "Sidesplit 3")
            df["details.style"] = df["details.style"].str.replace("Stacked Townhouse", "Stacked Townhse")
            df["details.style"] = df["details.style"].str.replace("5 Level Backsplit", "Backsplit 5")
            df["details.style"] = df["details.style"].str.replace("Other (see Remarks)", "Other")
            df["details.style"] = df["details.style"].str.replace("Backsplit", "Backsplt-All")
            df["details.style"] = df["details.style"].str.replace("Sidesplit", "Sidesplt-All")

            df["details.numFireplaces"] = df["details.numFireplaces"].str.replace("0", "N", regex=False)
            df["details.numFireplaces"] = df["details.numFireplaces"].str.replace("3", "Y", regex=False)
            df["details.numFireplaces"] = df["details.numFireplaces"].str.replace("9", "Y", regex=False)
            df["details.numFireplaces"] = df["details.numFireplaces"].str.replace("1", "Y", regex=False)
            df["details.numFireplaces"] = df["details.numFireplaces"].str.replace("2", "Y", regex=False)
            df["details.numFireplaces"] = df["details.numFireplaces"].fillna("N")
            df["details.propertyType"] = df["details.propertyType"].str.replace("Townhouse/Row House",
                                                                                "Att/Row/Twnhouse")

            if boardId == "19":
                df["details.numBathrooms"] = pd.to_numeric(df["details.numBathrooms"], errors="coerce") + pd.to_numeric(
                    df["details.numBathroomsHalf"], errors="coerce")
    except Exception as e:
        status = "failed: " + str(e)
        print(status)

    try:
        s = df["details.exteriorConstruction1"].str.split(",", n=2, expand=True)
        df[["ext1", "ext2", "other"]] = s
        df.loc[df["details.exteriorConstruction2"].isna(), "details.exteriorConstruction2"] = df["ext2"]
        df["details.exteriorConstruction1"] = df["ext1"]
        df.drop(["ext1", "ext2", "other"], axis="columns", inplace=True)

    except Exception as e:
        print(e)

    try:
        s = df["details.garage"].str.split(",", n=2, expand=True)
        df[["garage", "driveway", "other"]] = s
        df["details.garage"] = df["garage"]
        df.drop(["garage", "driveway", "other"], axis="columns", inplace=True)

    except Exception as e:
        print(e)

    try:
        df.loc[df["condominium.ammenities"] == "['', '', '', '', '', '']", "condominium.ammenities"] = df[
            "condominium.ammenities"].str.replace("['', '', '', '', '', '']", "[None,None,None,None,None,None]",
                                                  regex=False)
    except Exception as e:
        print(e)

    print("Records queried: " + str(len(df)))
    df = df.drop_duplicates("mlsNumber")
    df = df.reset_index(drop=True)
    print("after dedupe: " + str(len(df)))
    return df


df = getData(key = key, boardId="19")
# st.dataframe(df[["address.streetNumber","address.streetName","Postal FSA"]])
df["Days Since List"] = 1
df["association_id"] = df["address.unitNumber"].astype(str) + df["address.streetNumber"].astype(str) + df["address.streetName"].str.upper() + "A1B 2C3"
st.write("Historical property data loaded.")
st.dataframe(df)
with st.spinner("Processing Estimates"):

    dr.Client(token=drKey, endpoint='https://app.datarobot.com/api/v2')

    # Score for price
    deployment_id = '62614ee60a42bdaf2bb015b5'
    job, AJsProperties_scored = dr.BatchPredictionJob.score_pandas(deployment_id, df)

    #Score for confidence
    deployment_id = '626f50ef237de6fc05fecbba'
    job, AJsPropertiesConfidence = dr.BatchPredictionJob.score_pandas(deployment_id, df)


    AJsProperties_scored["confidence"] = AJsPropertiesConfidence["MAPE_PREDICTION"]
    AJsProperties_scored["estimateHigh"] = AJsProperties_scored["soldPrice_PREDICTION"] + (AJsProperties_scored["confidence"] * AJsProperties_scored["soldPrice_PREDICTION"])
    AJsProperties_scored["estimateLow"] = AJsProperties_scored["soldPrice_PREDICTION"] - (AJsProperties_scored["confidence"] * AJsProperties_scored["soldPrice_PREDICTION"])
    AJsProperties_scored["createdOn"] = datetime.datetime.today().date()
    AJsProperties_scored.rename({"soldPrice_PREDICTION":"Price Estimate Today"}, axis="columns", inplace=True)
    AJsProperties_scored.drop(['DEPLOYMENT_APPROVAL_STATUS'], axis="columns", inplace=True)
    AJsProperties_scored["Appreciation"] = pd.to_numeric(AJsProperties_scored["Price Estimate Today"]) - pd.to_numeric(AJsProperties_scored["soldPrice"].str.replace("$","").str.replace(",",""))

    AJsProperties_scored = AJsProperties_scored[["mlsNumber",
                                            "listDate",
                                            "listPrice",
                                            "soldDate",
                                            "soldPrice",
                                            "Price Estimate Today",
                                            "Appreciation",
                                            "estimateLow",
                                            "estimateHigh",
                                            "confidence",
                                            "details.propertyType",
                                            "details.style",
                                            "details.sqft",
                                            "details.numBedrooms",
                                            "details.numBathrooms",
                                            "address.streetNumber",
                                            "address.unitNumber",
                                            "address.streetName",
                                            "address.streetSuffix",
                                            "address.streetDirection",
                                            "address.city",
                                            "address.zip",
                                            "condominium.unitNumber",
                                            "taxes.annualAmount"]].sort_values(by="soldDate", ascending=True).reset_index(drop=True)


st.dataframe(AJsProperties_scored)
def to_excel(df) -> bytes:
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine="xlsxwriter")
    df.to_excel(writer, sheet_name="Sheet1")
    writer.save()
    processed_data = output.getvalue()
    return processed_data

st.download_button(
        "Download all",
        data=to_excel(AJsProperties_scored),
        file_name="intput.xlsx",
        mime="application/vnd.ms-excel",
    )

