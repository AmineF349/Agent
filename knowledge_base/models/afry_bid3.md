# AFRY BID3 - Modèle Marché Électrique

## Présentation

**BID3** = Better Investment Decisions, modèle fondamental marché électrique développé par AFRY (ex Pöyry).

- **Type**: Optimisation dispatch hourly, unit commitment, hydro-thermal
- **Horizon**: 30+ ans (2025-2060)
- **Géographie**: EU 30+ pays, 50+ zones, interco détaillées
- **Résolution**: Horaire, 8760h/an
- **Utilisateurs**: Utilities (EDF, Engie, TotalEnergies), investisseurs, TSO

## Méthodologie

1. **Inputs**:
   - Demande hourly par pays
   - Capacités installées par techno (RES, nucléaire, gaz, charbon, hydro, BESS)
   - Coûts variables (gas, CO2, charbon, uranium)
   - Disponibilités (nucléaire, hydro, RES profiles)
   - Interco NTC
   - Politiques (CO2, subventions RES)

2. **Optimisation**:
   - Minimise coût total système
   - Respecte demande + réserves
   - Optimise dispatch + interco flows + hydro + BESS
   - Sort prix marginal horaire (shadow price contrainte demande)

3. **Outputs**:
   - Prix day-ahead hourly par zone
   - Mix génération, dispatch
   - Flows interco, curtailment, negative hours
   - Capture rates, émissions CO2

## Hypothèses Clés 2024 Central

| Paramètre | 2025 | 2030 | 2040 | Source |
|-----------|------|------|------|--------|
| Gas TTF | 35€ | 35€ | 32€ | AFRY |
| CO2 EUA | 75€ | 110€ | 140€ | AFRY |
| Demande FR | 480 TWh | 580 TWh | 650 TWh | RTE |
| Solaire FR | 20 GW | 45 GW | 70 GW | PPE |
| Éolien onshore FR | 22 GW | 38 GW | 50 GW | PPE |
| Éolien offshore FR | 1.5 GW | 8 GW | 20 GW | PPE |
| Nucléaire FR dispo | 75% | 75% | 75% | EDF |
| BESS FR | 1 GW | 5 GW | 15 GW | AFRY |
| Interco FR-DE | 4 GW | 6 GW | 8 GW | ENTSO-E |

## Forces / Faiblesses

**Forces**:
- Très détaillé réseau EU, interco, hydro
- Bonne modélisation nucléaire FR
- Scénarios policy (Fit-for-55, etc.)
- Utilisé par beaucoup d'acteurs -> benchmark

**Faiblesses**:
- Capture rates parfois optimistes (flexibilité surestimée?)
- BESS modeling simplifié vs Aurora
- Pas de modélisation intraday/balancing
- Coût licence élevé (~100k€/an)

## Comparaison Aurora

| Critère | AFRY BID3 | Aurora |
|---------|-----------|--------|
| Focus | Réseau + dispatch | Valorisation RES/BESS |
| Capture rate | Moins détaillé | Très détaillé |
| BESS | Basique | Avancé (stacking) |
| Prix | Souvent plus haut | Plus bas (plus flex) |
| Écart typique baseload FR 2030 | 70-90€ | 60-80€ (10-20% écart) |

## Utilisation Business

- **Valorisation portefeuille RES**: Prix captés long-terme pour business plan
- **PPA**: Benchmark prix pour négociation
- **Investissement**: BESS, RES, flexibilité
- **Stratégie**: Scénarios long-terme pour COMEX

## Questions pour Challenger AFRY

1. Gas 35€ 2030: vs forward 2027 32€, cohérent? Sensibilité?
2. CO2 110€ 2030: trajectoire EU ETS MSR, Fit-for-55, justifié?
3. Demande 580 TWh FR 2030: source RTE Bilan Prévisionnel? Électrification vs sobriété?
4. Solaire 45GW FR 2030: vs PPE 35-44GW, haut de fourchette, rythme autorisations?
5. Nucléaire 75% dispo: vs 65% 2022 crise, 70% 2023, optimiste?
6. BESS 5GW FR 2030: vs 1GW 2024, rythme 0.8GW/an réaliste? Revenue stacking?
7. Interco FR-DE 6GW 2030: projets concrets? Si retard, impact prix?
8. Capture rate solaire 0.78 2030: vs 0.85 aujourd'hui, baisse modérée, flexibilité assumée?
9. Negative hours 250h 2030: cohérent avec 45GW solaire + 5GW BESS?
10. CCGT marginal combien d'heures? Si <20%, prix plus par RES/nucléaire

## Tips Analyste

- Toujours comparer AFRY vs Aurora vs interne, écart >20% = investiguer
- Lancer sensibilités gas +/-20%, CO2 +/-30%, demande +/-10%
- Vérifier changelog AFRY: qu'est-ce qui a changé vs dernier run?
- Préparer Q&A pour COMEX: 3 risques, 3 opportunités, 1 recommandation
