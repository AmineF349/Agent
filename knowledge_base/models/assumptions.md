# Hypothèses Modèles - Guide Challenge

## Check-list Hypothèses à Challenger

### 1. Commodités

**Gas TTF**
- Range 2030: 20-60€, typique 30-40€
- Forward 2027: ~32€ (juin 2024)
- Si scénario 25€ = optimiste (abondance LNG US/Qatar, faible demande Asie)
- Si 50€ = stress (crise, froid, faible offre)
- Sensibilité: +10€ gas = +5-7€ élec si CCGT marginal

**CO2 EUA**
- 2024: ~70€, 2023: ~85€
- 2030: 80-150€, typique 90-120€
- Trajectoire EU Green Deal: MSR (Market Stability Reserve) réduit offre
- Fit-for-55: -62% émissions 2030 vs 2005
- Si <60€ = sous-estime décarbonation
- Si >150€ = décarbonation agressive
- Sensibilité: +10€ CO2 = +4-5€ élec si CCGT marginal

**Charbon**
- Moins important FR, mais influence DE/PL
- Phase-out DE 2030-2038

### 2. Demande

**FR**
- 2024: ~475 TWh
- 2030: 500-650 TWh, typique 550-600 TWh
- 2040: 550-750 TWh
- 2050: 600-850 TWh

Facteurs hausse:
- EV: +30-50 TWh 2030
- PAC (pompes chaleur): +20-30 TWh
- H2 électrolyse: +10-30 TWh 2030, +50-100 TWh 2040
- Data centers: +10-20 TWh
- Industrie: électrification

Facteurs baisse:
- Efficacité énergétique
- Sobriété
- Désindustrialisation (risque)

Source: RTE Bilan Prévisionnel 2023

**DE**
- 2024: ~550 TWh
- 2030: 600-700 TWh

### 3. Offre RES

**Solaire FR**
- 2024: 20 GW
- 2030: 30-60 GW, PPE 35-44 GW
- 2040: 50-100 GW
- Facteur charge: 12-16% (Sud > Nord)
- Rythme: 3-5 GW/an nécessaire pour 45GW 2030, vs 2-3 GW/an historique

**Éolien onshore FR**
- 2024: 22 GW
- 2030: 30-55 GW, PPE 33-34 GW
- 2040: 40-80 GW
- Facteur charge: 22-30%
- Enjeu: acceptabilité, autorisations

**Éolien offshore FR**
- 2024: 1.5 GW (Saint-Nazaire, Fécamp)
- 2030: 5-15 GW, PPE 5.2-6.2 GW
- 2040: 15-40 GW
- Facteur charge: 40-50%

**DE**
- Solaire: 80 GW 2024 -> 150-250 GW 2030
- Éolien onshore: 60 GW 2024 -> 100-160 GW 2030

### 4. Nucléaire FR

- Capacité: 61 GW (56 réacteurs)
- Dispo historique: 70-80%, 2022 crise 65% (corrosion), 2023 70%
- 2030: 75% central, 65% stress, 85% optimiste
- EPR Flamanville: 1.6 GW 2024
- EPR2: 6 réacteurs 2035-2040?
- Fermetures: Fessenheim 2020, pas d'autres prévues avant 2035

Impact: -5% dispo = +5-8€/MWh baseload FR

### 5. BESS

Voir bess.md

### 6. Interco

Voir interconnectors.md

### 7. Capture Rates & Negative Hours

Voir concepts

### 8. Coûts

- WACC: 5-8% pour RES, 8-12% pour BESS
- CAPEX solaire: 600-800 €/kW 2024, baisse 5%/an
- CAPEX éolien onshore: 1200-1500 €/kW
- CAPEX offshore: 2500-3500 €/kW
- CAPEX BESS: 300-500 €/kWh (2h)

## Méthode Challenge

1. **Comparer à historique**: Hypothèse vs 2020-2024 réel
2. **Comparer à forward**: Gas, CO2, élec forward vs scénario
3. **Comparer AFRY vs Aurora**: Écart >20% = investiguer
4. **Vérifier cohérence**: Gas haut + CO2 haut = élec haut, sinon vérifier
5. **Sensibilités**: Lancer +/-20% gas, +/-30% CO2, +/-10% demande
6. **Benchmark EU**: Comparer avec autres pays, même ordre grandeur?

## Template Questions COMEX

- Quelle est l'hypothèse X et sa justification?
- Quelle est la sensibilité prix si X +/-20%?
- Comparaison avec forward / historique / AFRY / Aurora?
- Quel est le risque si hypothèse fausse? Impact business?
- Quelle est la recommandation? Hedging? PPA? BESS?

## Risque Business

Erreur hypothèse = erreur valorisation multi-M€ sur 20 ans PPA.

Exemple:
- Capture rate 0.7 vs 0.9 sur 100MW solaire, 20 ans, baseload 70€ = (0.9-0.7)*70*100*8760*0.14*20 = ~34 M€ écart!
