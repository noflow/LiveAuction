
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Authorize using environment variable
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = json.loads(os.environ["GOOGLE_CREDENTIALS"])
client = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds, scope))


def get_team_role_id(team_name):
    return os.getenv(team_name.upper().replace(" ", "_"))


def update_team_after_win(discord_id, bid_amount):
    try:
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
        sheet = client.open_by_key("1QeLyKIgTSYFkLUqPcUrKyJBqTIo8WZoL-BI6tmqWcHk")
        draft_sheet = sheet.worksheet("Draft")
        values = draft_sheet.get_all_values()

        for i, row in enumerate(values):
            if row and row[0].strip().lower() == player_name.strip().lower():
                draft_sheet.delete_row(i + 1)
                break
    except Exception as e:
        print(f"[Error] remove_player_from_draft: {e}")


def get_team_limits(discord_id):
    try:
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


def load_draft_list():
    sheet = client.open_by_key("1QeLyKIgTSYFkLUqPcUrKyJBqTIo8WZoL-BI6tmqWcHk")
    worksheet = sheet.worksheet("Draft List")
    rows = worksheet.get_all_records()

    players = []
    for row in rows:
        name = row.get("PSN / XBL ID", "").strip()
        main = row.get("Main Position", "").strip()
        other = row.get("Other Positions", "").strip()
        hand = row.get("Hand", "").strip()

        if not name:
            continue

        position = f"{main}/{other}" if other else main
        players.append({
            "id": name,
            "position": position,
            "hand": hand
        })

    return players


def get_team_roster(team_name):
    try:
        sheet = client.open_by_key("1QeLyKIgTSYFkLUqPcUrKyJBqTIo8WZoL-BI6tmqWcHk")
        team_sheet = sheet.worksheet("Team")
        values = team_sheet.get_all_values()

        players = []
        for row in values:
            if len(row) >= 2 and row[0].strip() == team_name:
                player_name = row[1].strip()
                try:
                    amount = float(row[2].replace("$", "").strip())
                except:
                    amount = 0
                players.append({"name": player_name, "amount": amount})
        return players
    except Exception as e:
        print(f"[Error] get_team_roster: {e}")
        return []


def get_team_data_for_user(username):
    try:
        sheet = client.open_by_key("1QeLyKIgTSYFkLUqPcUrKyJBqTIo8WZoL-BI6tmqWcHk")
        settings = sheet.worksheet("Settings")
        records = settings.get_all_records()

        for row in records:
            owner = str(row.get("Owner Discord ID", "")).strip().lower()
            gm = str(row.get("GM Discord ID", "")).strip().lower()

            if username.lower() == owner or username.lower() == gm:
                team_name = row.get("Team Name")
                salary_remaining = float(row.get("Salary Remaining", 0))
                roster_count = int(row.get("Roster Count", 0))
                role = "Owner" if username.lower() == owner else "GM"

                players = get_team_roster(team_name)

                return {
                    "teamName": team_name,
                    "salaryRemaining": salary_remaining,
                    "rosterCount": roster_count,
                    "players": players,
                    "role": role
                }

        return None
    except Exception as e:
        print(f"[ERROR] get_team_data_for_user: {e}")
        return None


def load_nomination_order():
    try:
        sheet = client.open_by_key("1QeLyKIgTSYFkLUqPcUrKyJBqTIo8WZoL-BI6tmqWcHk")
        worksheet = sheet.worksheet("Team List")
        values = worksheet.col_values(1)[1:]  # skip header
        return [team.strip() for team in values if team.strip()]
    except Exception as e:
        print(f"[ERROR] Failed to load nomination order: {e}")
        return []
