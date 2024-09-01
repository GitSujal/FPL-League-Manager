# FPL Private League Manager

This repo contains a Python script that can be used to manage a private league in the Fantasy Premier League (FPL) game. The list of the player id needs to be provided in the `players.config` file. The script will then fetch the data of the players and display it in a tabular format. The data includes the player's name, team, position, total points, and the points scored in the last gameweek. The data is fetched from the FPL API. It will also calculate the current balance for each player to make managing your leagues easier with your friends. 

Enjoy!

## Requirements

Install the required packages using the following command:

```bash
pip install -r requirements.txt
```

## Usage

Run the streamlit app using the following command:

```bash
streamlit run main.py
```
