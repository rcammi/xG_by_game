import warnings

from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt

from bs4 import BeautifulSoup
import requests


# avoid deprecated warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# scraps url and gets squad name, link to squad and squad logo. Returns dataframe with scraped data. URL = https://fbref.com/en/comps/Big5/Big-5-European-Leagues-Stats
def scrap_urls():
    URL = "https://fbref.com/en/comps/Big5/Big-5-European-Leagues-Stats"
    req = requests.get(URL, headers={'User-Agent': 'Mozilla/5.0'})

    soup = BeautifulSoup(req.content, 'lxml')

    squads = {}

    for link in (soup.find_all('td', {"class":"left", "data-stat":["squad", "country"]})):
        if link.find("a") != None:
            squad = link.a.text.replace(" ","-").rstrip().lstrip().encode('utf-8')
            data_link = link.a.get("href")
            squadId = data_link.split("/")[3]
            img_link = link.img.get("src")
            data = ['https://fbref.com' + data_link, squadId, img_link]
        elif link.find("span") != None:    
            data.append(link.text)
            
        squads[squad] = data
        
    squads_df = pd.DataFrame.from_dict(squads, orient='index', columns=["data_link", "squadId", "img_link", "country"])

    return(squads_df)

#print(url_data[url_data["country"] == "it ITA"])

def scrap_data(url_df, league):
    # create big frame to append all league squads
    big_frame = pd.DataFrame()
    
    url_df = url_df[url_df["country"] == league].reset_index().rename(columns={'index':'squad'})
    squadName = (list(url_df.squad))
    for squad in squadName:
        squad_df = url_df[url_df["squad"] == squad]
        #print(squad_df["squadId"].values[0])
        squadId = squad_df["squadId"].values[0]
        table_link = "http://fbref.com/en/squads/{id}//2021-2022/matchlogs/{squadName}-Stats#matchlogs_for".format(id=squadId, squadName=squad)
        #print(table_link)
        
        # read data from html
        data = pd.read_html(table_link)[0]
        #print(data[0])
        data["squadName"] = squad.decode('utf-8').replace("-"," ") #.replace("b","").replace("'","")  
        big_frame = big_frame.append(data)
        print(squad.decode('utf-8') + " DONE")

    return(big_frame)

#big_frame = scrap_data(url_data, "it ITA")

#print(big_frame)

def clean_data(data):
    # filter by home leagues only
    comp = ['Bundesliga','Premier League','La Liga','Ligue 1','Serie A']
    only_leagues = data[data["Comp"].isin(comp)]
    # if match report equals "head to head" match is not played. Skip today matches. Skip postponed matches.from datetime import datetime
    today = datetime.today().strftime('%Y-%m-%d')
    only_league_filt = only_leagues[(only_leagues["Match Report"] != 'Head-to-Head') & (only_leagues["Date"] != today) & (only_leagues["Notes"] != 'Match Postponed')]
    # fill nan notes values notes with "-"
    only_league_filt["Notes"] = only_league_filt["Notes"].fillna("-")
    # fill nan attendance values notes with 0
    only_league_filt["Attendance"] = only_league_filt["Attendance"].fillna(0)
    # set GA and GF to float values
    only_league_filt[["GF","GA"]] = only_league_filt[["GF","GA"]].apply(pd.to_numeric)
    # calculate xG diff
    only_league_filt["xG_dif"] = only_league_filt["xG"] - only_league_filt["xGA"]
    # set col of matchweek
    only_league_filt["Matchweek"] = only_league_filt["Round"].apply(lambda x: int(x.split(" ")[1]))
    # set col of matchweek + opponent
    only_league_filt["Matchweek_rival"] = only_league_filt["Matchweek"].apply(lambda x: str(x)) + "_" + only_league_filt["Opponent"].apply(lambda x: x[:3].upper())

    return(only_league_filt)


def plot(data, league):
    #data = only_league_filt[only_league_filt["Comp"] == league].reset_index().sort_values(by="Matchweek", ascending=True)
    
    # set style
    plt.style.use('grayscale') # default

    # open figure
    fig, axes = plt.subplots(nrows=4, ncols=5,sharex=True, sharey=True, figsize=(12,8))
    axes_list = [item for sublist in axes for item in sublist]

    #plot main titles
    plt.figtext(0,1.02,'xG by Game, {league} 2021-22'.format(league=league), fontsize=18, ha='left', weight='bold', color='black') # 1.01

    # plot credits
    plt.figtext(1.0,1.03,'By: Renzo Cammi (@cammi_renzo)',
                ha='right',fontsize=10)
    plt.figtext(1.0,1.0090,'Data: StatsBomb via FBref',
            ha='right', fontsize=10)

    squadNames = sorted(list(data.squadName.unique()))

    for squad in squadNames:
        data_squad = data[data["squadName"] == squad]

        ax = axes_list.pop(0)

        ax.set_title(squad, fontsize=14)

        x = data_squad.xG
        y = data_squad.xGA

        ax.scatter(x, y, c=data_squad["xG_dif"], cmap='seismic_r') #, linewidth=5

        # get 3 outliers matches
        outliers_xG = data_squad.sort_values(by='xG', ascending=False).head(1)
        outliers_xGA = data_squad.sort_values(by='xGA', ascending=False).head(1)
        outliers = outliers_xG.append(outliers_xGA)

        for row in outliers.iterrows():
            texts = [ax.annotate(row[1]["Matchweek_rival"], (row[1].xG+0.01, row[1].xGA+0.01), fontsize=8, ha='left')]
            #texts = [plt.figtext(row[1].xG, row[1].xGA, row[1]["Matchweek_rival"], ha='center', transform=ax.transData)]
            #texts = [plt.text(row[1].xG, row[1].xGA, row[1]["Matchweek_rival"])]
            #adjust_text(texts)
        

        ax.plot([0, 1], [0, 1], color='black', ls='--', alpha=0.30, transform=ax.transAxes)

    for ax in axes_list:
        ax.remove()

    # set labels
    plt.figtext(0,0.5,'xGA', rotation=90, fontsize=12, ha='center', color='black')
    plt.figtext(0.5,0,'xG', fontsize=12, ha='center', color='black')


    #adjust subplots in the figure 
    plt.tight_layout()

    #save figure
    plt.savefig('xG_by_Game_{league}.png'.format(league=league), bbox_inches="tight", dpi=300)

    #Display figure
    return(plt.show())

def main():
    url_data = scrap_urls()
    leagues = {'Bundesliga':'de GER', 'Premier League':'eng ENG', 'La Liga':'es ESP', 'Ligue 1':'fr FRA', 'Serie A':'it ITA'} 
    # Ask user to pick league
    print("##Choose between top 5 leagues of europe##")
    print("")
    for league in leagues.keys():
        print('##'+league)
    print("")
    answer = input("Write your answer: ")
    print("")
    while answer not in list(leagues.keys()):
        print("Try again. Type league name correctly.")
        answer = input("Write your answer: ")
    else:
        # big_frame = pd.DataFrame() # build big dataframe with top 5 leagues
        #return(print(scrap_data(url_data, leagues[1])))
        country = leagues[answer]
        league_df = scrap_data(url_data, country)
        data = clean_data(league_df)
        print(data)
        plot(data, answer)

    quit()

    #return(data.to_csv("{league}.csv".format(league=answer)))
    
    # for league in leagues:
    #     league_df = scrap_data(url_data, league)
    #     print(league_df)
    #     big_frame = big_frame.append(league_df)

    
    #return(big_frame.to_csv("big_frame.csv"))

main()    

# set colors by result of match
# big_frame.loc[big_frame["Result"] == 'W', 'color'] = 'g'
# big_frame.loc[big_frame["Result"] == 'D', 'color'] = 'b'
# big_frame.loc[big_frame["Result"] == 'L', 'color'] = 'r'
# big_frame.loc[big_frame["Notes"] == 'Match Postponed', ['Poss','Result','color']] = [0,'Match Postponed','y']

# crear big frame
# analizar big frame (valores nulos, incoherencias, cosas por corregir)
# plotear grafico con distintas variables y posibilidad de elegir liga

# get league squad
# squad_df = pd.read_html("https://fbref.com/en/comps/9/Premier-League-Stats#results111601_overall")[0]
# squad_df["Squad_dash"] = squad_df["Squad"].apply(lambda x: x.replace(" ","-"))
# squads = squad_df.Squad_dash.unique()

# print(squads)

# print (big_frame.tail())
# print (big_frame.shape)

# drop NA rows
# data = data.iloc[:29,:]

# print(data[["Round","Poss","Result","color"]])

# # plot scatter

# #set plot style
# plt.style.use('classic')

# plt.title("Aca va el titulo")

# ax = plt.scatter(x=data.Round, y=data.Poss, color=data.color)

# plt.xticks(rotation = 90)
# plt.grid(alpha=0.2)

# handles, labels = ax.get_legend_handles_labels()
# ax.legend(handles, labels)
# plt.show()