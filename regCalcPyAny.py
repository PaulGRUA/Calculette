
import pandas as pd

import math

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import base64
import dash_bootstrap_components as dbc
import dash_table
import dash_auth

# %%
dfInfos = pd.read_csv('dfInfos.csv')
dfInfos['Code_région'] = dfInfos['Code_région'].apply(lambda x: str(x).zfill(2))
dfInfos['Population_département'] = dfInfos['Population_département'].astype(int)



# calculette :
def Algo_regionales(test72):
    # étape 1 : Vérifier la liste en tête :
    dfVoixRegionNuance = pd.DataFrame(test72.groupby('Nuance')['Voix_département_nuance'].sum()).reset_index()
    dfVoixRegionNuance.columns = ['Nuance', 'Voix_région_nuance']
    test72 = test72.merge(dfVoixRegionNuance)
    test72 = test72.sort_values('Voix_région_nuance', ascending=False).reset_index(drop=True)
    NuanceTete = test72.loc[0, 'Nuance']

    # calculer le nombre de siege pour la nuance de tête:
    NbSiegeRegion = dfInfos[dfInfos['Code_région'] == test72['Code_région'].unique()[0]]['Nb_sieges_région'].unique()[0]
    SiegeTete = math.ceil(NbSiegeRegion / 4)

    # étape 2 calculer le nombre de siège par nuance :
    # Quotient électoral :
    SiegeApourvoir = NbSiegeRegion - SiegeTete
    TotalVoixRegion = test72['Voix_département_nuance'].sum()

    # Calcul quotient électoral:
    QElectoral = TotalVoixRegion / SiegeApourvoir
    dfSiegeRegNuance = test72[['Nuance', 'Voix_région_nuance']].drop_duplicates().copy()

    # Colonne siège pour nuance tête
    dfSiegeRegNuance['Siege_Region_Nuance_Tete'] = 0
    dfSiegeRegNuance.loc[
        dfSiegeRegNuance[dfSiegeRegNuance['Nuance'] == NuanceTete].index, 'Siege_Region_Nuance_Tete'] = SiegeTete

    # Colonne Calcul siège quotient
    dfSiegeRegNuance['Calcul_Siege_Region_Nuance_Quotient'] = dfSiegeRegNuance['Voix_région_nuance'] / QElectoral

    # colonne nb siège
    dfSiegeRegNuance['Siege_Region_Nuance_Quotient'] = dfSiegeRegNuance['Calcul_Siege_Region_Nuance_Quotient'].apply(
        lambda x: math.floor(x))

    # Plus forte moyenne :
    # création colonne nb siège plus forte moyenne :
    dfSiegeRegNuance['Siege_Region_Nuance_Moyenne'] = 0

    # Création colonne nb de siège total :
    dfSiegeRegNuance['Siege_Region_Nuance_Total'] = dfSiegeRegNuance['Siege_Region_Nuance_Tete'] + dfSiegeRegNuance[
        'Siege_Region_Nuance_Quotient'] + dfSiegeRegNuance['Siege_Region_Nuance_Moyenne']

    # Création colonne nb de siège quotient + moyenne :
    dfSiegeRegNuance['Siege_Region_Nuance_Somme_Quotient_Moyenne'] = dfSiegeRegNuance['Siege_Region_Nuance_Quotient'] + \
                                                                     dfSiegeRegNuance['Siege_Region_Nuance_Moyenne']

    # Boucle pour incrémenter d'un siège en fonction de la plus forte moyenne pour la région :
    NbSiegeAPourvoirParMoyenne = NbSiegeRegion - dfSiegeRegNuance['Siege_Region_Nuance_Total'].sum()
    for a in range(NbSiegeAPourvoirParMoyenne):
        # déterminer les scores donné par nb voix nuance / nb sièges obtenus + 1
        dfMoyenne = dfSiegeRegNuance[
            ['Nuance', 'Voix_région_nuance', 'Siege_Region_Nuance_Somme_Quotient_Moyenne']].copy()
        dfMoyenne['Score_Moyenne'] = dfMoyenne['Voix_région_nuance'] / (
                    dfMoyenne['Siege_Region_Nuance_Somme_Quotient_Moyenne'] + 1)
        # Nuance avec le plus haut score :
        NuanceSiegeAjout = dfMoyenne.sort_values('Score_Moyenne', ascending=False).reset_index(drop=True).loc[
            0, 'Nuance']
        # Incrémenter de 1 le nombre de siège :
        dfSiegeRegNuance.loc[
            dfSiegeRegNuance[dfSiegeRegNuance['Nuance'] == NuanceSiegeAjout].index, 'Siege_Region_Nuance_Moyenne'] = \
        dfSiegeRegNuance.loc[
            dfSiegeRegNuance[dfSiegeRegNuance['Nuance'] == NuanceSiegeAjout].index, 'Siege_Region_Nuance_Moyenne'] + 1
        # Mettre à jour le total Quotient plus moyenne :
        dfSiegeRegNuance['Siege_Region_Nuance_Somme_Quotient_Moyenne'] = dfSiegeRegNuance[
                                                                             'Siege_Region_Nuance_Quotient'] + \
                                                                         dfSiegeRegNuance['Siege_Region_Nuance_Moyenne']

    # mettre à jour colonne siège total :
    dfSiegeRegNuance['Siege_Region_Nuance_Total'] = dfSiegeRegNuance['Siege_Region_Nuance_Tete'] + dfSiegeRegNuance[
        'Siege_Region_Nuance_Quotient'] + dfSiegeRegNuance['Siege_Region_Nuance_Moyenne']

    ### 2éme phase : Répartir le nombre de siège entre les départements :
    # Récupérer le nombre de siège par nuance dans la région :
    test72 = test72.merge(dfSiegeRegNuance[['Nuance', 'Siege_Region_Nuance_Total']]).copy()

    # Calculer le quotient électoral départemental par nuance :
    test72['Quotient_electoral_dep_nuance'] = test72['Voix_région_nuance'] / test72['Siege_Region_Nuance_Total']

    # Calcul du nb de siege par département avec le quotient :
    test72['Calcul_Siege_département_Nuance_Quotient'] = test72['Voix_département_nuance'] / test72[
        'Quotient_electoral_dep_nuance']

    # Arrondi à l'inférieur nb de siege par département avec le quotient :
    test72['Siege_département_Nuance_Quotient'] = test72['Calcul_Siege_département_Nuance_Quotient'].apply(
        lambda x: math.floor(x))

    # Calcul de la différence entre le calcul pour le nombre de siège et le nombre de siège
    # pour avoir le reste après la virgule pour pouvoir classer les départements
    test72['Reste_après_virgule_calcul_siege_dep'] = test72['Calcul_Siege_département_Nuance_Quotient'] - test72[
        'Siege_département_Nuance_Quotient']
    # créer liste qui contient les départements par ordre :
    l_ordreDepartement = \
    test72[test72['Nuance'] == NuanceTete].sort_values('Reste_après_virgule_calcul_siege_dep', ascending=False)[
        'Code_département'].tolist()

    # calcul du total de sièges attribués avec le quotient dans tous les départements par nuance :
    dfSiegeDepNuance = pd.DataFrame(
        test72.groupby('Nuance')['Siege_département_Nuance_Quotient'].sum()).reset_index().copy()
    dfSiegeDepNuance.columns = ['Nuance', 'Total_départements_sieges_quotient_nuance']
    test72 = test72.merge(dfSiegeDepNuance).copy()

    # calcul du nombre de sièges qu'il reste à attribuer par plus forte moyenne selon les nuances :
    test72['Nb_Siege_a_attribué_par_moyenne'] = test72['Siege_Region_Nuance_Total'] - test72[
        'Total_départements_sieges_quotient_nuance']

    # Création de la colonne des sièges attribués par plus forte moyenne pour les départements :
    test72['Siege_département_nuance_moyenne'] = 0

    # Création de la colonne qui calcule la somme des sièges attribués par quotient et moyenne :
    test72['Siege_département_Nuance_Somme_Quotient_Moyenne'] = test72['Siege_département_Nuance_Quotient'] + test72[
        'Siege_département_nuance_moyenne']

    # faire une 1ère boucle avec les nuances,
    # puis une 2éme boucle en fonction du nombre du nombre de siège à rajouter pour la nuance :
    l_nuances = test72['Nuance'].unique().tolist()

    # 1ére boucle pour les nuances :
    for a in range(len(l_nuances)):
        # 2éme boucle pour attribuer siège :
        try:
            for b in range(test72[(test72['Nuance'] == l_nuances[a]) & (test72['Nb_Siege_a_attribué_par_moyenne'] > 0)][
                               'Nb_Siege_a_attribué_par_moyenne'].unique()[0]):
                # pour une nuance, sélectionner le département à incrémenter :
                dfMoyenne = \
                test72[(test72['Nuance'] == l_nuances[a]) & (test72['Nb_Siege_a_attribué_par_moyenne'] > 0)][
                    ['Nom_département', 'Code_département', 'Nuance', 'Voix_département_nuance',
                     'Siege_département_Nuance_Somme_Quotient_Moyenne']].copy()
                dfMoyenne['Score_par_dep'] = dfMoyenne['Voix_département_nuance'] / (
                            dfMoyenne['Siege_département_Nuance_Somme_Quotient_Moyenne'] + 1)
                depNuanceToIncrement = \
                dfMoyenne.sort_values('Score_par_dep', ascending=False).reset_index(drop=True).loc[
                    0, 'Code_département']

                # Incrémenter la bonne nuance et le bon dep :
                test72.loc[test72[(test72['Nuance'] == l_nuances[a]) & (test72[
                                                                            'Code_département'] == depNuanceToIncrement)].index, 'Siege_département_nuance_moyenne'] = \
                test72.loc[test72[(test72['Nuance'] == l_nuances[a]) & (test72[
                                                                            'Code_département'] == depNuanceToIncrement)].index, 'Siege_département_nuance_moyenne'] + 1

                # Mettre à jour la colonne somme quotient + moyenne :
                test72['Siege_département_Nuance_Somme_Quotient_Moyenne'] = test72[
                                                                                'Siege_département_Nuance_Quotient'] + \
                                                                            test72['Siege_département_nuance_moyenne']
                if l_nuances[a] == NuanceTete:
                    l_ordreDepartement.append(depNuanceToIncrement)
        except IndexError:
            pass

    # Sélectionner et renommer les colonnes :
    test72 = test72[['Code_département', 'Nom_département', 'Nuance', 'Siege_département_Nuance_Somme_Quotient_Moyenne',
                     'Voix_département_nuance', 'Voix_région_nuance', 'Siege_Region_Nuance_Total',
                     'Siege_département_Nuance_Quotient', 'Siege_département_nuance_moyenne']].copy()
    test72.columns = ['Code_département', 'Nom_département', 'Nuance', 'Nb_siege', 'Voix_département_nuance',
                      'Voix_région_nuance',
                      'Siege_Region_Nuance_Total', 'Siege_département_Nuance_Quotient',
                      'Siege_département_nuance_moyenne']

    dfSiegeRegNuance = dfSiegeRegNuance[
        ['Nuance', 'Voix_région_nuance', 'Siege_Region_Nuance_Total', 'Siege_Region_Nuance_Tete',
         'Siege_Region_Nuance_Quotient', 'Siege_Region_Nuance_Moyenne']].reset_index(drop=True).copy()

    # Dernière phase : ajouter et retirer siège en fonction de la population et du nombre minimal de siège :

    # vérifier que le nombre minimal de conseiller par département soit respecté :
    dfVerifMinimumConseillers = pd.DataFrame(test72.groupby('Code_département')['Nb_siege'].sum()).reset_index().copy()
    dfVerifMinimumConseillers.columns = ['Code_département', 'Nb_siege_par_dep']
    # ajouter la variable population :
    dfVerifMinimumConseillers = dfVerifMinimumConseillers.merge(
        dfInfos[['Code_département', 'Population_département']]).copy()

    # Enfonction de la pop fixer un nombre minimal de siège :
    dfVerifMinimumConseillers.loc[dfVerifMinimumConseillers[dfVerifMinimumConseillers[
                                                                'Population_département'] < 100000].index, 'Nombre_minimal_siege'] = 2
    dfVerifMinimumConseillers.loc[dfVerifMinimumConseillers[dfVerifMinimumConseillers[
                                                                'Population_département'] > 100000].index, 'Nombre_minimal_siege'] = 4
    dfVerifMinimumConseillers['Nombre_minimal_siege'] = dfVerifMinimumConseillers['Nombre_minimal_siege'].astype(int)

    # Attention ne pas intégrer
    # on met le nombre de siege de la Mayenne à 2 pour le test :
    # dfVerifMinimumConseillers.loc[2,'Nb_siege_par_dep'] = 2

    # calculer le nombre de siège à ajouter :
    dfVerifMinimumConseillers['Nb_siege_a_ajouter'] = dfVerifMinimumConseillers['Nombre_minimal_siege'] - \
                                                      dfVerifMinimumConseillers['Nb_siege_par_dep']
    dfVerifMinimumConseillers.loc[
        dfVerifMinimumConseillers[dfVerifMinimumConseillers['Nb_siege_a_ajouter'] < 1].index, 'Nb_siege_a_ajouter'] = 0

    # liste des départements ou il faut ajouter :
    l_depAjoutSiege = dfVerifMinimumConseillers[dfVerifMinimumConseillers['Nb_siege_a_ajouter'] > 0][
        'Code_département'].tolist()

    # créer une colonne ajout_conseiller_nb_min
    test72['Siege_département_Nuance_Nb_min'] = 0

    # Calculer le nombre de siege à ajouter dans le df dep :
    for a in range(len(l_depAjoutSiege)):
        test72.loc[test72[(test72['Code_département'] == l_depAjoutSiege[a]) & (
                    test72['Nuance'] == NuanceTete)].index, 'Siege_département_Nuance_Nb_min'] = test72.loc[test72[(
                                                                                                                               test72[
                                                                                                                                   'Code_département'] ==
                                                                                                                               l_depAjoutSiege[
                                                                                                                                   a]) & (
                                                                                                                               test72[
                                                                                                                                   'Nuance'] == NuanceTete)].index, 'Siege_département_Nuance_Nb_min'] + \
                                                                                                 dfVerifMinimumConseillers.loc[
                                                                                                     dfVerifMinimumConseillers[
                                                                                                         dfVerifMinimumConseillers[
                                                                                                             'Code_département'] ==
                                                                                                         l_depAjoutSiege[
                                                                                                             a]].index, 'Nb_siege_a_ajouter']

        # Calculer le nombre de siège à retirer pour la nuance tête :
    NbSiegeAretirer = dfVerifMinimumConseillers['Nb_siege_a_ajouter'].sum()

    # Créér liste des départements ou il faut retirer un siège dans le bon ordre :

    if NbSiegeAretirer != 0:
        l_DepartementRetirerSiege = l_ordreDepartement[-NbSiegeAretirer:]
        l_DepartementRetirerSiege = l_DepartementRetirerSiege[::-1]
    else:
        l_DepartementRetirerSiege = []

    # Créer une colonne ou on inscrit le nombre de siège à retirer à cause du nb_min
    test72['Siege_reattribue_min'] = 0

    # boucler pour retirer un siège à chaque itération :
    for a in range(len(l_DepartementRetirerSiege)):
        test72.loc[test72[(test72['Nuance'] == NuanceTete) & (
                    test72['Code_département'] == l_DepartementRetirerSiege[a])].index, 'Siege_reattribue_min'] = \
        test72.loc[test72[(test72['Nuance'] == NuanceTete) & (
                    test72['Code_département'] == l_DepartementRetirerSiege[a])].index, 'Siege_reattribue_min'] - 1

        # mettre à jour la colonne Nb_siege :
    test72['Nb_siege'] = test72['Siege_département_Nuance_Quotient'] + test72['Siege_département_nuance_moyenne'] + \
                         test72['Siege_département_Nuance_Nb_min'] + test72['Siege_reattribue_min']
    test72.sort_values(['Siege_Region_Nuance_Total', 'Nb_siege'], ascending=False, inplace=True)

    # réarranger les colonnes :
    dfSiegeRegNuance.columns = ['Nuance', 'Voix_nuance', 'Siege_Nuance_Total',
                                'Siege_Nuance_Tete', 'Siege_Nuance_Quotient',
                                'Siege_Nuance_Moyenne']

    test72 = test72[['Code_département', 'Nom_département', 'Nuance', 'Nb_siege',
                     'Voix_département_nuance', 'Siege_département_Nuance_Quotient',
                     'Siege_département_nuance_moyenne', 'Siege_département_Nuance_Nb_min',
                     'Siege_reattribue_min']].copy()
    test72.columns = ['Code_dép', 'Département', 'Nuance', 'Nb_siege',
                      'Voix_nuance', 'Siege_Nuance_Quotient', 'Siege_nuance_moyenne', 'Siege_Nuance_Nb_min',
                      'Siege_reattribue_min']

    return test72, dfSiegeRegNuance


# %%
# Fichier correspondance entre région et départements :
dfRegionsDepartement = pd.read_csv('dfRegionsDepartement.csv', index_col=0)
dfRegionsDepartement['Code_région'] = dfRegionsDepartement['Code_région'].apply(lambda x: str(x).zfill(2))
# dfRegionsDepartement


# %%
# Création des options pour dropdown région :
dfDropdownRegion = dfRegionsDepartement[['Nom_région', 'Code_région']].drop_duplicates().copy()
dfDropdownRegion.columns = ['label', 'value']
dfDropdownRegion.sort_values('label', inplace=True)
dfDropdownRegion.reset_index(inplace=True, drop=True)
dfDropdownRegion = dfDropdownRegion.T.to_dict()
optDropdownRegion = []
for a in range(len(dfDropdownRegion)):
    optDropdownRegion.append(dfDropdownRegion[a])


# optDropdownRegion


# %%
# Fonction qui retourne le nombre de departement :

# input : Code_région
# output : nombre entier
# codReg = '53'

def countDep(codReg):
    dfCountDep = dfRegionsDepartement[dfRegionsDepartement['Code_région'] == codReg].copy()
    return len(dfCountDep['Code_département'].unique().tolist())


# %%
# fonction pour dropdown département après choix de la région :

# input : Code_région
# output : les options du dropdown

# codReg = '84'

def DropdownLibelleDep(codReg):
    dfDropdownLibelleDep = dfRegionsDepartement[dfRegionsDepartement['Code_région'] == codReg].copy()
    dfDropdownLibelleDep = dfDropdownLibelleDep[['Nom_département', 'Code_département']].copy()
    dfDropdownLibelleDep.columns = ['label', 'value']
    dfDropdownLibelleDep.reset_index(inplace=True, drop=True)
    dfDropdownLibelleDep.sort_values('label', inplace=True)
    dfDropdownLibelleDep = dfDropdownLibelleDep.T.to_dict()
    optDropdownDep = []
    for a in range(len(dfDropdownLibelleDep)):
        optDropdownDep.append(dfDropdownLibelleDep[a])

    return optDropdownDep


# %%
# Fonction pour transformer les input en dataframe :
def DfFromInputs(l_nuances, codReg):
    nbListes = len(l_nuances)
    dfResult = dfRegionsDepartement[dfRegionsDepartement['Code_région'] == codReg].reset_index(drop=True)
    dfResult['Nuance'] = None

    # Concat autant de fois qu'il y a de nuances :
    dfResultListes = dfResult.copy()
    for a in range(nbListes):
        dfResult['Nuance'] = l_nuances[a]
        dfResultListes = pd.concat([dfResultListes, dfResult]).copy()

    dfResultListes = dfResultListes.dropna()
    dfResultListes['Voix_département_nuance'] = 0
    # dfResultListes.sort_values(['Nom_département','Nuance'],inplace=True)
    dfResultListes.sort_values('Nom_département', inplace=True)
    dfResultListes.reset_index(drop=True, inplace=True)
    return dfResultListes


# %%
# id mdp
VALID_USERNAME_PASSWORD_PAIRS = {
    'Paul': 'SOC1',
    'Ambre': 'SOC2',
    'BMAURIN': 'SOC3',
}

# %%
##########################################
# Titre
TitreGeneral = html.H1('Calculette élections régionales',
                       style={'font-size': '64px', }
                       , className="h-50"
                       )
image_filenamePS = 'LogoPSFond.png'
encoded_imageLogoPS = base64.b64encode(open(image_filenamePS, 'rb').read())
logoDashPS = html.Img(src='data:image/png;base64,{}'.format(encoded_imageLogoPS.decode()))

header = dbc.FormGroup(
    [
        dbc.Row(  # ligne avec échelon code et nuance
            [
                dbc.Col(logoDashPS, width={'size': 4, 'offset': 1}
                        ),
                dbc.Col(TitreGeneral, width={'size': 5, 'offset': 0}
                        ),
            ]
        ),
    ], style={"border": "5px black solid", 'backgroundColor': '#f05d7d', 'vertical-align': 'middle'}
)

# Région & nb de liste picker :
LabelDropdownRegion = html.Label('Sélectionnez une région :')

DropdownRegionLibelle = dcc.Dropdown(id='region_Libelle_picker',
                                     options=optDropdownRegion,

                                     # value = '7515',
                                     # disabled=True,
                                     )
LabelInputNbListes = html.Label('Entrez le nombre de liste : (min. 2, max. 5)')

NbListesInput = dcc.Input(id='nb_listes_input',
                          type='number',
                          value=3
                          )

RegionNbListePicker = html.Div([
    html.Hr(),
    dbc.Row([
        dbc.Col(LabelDropdownRegion, width={'size': 4, 'offset': 4}),
    ]),
    dbc.Row([
        dbc.Col(DropdownRegionLibelle, width={'size': 4, 'offset': 4}),
    ]),
    dbc.Row([
        dbc.Col(LabelInputNbListes, width={'size': 4, 'offset': 4}),
    ]),
    dbc.Row([
        dbc.Col(NbListesInput, width={'size': 4, 'offset': 4}),
    ]),

]
    # , style= {'display': 'block'}
)

# Noms des listes :
LabelInputNomsListes = html.Label('Entrez les noms des listes :')

InputNomListe1 = dcc.Input(id='nom_liste_1',
                           type='text',
                           value='SOC',
                           style={'display': 'block'},
                           )
InputNomListe2 = dcc.Input(id='nom_liste_2',
                           type='text',
                           value=None,
                           style={'display': 'block'},
                           )
InputNomListe3 = dcc.Input(id='nom_liste_3',
                           type='text',
                           value=None,
                           style={'display': 'block'},
                           )
InputNomListe4 = dcc.Input(id='nom_liste_4',
                           type='text',
                           # value ='Liste 4',
                           style={'display': 'none'},
                           )
InputNomListe5 = dcc.Input(id='nom_liste_5',
                           type='text',
                           # value ='Liste 5',
                           style={'display': 'none'},

                           )

NomsListePicker = html.Div([
    html.Hr(),
    dbc.Row([
        dbc.Col(LabelInputNomsListes, width={'size': 4, 'offset': 4}),
    ]),
    dbc.Row([
        dbc.Col(InputNomListe1, width={'size': 4, 'offset': 4}),
    ]),
    dbc.Row([
        dbc.Col(InputNomListe2, width={'size': 4, 'offset': 4}),
    ]),
    dbc.Row([
        dbc.Col(InputNomListe3, width={'size': 4, 'offset': 4}),
    ]),
    dbc.Row([
        dbc.Col(InputNomListe4, width={'size': 4, 'offset': 4}),
    ]),
    dbc.Row([
        dbc.Col(InputNomListe5, width={'size': 4, 'offset': 4}),
    ]),

]
    # , style= {'display': 'block'}
)

# df résultats :

labelTatbleResults = html.Label("Entrez le nombre de voix dans la colonne 'Voix_département_nuance' :")

tableResults = dash_table.DataTable(
    id='table_results',
    # columns=[{"name": i, "id": i} for i in dfTableCodeBase.columns],
    page_action='none',
    style_table={
        'height': 'auto',
        # 'overflowY': 'auto'
    },
    fixed_rows={'headers': True},
    style_cell_conditional=[
        {'if': {'column_id': 'Nom_région'}, 'width': '19%', 'textAlign': 'left'},
        {'if': {'column_id': 'Nom_département'}, 'width': '19%', 'textAlign': 'left'},
        {'if': {'column_id': 'Code_région'}, 'width': '10%', 'textAlign': 'center'},
        {'if': {'column_id': 'Code_département'}, 'width': '13%', 'textAlign': 'center'},
        {'if': {'column_id': 'Nuance'}, 'width': '18%', 'textAlign': 'left'},
        {'if': {'column_id': 'Voix_département_nuance'}, 'width': '21%', 'textAlign': 'right'},
    ],
    style_data_conditional=[
        {
            'if': {'row_index': 'odd'},
            'backgroundColor': '#f0f0f0'
        }
    ],
    style_header={
        'backgroundColor': '#edcad0',
        'fontWeight': 'bold'
    },
    editable=True
)

TableInputs = html.Div([
    html.Hr(),
    dbc.Row([
        dbc.Col(labelTatbleResults, width={'size': 10, 'offset': 1}),
    ]),
    dbc.Row([
        dbc.Col(tableResults, width={'size': 10, 'offset': 1}),
    ]),
]
    # , style= {'display': 'block'}
)

# tables nombres de sièges régions et départements :

LabelSiegeRegion = html.H4("Résultats de l'obtention des sièges au niveau de la région :")

LabelSiegeDepartement = html.H4("Répartition des sièges dans les départements :")

colsTableSiegeReg = ['Nuance', 'Voix_nuance', 'Siege_Nuance_Total', 'Siege_Nuance_Tete',
                     'Siege_Nuance_Quotient', 'Siege_Nuance_Moyenne']

tableSiegeRegion = dash_table.DataTable(
    id='table_siege_region',
    columns=[{"name": i, "id": i} for i in colsTableSiegeReg],
    page_action='none',
    style_table={
        'height': 'auto',
        'overflowX': 'auto'
    },
    fixed_rows={'headers': True},
    style_cell_conditional=[
        {'if': {'column_id': 'Nuance'}, 'width': '16%', 'textAlign': 'left'},
        {'if': {'column_id': 'Voix_nuance'}, 'width': '16%', 'textAlign': 'left'},
        {'if': {'column_id': 'Siege_Nuance_Total'}, 'width': '16%', 'textAlign': 'center'},
        {'if': {'column_id': 'Siege_Nuance_Tete'}, 'width': '16%', 'textAlign': 'center'},
        {'if': {'column_id': 'Siege_Nuance_Quotient'}, 'width': '16%', 'textAlign': 'center'},
        {'if': {'column_id': 'Siege_Nuance_Moyenne'}, 'width': '16%', 'textAlign': 'center'},
    ],
    style_data_conditional=[
        {
            'if': {'row_index': 'odd'},
            'backgroundColor': '#f0f0f0'
        }
    ],
    style_header={
        'backgroundColor': '#edcad0',
        'fontWeight': 'bold'
    },
    export_format='xlsx',
)

colsTableSiegeDep = ['Code_dép', 'Département', 'Nuance', 'Nb_siege', 'Voix_nuance',
                     'Siege_Nuance_Quotient', 'Siege_nuance_moyenne', 'Siege_Nuance_Nb_min',
                     'Siege_reattribue_min']

tableSiegeDepartement = dash_table.DataTable(
    id='table_siege_departement',
    columns=[{"name": i, "id": i} for i in colsTableSiegeDep],
    page_action='none',
    style_table={
        'height': 'auto',
        'overflowX': 'auto'
    },
    fixed_rows={'headers': True},
    style_cell_conditional=[
        {'if': {'column_id': 'Code_dép'}, 'width': '7%', 'textAlign': 'center'},
        {'if': {'column_id': 'Département'}, 'width': '11%', 'textAlign': 'left'},
        {'if': {'column_id': 'Nuance'}, 'width': '11%', 'textAlign': 'left'},
        {'if': {'column_id': 'Nb_siege'}, 'width': '7%', 'textAlign': 'center'},
        {'if': {'column_id': 'Voix_nuance'}, 'width': '11%', 'textAlign': 'center'},
        {'if': {'column_id': 'Siege_Nuance_Quotient'}, 'width': '13%', 'textAlign': 'center'},
        {'if': {'column_id': 'Siege_nuance_moyenne'}, 'width': '13%', 'textAlign': 'center'},
        {'if': {'column_id': 'Siege_Nuance_Nb_min'}, 'width': '13%', 'textAlign': 'center'},
        {'if': {'column_id': 'Siege_reattribue_min'}, 'width': '13%', 'textAlign': 'center'},
    ],
    style_data_conditional=[
        {
            'if': {'row_index': 'odd'},
            'backgroundColor': '#f0f0f0'
        }
    ],
    style_header={
        'backgroundColor': '#edcad0',
        'fontWeight': 'bold'
    },
    export_format='xlsx',
)

TablesResultsSiege = html.Div([
    html.Hr(),
    dbc.Row([
        dbc.Col(LabelSiegeRegion, width={'size': 10, 'offset': 1}),
    ]),
    html.Hr(),
    dbc.Row([
        dbc.Col(tableSiegeRegion, width={'size': 10, 'offset': 1}),
    ]),
    html.Hr(),
    dbc.Row([
        dbc.Col(LabelSiegeDepartement, width={'size': 10, 'offset': 1}),
    ]),
    html.Hr(),
    dbc.Row([
        dbc.Col(tableSiegeDepartement, width={'size': 10, 'offset': 1}),
    ]),
]
    # , style= {'display': 'block'}
)

##########################################
# initialise the Dash interface
backGroundColor = '#f7f7f7'
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
# mdp :
auth = dash_auth.BasicAuth(
    app,
    VALID_USERNAME_PASSWORD_PAIRS
)

app.layout = html.Div([

    header,
    RegionNbListePicker,
    NomsListePicker,
    TableInputs,
    TablesResultsSiege,

], style={'backgroundColor': backGroundColor})


##############################################
# Call backs :

# Calls backs sur input noms de listes selon nb de listes sur la région :
# 1er
@app.callback(

    [Output('nom_liste_1', 'style'), Output('nom_liste_1', 'value')],
    [
        Input('nb_listes_input', 'value'),
        Input('nom_liste_1', 'value'),
    ]
)
def UpdateStyleInputNomListe(nb_liste_value, val):
    if nb_liste_value >= 1:
        return {'display': 'block'}, val
    else:
        return {'display': 'none'}, None


@app.callback(

    [Output('nom_liste_2', 'style'), Output('nom_liste_2', 'value')],
    [
        Input('nb_listes_input', 'value'), Input('nom_liste_2', 'value'),
    ]
)
def UpdateStyleInputNomListe(nb_liste_value, val):
    if nb_liste_value >= 2:
        return {'display': 'block'}, val
    else:
        return {'display': 'none'}, None


# 1er
@app.callback(

    [Output('nom_liste_3', 'style'), Output('nom_liste_3', 'value')],
    [
        Input('nb_listes_input', 'value'), Input('nom_liste_3', 'value'),
    ]
)
def UpdateStyleInputNomListe(nb_liste_value, val):
    if nb_liste_value >= 3:
        return {'display': 'block'}, val
    else:
        return {'display': 'none'}, None


# 2ème
@app.callback(

    [Output('nom_liste_4', 'style'), Output('nom_liste_4', 'value')],
    [
        Input('nb_listes_input', 'value'), Input('nom_liste_4', 'value'),
    ]
)
def UpdateStyleInputNomListe(nb_liste_value, val):
    if nb_liste_value >= 4:
        return {'display': 'block'}, val
    else:
        return {'display': 'none'}, None


# 3ème
@app.callback(

    [Output('nom_liste_5', 'style'), Output('nom_liste_5', 'value')],
    [
        Input('nb_listes_input', 'value'), Input('nom_liste_5', 'value'),
    ]
)
def UpdateStyleInputNomListe(nb_liste_value):
    if nb_liste_value >= 5:
        return {'display': 'block'}, val
    else:
        return {'display': 'none'}, None


# Call backs pour la table input :
@app.callback(

    [Output('table_results', 'data'), Output('table_results', 'columns')],
    [
        Input('nom_liste_1', 'value'),
        Input('nom_liste_2', 'value'),
        Input('nom_liste_3', 'value'),
        Input('nom_liste_4', 'value'),
        Input('nom_liste_5', 'value'),
        Input('region_Libelle_picker', 'value'),
    ]
)
def UpdateTableInputs(ValueNom_liste_1, ValueNom_liste_2, ValueNom_liste_3, ValueNom_liste_4, ValueNom_liste_5,
                      ValueRegion_Libelle_picker):
    l_nuances = [ValueNom_liste_1, ValueNom_liste_2, ValueNom_liste_3, ValueNom_liste_4, ValueNom_liste_5]
    df = DfFromInputs(l_nuances, ValueRegion_Libelle_picker).copy()
    columns = [{'name': i, 'id': i} for i in df.columns]
    return df.to_dict('records'), columns


# CallBack pour les tableaux des sièges :

@app.callback(

    [Output('table_siege_departement', 'data'), Output('table_siege_region', 'data')],
    [
        Input('table_results', 'data'),
    ]
)
def UpdateTableAlgo(data_table_results):
    df = pd.DataFrame(data_table_results)
    df['Voix_département_nuance'] = df['Voix_département_nuance'].astype(int)
    ResultDep, ResultReg = Algo_regionales(df)
    return ResultDep.to_dict('records'), ResultReg.to_dict('records')


if __name__ == '__main__':
    app.run_server(debug=False)

# %%



