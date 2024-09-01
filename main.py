from fpl import FPL
import asyncio
import aiohttp
import json
import pandas as pd
import streamlit as st

st.set_page_config(page_title="FPL Manager", page_icon=":soccer:", layout="wide")
st.title("FPL Manager - Hostel Gang")   


config_file = 'players.json'
config = json.load(open(config_file))
players = config['players']
accounts = config['accounts']

c1, c2 = st.columns([1, 3])

async def get_current_gameweek():
    async with aiohttp.ClientSession() as session:
        fpl = FPL(session)
        for i in range(1,47):
            try:
                gameweek = await fpl.get_gameweek(i)
                if gameweek.is_current:
                    return gameweek
            except:
                return None    
        return None

async def get_user_gameweek_score(user_id, gameweek):
    async with aiohttp.ClientSession() as session:
        fpl = FPL(session)
        user = await fpl.get_user(user_id)
        gameweek = await user.get_gameweek_history(gameweek)
        return gameweek['points']

async def get_users():
    users_df = pd.DataFrame(columns=["Name", "Team Name", "Total Points"])
    async with aiohttp.ClientSession() as session:
        fpl = FPL(session)
        for player in players:
            user = await fpl.get_user(player)
            new_user_df = pd.DataFrame([[f"{user.player_first_name} {user.player_last_name}", 
                                         user.name, 
                                         user.summary_overall_points,
                                         user.id
                                         ]], columns=["Name", "Team Name", "Total Points", 'ID'])
            users_df = pd.concat([users_df, new_user_df], ignore_index=True)
        # sort the users by total points in descending order and reset the index
        users_df = users_df.sort_values(by="Total Points", ascending=False)
        users_df = users_df.reset_index(drop=True)
        # add a rank column
        users_df.index += 1
        users_df.index.name = "Rank"
    return users_df

users_df = asyncio.run(get_users())
# display the users in a table
# st.write(f" ### Overall Table")
# st.dataframe(users_df, hide_index=False, use_container_width=True, column_config={
#     "Rank": {"max_width": 100},
#     "Name": {"max_width": 200},
#     "Team Name": {"max_width": 200},
#     "Total Points": {"max_width": 100},
#     },
#     column_order=["Rank", "Name", "Team Name", "Total Points"])

current_gameweek = asyncio.run(get_current_gameweek())
# st.write(f"### Current Gameweek: {current_gameweek.id}")

all_gameweek_df = pd.DataFrame(columns=["Player_ID", "Gameweek", "Points"])

completed_gameweeks = range(1, current_gameweek.id)

# for all completed gameweeks find the weekly scores for each player and store in a dataframe
for gameweek in completed_gameweeks:
    gameweek_df = pd.DataFrame(columns=["Player_ID", "Gameweek", "Points", "Winner"])
    for player in players:
        user_gameweek_score = asyncio.run(get_user_gameweek_score(player, gameweek))
        new_gameweek_df = pd.DataFrame([[int(player), f"Gameweek {gameweek}", user_gameweek_score, False]], columns=["Player_ID", "Gameweek", "Points", "Winner"])
        gameweek_df = pd.concat([gameweek_df, new_gameweek_df], ignore_index=True)
    gameweek_df = gameweek_df.sort_values(by="Points", ascending=False)
    gameweek_df = gameweek_df.reset_index(drop=True)
    # mark the winner of the gameweek
    max_points = gameweek_df["Points"].max()
    gameweek_df.loc[gameweek_df["Points"] == max_points, "Winner"] = True
    all_gameweek_df = pd.concat([all_gameweek_df, gameweek_df], ignore_index=True)

# PIVOT the table to show each gameweek as a column
pivot_df = all_gameweek_df.pivot(index="Player_ID", columns="Gameweek", values="Points")

# join the gameweek dataframe with the users dataframe to get the names of the players
pivot_df = pd.merge(pivot_df, users_df, left_on="Player_ID", right_on="ID", how="left")
# sort it based on the total points
pivot_df = pivot_df.sort_values(by="Total Points", ascending=False)
pivot_df = pivot_df.reset_index(drop=True)
# add a rank column
pivot_df.index += 1
pivot_df.index.name = "Rank"
st.write("### Current Standings")
req_columns = ["Rank", "Name", "Team Name"] + [f"Gameweek {i}" for i in completed_gameweeks] + ["Total Points"]
st.dataframe(pivot_df.style.highlight_max(axis=0, color='blue', subset=[f"Gameweek {i}" for i in completed_gameweeks]),
             hide_index=False, 
             use_container_width=True,
             column_order=req_columns
)

# Ledger Management
st.write("### Accounts Ledger")

# League Rule
# Every player pays $5 per gameweek
# Winner of the gameweek gets $30
# Overall winner gets remaining amount

# Calculate the total amount collected
gameweek_amount = accounts["gameweek_win"]
overall_win_amount = accounts["overall_win"]
each_gameweek_cost = accounts["per_gameweek_cost"]


# Money to be distributed
# Find the winner of each gameweek
ledger_df = pd.DataFrame(columns=["Player_ID","Name", "Gameweek Wins", "Total Points", "Current Balance"])

# Find the winners of each gameweek and calculate the weekly win amount The sum will be divided by the number of winners
winners = all_gameweek_df[all_gameweek_df["Winner"] == True]
winners_each_gameweek = winners.groupby("Gameweek")["Player_ID"].count().reset_index()
winners_each_gameweek.columns = ["Gameweek", "Winners"]
winners_each_gameweek["Weekly Win"] = gameweek_amount / winners_each_gameweek["Winners"]


# join teh winners_each_gameweek with all gameweek df 
all_gameweek_df = pd.merge(all_gameweek_df, winners_each_gameweek, on="Gameweek", how="left")
all_gameweek_df["Weekly Win"] = all_gameweek_df["Weekly Win"].fillna(0)
# only keep the win amount for the winners
all_gameweek_df.loc[all_gameweek_df["Winner"] == False, "Weekly Win"] = 0
# join the all_gameweek_df with the users_df to get the names
all_gameweek_df = pd.merge(all_gameweek_df, users_df, left_on="Player_ID", right_on="ID", how="left")

# group by Name and sum the weekly wins
ledger_df = all_gameweek_df.groupby("Name").agg({"Weekly Win": "sum", "Total Points": "first"}).reset_index()

# overall winner
pivot_df["Overall Winner"] = False
max_points = pivot_df["Total Points"].max()
pivot_df.loc[pivot_df["Total Points"] == max_points, "Overall Winner"] = True
# count the number of overall winners
overall_winners = pivot_df[pivot_df["Overall Winner"] == True].shape[0]
# calculate the overall win amount
overall_win_amount = overall_win_amount / overall_winners
# add the overall win amount to the ledger
ledger_df["Overall Win"] = 0
ledger_df.loc[ledger_df["Total Points"] == max_points, "Overall Win"] = overall_win_amount

# Final Balance
ledger_df["Current Balance"] = ledger_df["Weekly Win"] + ledger_df["Overall Win"] - each_gameweek_cost*len(completed_gameweeks)
ledger_df["Current Balance"] = ledger_df["Current Balance"].round(2)
# sort the ledger by the Total Points in descending order
ledger_df = ledger_df.sort_values(by="Total Points", ascending=False)
ledger_df = ledger_df.reset_index(drop=True)
# add a rank column
ledger_df.index += 1
ledger_df.index.name = "Rank"
st.dataframe(ledger_df,
             hide_index=False, use_container_width=True, column_config={
    "Rank": {"max_width": 100},
    "Name": {"max_width": 200},
    "Gameweek Wins": {"max_width": 100},
    "Total Points": {"max_width": 100},
    "Weekly Win": st.column_config.NumberColumn(format="$ %.2f"),
    "Overall Win": st.column_config.NumberColumn(format="$ %.2f"),
    "Current Balance": st.column_config.NumberColumn(format="$ %.2f")
    },
    column_order=["Rank", "Name", "Gameweek Wins", "Weekly Win", "Overall Win", "Current Balance"]
)
