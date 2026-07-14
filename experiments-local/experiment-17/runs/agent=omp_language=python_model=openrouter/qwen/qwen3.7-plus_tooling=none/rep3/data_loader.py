import pandas as pd
import unidecode
import re
from pathlib import Path

def normalize_team(name: str) -> str:
    if pd.isna(name):
        return ""
    name = str(name).strip()
    # Remove state suffixes like -SP, -RJ
    name = re.sub(r'-[A-Z]{2}$', '', name, flags=re.IGNORECASE)
    # Remove accents and lowercase
    name = unidecode.unidecode(name).lower()
    
    simplifications = {
        "sport club corinthians paulista": "corinthians",
        "corinthians": "corinthians",
        "sao paulo fc": "sao paulo",
        "sao paulo": "sao paulo",
        "fluminense fc": "fluminense",
        "fluminense": "fluminense",
        "cr flamengo": "flamengo",
        "flamengo": "flamengo",
        "sociedade esportiva palmeiras": "palmeiras",
        "palmeiras": "palmeiras",
        "gremio foot-ball porto alegrense": "gremio",
        "gremio": "gremio",
        "sport club internacional": "internacional",
        "internacional": "internacional",
        "cruzeiro esporte clube": "cruzeiro",
        "cruzeiro": "cruzeiro",
        "atletico mineiro": "atletico-mg",
        "atletico-mg": "atletico-mg",
        "atletico paranaense": "atletico-pr",
        "atletico-pr": "atletico-pr",
        "botafogo de futebol e regatas": "botafogo",
        "botafogo": "botafogo",
        "club de regatas vasco da gama": "vasco",
        "vasco da gama": "vasco",
        "vasco": "vasco",
        "ec vitoria": "vitoria",
        "vitoria": "vitoria",
        "ec bahia": "bahia",
        "bahia": "bahia",
        "sport club do recife": "sport recife",
        "sport recife": "sport recife",
        "ceara sporting club": "ceara",
        "ceara": "ceara",
        "fortaleza esporte clube": "fortaleza",
        "fortaleza": "fortaleza",
        "santos fc": "santos",
        "santos": "santos",
    }
    
    # Check for exact match or substring match in simplifications
    for key, val in simplifications.items():
        if key in name or name in key:
            return val
            
    # Generic cleanup for other names
    name = name.replace(" sport club", "").replace(" futebol clube", "").replace(" fc", "").replace(" ec ", " ").replace(" clube de regatas", "").replace(" associação", "").strip()
    return name

def load_data(data_dir: Path = Path("data/kaggle")):
    # 1. Brasileirao Matches
    df_brasileirao = pd.read_csv(data_dir / "Brasileirao_Matches.csv")
    df_brasileirao["competition"] = "Brasileirao"
    df_brasileirao["round_stage"] = df_brasileirao["round"].astype(str)
    df_brasileirao["date"] = pd.to_datetime(df_brasileirao["datetime"], errors="coerce")
    df_brasileirao["home_team_norm"] = df_brasileirao["home_team"].apply(normalize_team)
    df_brasileirao["away_team_norm"] = df_brasileirao["away_team"].apply(normalize_team)

    # 2. Brazilian Cup Matches
    df_cup = pd.read_csv(data_dir / "Brazilian_Cup_Matches.csv")
    df_cup["competition"] = "Copa do Brasil"
    df_cup["round_stage"] = df_cup["round"].astype(str)
    df_cup["date"] = pd.to_datetime(df_cup["datetime"], errors="coerce")
    df_cup["home_team_norm"] = df_cup["home_team"].apply(normalize_team)
    df_cup["away_team_norm"] = df_cup["away_team"].apply(normalize_team)

    # 3. Libertadores Matches
    df_libertadores = pd.read_csv(data_dir / "Libertadores_Matches.csv")
    df_libertadores["competition"] = "Libertadores"
    df_libertadores["round_stage"] = df_libertadores["stage"].astype(str)
    df_libertadores["date"] = pd.to_datetime(df_libertadores["datetime"], errors="coerce")
    df_libertadores["home_team_norm"] = df_libertadores["home_team"].apply(normalize_team)
    df_libertadores["away_team_norm"] = df_libertadores["away_team"].apply(normalize_team)

    # 4. BR Football Dataset
    df_br = pd.read_csv(data_dir / "BR-Football-Dataset.csv")
    df_br["competition"] = df_br["tournament"]
    df_br["round_stage"] = "N/A"
    df_br["date"] = pd.to_datetime(df_br["date"].astype(str) + " " + df_br["time"].astype(str), errors="coerce")
    df_br["season"] = pd.to_datetime(df_br["date"]).dt.year
    df_br.rename(columns={"home": "home_team", "away": "away_team"}, inplace=True)
    df_br["home_team_norm"] = df_br["home_team"].apply(normalize_team)
    df_br["away_team_norm"] = df_br["away_team"].apply(normalize_team)

    # 5. Novo Campeonato Brasileiro
    df_novo = pd.read_csv(data_dir / "novo_campeonato_brasileiro.csv")
    df_novo["competition"] = "Brasileirao Historico"
    df_novo["round_stage"] = df_novo["Rodada"].astype(str)
    df_novo["date"] = pd.to_datetime(df_novo["Data"], format="%d/%m/%Y", errors="coerce")
    df_novo.rename(columns={
        "Equipe_mandante": "home_team",
        "Equipe_visitante": "away_team",
        "Gols_mandante": "home_goal",
        "Gols_visitante": "away_goal",
        "Ano": "season"
    }, inplace=True)
    df_novo["home_team_norm"] = df_novo["home_team"].apply(normalize_team)
    df_novo["away_team_norm"] = df_novo["away_team"].apply(normalize_team)

    # Combine all match data
    common_cols = ["competition", "season", "round_stage", "date", "home_team", "away_team", "home_team_norm", "away_team_norm", "home_goal", "away_goal"]
    
    dfs_to_concat = []
    for df in [df_brasileirao, df_cup, df_libertadores, df_br, df_novo]:
        for col in common_cols:
            if col not in df.columns:
                df[col] = None
        dfs_to_concat.append(df[common_cols])
                
    df_matches = pd.concat(dfs_to_concat, ignore_index=True)
    df_matches = df_matches.dropna(subset=["date"])
    df_matches["season"] = df_matches["season"].astype("Int64")
    
    # Ensure goal columns are numeric
    df_matches["home_goal"] = pd.to_numeric(df_matches["home_goal"], errors="coerce").fillna(0).astype(int)
    df_matches["away_goal"] = pd.to_numeric(df_matches["away_goal"], errors="coerce").fillna(0).astype(int)
    
    # 6. FIFA Player Data
    df_players = pd.read_csv(data_dir / "fifa_data.csv")
    df_players["Name_norm"] = df_players["Name"].apply(lambda x: normalize_team(x) if pd.notna(x) else "")
    df_players["Club_norm"] = df_players["Club"].apply(lambda x: normalize_team(x) if pd.notna(x) else "")
    df_players["Nationality_norm"] = df_players["Nationality"].apply(lambda x: normalize_team(x) if pd.notna(x) else "")
    
    return df_matches, df_players
