import gspread
from oauth2client.service_account import ServiceAccountCredentials

def update_team_after_win(discord_id, bid_amount):
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name("google_credentials.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key("1QeLyKIgTSYFkLUqPcUrKyJBqTIo8WZoL-BI6tmqWcHk")
        settings = sheet.worksheet("Settings")
        data = settings.get_all_records()

        for i, row in enumerate(data):
            if str(row.get("Owner Discord ID")) == str(discord_id) or str(row.get("GM Discord ID")) == str(discord_id):
                used = float(row.get("Salary Used", 0))
                roster = int(row.get("Roster Count", 0))
                new_used = used + bid_amount
                new_roster = roster + 1
                row_index = i + 2
                settings.update_cell(row_index, 7, new_used)
                settings.update_cell(row_index, 8, new_roster)
                return row.get("Team Name")
        return None
    except Exception as e:
        print(f"[Error] update_team_after_win: {e}")
        return None

def append_player_to_team_tab(team_name, player_name, amount):
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name("google_credentials.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key("1QeLyKIgTSYFkLUqPcUrKyJBqTIo8WZoL-BI6tmqWcHk")
        team_sheet = sheet.worksheet("Team")

        all_values = team_sheet.get_all_values()
        insert_row = len(all_values) + 1
        for i, row in enumerate(all_values):
            if len(row) > 0 and row[0].strip() == team_name:
                insert_row = i + 2
                while insert_row <= len(all_values) and all_values[insert_row - 1][0].strip() == "":
                    insert_row += 1
                break

        team_sheet.insert_row([player_name, f"${amount}"], insert_row)
    except Exception as e:
        print(f"[Error] append_player_to_team_tab: {e}")

def remove_player_from_draft(player_name):
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name("google_credentials.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key("1QeLyKIgTSYFkLUqPcUrKyJBqTIo8WZoL-BI6tmqWcHk")
        draft_sheet = sheet.worksheet("Draft")
        values = draft_sheet.get_all_values()

        for i, row in enumerate(values):
            if row and row[0].strip().lower() == player_name.strip().lower():
                draft_sheet.delete_row(i + 1)
                break
    except Exception as e:
        print(f"[Error] remove_player_from_draft: {e}")

# === Google Sheets Setup ===


def get_team_limits(discord_id):
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_path = "google_credentials.json"
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key("1QeLyKIgTSYFkLUqPcUrKyJBqTIo8WZoL-BI6tmqWcHk")
        settings = sheet.worksheet("Settings")
        records = settings.get_all_records()

        for row in records:
            if str(row.get("Owner Discord ID")) == str(discord_id) or str(row.get("GM Discord ID")) == str(discord_id):
                salary = float(row.get("Salary", 0))
                used = float(row.get("Salary Used", 0))
                roster = int(row.get("Roster Count", 0))
                return {
                    "team": row.get("Team Name"),
                    "salary": salary,
                    "salary_used": used,
                    "roster_count": roster,
                    "remaining": salary - used
                }
        return None
    except Exception as e:
        print(f"[Error] Google Sheets access failed: {e}")
        return None



def load_nomination_order():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name("google_credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key("1QeLyKIgTSYFkLUqPcUrKyJBqTIo8WZoL-BI6tmqWcHk")
    worksheet = sheet.worksheet("Team List")
    rows = worksheet.get_all_records()

    teams = []
    for row in rows:
        team_name = row.get("Team Name", "").strip()
        owner_id = row.get("Owner Discord ID", "").strip()
        gm_id = row.get("GM Discord ID", "").strip()
        if not team_name:
            continue
        teams.append({
            "team_name": team_name,
            "owner_id": owner_id,
            "gm_id": gm_id
        })

    return teams
