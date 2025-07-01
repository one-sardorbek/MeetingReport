import pandas as pd
import numpy as np
import json
import re
import json
import pandas as pd


def fix_extra_closing_brackets(s):
    s = s.strip()
    # Try parsing directly first
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass  # Continue if it fails

    # Try removing extra closing brackets at the end
    while s.endswith('}') or s.endswith(']'):
        s = s[:-1].strip()
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            continue

    # If still not valid, raise error
    raise ValueError("Could not fix the JSON string.")

# --- Load Excel and parse each row ---
path = "C:\\Users\\sardorbek\\Desktop\\source\\raw_data.xlsx"
df = pd.read_excel(path, sheet_name='Sheet1')

# Apply cleaning parser
df['parsed'] = df['raw_content'].apply(fix_extra_closing_brackets)


# dimm_comm_type

dim_comm_type = df[["comm_type"]]
dim_comm_type = dim_comm_type.drop_duplicates()

dim_comm_type["comm_type_id"] = np.where(dim_comm_type["comm_type"] == "call", 1, 3)


# dim_subject

dim_subject = df[["subject"]]
dim_subject = dim_subject.drop_duplicates()
dim_subject["subject_id"] = range(1, len(dim_subject["subject"]) + 1)

#dim_user


dim_user=pd.DataFrame(columns=["user_id","name","email","location","displayName","PhoneNumber"])
all_attendees=df["parsed"].apply(lambda x: x.get("meeting_attendees"))


for attendees in all_attendees:
    for user in attendees:
        dim_user = pd.concat([
                dim_user,
                pd.DataFrame([{
                    "user_id": None,
                    "name": user.get("name"),
                    "email": user.get("email"),
                    "location": user.get("location"),
                    "displayName": user.get("displayName"),
                    "PhoneNumber": user.get("phoneNumber")
                }])
            ], ignore_index=True)
        

all_participants=df["parsed"].apply(lambda x: x.get("participants"))
for participants in all_participants:
    for email in participants:
        dim_user = pd.concat([
        dim_user,
        pd.DataFrame([{
            "user_id": None,
            "name": None,
            "email": email,
            "location": None,
            "displayName": None,
            "PhoneNumber": None
            }])
        ], ignore_index=True)

host_emails=df["parsed"].apply(lambda x: x.get("host_email"))
for host_email in host_emails:
    dim_user = pd.concat([
        dim_user,
        pd.DataFrame([{
            "user_id": None,
            "name": None,
            "email": host_email,
            "location": None,
            "displayName": None,
            "PhoneNumber": None
            }])
        ], ignore_index=True)
    
organizer_emails=df["parsed"].apply(lambda x: x.get("organizer_email"))
for organizer_email in organizer_emails:
    dim_user = pd.concat([
        dim_user,
        pd.DataFrame([{
            "user_id": None,
            "name": None,
            "email": organizer_email,
            "location": None,
            "displayName": None,
            "PhoneNumber": None
            }])
        ], ignore_index=True)

dim_user=dim_user.drop_duplicates()

dim_user["user_id"]=range(1, len(dim_user) + 1)

def normalize_string(s):
    """Lowercase and remove non-letters."""
    return re.sub(r'[^a-z]', '', s.lower())

def email_letters_in_name(email_username, name):
    """Check if all letters in email username are in name."""
    email_letters = normalize_string(email_username)
    name_letters = normalize_string(name)
    return all(letter in name_letters for letter in email_letters)


all_speaker_names = set()
for row in df["parsed"]:
    speakers = row.get("speakers", [])
    for speaker in speakers:
        if speaker.get("name"):
            all_speaker_names.add(speaker["name"])


for idx, row in dim_user.iterrows():
    if pd.isna(row["name"]) and pd.notna(row["email"]):
        email_username = row["email"].split("@")[0]
        for speaker_name in all_speaker_names:
            if email_letters_in_name(email_username, speaker_name):
                dim_user.at[idx, "name"] = speaker_name
                break  

dim_user=dim_user.fillna("")


# dim_calendar

raw_calendar_id = df["parsed"].apply(lambda x: x.get("calendar_id"))
raw_calendar_id = raw_calendar_id[raw_calendar_id.notnull()]
dim_calendar=pd.DataFrame({"raw_calendar_id": raw_calendar_id})
dim_calendar["calendar_id"]=range(1, len(dim_calendar) + 1)

# dim_audio

raw_audio_url = df["parsed"].apply(lambda x: x.get("audio_url"))
raw_audio_url = raw_audio_url[raw_audio_url.notnull()]
dim_audio=pd.DataFrame({"raw_audio_url": raw_audio_url})
dim_audio["audio_id"]=range(1, len(dim_audio) + 1)

#dim_video

raw_video_url = df["parsed"].apply(lambda x: x.get("video_url"))
raw_video_url = raw_video_url[raw_video_url.notnull()]
dim_video=pd.DataFrame({"raw_video_url": raw_video_url})
dim_video["video_id"]=range(1, len(dim_video) + 1)


#dim_transcript

raw_transcript_url = df["parsed"].apply(lambda x: x.get("transcript_url"))
raw_transcript_url = raw_transcript_url[raw_transcript_url.notnull()]
dim_transcript=pd.DataFrame({"raw_transcript_url": raw_transcript_url})
dim_transcript["transcript_id"] = range(1, len(dim_transcript) + 1)

#fact_communication

df = df.merge(dim_comm_type, on="comm_type", how="left")
df = df.merge(dim_subject, on="subject", how="left")


fact_communication = pd.DataFrame({
    "comm_id": df["id"],
    "raw_id": df["parsed"].apply(lambda x: x.get("id")),
    "source_id": df["source_id"],
    "comm_type_id": df["comm_type_id"],  
    "subject_id": df["subject_id"],     
    "calendar_id": dim_calendar["calendar_id"],
    "audio_id": dim_audio["audio_id"],
    "video_id": dim_video["video_id"],
    "transcript_id":dim_transcript["transcript_id"],
    "datetime_id": df["parsed"].apply(lambda x: x.get("dateString")),  
    "ingested_at": df["ingested_at"],
    "processed_at": df["processed_at"],
    "is_processed": df["is_processed"],
    "raw_title": df["parsed"].apply(lambda x: x.get("title")),
    "raw_duration": df["parsed"].apply(lambda x: x.get("duration")),
})

#bridge_comm_user

bridge_records = {}
email_to_user_id = dict(zip(dim_user["email"].str.lower(), dim_user["user_id"]))

for idx, row in df.iterrows():
    parsed = row["parsed"]
    comm_id = row["id"]

    def add(email, role):
        user_id = email_to_user_id.get(email.lower())
        if not user_id:
            return
        key = (comm_id, user_id)
        if key not in bridge_records:
            bridge_records[key] = {
                "comm_id": comm_id,
                "user_id": user_id,
                "isAttendee": False,
                "isParticipant": False,
                "isSpeaker": False,
                "isOrganiser": False
            }
        bridge_records[key][role] = True

    # Add roles
    for attendee in parsed.get("meeting_attendees", []):
        if attendee and "email" in attendee:
            add(attendee["email"], "isAttendee")

    for email in parsed.get("participants", []):
        add(email, "isParticipant")

    for speaker in parsed.get("speakers", []):
        name = speaker.get("name")
        matches = dim_user[dim_user["name"] == name]
        for _, m in matches.iterrows():
            if m["email"]:
                add(m["email"], "isSpeaker")

    organizer = parsed.get("organizer_email")
    if organizer:
        add(organizer, "isOrganiser")

bridge_comm_user = pd.DataFrame(list(bridge_records.values()))

#to_excel

output_path = "C:\\Users\\sardorbek\\Desktop\\full_final_data.xlsx"

with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
    dim_user.to_excel(writer, sheet_name='dim_user', index=False)
    dim_comm_type.to_excel(writer, sheet_name='dim_comm_type', index=False)
    dim_subject.to_excel(writer, sheet_name='dim_subject', index=False)
    dim_calendar.to_excel(writer, sheet_name='dim_calendar', index=False)
    dim_audio.to_excel(writer, sheet_name='dim_audio', index=False)
    dim_video.to_excel(writer, sheet_name='dim_video', index=False)
    dim_transcript.to_excel(writer, sheet_name='dim_transcript', index=False)
    fact_communication.to_excel(writer, sheet_name='fact_communication', index=False)
    bridge_comm_user.to_excel(writer, sheet_name='bridge_comm_user', index=False)
