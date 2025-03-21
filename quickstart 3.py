import datetime
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import tzlocal

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

# Hardcoded calendar IDs
RELEVANT_CAL_IDS = [
    "auh94mav0t03nkb6msorltnq5c@group.calendar.google.com",
    "alexander.pieroni@duke.edu",
    "dukepitchforks@gmail.com",
    "979a35bb2f0c74ab8aca0868feeb5d485c595bc85e30683463c426927ba49b7b@group.calendar.google.com",
    "4fcda66bf9bee7ab50963d3dc47879103efadbde75ccbf7f961ecb6ecf551fcd@group.calendar.google.com",
    "adunq704chaon3jlrr7pdbe3js@group.calendar.google.com",
    "alexanderjpieroni@gmail.com",
    "b98421b54b8241116adb7fcdd6e91ea7bae06619ca0495a432d5ee63505b3ea8@group.calendar.google.com",
    "bd188c1dd513dce377fd9b3e198a11dc63f1c892fae5b64154bc568578ad3146@group.calendar.google.com",
    "apieroni@kyros.ai",
    "898f2b3oak6pvpdgcomjv261i1ktg0ns@import.calendar.google.com",
    "43b2063fd153b80e0c8cf662ebd57a99f25336abc3cac85ff1369d1933b8883d@group.calendar.google.com",
]

def main():
    """
    Asks user whether to fetch events for "today" or "tomorrow".
    Then displays all events (start -> end) from midnight to midnight local time
    for each relevant calendar.
    """
    choice = input("Fetch events for [T]oday or [Tom]orrow? ").strip().lower()
    local_tz = tzlocal.get_localzone()
    now_local = datetime.datetime.now(local_tz).replace(second=0, microsecond=0)

    if choice.startswith("t") and not choice.startswith("tom"):
        # 't' => "today"
        chosen_date = now_local.date()
    else:
        # 'tomorrow' or unrecognized => tomorrow
        chosen_date = now_local.date() + datetime.timedelta(days=1)

    start_of_day_local = datetime.datetime.combine(chosen_date, datetime.time(0, 0), tzinfo=local_tz)
    end_of_day_local = start_of_day_local + datetime.timedelta(days=1)
    time_min = start_of_day_local.isoformat()
    time_max = end_of_day_local.isoformat()

    # Load credentials
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)

        print(f"\nFetching events for {chosen_date} (Local Time)\n")
        print(f" timeMin = {time_min}")
        print(f" timeMax = {time_max}\n")

        for cal_id in RELEVANT_CAL_IDS:
            cal_info = service.calendarList().get(calendarId=cal_id).execute()
            cal_name = cal_info.get("summary", cal_id)

            print(f"--- Calendar: {cal_name} ---")

            events_result = (
                service.events()
                .list(
                    calendarId=cal_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    maxResults=50,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = events_result.get("items", [])
            if not events:
                print("No events found.\n")
                continue

            for event in events:
                summary = event.get("summary", "No Title")

                # Attempt to get dateTime; if not present, fall back to date
                start = event["start"].get("dateTime", event["start"].get("date"))
                end = event["end"].get("dateTime", event["end"].get("date"))

                print(f"{start} -> {end}  |  {summary}")
            print()

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
