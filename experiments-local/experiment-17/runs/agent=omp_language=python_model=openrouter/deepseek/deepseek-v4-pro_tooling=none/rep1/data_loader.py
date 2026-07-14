"""
Brazilian Soccer MCP Server - Data Loader
========================================
Loads all 6 CSV datasets from data/kaggle/ and normalizes team names
for consistent cross-dataset querying.

Data sources:
  - Brasileirao_Matches.csv: Serie A matches (2012+)
  - Brazilian_Cup_Matches.csv: Copa do Brasil matches (2012+)
  - Libertadores_Matches.csv: Copa Libertadores matches (2013+)
  - BR-Football-Dataset.csv: Extended match statistics
  - novo_campeonato_brasileiro.csv: Historical Brasileirao (2003-2019)
  - fifa_data.csv: FIFA player database

Team name normalization handles:
  - State suffixes: "Palmeiras-SP" -> "Palmeiras"
  - Full names: "Sport Club Corinthians Paulista" -> "Corinthians"
  - Parentheticals: "Nacional (URU)" -> "Nacional"
  - Extra descriptors: "Boavista Sport Club (antigo ...) - RJ" -> "Boavista"

Date formats handled:
  - ISO: "2023-09-24"
  - Brazilian: "29/03/2003"
  - With time: "2012-05-19 18:30:00"
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd


DATA_DIR = Path(__file__).parent / "data" / "kaggle"


# ── Team Name Normalization ─────────────────────────────────────────────────

# Known team name mappings: canonical name -> set of variants
_TEAM_ALIASES: dict[str, set[str]] = {
    'Flamengo': {'Flamengo', 'Flamengo (RJ)', 'Flamengo-RJ'},
    'Fluminense': {'Fluminense', 'Fluminense (RJ)', 'Fluminense-RJ'},
    'Vasco': {'Vasco', 'Vasco (RJ)', 'Vasco da Gama', 'Vasco-RJ'},
    'Botafogo': {'Botafogo', 'Botafogo (RJ)', 'Botafogo-RJ'},
    'Palmeiras': {'Palmeiras', 'Palmeiras (SP)', 'Palmeiras-SP'},
    'Corinthians': {'Corinthians', 'Corinthians (SP)', 'Corinthians-SP', 'Sport Club Corinthians Paulista'},
    'Sao Paulo': {'Sao Paulo', 'Sao Paulo (SP)', 'Sao Paulo-SP', 'São Paulo', 'São Paulo (SP)', 'São Paulo-SP'},
    'Santos': {'Santos', 'Santos (SP)', 'Santos-SP'},
    'Gremio': {'Gremio', 'Gremio (RS)', 'Gremio-RS', 'Grêmio', 'Grêmio (RS)', 'Grêmio-RS'},
    'Internacional': {'Internacional', 'Internacional (RS)', 'Internacional-RS'},
    'Atletico-MG': {'Atletico (MG)', 'Atletico-MG', 'Atlético (MG)', 'Atlético-MG'},
    'Cruzeiro': {'Cruzeiro', 'Cruzeiro (MG)', 'Cruzeiro-MG'},
    'Athletico-PR': {'Athletico-PR', 'Atletico (PR)', 'Atlético (PR)', 'Atlético-PR'},
    'Coritiba': {'Coritiba', 'Coritiba (PR)', 'Coritiba-PR'},
    'Bahia': {'Bahia', 'Bahia (BA)', 'Bahia-BA'},
    'Vitoria': {'Vitoria', 'Vitoria (BA)', 'Vitoria-BA', 'Vitória', 'Vitória (BA)', 'Vitória-BA'},
    'Sport': {'Sport', 'Sport (PE)', 'Sport Recife', 'Sport-PE'},
    'Fortaleza': {'Fortaleza', 'Fortaleza (CE)', 'Fortaleza-CE'},
    'Ceara': {'Ceara', 'Ceara (CE)', 'Ceara-CE', 'Ceará', 'Ceará (CE)', 'Ceará-CE'},
    'Goias': {'Goias', 'Goias (GO)', 'Goias-GO', 'Goiás', 'Goiás (GO)', 'Goiás-GO'},
    'Atletico-GO': {'Atletico (GO)', 'Atletico-GO', 'Atlético (GO)', 'Atlético-GO'},
    'Avai': {'Avai', 'Avai (SC)', 'Avai-SC', 'Avaí', 'Avaí (SC)', 'Avaí-SC'},
    'Figueirense': {'Figueirense', 'Figueirense (SC)', 'Figueirense-SC'},
    'Chapecoense': {'Chapecoense', 'Chapecoense (SC)', 'Chapecoense-SC'},
    'Criciuma': {'Criciuma', 'Criciuma (SC)', 'Criciuma-SC', 'Criciúma', 'Criciúma (SC)', 'Criciúma-SC'},
    'Joinville': {'Joinville', 'Joinville (SC)', 'Joinville-SC'},
    'Ponte Preta': {'Ponte Preta', 'Ponte Preta (SP)', 'Ponte Preta-SP'},
    'Portuguesa': {'Portuguesa', 'Portuguesa (SP)', 'Portuguesa-SP'},
    'Bragantino': {'Bragantino', 'Bragantino (SP)', 'Bragantino-SP', 'Red Bull Bragantino'},
    'Guarani': {'Guarani', 'Guarani (SP)', 'Guarani-SP'},
    'Nautico': {'Nautico', 'Nautico (PE)', 'Nautico-PE', 'Náutico', 'Náutico (PE)', 'Náutico-PE'},
    'Santa Cruz': {'Santa Cruz', 'Santa Cruz (PE)', 'Santa Cruz-PE'},
    'America-MG': {'America (MG)', 'America-MG', 'América (MG)', 'América-MG'},
    'America-RN': {'America (RN)', 'America-RN', 'América (RN)', 'América-RN'},
    'Parana': {'Parana', 'Parana (PR)', 'Parana-PR', 'Paraná', 'Paraná (PR)', 'Paraná-PR'},
    'Paysandu': {'Paysandu', 'Paysandu (PA)', 'Paysandu-PA'},
    'ABC': {'ABC', 'ABC (RN)', 'ABC-RN'},
    'CSA': {'CSA', 'CSA (AL)', 'CSA-AL'},
    'Cuiaba': {'Cuiaba', 'Cuiaba-MT', 'Cuiabá', 'Cuiabá-MT'},
    'Juventude': {'Juventude', 'Juventude (RS)', 'Juventude-RS'},
    'Botafogo-SP': {'Botafogo (SP)', 'Botafogo-SP'},
    'Sampaio Correa': {'Sampaio Correa', 'Sampaio Correa-MA', 'Sampaio Corrêa', 'Sampaio Corrêa-MA'},
    'CRB': {'CRB', 'CRB (AL)', 'CRB-AL'},
    'Londrina': {'Londrina', 'Londrina (PR)', 'Londrina-PR'},
    'Oeste': {'Oeste', 'Oeste (SP)', 'Oeste-SP'},
    'Brasil de Pelotas': {'Brasil (RS)', 'Brasil de Pelotas', 'Brasil de Pelotas-RS', 'Brasil-RS'},
    'Vila Nova': {'Vila Nova', 'Vila Nova (GO)', 'Vila Nova-GO'},
    'Tombense': {'Tombense', 'Tombense-MG'},
    'Novorizontino': {'Grêmio Novorizontino', 'Novorizontino', 'Novorizontino-SP'},
    'Mirassol': {'Mirassol', 'Mirassol-SP'},
    'Ituano': {'Ituano', 'Ituano-SP'},
    'Santo Andre': {'Santo Andre', 'Santo Andre-SP', 'Santo André', 'Santo André-SP'},
    'Sao Caetano': {'Sao Caetano', 'São Caetano', 'São Caetano-SP'},
    'Ipatinga': {'Ipatinga', 'Ipatinga-MG'},
    'Barueri': {'Barueri', 'Grêmio Barueri', 'Grêmio Prudente'},
    'Portuguesa-RJ': {'Portuguesa (RJ)', 'Portuguesa-RJ'},
    'America-RJ': {'America (RJ)', 'America-RJ', 'América (RJ)', 'América-RJ'},
    'Bangu': {'Bangu', 'Bangu-RJ'},
    'Madureira': {'Madureira', 'Madureira-RJ'},
    'Volta Redonda': {'Volta Redonda', 'Volta Redonda-RJ'},
    'Remo': {'Remo', 'Remo-PA'},
    'Confianca': {'Confianca', 'Confianca-SE', 'Confiança', 'Confiança-SE'},
    'Ferroviario': {'Ferroviario', 'Ferroviario-CE', 'Ferroviário', 'Ferroviário-CE'},
    'Operario': {'Operario', 'Operario-PR', 'Operário', 'Operário-PR'},
    'Brusque': {'Brusque', 'Brusque-SC'},
    'Ypiranga': {'Ypiranga', 'Ypiranga-RS'},
    'Manaus': {'Manaus', 'Manaus-AM'},
    'Altos': {'Altos', 'Altos-PI'},
    'Botafogo-PB': {'Botafogo (PB)', 'Botafogo-PB'},
    'Treze': {'Treze', 'Treze-PB'},
    'Campinense': {'Campinense', 'Campinense-PB'},
    'Sousa': {'Sousa', 'Sousa-PB'},
    'Moto Club': {'Moto Club', 'Moto Club-MA'},
    'River-PI': {'River (PI)', 'River-PI'},
    'Flamengo-PI': {'Flamengo (PI)', 'Flamengo-PI'},
    'Parnahyba': {'Parnahyba', 'Parnahyba-PI'},
    '4 de Julho': {'4 de Julho', '4 de Julho-PI'},
    'Atletico-CE': {'Atletico (CE)', 'Atletico-CE', 'Atlético (CE)', 'Atlético-CE'},
    'Bahia de Feira': {'Bahia de Feira', 'Bahia de Feira-BA'},
    'Juazeirense': {'Juazeirense', 'Juazeirense-BA'},
    'Jacuipense': {'Jacuipense', 'Jacuipense-BA'},
    'Vitoria da Conquista': {'Vitoria da Conquista', 'Vitória da Conquista', 'Vitória da Conquista-BA'},
    'Flamengo-BA': {'Flamengo (BA)', 'Flamengo-BA'},
    'Atletico-BA': {'Atletico (BA)', 'Atletico-BA', 'Atlético (BA)', 'Atlético-BA'},
    'Barcelona de Ilheus': {'Barcelona de Ilheus', 'Barcelona de Ilhéus', 'Barcelona-BA'},
    'ASA': {'ASA', 'ASA de Arapiraca', 'ASA-AL'},
    'Murici': {'Murici', 'Murici-AL'},
    'Coruripe': {'Coruripe', 'Coruripe-AL'},
    'CSE': {'CSE', 'CSE-AL'},
    'CEO': {'CEO', 'CEO-AL'},
    'Cruzeiro-AL': {'Cruzeiro (AL)', 'Cruzeiro-AL'},
    'Sergipe': {'Sergipe', 'Sergipe-SE'},
    'Itabaiana': {'Itabaiana', 'Itabaiana-SE'},
    'Lagarto': {'Lagarto', 'Lagarto-SE'},
    'Falcon': {'Falcon', 'Falcon-SE'},
    'Atletico-Globo': {'Atletico-Globo', 'Atlético Globo', 'Globo', 'Globo-RN'},
    'Potiguar': {'Potiguar', 'Potiguar de Mossoro', 'Potiguar-RN'},
    'Santa Cruz-RN': {'Santa Cruz (RN)', 'Santa Cruz de Natal', 'Santa Cruz-RN'},
    'Forca e Luz': {'Forca e Luz', 'Força e Luz', 'Força e Luz-RN'},
    'ASSU': {'ASSU', 'ASSU-RN'},
    'Baraunas': {'Baraunas', 'Baraunas-RN', 'Baraúnas', 'Baraúnas-RN'},
    'Alecrim': {'Alecrim', 'Alecrim-RN'},
    'Palmeira': {'Palmeira', 'Palmeira-RN'},
    'Visao Celeste': {'Visao Celeste', 'Visão Celeste', 'Visão Celeste-RN'},
    'Sociedade Esportiva Caico': {'Caico-RN', 'Caicó', 'Sociedade Esportiva Caico'},
    'Campinense-PB': {'Campinense (PB)', 'Campinense-PB'},
    'Auto Esporte-PB': {'Auto Esporte (PB)', 'Auto Esporte-PB'},
    'Atletico-PB': {'Atletico de Cajazeiras', 'Atletico-PB', 'Atlético de Cajazeiras', 'Atlético-PB'},
    'Nacional-PB': {'Nacional (PB)', 'Nacional de Patos', 'Nacional-PB'},
    'CSP': {'CSP', 'CSP-PB'},
    'Sao Paulo Crystal': {'Sao Paulo Crystal', 'São Paulo Crystal', 'São Paulo Crystal-PB'},
    'Salgueiro': {'Salgueiro', 'Salgueiro-PE'},
    'Central': {'Central', 'Central-PE'},
    'Petrolina': {'Petrolina', 'Petrolina-PE'},
    'Afogados': {'Afogados', 'Afogados da Ingazeira', 'Afogados-PE'},
    'Retro': {'Retro', 'Retro-PE', 'Retrô', 'Retrô-PE'},
    'Sete de Setembro': {'Sete de Setembro', 'Sete de Setembro-PE'},
    'Vera Cruz': {'Vera Cruz', 'Vera Cruz-PE'},
    'Academica Vitoria': {'Academica Vitoria', 'Acadêmica Vitória', 'Acadêmica Vitória-PE'},
    'Caruaru City': {'Caruaru City', 'Caruaru City-PE'},
    'Ibis': {'Ibis', 'Ibis-PE', 'Íbis', 'Íbis-PE'},
    'Decisao': {'Decisao', 'Decisao-PE', 'Decisão', 'Decisão-PE'},
    'Ferroviario-PE': {'Ferroviario (PE)', 'Ferroviario-PE', 'Ferroviário (PE)', 'Ferroviário-PE'},
    'Porto-PE': {'Clube Atlético do Porto', 'Porto (PE)', 'Porto-PE'},
    'Belo Jardim': {'Belo Jardim', 'Belo Jardim-PE'},
    'America-PE': {'America (PE)', 'America-PE', 'América (PE)', 'América-PE'},
    'Atletico-Torres': {'Atletico-Torres', 'Atlético Torres', 'Atlético Torres-PE'},
    'Jaguar': {'Jaguar', 'Jaguar-PE'},
    'Cabense': {'Cabense', 'Cabense-PE'},
    'Pesqueira': {'Pesqueira', 'Pesqueira-PE'},
    'Serrano-PE': {'Serrano (PE)', 'Serrano-PE'},
    'Timbauba': {'Timbauba', 'Timbauba-PE', 'Timbaúba', 'Timbaúba-PE'},
    'Ypiranga-PE': {'Ypiranga (PE)', 'Ypiranga-PE'},
    'Centro Limoeirense': {'Centro Limoeirense', 'Centro Limoeirense-PE'},
    'Flamengo-PE': {'Flamengo (PE)', 'Flamengo de Arcoverde', 'Flamengo-PE'},
    '1 de Maio': {'1 de Maio', '1 de Maio-PE'},
    'Chã Grande': {'Chã Grande', 'Chã Grande-PE'},
    'Atletico-PE': {'Atletico (PE)', 'Atletico-PE', 'Atlético (PE)', 'Atlético-PE'},
    'Sao Domingos': {'Sao Domingos', 'São Domingos', 'São Domingos-PE'},
    'Barreiros': {'Barreiros', 'Barreiros-PE'},
    'Ferroviario do Cabo': {'Ferroviario do Cabo', 'Ferroviário do Cabo', 'Ferroviário do Cabo-PE'},
    'Estudantes': {'Estudantes', 'Estudantes-PE'},
    'Flamengo de Arcoverde': {'Flamengo de Arcoverde', 'Flamengo de Arcoverde-PE'},
    'Interporto': {'Interporto', 'Interporto-TO'},
    'Tocantinopolis': {'Tocantinopolis', 'Tocantinopolis-TO', 'Tocantinópolis', 'Tocantinópolis-TO'},
    'Palmas': {'Palmas', 'Palmas-TO'},
    'Gurupi': {'Gurupi', 'Gurupi-TO'},
    'Araguaina': {'Araguaina', 'Araguaina-TO', 'Araguaína', 'Araguaína-TO'},
    'Capital-TO': {'Capital (TO)', 'Capital-TO'},
    'Sparta': {'Sparta', 'Sparta-TO'},
    'Alvorada': {'Alvorada', 'Alvorada-TO'},
    'Uniao Araguainense': {'Uniao Araguainense', 'União Araguainense', 'União Araguainense-TO'},
    'Tocantins': {'Tocantins', 'Tocantins-TO'},
    'Atletico Cerrado': {'Atletico Cerrado', 'Atlético Cerrado', 'Atlético Cerrado-TO'},
    'Paraiso': {'Paraiso', 'Paraiso-TO', 'Paraíso', 'Paraíso-TO'},
    'Bela Vista-TO': {'Bela Vista (TO)', 'Bela Vista-TO'},
    'Colinas': {'Colinas', 'Colinas-TO'},
    'Guarai': {'Guarai', 'Guarai-TO', 'Guaraí', 'Guaraí-TO'},
    'Impratriz': {'Imperatriz', 'Imperatriz-MA', 'Impratriz'},
    'Sampaio Correa-MA': {'Sampaio Correa (MA)', 'Sampaio Correa-MA', 'Sampaio Corrêa (MA)', 'Sampaio Corrêa-MA'},
    'Maranhao': {'Maranhao', 'Maranhao-MA', 'Maranhão', 'Maranhão-MA'},
    'Cordino': {'Cordino', 'Cordino-MA'},
    'Juventude-MA': {'Juventude (MA)', 'Juventude Samas', 'Juventude-MA'},
    'Tuntum': {'Tuntum', 'Tuntum-MA'},
    'Sao Jose-MA': {'Sao Jose (MA)', 'Sao Jose-MA', 'São José (MA)', 'São José-MA'},
    'Pinheiro': {'Pinheiro', 'Pinheiro-MA'},
    'Chapadinha': {'Chapadinha', 'Chapadinha-MA'},
    'Timon': {'Timon', 'Timon-MA'},
    'Bacabal': {'Bacabal', 'Bacabal-MA'},
    'IAPE': {'IAPE', 'IAPE-MA'},
    'Santa Quiteria': {'Santa Quiteria', 'Santa Quitéria', 'Santa Quitéria-MA'},
    'Americano-MA': {'Americano (MA)', 'Americano-MA'},
    'Expressinho': {'Expressinho', 'Expressinho-MA'},
    'Sabia': {'Sabia', 'Sabia-MA', 'Sabiá', 'Sabiá-MA'},
    'JV Lideral': {'JV Lideral', 'JV Lideral-MA'},
    'Sao Bento-MA': {'Sao Bento (MA)', 'Sao Bento-MA', 'São Bento (MA)', 'São Bento-MA'},
    'Viana': {'Viana', 'Viana-MA'},
    'Sao Raimundo-RR': {'Sao Raimundo (RR)', 'Sao Raimundo-RR', 'São Raimundo (RR)', 'São Raimundo-RR'},
    'Nautico-RR': {'Nautico (RR)', 'Nautico-RR', 'Náutico (RR)', 'Náutico-RR'},
    'Atletico Roraima': {'Atletico Roraima', 'Atlético Roraima', 'Atlético Roraima-RR'},
    'Baré': {'Baré', 'Baré-RR'},
    'GAS': {'GAS', 'GAS-RR'},
    'Rio Negro-RR': {'Rio Negro (RR)', 'Rio Negro-RR'},
    'Progresso': {'Progresso', 'Progresso-RR'},
    'Real-RR': {'Real (RR)', 'Real-RR'},
    'River-RR': {'River (RR)', 'River-RR'},
    'Sao Raimundo-AM': {'Sao Raimundo (AM)', 'Sao Raimundo-AM', 'São Raimundo (AM)', 'São Raimundo-AM'},
    'Fast Clube': {'Fast Clube', 'Fast Clube-AM'},
    'Nacional-AM': {'Nacional (AM)', 'Nacional-AM'},
    'Princesa do Solimoes': {'Princesa do Solimoes', 'Princesa do Solimões', 'Princesa do Solimões-AM'},
    'Penarol-AM': {'Penarol (AM)', 'Penarol-AM', 'Peñarol (AM)'},
    'Manaus FC': {'Manaus FC', 'Manaus-AM'},
    'Amazonas': {'Amazonas', 'Amazonas-AM'},
    'Manauara': {'Manauara', 'Manauara-AM'},
    'Iranduba': {'Iranduba', 'Iranduba-AM'},
    'Rio Negro-AM': {'Rio Negro (AM)', 'Rio Negro-AM'},
    'Sul America': {'Sul America', 'Sul América', 'Sul América-AM'},
    'Nacional Fast Clube': {'Nacional Fast Clube', 'Nacional Fast Clube-AM'},
    'Holanda': {'Holanda', 'Holanda-AM'},
    'Tarumã': {'Tarumã', 'Tarumã-AM'},
    'CDC Manicoré': {'CDC Manicoré', 'CDC Manicoré-AM'},
    'Operario-AM': {'Operario (AM)', 'Operario-AM', 'Operário (AM)', 'Operário-AM'},
    'JC': {'JC', 'JC-AM'},
    'Clíper': {'Clíper', 'Clíper-AM'},
    'Humaitá': {'Humaitá', 'Humaitá-AM'},
    'Atletico Acreano': {'Atletico Acreano', 'Atlético Acreano', 'Atlético Acreano-AC'},
    'Rio Branco-AC': {'Rio Branco (AC)', 'Rio Branco-AC'},
    'Galvez': {'Galvez', 'Galvez-AC'},
    'Placido de Castro': {'Placido de Castro', 'Plácido de Castro', 'Plácido de Castro-AC'},
    'Vasco-AC': {'Vasco (AC)', 'Vasco-AC'},
    'Andira': {'Andira', 'Andira-AC', 'Andirá', 'Andirá-AC'},
    'Humaita-AC': {'Humaita (AC)', 'Humaita-AC', 'Humaitá (AC)', 'Humaitá-AC'},
    'Nauas': {'Nauas', 'Nauas-AC'},
    'Sao Francisco-AC': {'Sao Francisco-AC', 'São Francisco (AC)', 'São Francisco-AC'},
    'Independencia': {'Independencia', 'Independência', 'Independência-AC'},
    'ADESG': {'ADESG', 'ADESG-AC'},
    'Alto Acre': {'Alto Acre', 'Alto Acre-AC'},
    'Juventus-AC': {'Juventus (AC)', 'Juventus-AC'},
    'Amax': {'Amax', 'Amax-AC'},
    'Nacional-AC': {'Nacional (AC)', 'Nacional-AC'},
    'Senador Guiomard': {'Senador Guiomard', 'Senador Guiomard-AC'},
    'Atletico-AC': {'Atletico (AC)', 'Atletico-AC', 'Atlético (AC)', 'Atlético-AC'},
    'Sao Raimundo-PA': {'Sao Raimundo (PA)', 'Sao Raimundo-PA', 'São Raimundo (PA)', 'São Raimundo-PA'},
    'Aguia de Maraba': {'Aguia de Maraba', 'Águia de Marabá', 'Águia de Marabá-PA'},
    'Independente-PA': {'Independente (PA)', 'Independente-PA'},
    'Paragominas': {'Paragominas', 'Paragominas-PA'},
    'Castanhal': {'Castanhal', 'Castanhal-PA'},
    'Bragantino-PA': {'Bragantino (PA)', 'Bragantino-PA'},
    'Cameta': {'Cameta', 'Cameta-PA', 'Cametá', 'Cametá-PA'},
    'Santa Rosa': {'Santa Rosa', 'Santa Rosa-PA'},
    'Tuna Luso': {'Tuna Luso', 'Tuna Luso-PA'},
    'Tapajos': {'Tapajos', 'Tapajos-PA', 'Tapajós', 'Tapajós-PA'},
    'Carajas': {'Carajas', 'Carajas-PA', 'Carajás', 'Carajás-PA'},
    'Parauapebas': {'Parauapebas', 'Parauapebas-PA'},
    'Itupiranga': {'Itupiranga', 'Itupiranga-PA'},
    'Pedreira': {'Pedreira', 'Pedreira-PA'},
    'Pinheirense': {'Pinheirense', 'Pinheirense-PA'},
    'Sport Belem': {'Sport Belem', 'Sport Belém', 'Sport Belém-PA'},
    'Sao Francisco-PA': {'Sao Francisco-PA', 'São Francisco (PA)', 'São Francisco-PA'},
    'Desportiva Paraense': {'Desportiva Paraense', 'Desportiva Paraense-PA'},
    'Vila Rica': {'Vila Rica', 'Vila Rica-PA'},
    'Tiradentes-PA': {'Tiradentes (PA)', 'Tiradentes-PA'},
    'Atletico-PA': {'Atletico (PA)', 'Atletico-PA', 'Atlético (PA)', 'Atlético-PA'},
    'Izabelense': {'Izabelense', 'Izabelense-PA'},
    'Vila Nova-PA': {'Vila Nova (PA)', 'Vila Nova-PA'},
    'Elf': {'Elf', 'Elf-PA'},
    'Canaa': {'Canaa', 'Canaã', 'Canaã-PA'},
    'Fonte Nova': {'Fonte Nova', 'Fonte Nova-PA'},
    'Caete': {'Caete', 'Caeté', 'Caeté-PA'},
    'Atletico-AP': {'Atletico (AP)', 'Atletico-AP', 'Atlético (AP)', 'Atlético-AP'},
    'Santos-AP': {'Santos (AP)', 'Santos-AP'},
    'Ypiranga-AP': {'Ypiranga (AP)', 'Ypiranga-AP'},
    'Sao Paulo-AP': {'Sao Paulo (AP)', 'Sao Paulo-AP', 'São Paulo (AP)', 'São Paulo-AP'},
    'Trem': {'Trem', 'Trem-AP'},
    'Independente-AP': {'Independente (AP)', 'Independente-AP'},
    'Macapa': {'Macapa', 'Macapa-AP', 'Macapá', 'Macapá-AP'},
    'Santana': {'Santana', 'Santana-AP'},
    'Oratorio': {'Oratorio', 'Oratorio-AP', 'Oratório', 'Oratório-AP'},
    'Cristal': {'Cristal', 'Cristal-AP'},
    'Mazagao': {'Mazagao', 'Mazagao-AP', 'Mazagão', 'Mazagão-AP'},
    'Bare': {'Bare', 'Baré', 'Baré-RR'},
    'Genus': {'Genus', 'Genus-RO'},
    'Real Ariquemes': {'Real Ariquemes', 'Real Ariquemes-RO'},
    'Barcelona-RO': {'Barcelona (RO)', 'Barcelona-RO'},
    'Ji-Parana': {'Ji-Parana', 'Ji-Parana-RO', 'Ji-Paraná', 'Ji-Paraná-RO'},
    'Rondoniense': {'Rondoniense', 'Rondoniense-RO'},
    'Porto Velho': {'Porto Velho', 'Porto Velho-RO'},
    'Vilhenense': {'Vilhenense', 'Vilhenense-RO'},
    'Uniao Cacoalense': {'Uniao Cacoalense', 'União Cacoalense', 'União Cacoalense-RO'},
    'Guapore': {'Guapore', 'Guapore-RO', 'Guaporé', 'Guaporé-RO'},
    'Vilhena': {'Vilhena', 'Vilhena-RO'},
    'Pimentense': {'Pimentense', 'Pimentense-RO'},
    'Colorado': {'Colorado', 'Colorado-RO'},
    'Cacoalense': {'Cacoalense', 'Cacoalense-RO'},
    'Rolim de Moura': {'Rolim de Moura', 'Rolim de Moura-RO'},
    'Cruzeiro-RO': {'Cruzeiro (RO)', 'Cruzeiro-RO'},
    'Ariquemes': {'Ariquemes', 'Ariquemes-RO'},
    'Espigao': {'Espigao', 'Espigao-RO', 'Espigão', 'Espigão-RO'},
    'Sao Domingos-RO': {'Sao Domingos-RO', 'São Domingos (RO)', 'São Domingos-RO'},
    'Jaru': {'Jaru', 'Jaru-RO'},
    'Moto Club-RO': {'Moto Club (RO)', 'Moto Club-RO'},
    'Shallon': {'Shallon', 'Shallon-RO'},
    'Luverdense': {'Luverdense', 'Luverdense-MT'},
    'Sinop': {'Sinop', 'Sinop-MT'},
    'Uniao Rondonopolis': {'Uniao Rondonopolis', 'União Rondonópolis', 'União Rondonópolis-MT'},
    'Operario-MT': {'Operario (MT)', 'Operario-MT', 'Operário (MT)', 'Operário-MT'},
    'Mixto': {'Mixto', 'Mixto-MT'},
    'Dom Bosco': {'Dom Bosco', 'Dom Bosco-MT'},
    'Acao': {'Acao', 'Acao-MT', 'Ação', 'Ação-MT'},
    'Cacerense': {'Cacerense', 'Cacerense-MT'},
    'Nova Mutum': {'Nova Mutum', 'Nova Mutum-MT'},
    'Sorriso': {'Sorriso', 'Sorriso-MT'},
    'Gremio Sorriso': {'Gremio Sorriso', 'Grêmio Sorriso', 'Grêmio Sorriso-MT'},
    'Araguaia': {'Araguaia', 'Araguaia-MT'},
    'Poconé': {'Poconé', 'Poconé-MT'},
    'Campo Verde': {'Campo Verde', 'Campo Verde-MT'},
    'Rondonopolis': {'Rondonopolis', 'Rondonopolis-MT', 'Rondonópolis', 'Rondonópolis-MT'},
    'Barra do Garcas': {'Barra do Garcas', 'Barra do Garças', 'Barra do Garças-MT'},
    'Comercial-MS': {'Comercial (MS)', 'Comercial-MS'},
    'Aquidauanense': {'Aquidauanense', 'Aquidauanense-MS'},
    'Operario-MS': {'Operario (MS)', 'Operario-MS', 'Operário (MS)', 'Operário-MS'},
    'Costa Rica': {'Costa Rica', 'Costa Rica-MS'},
    'Corumbaense': {'Corumbaense', 'Corumbaense-MS'},
    'Sete de Setembro-MS': {'Sete de Setembro (MS)', 'Sete de Setembro-MS'},
    'Chapadao': {'Chapadao', 'Chapadao-MS', 'Chapadão', 'Chapadão-MS'},
    'Naviraiense': {'Naviraiense', 'Naviraiense-MS'},
    'Dourados': {'Dourados', 'Dourados-MS'},
    'Ivinhema': {'Ivinhema', 'Ivinhema-MS'},
    'URSO': {'URSO', 'URSO-MS'},
    'Novoperario': {'Novoperario', 'Novoperário', 'Novoperário-MS'},
    'Agua Santa': {'Agua Santa', 'Água Santa', 'Água Santa-MS'},
    'Maracaju': {'Maracaju', 'Maracaju-MS'},
    'Mundo Novo': {'Mundo Novo', 'Mundo Novo-MS'},
    'Uniao ABC': {'Uniao ABC', 'União ABC', 'União ABC-MS'},
    'CENE': {'CENE', 'CENE-MS'},
    'Itaporã': {'Itaporã', 'Itaporã-MS'},
    'CEOV': {'CEOV', 'CEOV-MT'},
    'Atletico-MT': {'Atletico (MT)', 'Atletico-MT', 'Atlético (MT)', 'Atlético-MT'},
    'Cuiaba EC': {'Cuiaba EC', 'Cuiabá EC', 'Cuiabá-MT'},
    'Gama': {'Gama', 'Gama-DF'},
    'Brasiliense': {'Brasiliense', 'Brasiliense-DF'},
    'Ceilandia': {'Ceilandia', 'Ceilandia-DF', 'Ceilândia', 'Ceilândia-DF'},
    'Sobradinho': {'Sobradinho', 'Sobradinho-DF'},
    'Luziania': {'Luziania', 'Luziania-DF', 'Luziânia', 'Luziânia-DF'},
    'Capital-DF': {'Capital (DF)', 'Capital-DF'},
    'Paranoa': {'Paranoa', 'Paranoa-DF', 'Paranoá', 'Paranoá-DF'},
    'Santa Maria-DF': {'Santa Maria (DF)', 'Santa Maria-DF'},
    'Taguatinga': {'Taguatinga', 'Taguatinga-DF'},
    'Real Brasilia': {'Real Brasilia', 'Real Brasília', 'Real Brasília-DF'},
    'Formosa': {'Formosa', 'Formosa-GO'},
    'Samambaia': {'Samambaia', 'Samambaia-DF'},
    'Unaí': {'Unaí', 'Unaí-DF'},
    'Brasilia': {'Brasilia', 'Brasília', 'Brasília-DF'},
    'Legiao': {'Legiao', 'Legião', 'Legião-DF'},
    'Planaltina': {'Planaltina', 'Planaltina-DF'},
    'Guara': {'Guara', 'Guara-DF', 'Guará', 'Guará-DF'},
    'Dom Pedro': {'Dom Pedro', 'Dom Pedro-DF'},
    'Bolamense': {'Bolamense', 'Bolamense-DF'},
    'CFZ': {'CFZ', 'CFZ-DF'},
    'Bosque': {'Bosque', 'Bosque-DF'},
    'Aparecidense': {'Aparecidense', 'Aparecidense-GO'},
    'Anapolis': {'Anapolis', 'Anapolis-GO', 'Anápolis', 'Anápolis-GO'},
    'Goianesia': {'Goianesia', 'Goianesia-GO', 'Goianésia', 'Goianésia-GO'},
    'Ipora': {'Ipora', 'Ipora-GO', 'Iporá', 'Iporá-GO'},
    'Gremio Anapolis': {'Gremio Anapolis', 'Grêmio Anápolis', 'Grêmio Anápolis-GO'},
    'CRAC': {'CRAC', 'CRAC-GO'},
    'Goiania': {'Goiania', 'Goiania-GO', 'Goiânia', 'Goiânia-GO'},
    'Morrinhos': {'Morrinhos', 'Morrinhos-GO'},
    'Rio Verde': {'Rio Verde', 'Rio Verde-GO'},
    'Itumbiara': {'Itumbiara', 'Itumbiara-GO'},
    'Jataiense': {'Jataiense', 'Jataiense-GO'},
    'Jaragua': {'Jaragua', 'Jaragua-GO', 'Jaraguá', 'Jaraguá-GO'},
    'Trindade': {'Trindade', 'Trindade-GO'},
    'Goiatuba': {'Goiatuba', 'Goiatuba-GO'},
    'Inhumas': {'Inhumas', 'Inhumas-GO'},
    'Santa Helena': {'Santa Helena', 'Santa Helena-GO'},
    'Rio Branco-ES': {'Rio Branco (ES)', 'Rio Branco-ES'},
    'Desportiva Ferroviaria': {'Desportiva Ferroviaria', 'Desportiva Ferroviária', 'Desportiva Ferroviária-ES'},
    'Real Noroeste': {'Real Noroeste', 'Real Noroeste-ES'},
    'Vitoria-ES': {'Vitoria (ES)', 'Vitoria-ES', 'Vitória (ES)', 'Vitória-ES'},
    'Estrela do Norte': {'Estrela do Norte', 'Estrela do Norte-ES'},
    'Sao Mateus': {'Sao Mateus', 'São Mateus', 'São Mateus-ES'},
    'Serra': {'Serra', 'Serra-ES'},
    'Atletico Itapemirim': {'Atletico Itapemirim', 'Atlético Itapemirim', 'Atlético Itapemirim-ES'},
    'Espirito Santo': {'Espirito Santo', 'Espírito Santo', 'Espírito Santo-ES'},
    'Linhares': {'Linhares', 'Linhares-ES'},
    'Nova Venecia': {'Nova Venecia', 'Nova Venécia', 'Nova Venécia-ES'},
    'CTE Colatina': {'CTE Colatina', 'CTE Colatina-ES'},
    'Vilavelhense': {'Vilavelhense', 'Vilavelhense-ES'},
    'Castelo': {'Castelo', 'Castelo-ES'},
    'Tupy': {'Tupy', 'Tupy-ES'},
    'Rio Branco-VN': {'Rio Branco VN', 'Rio Branco VN-ES', 'Rio Branco-VN'},
    'Pinheiros-ES': {'Pinheiros (ES)', 'Pinheiros-ES'},
    'Sport-ES': {'Sport (ES)', 'Sport-ES'},
    'Capixaba': {'Capixaba', 'Capixaba-ES'},
    'Doze': {'Doze', 'Doze-ES'},
    'Atletico Colatinense': {'Atletico Colatinense', 'Atlético Colatinense', 'Atlético Colatinense-ES'},
    'Aracruz': {'Aracruz', 'Aracruz-ES'},
    'Colatina': {'Colatina', 'Colatina-ES'},
    'GEL': {'GEL', 'GEL-ES'},
    'Jaguaré': {'Jaguaré', 'Jaguaré-ES'},
    'Sao Gabriel': {'Sao Gabriel', 'São Gabriel', 'São Gabriel-ES'},
    'Boa Vista': {'Boa Vista', 'Boa Vista-ES'},
    'Fundao': {'Fundao', 'Fundão', 'Fundão-ES'},
    'Cachoeiro': {'Cachoeiro', 'Cachoeiro-ES'},
    'Atletico Cariacica': {'Atletico Cariacica', 'Atlético Cariacica', 'Atlético Cariacica-ES'},
    'Guarapari': {'Guarapari', 'Guarapari-ES'},
    'Sao Bento-ES': {'Sao Bento (ES)', 'Sao Bento-ES', 'São Bento (ES)', 'São Bento-ES'},
    'America-ES': {'America (ES)', 'America-ES', 'América (ES)', 'América-ES'},
    'Botafogo-ES': {'Botafogo (ES)', 'Botafogo-ES'},
    'Vila Nova-ES': {'Vila Nova (ES)', 'Vila Nova-ES'},
    'Flamengo-ES': {'Flamengo (ES)', 'Flamengo-ES'},
    'Itapemirim': {'Itapemirim', 'Itapemirim-ES'},
    'Sao Jose-ES': {'Sao Jose (ES)', 'Sao Jose-ES', 'São José (ES)', 'São José-ES'},
    'Comercial-ES': {'Comercial (ES)', 'Comercial-ES'},
    'Alfredo Chaves': {'Alfredo Chaves', 'Alfredo Chaves-ES'},
    'Muniz Freire': {'Muniz Freire', 'Muniz Freire-ES'},
    'Gremio Laranjeiras': {'Gremio Laranjeiras', 'Grêmio Laranjeiras', 'Grêmio Laranjeiras-ES'},
    'Botafogo-BA': {'Botafogo (BA)', 'Botafogo-BA'},
    'Fluminense de Feira': {'Fluminense de Feira', 'Fluminense de Feira-BA'},
    'Jacobina': {'Jacobina', 'Jacobina-BA'},
    'Jequie': {'Jequie', 'Jequie-BA', 'Jequié', 'Jequié-BA'},
    'Colo Colo': {'Colo Colo', 'Colo Colo-BA'},
    'Galicia': {'Galicia', 'Galicia-BA', 'Galícia', 'Galícia-BA'},
    'Catuense': {'Catuense', 'Catuense-BA'},
    'Feirense': {'Feirense', 'Feirense-BA'},
    'Ipitanga': {'Ipitanga', 'Ipitanga-BA'},
    'Itabuna': {'Itabuna', 'Itabuna-BA'},
    'UNIRB': {'UNIRB', 'UNIRB-BA'},
    'Atletico Alagoinhas': {'Atletico Alagoinhas', 'Atlético Alagoinhas', 'Atlético Alagoinhas-BA'},
    'Doce Mel': {'Doce Mel', 'Doce Mel-BA'},
    'Grapiuna': {'Grapiuna', 'Grapiúna', 'Grapiúna-BA'},
    'Barcelona-BA': {'Barcelona (BA)', 'Barcelona-BA'},
    'Jacobina EC': {'Jacobina EC', 'Jacobina-BA'},
    'Camacari': {'Camacari', 'Camaçari', 'Camaçari-BA'},
    'Madre de Deus': {'Madre de Deus', 'Madre de Deus-BA'},
    'Teixeira de Freitas': {'Teixeira de Freitas', 'Teixeira de Freitas-BA'},
    'Eunapolis': {'Eunapolis', 'Eunápolis', 'Eunápolis-BA'},
    'Paulo Afonso': {'Paulo Afonso', 'Paulo Afonso-BA'},
    'Serrinha': {'Serrinha', 'Serrinha-BA'},
    'Astro': {'Astro', 'Astro-BA'},
    'Camaçariense': {'Camaçariense', 'Camaçariense-BA'},
    'ABAH': {'ABAH', 'ABAH-BA'},
    'Cruzeiro-BA': {'Cruzeiro (BA)', 'Cruzeiro-BA'},
    'America-BA': {'America (BA)', 'America-BA', 'América (BA)', 'América-BA'},
    'Fluminense-BA': {'Fluminense (BA)', 'Fluminense-BA'},
    'Santos-BA': {'Santos (BA)', 'Santos-BA'},
    'Sao Paulo-BA': {'Sao Paulo-BA', 'São Paulo (BA)', 'São Paulo-BA'},
    'Internacional-BA': {'Internacional (BA)', 'Internacional-BA'},
    'Corinthians-BA': {'Corinthians (BA)', 'Corinthians-BA'},
    'Palmeiras-BA': {'Palmeiras (BA)', 'Palmeiras-BA'},
    'Gremio-BA': {'Gremio (BA)', 'Gremio-BA', 'Grêmio (BA)', 'Grêmio-BA'},
    'Vasco-BA': {'Vasco (BA)', 'Vasco-BA'},
    'Gremio Esportivo Juventus': {'Gremio Esportivo Juventus', 'Grêmio Esportivo Juventus'},
    'Marcilio Dias': {'Marcilio Dias', 'Marcílio Dias', 'Marcílio Dias-SC'},
    'Metropolitano': {'Metropolitano', 'Metropolitano-SC'},
    'Hercilio Luz': {'Hercilio Luz', 'Hercílio Luz', 'Hercílio Luz-SC'},
    'Concordia': {'Concordia', 'Concordia-SC', 'Concórdia', 'Concórdia-SC'},
    'Camboriu': {'Camboriu', 'Camboriu-SC', 'Camboriú', 'Camboriú-SC'},
    'Barra-SC': {'Barra (SC)', 'Barra-SC'},
    'Inter de Lages': {'Inter de Lages', 'Inter de Lages-SC'},
    'Tubarao': {'Tubarao', 'Tubarao-SC', 'Tubarão', 'Tubarão-SC'},
    'Guarani de Palhoca': {'Guarani de Palhoca', 'Guarani de Palhoça', 'Guarani de Palhoça-SC'},
    'Almirante Barroso': {'Almirante Barroso', 'Almirante Barroso-SC'},
    'Atletico Tubarao': {'Atletico Tubarao', 'Atlético Tubarão', 'Atlético Tubarão-SC'},
    'Atletico Itajai': {'Atletico Itajai', 'Atlético Itajaí', 'Atlético Itajaí-SC'},
    'Carlos Renaux': {'Carlos Renaux', 'Carlos Renaux-SC'},
    'Blumenau': {'Blumenau', 'Blumenau-SC'},
    'Paysandu-SC': {'Paysandu (SC)', 'Paysandu-SC'},
    'Imbituba': {'Imbituba', 'Imbituba-SC'},
    'Oeste-SC': {'Oeste (SC)', 'Oeste-SC'},
    'Porto-SC': {'Porto (SC)', 'Porto-SC'},
    'Atletico Hermann Aichinger': {'Atletico Hermann Aichinger', 'Atlético Hermann Aichinger', 'Atlético Hermann Aichinger-SC'},
    'Biguaçu': {'Biguaçu', 'Biguaçu-SC'},
    'Orleans': {'Orleans', 'Orleans-SC'},
    'Atletico Batistense': {'Atletico Batistense', 'Atlético Batistense', 'Atlético Batistense-SC'},
    'Fluminense-SC': {'Fluminense (SC)', 'Fluminense-SC'},
    'Juventus-SC': {'Juventus (SC)', 'Juventus-SC'},
    'Canoinhas': {'Canoinhas', 'Canoinhas-SC'},
    'Guarani-SC': {'Guarani (SC)', 'Guarani-SC'},
    'Campo Grande': {'Campo Grande', 'Campo Grande-RJ'},
    'Bonsucesso': {'Bonsucesso', 'Bonsucesso-RJ'},
    'Americano': {'Americano', 'Americano-RJ'},
    'Resende': {'Resende', 'Resende-RJ'},
    'Macaé': {'Macaé', 'Macaé-RJ'},
    'Cabofriense': {'Cabofriense', 'Cabofriense-RJ'},
    'Nova Iguacu': {'Nova Iguacu', 'Nova Iguaçu', 'Nova Iguaçu-RJ'},
    'Friburguense': {'Friburguense', 'Friburguense-RJ'},
    'Audax Rio': {'Audax Rio', 'Audax Rio-RJ'},
    'Boavista': {'Boavista', 'Boavista Sport Club', 'Boavista-RJ'},
    'Boavista Sport Club': {'Boavista', 'Boavista Sport Club', 'Boavista-RJ'},
    'Olaria': {'Olaria', 'Olaria-RJ'},
    'Duque de Caxias': {'Duque de Caxias', 'Duque de Caxias-RJ'},
    'Tigres do Brasil': {'Tigres do Brasil', 'Tigres do Brasil-RJ'},
    'Artsul': {'Artsul', 'Artsul-RJ'},
    'Goncalense': {'Goncalense', 'Gonçalense', 'Gonçalense-RJ'},
    'Sampaio Correa-RJ': {'Sampaio Correa (RJ)', 'Sampaio Correa-RJ', 'Sampaio Corrêa (RJ)', 'Sampaio Corrêa-RJ'},
    'Goytacaz': {'Goytacaz', 'Goytacaz-RJ'},
    'Serra Macaense': {'Serra Macaense', 'Serra Macaense-RJ'},
    'Sao Goncalo': {'Sao Goncalo', 'São Gonçalo', 'São Gonçalo-RJ'},
    'Barcelona-RJ': {'Barcelona (RJ)', 'Barcelona-RJ'},
    'Carapebus': {'Carapebus', 'Carapebus-RJ'},
    'Barra da Tijuca': {'Barra da Tijuca', 'Barra da Tijuca-RJ'},
    'Campos': {'Campos', 'Campos-RJ'},
    'Itaborai': {'Itaborai', 'Itaboraí', 'Itaboraí-RJ'},
    'Mesquita': {'Mesquita', 'Mesquita-RJ'},
    'Serrano-RJ': {'Serrano (RJ)', 'Serrano-RJ'},
    'Angra dos Reis': {'Angra dos Reis', 'Angra dos Reis-RJ'},
    'CerES': {'CerES', 'CerES-RJ'},
    'Sao Cristovao': {'Sao Cristovao', 'São Cristóvão', 'São Cristóvão-RJ'},
    'Barra Mansa': {'Barra Mansa', 'Barra Mansa-RJ'},
    'Casimiro de Abreu': {'Casimiro de Abreu', 'Casimiro de Abreu-RJ'},
    'Rio Sao Paulo': {'Rio Sao Paulo', 'Rio São Paulo', 'Rio São Paulo-RJ'},
    'Araruama': {'Araruama', 'Araruama-RJ'},
    '7 de Abril': {'7 de Abril', '7 de Abril-RJ'},
    'Atletico Carioca': {'Atletico Carioca', 'Atlético Carioca', 'Atlético Carioca-RJ'},
    'Buzios': {'Buzios', 'Búzios', 'Búzios-RJ'},
    'CEAC': {'CEAC', 'CEAC-RJ'},
    'Mageense': {'Mageense', 'Mageense-RJ'},
    'Sao Pedro-RJ': {'Sao Pedro (RJ)', 'Sao Pedro-RJ', 'São Pedro (RJ)', 'São Pedro-RJ'},
    'Nova Cidade': {'Nova Cidade', 'Nova Cidade-RJ'},
    'Rio de Janeiro': {'Rio de Janeiro', 'Rio de Janeiro-RJ'},
    'Santa Cruz-RJ': {'Santa Cruz (RJ)', 'Santa Cruz-RJ'},
    'Bela Vista-RJ': {'Bela Vista (RJ)', 'Bela Vista-RJ'},
    'Uniao de Marechal Hermes': {'Uniao de Marechal Hermes', 'União de Marechal Hermes', 'União de Marechal Hermes-RJ'},
    'Heliopolis': {'Heliopolis', 'Heliópolis', 'Heliópolis-RJ'},
    'Sao Jose-RJ': {'Sao Jose (RJ)', 'Sao Jose-RJ', 'São José (RJ)', 'São José-RJ'},
    'Juventus-RJ': {'Juventus (RJ)', 'Juventus-RJ'},
    'Vera Cruz-RJ': {'Vera Cruz (RJ)', 'Vera Cruz-RJ'},
    'Atletico-RJ': {'Atletico (RJ)', 'Atletico-RJ', 'Atlético (RJ)', 'Atlético-RJ'},
    'Rio Branco-RJ': {'Rio Branco (RJ)', 'Rio Branco-RJ'},
    'Portuguesa Carioca': {'Portuguesa Carioca', 'Portuguesa Carioca-RJ'},
    'Paduano': {'Paduano', 'Paduano-RJ'},
    'Santo Antonio': {'Santo Antonio', 'Santo Antônio', 'Santo Antônio-RJ'},
    'Sao Goncalo EC': {'Sao Goncalo EC', 'São Gonçalo EC', 'São Gonçalo EC-RJ'},
    'Perolas Negras': {'Perolas Negras', 'Pérolas Negras', 'Pérolas Negras-RJ'},
    'Belford Roxo': {'Belford Roxo', 'Belford Roxo-RJ'},
    'Riostrense': {'Riostrense', 'Riostrense-RJ'},
    'Sao Jose-SP': {'Sao Jose (SP)', 'Sao Jose-SP', 'São José (SP)', 'São José-SP'},
    'Ferroviaria': {'Ferroviaria', 'Ferroviária', 'Ferroviária-SP'},
    'Inter de Limeira': {'Inter de Limeira', 'Inter de Limeira-SP'},
    'Sao Bento': {'Sao Bento', 'São Bento', 'São Bento-SP'},
    'XV de Piracicaba': {'XV de Piracicaba', 'XV de Piracicaba-SP'},
    'Rio Claro': {'Rio Claro', 'Rio Claro-SP'},
    'Portuguesa Santista': {'Portuguesa Santista', 'Portuguesa Santista-SP'},
    'Sao Bernardo': {'Sao Bernardo', 'São Bernardo', 'São Bernardo-SP'},
    'Agua Santa-SP': {'Agua Santa (SP)', 'Agua Santa-SP', 'Água Santa (SP)', 'Água Santa-SP'},
    'Velo Clube': {'Velo Clube', 'Velo Clube-SP'},
    'Linense': {'Linense', 'Linense-SP'},
    'Penapolense': {'Penapolense', 'Penapolense-SP'},
    'Marilia': {'Marilia', 'Marília', 'Marília-SP'},
    'Noroeste': {'Noroeste', 'Noroeste-SP'},
    'Comercial-SP': {'Comercial (SP)', 'Comercial-SP'},
    'Batatais': {'Batatais', 'Batatais-SP'},
    'Matonense': {'Matonense', 'Matonense-SP'},
    'Monte Azul': {'Monte Azul', 'Monte Azul-SP'},
    'Sertaozinho': {'Sertaozinho', 'Sertãozinho', 'Sertãozinho-SP'},
    'Uniao Sao Joao': {'Uniao Sao Joao', 'União São João', 'União São João-SP'},
    'Catanduvense': {'Catanduvense', 'Catanduvense-SP'},
    'Olimpia': {'Olimpia', 'Olímpia', 'Olímpia-SP'},
    'Votuporanguense': {'Votuporanguense', 'Votuporanguense-SP'},
    'Barretos': {'Barretos', 'Barretos-SP'},
    'Atletico Sorocaba': {'Atletico Sorocaba', 'Atlético Sorocaba', 'Atlético Sorocaba-SP'},
    'Capivariano': {'Capivariano', 'Capivariano-SP'},
    'Independente-SP': {'Independente (SP)', 'Independente-SP'},
    'Taubate': {'Taubate', 'Taubaté', 'Taubaté-SP'},
    'Nacional-SP': {'Nacional (SP)', 'Nacional-SP'},
    'Juventus-SP': {'Juventus (SP)', 'Juventus-SP'},
    'Paulista': {'Paulista', 'Paulista-SP'},
    'Gremio Osasco': {'Gremio Osasco', 'Grêmio Osasco', 'Grêmio Osasco-SP'},
    'Audax-SP': {'Audax (SP)', 'Audax-SP'},
    'Taboao da Serra': {'Taboao da Serra', 'Taboão da Serra', 'Taboão da Serra-SP'},
    'Flamengo-SP': {'Flamengo (SP)', 'Flamengo-SP'},
    'Jabaquara': {'Jabaquara', 'Jabaquara-SP'},
    'Gremio Prudente': {'Gremio Prudente', 'Grêmio Prudente', 'Grêmio Prudente-SP'},
    'Santacruzense': {'Santacruzense', 'Santacruzense-SP'},
    'Joseense': {'Joseense', 'Joseense-SP'},
    'Gremio Mauaense': {'Gremio Mauaense', 'Grêmio Mauaense', 'Grêmio Mauaense-SP'},
    'Gremio Barueri': {'Gremio Barueri', 'Grêmio Barueri', 'Grêmio Barueri-SP'},
    'Osasco': {'Osasco', 'Osasco-SP'},
    'EC Sao Bernardo': {'EC Sao Bernardo', 'EC São Bernardo', 'EC São Bernardo-SP'},
    'Sao Vicente': {'Sao Vicente', 'São Vicente', 'São Vicente-SP'},
    'Mauaense': {'Mauaense', 'Mauaense-SP'},
    'Manthiqueira': {'Manthiqueira', 'Manthiqueira-SP'},
    'Atletico Mogi': {'Atletico Mogi', 'Atlético Mogi', 'Atlético Mogi-SP'},
    'Guarulhos': {'Guarulhos', 'Guarulhos-SP'},
    'Uniao Mogi': {'Uniao Mogi', 'União Mogi', 'União Mogi-SP'},
    'Barcelona-SP': {'Barcelona (SP)', 'Barcelona-SP'},
    'Flamengo de Guarulhos': {'Flamengo de Guarulhos', 'Flamengo de Guarulhos-SP'},
    'Colorado Caieiras': {'Colorado Caieiras', 'Colorado Caieiras-SP'},
    'Inter de Bebedouro': {'Inter de Bebedouro', 'Inter de Bebedouro-SP'},
    'America-SP': {'America (SP)', 'America-SP', 'América (SP)', 'América-SP'},
    'Itapirense': {'Itapirense', 'Itapirense-SP'},
    'Amparo': {'Amparo', 'Amparo-SP'},
    'Bandeirante': {'Bandeirante', 'Bandeirante-SP'},
    'Aracatuba': {'Aracatuba', 'Araçatuba', 'Araçatuba-SP'},
    'Tupa': {'Tupa', 'Tupã', 'Tupã-SP'},
    'ECUS': {'ECUS', 'ECUS-SP'},
    'Suzano': {'Suzano', 'Suzano-SP'},
    'Sumare': {'Sumare', 'Sumaré', 'Sumaré-SP'},
    'Primavera': {'Primavera', 'Primavera-SP'},
    'Brasilis': {'Brasilis', 'Brasilis-SP'},
    'Sao Carlos': {'Sao Carlos', 'São Carlos', 'São Carlos-SP'},
    'Lemense': {'Lemense', 'Lemense-SP'},
    'Gremio Sao-Carlense': {'Gremio Sao-Carlense', 'Grêmio São-Carlense', 'Grêmio São-Carlense-SP'},
    'Uniao Barbarense': {'Uniao Barbarense', 'União Barbarense', 'União Barbarense-SP'},
    'Rio Branco-SP': {'Rio Branco (SP)', 'Rio Branco-SP'},
    'XV de Jau': {'XV de Jau', 'XV de Jaú', 'XV de Jaú-SP'},
    'Jose Bonifacio': {'Jose Bonifacio', 'José Bonifácio', 'José Bonifácio-SP'},
    'Assisense': {'Assisense', 'Assisense-SP'},
    'Vocem': {'Vocem', 'Vocem-SP'},
    'Osvaldo Cruz': {'Osvaldo Cruz', 'Osvaldo Cruz-SP'},
    'Paraguaçuense': {'Paraguaçuense', 'Paraguaçuense-SP'},
    'Presidente Prudente': {'Presidente Prudente', 'Presidente Prudente-SP'},
    'Rancharia': {'Rancharia', 'Rancharia-SP'},
    'Dracena': {'Dracena', 'Dracena-SP'},
    'Atletico Araçatuba': {'Atletico Araçatuba', 'Atlético Araçatuba', 'Atlético Araçatuba-SP'},
    'Brasil FC': {'Brasil FC', 'Brasil FC-SP'},
    'Fernandopolis': {'Fernandopolis', 'Fernandópolis', 'Fernandópolis-SP'},
    'Tanabi': {'Tanabi', 'Tanabi-SP'},
    'Olimpia-SP': {'Olimpia (SP)', 'Olimpia-SP', 'Olímpia (SP)', 'Olímpia-SP'},
    'Mirassol FC': {'Mirassol FC', 'Mirassol-SP'},
    'Jalesense': {'Jalesense', 'Jalesense-SP'},
    'America-SJRP': {'America-SJRP', 'América-SJRP', 'América-SJRP-SP'},
    'Rio Preto': {'Rio Preto', 'Rio Preto-SP'},
    'Catanduva': {'Catanduva', 'Catanduva-SP'},
    'Gremio Catanduvense': {'Gremio Catanduvense', 'Grêmio Catanduvense', 'Grêmio Catanduvense-SP'},
    'Bebedouro': {'Bebedouro', 'Bebedouro-SP'},
    'Barretos EC': {'Barretos EC', 'Barretos-SP'},
    'Olimpia FC': {'Olimpia FC', 'Olímpia FC', 'Olímpia-SP'},
    'Jaboticabal': {'Jaboticabal', 'Jaboticabal-SP'},
    'Monte Azul FC': {'Monte Azul FC', 'Monte Azul-SP'},
    'Sertaozinho FC': {'Sertaozinho FC', 'Sertãozinho FC', 'Sertãozinho-SP'},
    'Comercial-RP': {'Comercial (RP)', 'Comercial-RP', 'Comercial-RP-SP'},
    'Francana': {'Francana', 'Francana-SP'},
    'Batatais FC': {'Batatais FC', 'Batatais-SP'},
    'Orlandia': {'Orlandia', 'Orlândia', 'Orlândia-SP'},
    'Sao Joaquim': {'Sao Joaquim', 'São Joaquim', 'São Joaquim-SP'},
    'Ituveravense': {'Ituveravense', 'Ituveravense-SP'},
    'Passos': {'Passos', 'Passos-MG'},
    'Uberlandia': {'Uberlandia', 'Uberlândia', 'Uberlândia-MG'},
    'Caldense': {'Caldense', 'Caldense-MG'},
    'Boa Esporte': {'Boa Esporte', 'Boa Esporte-MG'},
    'Tupi': {'Tupi', 'Tupi-MG'},
    'URT': {'URT', 'URT-MG'},
    'Villa Nova-MG': {'Villa Nova (MG)', 'Villa Nova-MG'},
    'Atletico Patrocinense': {'Atletico Patrocinense', 'Atlético Patrocinense', 'Atlético Patrocinense-MG'},
    'Pouso Alegre': {'Pouso Alegre', 'Pouso Alegre-MG'},
    'Democrata-GV': {'Democrata (GV)', 'Democrata-GV', 'Democrata-GV-MG'},
    'Democrata-SL': {'Democrata (SL)', 'Democrata-SL', 'Democrata-SL-MG'},
    'Coimbra': {'Coimbra', 'Coimbra-MG'},
    'Uberaba': {'Uberaba', 'Uberaba-MG'},
    'Uberlandia EC': {'Uberlandia EC', 'Uberlândia EC', 'Uberlândia-MG'},
    'Araguari': {'Araguari', 'Araguari-MG'},
    'Social': {'Social', 'Social-MG'},
    'Nacional-MG': {'Nacional (MG)', 'Nacional de Muriaé', 'Nacional-MG'},
    'Mamoré': {'Mamoré', 'Mamoré-MG'},
    'Tricordiano': {'Tricordiano', 'Tricordiano-MG'},
    'Formiga': {'Formiga', 'Formiga-MG'},
    'Guarani-MG': {'Guarani (MG)', 'Guarani-MG'},
    'Araxá': {'Araxá', 'Araxá-MG'},
    'Patrocinense': {'Patrocinense', 'Patrocinense-MG'},
    'CAP Uberlandia': {'CAP Uberlandia', 'CAP Uberlândia', 'CAP Uberlândia-MG'},
    'Funorte': {'Funorte', 'Funorte-MG'},
    'Montes Claros': {'Montes Claros', 'Montes Claros-MG'},
    'Valeriodoce': {'Valeriodoce', 'Valeriodoce-MG'},
    'Ituiutaba': {'Ituiutaba', 'Ituiutaba-MG'},
    'Tombense FC': {'Tombense FC', 'Tombense-MG'},
    'America-TO': {'America (TO)', 'America-TO', 'América (TO)', 'América-TO'},
    'Nacional de Uberaba': {'Nacional de Uberaba', 'Nacional de Uberaba-MG'},
    'Fabril': {'Fabril', 'Fabril-MG'},
    'Atletico Três Corações': {'Atletico Três Corações', 'Atlético Três Corações', 'Atlético Três Corações-MG'},
    'Paraisense': {'Paraisense', 'Paraisense-MG'},
    'Sao Joao del Rei': {'Sao Joao del Rei', 'São João del Rei', 'São João del Rei-MG'},
    'Varginha': {'Varginha', 'Varginha-MG'},
    'Lafaiete': {'Lafaiete', 'Lafaiete-MG'},
    'Villa Nova AC': {'Villa Nova AC', 'Villa Nova AC-MG'},
    'Sete de Setembro-MG': {'Sete de Setembro (MG)', 'Sete de Setembro-MG'},
    'América-MG': {'America (MG)', 'América (MG)', 'América-MG'},
    'Ypiranga-MG': {'Ypiranga (MG)', 'Ypiranga-MG'},
    'Palmeiras-MG': {'Palmeiras (MG)', 'Palmeiras-MG'},
    'Siderurgica': {'Siderurgica', 'Siderúrgica', 'Siderúrgica-MG'},
    'Caldense-MG': {'Caldense (MG)', 'Caldense-MG'},
    'Tupi-MG': {'Tupi (MG)', 'Tupi-MG'},
    'URT-MG': {'URT (MG)', 'URT-MG'},
    'Boa Esporte-MG': {'Boa Esporte (MG)', 'Boa Esporte-MG'},
    'Tombense-MG': {'Tombense (MG)', 'Tombense-MG'},
    'Patrocinense-MG': {'Patrocinense (MG)', 'Patrocinense-MG'},
    'Uberlandia-MG': {'Uberlandia (MG)', 'Uberlandia-MG', 'Uberlândia (MG)'},
    'Coimbra-MG': {'Coimbra (MG)', 'Coimbra-MG'},
    'Pouso Alegre-MG': {'Pouso Alegre (MG)', 'Pouso Alegre-MG'},
    'Democrata-GV-MG': {'Democrata (GV)', 'Democrata GV (MG)', 'Democrata-GV-MG'},
    'Democrata-SL-MG': {'Democrata (SL)', 'Democrata SL (MG)', 'Democrata-SL-MG'},
    'Aymorés-MG': {'Aymorés (MG)', 'Aymorés-MG'},
    'Ipatinga-MG': {'Ipatinga (MG)', 'Ipatinga-MG'},
    'Mamoré-MG': {'Mamoré (MG)', 'Mamoré-MG'},
    'Nacional de Muriaé-MG': {'Nacional de Muriaé (MG)', 'Nacional de Muriaé-MG'},
    'Araxá-MG': {'Araxá (MG)', 'Araxá-MG'},
    'Social-MG': {'Social (MG)', 'Social-MG'},
    'Valeriodoce-MG': {'Valeriodoce (MG)', 'Valeriodoce-MG'},
    'Ituiutaba-MG': {'Ituiutaba (MG)', 'Ituiutaba-MG'},
    'Funorte-MG': {'Funorte (MG)', 'Funorte-MG'},
    'Formiga-MG': {'Formiga (MG)', 'Formiga-MG'},
    'Montes Claros-MG': {'Montes Claros (MG)', 'Montes Claros-MG'},
    'CAP Uberlandia-MG': {'CAP Uberlandia (MG)', 'CAP Uberlandia-MG', 'CAP Uberlândia (MG)'},
    'Atletico Patrocinense-MG': {'Atletico Patrocinense (MG)', 'Atletico Patrocinense-MG', 'Atlético Patrocinense (MG)'},
    'Varginha EC': {'Varginha EC', 'Varginha-MG'},
    'Caxias': {'Caxias', 'Caxias (RS)', 'Caxias-RS'},
    'Ypiranga-RS': {'Ypiranga (RS)', 'Ypiranga-RS'},
    'Sao Jose-RS': {'Sao Jose (RS)', 'Sao Jose-RS', 'São José (RS)', 'São José-RS'},
    'Aimore': {'Aimore', 'Aimore-RS', 'Aimoré', 'Aimoré-RS'},
    'Esportivo': {'Esportivo', 'Esportivo-RS'},
    'Novo Hamburgo': {'Novo Hamburgo', 'Novo Hamburgo-RS'},
    'Sao Luiz': {'Sao Luiz', 'São Luiz', 'São Luiz-RS'},
    'Pelotas': {'Pelotas', 'Pelotas-RS'},
    'Gremio Esportivo Brasil': {'Brasil de Pelotas', 'Gremio Esportivo Brasil', 'Grêmio Esportivo Brasil'},
    'Lajeadense': {'Lajeadense', 'Lajeadense-RS'},
    'Passo Fundo': {'Passo Fundo', 'Passo Fundo-RS'},
    'Veranopolis': {'Veranopolis', 'Veranopolis-RS', 'Veranópolis', 'Veranópolis-RS'},
    'Avenida': {'Avenida', 'Avenida-RS'},
    'Uniao Frederiquense': {'Uniao Frederiquense', 'União Frederiquense', 'União Frederiquense-RS'},
    'Sao Paulo-RS': {'Sao Paulo (RS)', 'Sao Paulo-RS', 'São Paulo (RS)', 'São Paulo-RS'},
    'Cruzeiro-RS': {'Cruzeiro (RS)', 'Cruzeiro-RS'},
    'Gloria': {'Gloria', 'Gloria-RS', 'Glória', 'Glória-RS'},
    'Guarany de Bage': {'Guarany de Bage', 'Guarany de Bagé', 'Guarany de Bagé-RS'},
    'Guarani-VA': {'Guarani (VA)', 'Guarani-VA', 'Guarani-VA-RS'},
    'Inter de Santa Maria': {'Inter de Santa Maria', 'Inter de Santa Maria-RS'},
    'Riograndense': {'Riograndense', 'Riograndense-RS'},
    'Santa Cruz-RS': {'Santa Cruz (RS)', 'Santa Cruz-RS'},
    'Sao Gabriel-RS': {'Sao Gabriel (RS)', 'Sao Gabriel-RS', 'São Gabriel (RS)', 'São Gabriel-RS'},
    'Farroupilha': {'Farroupilha', 'Farroupilha-RS'},
    'Brasil de Farroupilha': {'Brasil de Farroupilha', 'Brasil de Farroupilha-RS'},
    'Gremio Esportivo Glória': {'Gremio Esportivo Glória', 'Grêmio Esportivo Glória', 'Grêmio Esportivo Glória-RS'},
    'Tres Passos': {'Tres Passos', 'Três Passos', 'Três Passos-RS'},
    'Tres Coroas': {'Tres Coroas', 'Três Coroas', 'Três Coroas-RS'},
    'Ibiruba': {'Ibiruba', 'Ibirubá', 'Ibirubá-RS'},
    'Panambi': {'Panambi', 'Panambi-RS'},
    'Carazinho': {'Carazinho', 'Carazinho-RS'},
    'Santo Angelo': {'Santo Angelo', 'Santo Ângelo', 'Santo Ângelo-RS'},
    'Sao Borja': {'Sao Borja', 'São Borja', 'São Borja-RS'},
    '14 de Julho': {'14 de Julho', '14 de Julho-RS'},
    'Gremio Atletico Farroupilha': {'Gremio Atletico Farroupilha', 'Grêmio Atlético Farroupilha', 'Grêmio Atlético Farroupilha-RS'},
    'Estrela': {'Estrela', 'Estrela-RS'},
    'Encantado': {'Encantado', 'Encantado-RS'},
    'Nova Prata': {'Nova Prata', 'Nova Prata-RS'},
    'Garibaldi': {'Garibaldi', 'Garibaldi-RS'},
    'Atletico Carazinho': {'Atletico Carazinho', 'Atlético Carazinho', 'Atlético Carazinho-RS'},
    'Marau': {'Marau', 'Marau-RS'},
    'Santo Antonio-RS': {'Santo Antonio (RS)', 'Santo Antonio-RS', 'Santo Antônio (RS)', 'Santo Antônio-RS'},
    'Riograndense-SM': {'Riograndense (SM)', 'Riograndense-SM', 'Riograndense-SM-RS'},
    'Cuiaba-MT': {'Cuiaba (MT)', 'Cuiaba-MT', 'Cuiabá (MT)', 'Cuiabá-MT'},
    'Brasil de Pelotas-RS': {'Brasil de Pelotas (RS)', 'Brasil de Pelotas-RS'},
    'Novorizontino-SP': {'Novorizontino (SP)', 'Novorizontino-SP'},
    'Mirassol-SP': {'Mirassol (SP)', 'Mirassol-SP'},
    'Ituano-SP': {'Ituano (SP)', 'Ituano-SP'},
    'Santo Andre-SP': {'Santo Andre (SP)', 'Santo Andre-SP', 'Santo André (SP)', 'Santo André-SP'},
    'Sao Caetano-SP': {'Sao Caetano (SP)', 'Sao Caetano-SP', 'São Caetano (SP)', 'São Caetano-SP'},
    'Gremio Barueri-SP': {'Gremio Barueri (SP)', 'Gremio Barueri-SP', 'Grêmio Barueri (SP)', 'Grêmio Barueri-SP'},
    'Bangu-RJ': {'Bangu (RJ)', 'Bangu-RJ'},
    'Madureira-RJ': {'Madureira (RJ)', 'Madureira-RJ'},
    'Volta Redonda-RJ': {'Volta Redonda (RJ)', 'Volta Redonda-RJ'},
    'Remo-PA': {'Remo (PA)', 'Remo-PA'},
    'Confianca-SE': {'Confianca (SE)', 'Confianca-SE', 'Confiança (SE)', 'Confiança-SE'},
    'Ferroviario-CE': {'Ferroviario (CE)', 'Ferroviario-CE', 'Ferroviário (CE)', 'Ferroviário-CE'},
    'Operario-PR': {'Operario (PR)', 'Operario-PR', 'Operário (PR)', 'Operário-PR'},
    'Brusque-SC': {'Brusque (SC)', 'Brusque-SC'},
    'Manaus-AM': {'Manaus (AM)', 'Manaus-AM'},
    'Altos-PI': {'Altos (PI)', 'Altos-PI'},
    'Treze-PB': {'Treze (PB)', 'Treze-PB'},
    'Sousa-PB': {'Sousa (PB)', 'Sousa-PB'},
    'Moto Club-MA': {'Moto Club (MA)', 'Moto Club-MA'},
    'Parnahyba-PI': {'Parnahyba (PI)', 'Parnahyba-PI'},
    '4 de Julho-PI': {'4 de Julho (PI)', '4 de Julho-PI'},
    'Bahia de Feira-BA': {'Bahia de Feira (BA)', 'Bahia de Feira-BA'},
    'Juazeirense-BA': {'Juazeirense (BA)', 'Juazeirense-BA'},
    'Jacuipense-BA': {'Jacuipense (BA)', 'Jacuipense-BA'},
    'Vitoria da Conquista-BA': {'Vitoria da Conquista (BA)', 'Vitoria da Conquista-BA', 'Vitória da Conquista (BA)', 'Vitória da Conquista-BA'},
    'Barcelona de Ilheus-BA': {'Barcelona de Ilheus-BA', 'Barcelona de Ilhéus (BA)', 'Barcelona de Ilhéus-BA'},
    'ASA-AL': {'ASA (AL)', 'ASA-AL'},
    'Murici-AL': {'Murici (AL)', 'Murici-AL'},
    'Coruripe-AL': {'Coruripe (AL)', 'Coruripe-AL'},
    'CSE-AL': {'CSE (AL)', 'CSE-AL'},
    'CEO-AL': {'CEO (AL)', 'CEO-AL'},
    'Sergipe-SE': {'Sergipe (SE)', 'Sergipe-SE'},
    'Itabaiana-SE': {'Itabaiana (SE)', 'Itabaiana-SE'},
    'Lagarto-SE': {'Lagarto (SE)', 'Lagarto-SE'},
    'Falcon-SE': {'Falcon (SE)', 'Falcon-SE'},
}

# Build reverse mapping: any variant -> canonical name
_VARIANT_TO_CANONICAL: dict[str, str] = {}
for canonical, variants in _TEAM_ALIASES.items():
    for v in variants:
        _VARIANT_TO_CANONICAL[v] = canonical


def normalize_team_name(raw: str) -> str:
    """Normalize a team name to its canonical form.

    Handles:
    - State suffixes: "Palmeiras-SP" -> "Palmeiras"
    - Full names: "Sport Club Corinthians Paulista" -> "Corinthians"
    - Parentheticals: "Nacional (URU)" -> "Nacional"
    - Extra descriptors with dash suffix: "Boavista Sport Club (antigo ...) - RJ" -> "Boavista"
    - Accented characters: normalized for comparison
    - Whitespace normalization
    """
    if not isinstance(raw, str) or not raw.strip():
        return ""

    name = raw.strip()

    # Direct lookup in variant map
    if name in _VARIANT_TO_CANONICAL:
        return _VARIANT_TO_CANONICAL[name]

    # Try case-insensitive lookup
    name_lower = name.lower()
    for variant, canonical in _VARIANT_TO_CANONICAL.items():
        if variant.lower() == name_lower:
            return canonical

    # Aggressive normalization for unmatched names
    cleaned = _aggressive_normalize(name)

    # Try again with cleaned version
    if cleaned in _VARIANT_TO_CANONICAL:
        return _VARIANT_TO_CANONICAL[cleaned]

    # Try removing state suffix patterns: "-XX" or " (XX)"
    cleaned_no_suffix = re.sub(r'\s*[-–—]\s*[A-Za-z]{2,3}\s*$', '', cleaned)
    cleaned_no_suffix = re.sub(r'\s*\([A-Za-z]{2,3}\)\s*$', '', cleaned_no_suffix).strip()

    if cleaned_no_suffix in _VARIANT_TO_CANONICAL:
        return _VARIANT_TO_CANONICAL[cleaned_no_suffix]

    # Try with accented variants
    name_normalized = _strip_accents(cleaned)
    for variant, canonical in _VARIANT_TO_CANONICAL.items():
        if _strip_accents(variant) == name_normalized:
            return canonical

    name_normalized_ns = _strip_accents(cleaned_no_suffix)
    for variant, canonical in _VARIANT_TO_CANONICAL.items():
        if _strip_accents(variant) == name_normalized_ns:
            return canonical

    # Return the cleaned version without suffix as last resort
    return cleaned_no_suffix if cleaned_no_suffix else cleaned


def _aggressive_normalize(name: str) -> str:
    """Aggressively clean a team name by removing common suffixes and descriptors."""
    # Remove " (antigo ...)" patterns
    name = re.sub(r'\s*\(antigo[^)]*\)', '', name, flags=re.IGNORECASE)
    # Remove " - XX" state suffix at end
    name = re.sub(r'\s*[-–—]\s*[A-Za-z]{2,3}\s*$', '', name)
    # Remove " (XX)" state or country suffix at end
    name = re.sub(r'\s*\([A-Za-z]{2,3}\)\s*$', '', name)
    # Remove trailing parenthetical
    name = re.sub(r'\s*\([^)]*\)\s*$', '', name)
    return name.strip()


def _strip_accents(s: str) -> str:
    """Remove accents from a string for comparison."""
    nfkd = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


def fuzzy_match_team(query: str, candidates: set[str]) -> str | None:
    """Find the best matching canonical team name from a set of candidates.

    Returns None if no match found.
    """
    query_norm = normalize_team_name(query)
    if query_norm in candidates:
        return query_norm

    # Try without accents
    query_stripped = _strip_accents(query_norm).lower()
    for c in candidates:
        if _strip_accents(c).lower() == query_stripped:
            return c

    # Substring match
    query_lower = query_norm.lower()
    for c in candidates:
        if query_lower in c.lower() or c.lower() in query_lower:
            return c

    return None


# ── Date Parsing ────────────────────────────────────────────────────────────


def parse_date(date_str: str) -> pd.Timestamp | None:
    """Parse a date string in any of the supported formats.

    Handles:
    - ISO: "2023-09-24"
    - Brazilian: "29/03/2003"
    - With time: "2012-05-19 18:30:00"
    """
    if not isinstance(date_str, str) or not date_str.strip():
        return None
    date_str = date_str.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return pd.to_datetime(date_str, format=fmt)
        except (ValueError, TypeError):
            continue
    try:
        return pd.to_datetime(date_str)
    except (ValueError, TypeError):
        return None


# ── Data Loading ────────────────────────────────────────────────────────────


def load_brasileirao_matches() -> pd.DataFrame:
    """Load Brasileirao Serie A matches from Brasileirao_Matches.csv."""
    df = pd.read_csv(DATA_DIR / "Brasileirao_Matches.csv")
    df["competition"] = "Brasileirão"
    df["date"] = df["datetime"].apply(parse_date)

    # Normalize team names (strip state suffix)
    df["home_team_norm"] = df["home_team"].apply(normalize_team_name)
    df["away_team_norm"] = df["away_team"].apply(normalize_team_name)

    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce").fillna(0).astype(int)
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce").fillna(0).astype(int)
    df["season"] = pd.to_numeric(df["season"], errors="coerce").fillna(0).astype(int)

    return df


def load_copa_brasil_matches() -> pd.DataFrame:
    """Load Copa do Brasil matches from Brazilian_Cup_Matches.csv."""
    df = pd.read_csv(DATA_DIR / "Brazilian_Cup_Matches.csv")
    df["competition"] = "Copa do Brasil"
    df["date"] = df["datetime"].apply(parse_date)

    df["home_team_norm"] = df["home_team"].apply(normalize_team_name)
    df["away_team_norm"] = df["away_team"].apply(normalize_team_name)

    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce").fillna(0).astype(int)
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce").fillna(0).astype(int)
    df["season"] = pd.to_numeric(df["season"], errors="coerce").fillna(0).astype(int)

    return df


def load_libertadores_matches() -> pd.DataFrame:
    """Load Copa Libertadores matches from Libertadores_Matches.csv."""
    df = pd.read_csv(DATA_DIR / "Libertadores_Matches.csv")
    df["competition"] = "Copa Libertadores"
    df["date"] = df["datetime"].apply(parse_date)

    df["home_team_norm"] = df["home_team"].apply(normalize_team_name)
    df["away_team_norm"] = df["away_team"].apply(normalize_team_name)

    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce").fillna(0).astype(int)
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce").fillna(0).astype(int)
    df["season"] = pd.to_numeric(df["season"], errors="coerce").fillna(0).astype(int)

    return df


def load_br_football_dataset() -> pd.DataFrame:
    """Load extended match statistics from BR-Football-Dataset.csv."""
    df = pd.read_csv(DATA_DIR / "BR-Football-Dataset.csv")
    df["competition"] = df["tournament"]
    df["date"] = df["date"].apply(parse_date)

    df["home_team_norm"] = df["home"].apply(normalize_team_name)
    df["away_team_norm"] = df["away"].apply(normalize_team_name)

    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce").fillna(0).astype(int)
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce").fillna(0).astype(int)

    # Extract season from date
    df["season"] = df["date"].apply(lambda d: d.year if pd.notna(d) else 0)

    return df


def load_novo_brasileirao() -> pd.DataFrame:
    """Load historical Brasileirao data from novo_campeonato_brasileiro.csv."""
    df = pd.read_csv(DATA_DIR / "novo_campeonato_brasileiro.csv", encoding="utf-8")
    df["competition"] = "Brasileirão"
    df["date"] = df["Data"].apply(parse_date)

    df["home_team_norm"] = df["Equipe_mandante"].apply(normalize_team_name)
    df["away_team_norm"] = df["Equipe_visitante"].apply(normalize_team_name)

    df["home_goal"] = pd.to_numeric(df["Gols_mandante"], errors="coerce").fillna(0).astype(int)
    df["away_goal"] = pd.to_numeric(df["Gols_visitante"], errors="coerce").fillna(0).astype(int)
    df["season"] = pd.to_numeric(df["Ano"], errors="coerce").fillna(0).astype(int)

    return df


def load_fifa_players() -> pd.DataFrame:
    """Load FIFA player data from fifa_data.csv."""
    df = pd.read_csv(DATA_DIR / "fifa_data.csv", encoding="utf-8-sig")
    df["Name"] = df["Name"].astype(str).str.strip()
    df["Club"] = df["Club"].astype(str).str.strip()
    df["Nationality"] = df["Nationality"].astype(str).str.strip()
    df["Position"] = df["Position"].astype(str).str.strip()
    df["Overall"] = pd.to_numeric(df["Overall"], errors="coerce").fillna(0).astype(int)
    df["Potential"] = pd.to_numeric(df["Potential"], errors="coerce").fillna(0).astype(int)
    df["Age"] = pd.to_numeric(df["Age"], errors="coerce").fillna(0).astype(int)
    return df


def load_all_match_data() -> pd.DataFrame:
    """Load and combine all match data into a single unified DataFrame."""
    dfs = [
        load_brasileirao_matches(),
        load_copa_brasil_matches(),
        load_libertadores_matches(),
        load_br_football_dataset(),
        load_novo_brasileirao(),
    ]

    # Standardize columns for concatenation
    unified = pd.concat(dfs, ignore_index=True, sort=False)

    # Ensure core columns are present
    for col in ("home_team_norm", "away_team_norm", "home_goal", "away_goal", "season", "date", "competition"):
        if col not in unified.columns:
            unified[col] = None

    return unified


def get_all_team_names(matches_df: pd.DataFrame) -> set[str]:
    """Get the set of all canonical team names from the match data."""
    teams = set()
    for col in ("home_team_norm", "away_team_norm"):
        if col in matches_df.columns:
            teams.update(matches_df[col].dropna().unique())
    teams.discard("")
    return teams