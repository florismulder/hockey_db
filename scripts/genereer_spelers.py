"""
genereer_spelers.py
Genereert spelersprofielen JSON vanuit de KNHB spelerslijst 2025-2026
Gebruik: python3 scripts/genereer_spelers.py
"""
import json, re
from pathlib import Path

DB_ROOT = Path(__file__).parent.parent

CLUB_SLUGS = {
    "Amsterdam": "amsterdam", "Bloemendaal": "bloemendaal",
    "Den Bosch": "den_bosch", "HDM": "hdm", "HGC": "hgc",
    "Hurley": "hurley", "Kampong": "kampong",
    "Klein Zwitserland": "klein_zwitserland", "Laren": "laren",
    "Oranje-Rood": "oranje_rood", "Pinoké": "pinoke",
    "Rotterdam": "rotterdam", "Schaerweijde": "schaerweijde",
    "SCHC": "schc", "Tilburg": "tilburg",
}

def slugify(naam):
    naam = naam.lower()
    for a, b in [("à","a"),("á","a"),("â","a"),("ä","a"),("è","e"),("é","e"),
                 ("ê","e"),("ë","e"),("í","i"),("ï","i"),("ó","o"),("ô","o"),
                 ("ö","o"),("ú","u"),("ü","u"),("ý","y"),("ñ","n"),("ç","c"),
                 ("ě","e"),("š","s"),("č","c"),("ž","z"),("ï","i"),("'","")]:
        naam = naam.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "_", naam).strip("_")

# Volledige spelersdata uit KNHB PDF versie 11-09-2025
SPELERS_DATA = {
    ("Amsterdam","dames"): [
        ("Anne Veenendaal","1",True,False), ("Freeke Moes","18",False,True),
        ("Felice Albers","10",False,False), ("Fay van der Elst","12",False,False),
        ("Imke Verstraeten","11",False,False), ("Marijn Veen","19",False,False),
        ("Li Hong","15",False,False), ("Stella van Gils","22",False,False),
        ("Trijntje Beljaars","9",False,False), ("Daantje de Kruijff","6",False,False),
        ("Sabine Plönissen","13",False,False), ("Gabrielle Mosch","3",False,False),
        ("Noa Muller","14",False,False), ("Alessia Norbiato","7",False,False),
        ("Ivy Tellier","21",False,False), ("Katerina Langedijk","16",False,False),
        ("Renske Balemans","8",False,False), ("Merle Blaffert","4",False,False),
        ("Reese d'Ariano","20",False,False), ("Fere van der Maarel","2",True,False),
        ("Charlotte Adegeest","23",False,False), ("Sarah Smit Sibinga","24",False,False),
    ],
    ("Amsterdam","heren"): [
        ("Luke Dommershuijzen","5",False,False), ("Oliver Payne","1",True,False),
        ("Lucas Middendorp","6",False,False), ("Boris Burkhardt","20",False,True),
        ("Floris Middendorp","7",False,True), ("David Huussen","35",False,False),
        ("Lee Morton","11",False,False), ("Dayaan Cassiem","10",False,False),
        ("Musthapha Cassiem","2",False,False), ("Casper Berkman","13",False,False),
        ("Brent van Bijnen","17",False,False), ("Tjeerd Boermans","4",False,False),
        ("Robbert Kemperman","14",False,False), ("Karst Timmer","9",False,False),
        ("Thije Harm","18",False,False), ("Sam Steins Bisschop","8",False,False),
        ("Lucas Corstens","12",False,False), ("Sam van der Weijden","28",False,False),
        ("Joost Tolboom","24",False,False), ("Olivier Paalman","21",True,False),
        ("Jochem Blok","30",False,False), ("Mirco Pruyser","31",False,False),
    ],
    ("Bloemendaal","dames"): [
        ("Ankelein Baardemans","17",False,True), ("Sterre Bregman","11",False,False),
        ("Pientje Molenaar","24",False,False), ("Demi Hilterman","16",False,False),
        ("Phileine Hazen","1",True,False), ("Malou Nanninga","23",False,False),
        ("Rosalie Rosman","12",False,False), ("Maud Preyde","7",False,False),
        ("Lilli de Nooijer","20",False,False), ("Annelies Pos","5",False,False),
        ("Luca Preyde","10",False,False), ("Isa Huijbers","4",False,False),
        ("Ryanne van Dooijeweerd","14",False,False), ("Mijntje van Campen","22",False,False),
        ("Florien Sondern","9",False,False), ("Floks van der Beek","15",False,False),
        ("Sophie Thoolen","19",False,False), ("Julie Hoogendoorn","8",False,False),
        ("Isolde Otten","21",False,False), ("Diana Beemster","33",True,False),
    ],
    ("Bloemendaal","heren"): [
        ("Jorrit Croon","10",False,True), ("Floris Wortelboer","28",False,False),
        ("Maurits Visser","1",True,False), ("Jasper Brinkman","13",False,False),
        ("Zachary Wallace","7",False,False), ("Teun Beins","17",False,False),
        ("Arno van Dessel","5",False,False), ("Casper van der Veen","11",False,False),
        ("Marco Miltkau","22",False,False), ("Wiegert Schut","23",False,False),
        ("Lucas Veen","8",False,False), ("Elian Mazkour","26",False,False),
        ("Gijs ter Braak","6",False,False), ("Teun Hogenhout","18",False,False),
        ("Sheldon Schouten","4",False,False), ("Jan van 't Land","15",False,False),
        ("Max Langer","9",False,False), ("Tobias Bovelander","16",False,False),
        ("Ramses Zwijnenburg","19",False,False), ("Allard André de la Porte","32",False,True),
        ("Wouter Jolie","20",False,False), ("Matthijs Odekerken","33",True,False),
    ],
    ("Den Bosch","dames"): [
        ("Josine Koning","1",False,True), ("Charlotte Englebert","6",False,False),
        ("Rosa Fernig","3",False,False), ("Pien Sanders","11",False,True),
        ("Sanne Koolen","14",False,False), ("Frédérique Matla","15",False,False),
        ("Joosje Burg","16",False,False), ("Laura Nunnink","20",False,False),
        ("Maartje Krekelaar","22",False,False), ("Danique van der Veerdonk","7",False,False),
        ("Imme van der Hoek","21",False,False), ("Emma Reijnen","19",False,False),
        ("Babs Reijnen","13",False,False), ("Anouk Brouwer","4",False,False),
        ("Lieve Wijckmans","5",False,False), ("Teuntje de Wit","8",False,False),
        ("Romee Joosten","18",False,False), ("Josephine Bekkers","2",False,False),
        ("Kim Peters","10",False,False), ("Janneke van de Venne","9",False,False),
        ("Elke Boers","24",False,False), ("Laurette Abelen","17",False,True),
    ],
    ("Den Bosch","heren"): [
        ("Alexander Stadler","1",False,True), ("Thierry Brinkman","8",False,False),
        ("Jasper Tukkers","18",False,True), ("Koen Bijen","22",False,False),
        ("Timo Boers","21",False,False), ("Gijs Campbell","10",False,False),
        ("Joppe Wolbert","33",False,False), ("Eduard De Ignacio-Simó","17",False,False),
        ("Pepijn Reijenga","9",False,False), ("Imre Vos","2",False,False),
        ("Mees Kurvers","3",False,False), ("Jaïr van der Horst","7",False,False),
        ("Max Kreft","11",False,False), ("Lucas Driessen","24",False,False),
        ("Max Pastoor","6",False,False), ("Sweder Koens","30",False,False),
        ("Sander van Berkel","32",False,True), ("Cedric van Otterlo","4",False,False),
        ("Marc Vizcaino","19",False,False), ("Thomas Sorsby","29",False,False),
        ("Fabian Unterkircher","23",False,False), ("Tijn van Groesen","35",False,False),
    ],
    ("HDM","dames"): [
        ("Milou Klein","16",False,False), ("Belén van den Broek","10",False,False),
        ("Tessa Clasener","5",False,True), ("Frederique Dekker","12",False,False),
        ("Sabine van den Eijnden","14",False,False), ("Pien van der Heide","24",False,False),
        ("Julia Remmerswaal","1",True,False), ("Hester van der Veld","6",False,False),
        ("Kaat Walhof","2",False,False), ("Phileine van den Bosch","15",False,False),
        ("Delany van den Broek","17",False,False), ("Julia Duffhuis","3",False,False),
        ("Juliette Hijdra","9",False,False), ("Eva van 't Hoog","19",False,False),
        ("Lotte Beetsma","11",False,False), ("Claudia Negrete Garcia","4",False,False),
        ("Anke Sanders","8",False,False), ("Isa van Spronsen","18",False,False),
        ("Dirkie Chamberlain","20",False,False), ("Laila Dierkens Schuttevaer","36",False,True),
        ("Pien van Nes","22",False,False), ("Florien Vorderman","23",False,False),
    ],
    ("HDM","heren"): [
        ("Luis Beckmann","1",False,True), ("Cédric de Gier","18",False,True),
        ("Sander Groenheijde","23",False,True), ("Floris van der Kroon","22",False,False),
        ("Marc Boltó Gimó","17",False,False), ("Yorben Fontaine","9",False,False),
        ("Merijn Maas","10",False,False), ("Jasper van der Looy","8",False,False),
        ("Chris Taberima","21",False,False), ("Fabian Verzuu","11",False,False),
        ("Alexander Weterings","5",False,False), ("Jelte Kaptein","4",False,False),
        ("Rick van den IJssel","19",False,False), ("Ruben Versteeg","7",False,False),
        ("Guus van den Boezem","20",False,False), ("Sam Spencer","3",False,False),
        ("Tom Provily","16",False,False), ("Mats Dicke","25",False,False),
        ("Fenn Tellier","24",False,False), ("Siebe Pijpers","13",False,True),
        ("Duco Nieuwenhuizen Segaar","12",False,False),
    ],
    ("HGC","dames"): [
        ("Sofie ter Kuile","1",False,True), ("Isis van Loon","8",False,True),
        ("Cécile Pieper","29",False,True), ("Valentina Raposo Ruiz De Los Llanos","4",False,False),
        ("Marta Segú Rueda","17",False,False), ("Mariona Serrahima","9",False,False),
        ("Anna Serrahima","19",False,False), ("Lilly Stoffelsma","22",False,False),
        ("Zoë Admiraal","10",False,False), ("Jip Blaas","14",False,False),
        ("Amy van den Bosch","2",False,False), ("Tessel Huibregtsen","23",False,False),
        ("Bente Kolmus","12",False,False), ("Lisa Lejeune","6",False,False),
        ("Faye Muijderman","3",False,False), ("Julie Pieper","11",False,False),
        ("Mikki Roolaart","24",False,False), ("Julie Sytsema","16",False,False),
        ("Louisa Hopman","5",False,False), ("Valentine Hulsbergen","7",False,False),
        ("Ellie Vinh","18",False,False), ("Pip Jong","26",False,True),
    ],
    ("Hurley","dames"): [
        ("Maartje Kaptein","1",True,True), ("Sophie Schelfhout","13",False,True),
        ("Annelotte Nijhuis","14",False,False), ("Fiona Morgenstern","2",False,True),
        ("Chrisje van der Salm","6",False,True), ("Margot van Hecking Colenbrander","22",False,False),
        ("Sanne Caarls","30",False,False), ("Fleur Loomans","11",False,False),
        ("Teuntje Horn","10",False,False), ("Eliza Vermeulen","4",False,False),
        ("Nora Bruinsma","3",False,False), ("Dymph Luttge","12",False,False),
        ("Philine Vinkesteijn","8",False,False), ("Taheera Augousti","23",False,False),
        ("Romée Corver","5",False,False), ("Michelle van der Drift","7",False,False),
        ("Floor van den Dungen","21",False,False), ("Floor van Gorkum","24",False,False),
        ("Olivia Huisman","9",False,False), ("Ginella Zerbo","27",False,False),
        ("Laurien Leurink","26",False,True), ("Julia van den Heuvel","28",False,False),
    ],
    ("Hurley","heren"): [
        ("Nikas Berendts","20",False,False), ("Daan Dekker","3",False,False),
        ("Mees Loman","8",False,True), ("Harry Martin","7",False,False),
        ("Fred Newbold","19",False,False), ("Laurens Nievelstein","24",False,False),
        ("Rutger Plat","12",False,False), ("Joren Romijn","1",True,False),
        ("Hjalmar Voskuil","14",False,False), ("Grau Albert","22",False,False),
        ("Deegan Huisman","21",False,False), ("Joshua Keaveney","4",False,False),
        ("Theun de Leeuw","6",False,False), ("Jake Raben","18",False,False),
        ("Noam Sheridan","17",False,False), ("Lex Tump","10",False,True),
        ("Pim Wasser","15",False,False), ("Tieme Wiggers","9",False,False),
        ("Camiel Erselina","13",False,True), ("I-An van de Scheur","16",False,False),
        ("Imko de Vries","25",False,False), ("Benjamin Walker","11",False,False),
    ],
    ("Kampong","dames"): [
        ("Babette Backers","1",False,True), ("Luna Fokke","10",False,True),
        ("Bente van der Veldt","4",False,False), ("Noor van den Nieuwenhof","8",False,False),
        ("Eline Jansen","9",False,False), ("Guusje Moes","3",False,False),
        ("Carlijn Tukkers","11",False,False), ("Noor de Baat","12",False,False),
        ("Sosha Benninga","16",False,False), ("Veere ter Horst","2",False,False),
        ("Fleur Wolfert","15",False,False), ("Maria de Vries","19",False,False),
        ("Iris de Kemp","14",False,False), ("Julie Roovers","5",False,False),
        ("Kyra Fortuin","7",False,False), ("Charlotte Hoctin Boes","21",False,False),
        ("Sofie Stomps","24",False,False), ("Sophie van Grimbergen","23",False,False),
        ("Imme Van es","20",False,False), ("Anne Berends","22",False,True),
    ],
    ("Kampong","heren"): [
        ("Luis Calzado","15",False,True), ("Bram van Battum","2",False,False),
        ("Caspar Dobbelaar","21",False,False), ("Jip Janssen","4",False,False),
        ("Lars Balk","6",False,True), ("Derck de Vilder","23",False,False),
        ("Jonas de Geus","8",False,False), ("Duco Telgenkamp","14",False,False),
        ("Terrance Pieters","11",False,False), ("Kjell Plantenga","19",False,False),
        ("Sander de Wijn","12",False,False), ("Jens de Vuijst","3",False,False),
        ("Rik Sprengers","7",False,False), ("Thies Bakker","22",False,False),
        ("Finn van Bijnen","9",False,False), ("Hidde Plantenga","18",False,False),
        ("Mats Gruter","13",False,False), ("Sander van de Putte","20",False,False),
        ("Diederik van den Hoek","32",False,True), ("Hugo van Beusekom","16",False,False),
        ("Koen Meijerink","24",False,False), ("Silas Lageman","10",False,False),
    ],
    ("Klein Zwitserland","heren"): [
        ("Nicolas Santiago Keenan","23",False,True), ("Aki Käppeler","14",False,True),
        ("Lars Daniels","9",False,False), ("Ties Klinkhamer","12",False,False),
        ("Douwe Steens","15",False,True), ("Adrian Lehmann-Richter","35",False,False),
        ("Chad Futcher","13",False,False), ("Lucas Toscani","18",False,False),
        ("Pepijn Jones","19",False,False), ("Koene Schaper","1",True,True),
        ("Willem van Campen","10",False,False), ("Joaquin Toscani","17",False,False),
        ("Jochem Bakker","3",False,False), ("Florent Vaal","16",False,False),
        ("Linus Michler","7",False,False), ("Tom Schneider","4",False,False),
        ("Jonas Ellerman","11",False,False), ("Pepe Bijlaard","5",False,False),
        ("Philip van Aken","20",False,False), ("Štěpán Klaban","8",False,False),
        ("Julian Seckel","77",False,True), ("Maurik Smits","6",False,False),
    ],
    ("Laren","heren"): [
        ("Estiaan Kriek","29",False,True), ("Pelle Vos","12",False,False),
        ("Pieter Paul Houting","32",False,False), ("Thomas Vis","10",False,False),
        ("Diederick van Berckel","8",False,True), ("Valentijn Charbon","21",False,False),
        ("Luke Friederich","14",False,False), ("Thomas Selles","7",False,False),
        ("Wout Kooijman","22",False,False), ("Balder Reyenga","24",False,False),
        ("Berend van Langeveld","9",False,False), ("Ruben van Meer","16",False,False),
        ("Floris van der Wal","4",False,False), ("Sybren Loman","11",False,False),
        ("Joep Hagendoorn","6",False,False), ("Teun van Uunen","3",False,False),
        ("Stan Thoolen","19",False,False), ("Quinten Moojen","15",False,False),
        ("Bart de Nie","1",True,False), ("Giovanni Brand","5",False,True),
        ("Kenneth Bain","13",False,False), ("Xavier van de Kasteele","17",False,False),
    ],
    ("Oranje-Rood","dames"): [
        ("Vivienne Peters","8",False,True), ("Amber Brouwer","4",False,False),
        ("Juul van der Velden","5",False,False), ("Madelief de Beer","22",False,False),
        ("Pheline Vos","9",False,False), ("Jolien Bogers","20",False,False),
        ("Pieke van de Pas","18",False,False), ("Lynn Vasterink","10",False,False),
        ("Merel Voermans","13",False,False), ("Lucie Ehrmann","1",True,False),
        ("Renske van Limpt","17",False,True), ("Margje van der Loo","14",False,False),
        ("Sara Puglisi","21",False,False), ("Thirsa Kho","24",False,False),
        ("Loeki Treffers","6",False,False), ("Brechje Scheepers","19",False,False),
        ("Charlotte Schrijvers","12",False,False), ("Bibi Donraadt","7",False,False),
        ("Julianna Tornetta","15",False,False), ("Babs van Hest","11",False,False),
        ("Lara Raaijmakers","16",False,False), ("Lisa Scheerlinck","23",False,False),
    ],
    ("Oranje-Rood","heren"): [
        ("Joep de Mol","23",False,True), ("Tijmen Reyenga","29",False,False),
        ("Max de Bie","7",False,False), ("Arthur de Sloover","3",False,False),
        ("Gerard Clapes","11",False,False), ("Borja LaCalle","14",False,False),
        ("Struan Walker","13",False,False), ("Henrik Mertgens","21",False,False),
        ("Pol Cabre-Verdiell Badia","10",False,False), ("Jelle Galema","9",False,False),
        ("Bob de Voogd","19",False,False), ("Florian Gosselink","16",False,False),
        ("Jacky van Hout","22",False,False), ("Sem de Roij","18",False,False),
        ("Boaz Houben","5",False,False), ("Gijs van Merriënboer","12",False,False),
        ("Thijs Bams","17",False,False), ("Isha Houben","15",False,False),
        ("Noud van Deijck","8",False,False), ("Niek van der Schoot","2",False,False),
        ("Tomas Santiago","1",False,True), ("Nieki Verbeek","26",False,True),
    ],
    ("Pinoké","dames"): [
        ("Maria Steensma","7",False,False), ("Kiki Rozemeijer","10",False,True),
        ("Josephine Murray","15",False,False), ("Pam van der Laan","6",False,False),
        ("Tessa Beetsma","21",False,False), ("Lana Kalse","14",False,False),
        ("Floor de Haan","4",False,False), ("Sam Luttmer","5",False,False),
        ("Marloes Timmermans","23",False,False), ("Bente Jager","8",False,False),
        ("Anouk Stam","9",False,False), ("Elin van Erk","12",False,False),
        ("Flo Klinkhamer","20",False,False), ("Amber Ezechiels","19",False,False),
        ("Nina van der Marel","17",False,False), ("Florine Rodenburg","11",False,False),
        ("Eliana Boekhoven","22",False,False), ("Juul Sauer","2",False,False),
        ("Anouk Slotema","3",False,False), ("Meeuw Tulp","16",False,False),
        ("Kiki Gunneman","1",True,False), ("Marit van Buul","13",False,True),
    ],
    ("Pinoké","heren"): [
        ("Hidde Brink","1",True,False), ("Jack Waller","3",False,False),
        ("Jacob Draper","7",False,True), ("Florent van Aubel","8",False,False),
        ("Miles Bukkens","11",False,False), ("Daan Bonhof","12",False,False),
        ("Luca Wolff","19",False,False), ("Teo Hinrichs","22",False,False),
        ("Thies Prinz","23",False,False), ("Pieter Sutorius","2",False,False),
        ("Tim Knapper","4",False,False), ("Jannis van Hattum","6",False,False),
        ("Boris Aardenburg","10",False,False), ("Joep Troost","13",False,False),
        ("Texas Bukkens","14",False,False), ("Indra Aerts","16",False,False),
        ("Joppe Stappenbelt","17",False,False), ("Iwan Roukema","20",False,False),
        ("Pepijn van der Valk","9",False,False), ("Jimi Kummer","15",False,False),
        ("Gijs Somers","18",False,False), ("Ralph Grevenstuk","21",False,True),
    ],
    ("Rotterdam","dames"): [
        ("Emma van Santbrink","15",False,True), ("Myrthe van Kesteren","54",False,False),
        ("Brechtje van Santbrink","14",False,False), ("Caoimhe Perdue","2",False,False),
        ("Merel Boekhorst","17",False,False), ("Amber van den Dijssel","11",False,False),
        ("Lieke Elsman","12",False,False), ("Julie van Dam","10",False,False),
        ("Noor Omrani","34",False,False), ("Daphne Koolhaas","19",False,False),
        ("Kirsten Zennemers","6",False,False), ("Iris Hollander","18",False,False),
        ("Melle Vaessen","24",False,False), ("Isis van der Kooij","4",False,False),
        ("Joy Haarman","5",False,False), ("Bobbi Dijk","9",False,False),
        ("Iris Langejans","7",False,False), ("Jaidy Greebe","3",False,False),
        ("Danique Lucieer","8",False,False), ("Kelsey Bing","1",True,False),
        ("Olivia van der Knaap","20",False,True), ("Mascha Sterk","22",False,False),
    ],
    ("Rotterdam","heren"): [
        ("Derk Meijer","1",True,False), ("Thijs van Dam","10",False,True),
        ("Pepijn van der Heijden","2",False,False), ("Justen Blok","16",False,False),
        ("Steijn van Heijningen","24",False,False), ("Olivier Hortensius","9",False,False),
        ("Tjep Hoedemakers","14",False,False), ("Joaquín Menini","18",False,False),
        ("Marc Recasens","19",False,False), ("Lars Zijderveld","25",False,True),
        ("Lucas van Tetering","3",False,False), ("Vincent Langenhuijsen","5",False,False),
        ("Bouwe Buitenhuis","13",False,False), ("Dylan Lucieer","20",False,False),
        ("Timme van der Heijden","22",False,False), ("Nick van Trigt","17",False,False),
        ("Jesse Steenhoff","6",False,False), ("Matthijs van der Wielen","15",False,False),
        ("Guus Jansen","7",False,False), ("Menno Boeren","8",False,False),
        ("Jeroen Hertzberger","21",False,False),
    ],
    ("Schaerweijde","heren"): [
        ("Pepijn Leenhouts","6",False,True), ("Jelle Westendorp","20",False,False),
        ("Joost van Eijck","4",False,False), ("Peppe Veen","7",False,False),
        ("Stijn Draaijer","14",False,False), ("Lode Draaijer","77",False,False),
        ("Mick Bosse","3",False,False), ("Maarten Bruisten","24",False,False),
        ("Daan Troost","10",False,False), ("Tijs van Horn","2",False,False),
        ("Juup Veen","8",False,False), ("Jaap Solleveld","5",False,False),
        ("Graeme Scott","17",False,False), ("Niels de Joode","11",False,False),
        ("Jens Hagen","12",False,False), ("Michiel Moret","21",False,False),
        ("Teun van Aalderen","9",False,False), ("Thibaut Mordac","18",False,False),
        ("Derk Moret","16",False,False), ("Tom Vermeulen","19",False,False),
        ("Mahinder Terlouw","1",True,False), ("Guus van Holten","15",False,True),
    ],
    ("SCHC","dames"): [
        ("Xan de Waard","7",False,False), ("Yibbi Jansen","8",False,False),
        ("Renee van Laarhoven","9",False,True), ("Lisa Post","5",False,False),
        ("Pien Dicke","21",False,False), ("Marleen Jochems","17",False,False),
        ("Mette Winter","10",False,False), ("Maud van den Heuvel","11",False,False),
        ("Jip Dicke","20",False,False), ("Marsha Zwezereijn","23",False,True),
        ("Rifka Bakker","3",False,True), ("Naomi Brunsveld","4",False,False),
        ("Isa van Heerde","15",False,False), ("Elzemiek Zandee","6",False,False),
        ("Elodie Picard","29",False,True), ("Noa Boterman","12",False,False),
        ("Mariette Boot","22",False,False), ("Anna de Geus","24",False,False),
        ("Famke Richardson","14",False,False), ("Floortje Middelbos","31",False,False),
        ("Nanieck Mengelberg","19",False,False),
    ],
    ("Tilburg","dames"): [
        ("Mikki Roberts","22",False,True), ("Hannah Salden","3",False,False),
        ("Daphne Nikkels","17",False,False), ("Iris Dominicus","9",False,False),
        ("Carmen Victoria","10",False,False), ("Lotte de Heer","7",False,False),
        ("Sanne Koks","21",False,False), ("Merel Tukkers","18",False,False),
        ("Ingeborg Dijkstra","26",False,True), ("Pleun Wester","11",False,False),
        ("Roos Ezendam","5",False,False), ("Eef Hoyinck","12",False,False),
        ("Mijs Berkhemer","15",False,False), ("Carolin Hoffmann","2",False,False),
        ("Floor de Bruin","14",False,False), ("Precious Oud","16",False,False),
        ("Merlijn Roodenburg","13",False,False), ("Emmely Bekker","8",False,False),
        ("Emma Staats","1",True,False), ("Lieke Leeggangers","19",False,False),
        ("Lieke Van otten","4",False,False), ("Sophie van de Velde","20",False,False),
    ],
}

def genereer():
    alle_spelers = []
    totaal = 0

    for (club, geslacht), spelers in SPELERS_DATA.items():
        club_id = CLUB_SLUGS.get(club, slugify(club))
        pad = DB_ROOT / "spelers" / geslacht / f"{club_id}.json"
        pad.parent.mkdir(parents=True, exist_ok=True)

        selectie = []
        for naam, rug, keeper, aanvoerder in spelers:
            s = {
                "naam": naam,
                "id": slugify(naam),
                "rugnummer": rug,
                "keeper": keeper,
                "aanvoerder": aanvoerder,
                "club": club,
                "club_id": club_id,
                "geslacht": geslacht,
                "seizoen": "2025-2026",
            }
            selectie.append(s)
            alle_spelers.append(s)

        data = {
            "club": club, "club_id": club_id,
            "geslacht": geslacht, "seizoen": "2025-2026",
            "bron": "KNHB spelerslijst PDF v11-09-2025",
            "spelers": selectie,
        }
        pad.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        print(f"  ✅ {club} {geslacht}: {len(selectie)} spelers")
        totaal += len(selectie)

    # Centrale index
    index_pad = DB_ROOT / "spelers" / "index.json"
    index_pad.write_text(json.dumps({
        "seizoen": "2025-2026",
        "bron": "KNHB spelerslijst PDF v11-09-2025",
        "totaal": len(alle_spelers),
        "spelers": alle_spelers,
    }, indent=2, ensure_ascii=False))

    print(f"\n  📋 Index: {len(alle_spelers)} spelers → spelers/index.json")
    print(f"  🏑 Klaar! {totaal} spelers in {len(SPELERS_DATA)} selecties.")

if __name__ == "__main__":
    genereer()
