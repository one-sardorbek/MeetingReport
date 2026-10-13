# Communications Data Modeling Script

A Python ETL script that reads raw communication records (calls, meetings, etc.) from an Excel file, parses the JSON payload stored in each row, and builds a star-schema-style dataset (dimension, fact and bridge tables). The result is written to a multi-sheet Excel workbook.

## What it does

1. Loads `Sheet1` of the source Excel file.
2. Parses the `raw_content` column (a JSON string) into Python dictionaries. Malformed JSON with extra trailing `}` / `]` characters is repaired automatically.
3. Builds dimension tables, a fact table and a user/communication bridge table.
4. Exports all tables to a single Excel workbook, one sheet per table.

## Requirements

- Python 3.8+
- Packages:

```bash
pip install pandas numpy openpyxl xlsxwriter
```

(`openpyxl` is used to read `.xlsx`, `xlsxwriter` to write it.)

## Input

An Excel file with a sheet named `Sheet1` containing at least these columns:

| Column | Description |
|---|---|
| `id` | Unique ID of the communication row |
| `source_id` | ID of the source system |
| `comm_type` | Type of communication (e.g. `call`) |
| `subject` | Subject / topic of the communication |
| `raw_content` | JSON string with the full communication payload |
| `ingested_at` | Timestamp the record was ingested |
| `processed_at` | Timestamp the record was processed |
| `is_processed` | Processing flag |

### Expected JSON fields inside `raw_content`

`id`, `title`, `duration`, `dateString`, `calendar_id`, `audio_url`, `video_url`, `transcript_url`, `host_email`, `organizer_email`, `participants` (list of emails), `meeting_attendees` (list of objects with `name`, `email`, `location`, `displayName`, `phoneNumber`), `speakers` (list of objects with `name`).

## Configuration

Set the input and output paths near the top and bottom of the script:

```python
path = "C:\\Users\\<you>\\Desktop\\source\\raw_data.xlsx"        # input
output_path = "C:\\Users\\<you>\\Desktop\\full_final_data.xlsx"  # output
```

## Output tables

The output workbook contains one sheet per table:

| Sheet | Type | Description |
|---|---|---|
| `dim_user` | Dimension | Unique people: attendees, participants, hosts and organizers. Columns: `user_id`, `name`, `email`, `location`, `displayName`, `PhoneNumber` |
| `dim_comm_type` | Dimension | Distinct communication types with `comm_type_id` (`call` = 1, everything else = 3) |
| `dim_subject` | Dimension | Distinct subjects with a sequential `subject_id` |
| `dim_calendar` | Dimension | Raw calendar IDs with a surrogate `calendar_id` |
| `dim_audio` | Dimension | Raw audio URLs with a surrogate `audio_id` |
| `dim_video` | Dimension | Raw video URLs with a surrogate `video_id` |
| `dim_transcript` | Dimension | Raw transcript URLs with a surrogate `transcript_id` |
| `fact_communication` | Fact | One row per communication, with foreign keys to the dimensions plus `datetime_id`, `ingested_at`, `processed_at`, `is_processed`, `raw_title`, `raw_duration` |
| `bridge_comm_user` | Bridge | Many-to-many link between communications and users with role flags: `isAttendee`, `isParticipant`, `isSpeaker`, `isOrganiser` |

## How the main steps work

- **JSON repair** – `fix_extra_closing_bracke` first tries `json.loads`. If that fails, it removes trailing `}` or `]` characters one at a time until the string parses, or raises `ValueError`.
- **`dim_user` construction** – users are collected from attendees (full details), then participants, hosts and organizers (email only). Duplicates are dropped and IDs assigned.
- **Name enrichment** – for users with an email but no name, the script compares the email username with all speaker names and fills in the first speaker name that contains all the username's letters (a heuristic match).
- **Bridge table** – for each communication, roles are assigned by matching emails (attendees, participants, organizer) or speaker names (speakers) to `dim_user`.

## Usage

```bash
python script_name.py
```

On success, the output workbook is created at `output_path`.

## Known issues / things to fix

- **Function name mismatch:** the function is defined as `fix_extra_closing_bracke` but called as `fix_extra_closing_brackets`, which raises a `NameError`. Rename one so they match.
- **Index misalignment in `fact_communication`:** `calendar_id`, `audio_id`, `video_id` and `transcript_id` are taken from dimension tables that were built after dropping null rows, so they are assigned by index position and can end up attached to the wrong communication (or be `NaN`). Map them by value (as done for `comm_type` and `subject`) instead.
- **`dim_user` duplicates:** `drop_duplicates()` only removes fully identical rows, so the same email can appear several times (e.g. once with a name and once without). Consider deduplicating by email.
- **`comm_type_id` mapping:** any type other than `call` is assigned `3`, so multiple distinct types would share one ID. Use a proper mapping or sequential IDs.
- **Speaker matching is heuristic:** name matching via letter containment can produce false positives, and `isSpeaker` is resolved by name, which may link a speaker to the wrong user.
- **Performance:** repeated `pd.concat` inside loops is slow on large inputs. Collect rows in a list and build the DataFrame once.
- Hard-coded Windows paths should be replaced with configurable arguments or environment variables.
- The `# dimm_comm_type` comment contains a typo (`dimm`).
