# Aurora Energy Research - Modèle Marché Électrique

## Présentation

Aurora = cabinet conseil UK, modèle marché électrique EU, focus valorisation RES/BESS.

- **Type**: Modèle fondamental + optimisation, focus prix + capture rates
- **Horizon**: 2025-2060
- **Géographie**: EU, GB, US, Australia
- **Résolution**: Horaire, mais agrégé pour long-terme
- **Utilisateurs**: Investisseurs RES/BESS, utilities, fonds

## Méthodologie

Similaire AFRY mais focus différent:
- Plus détaillé sur **capture rates** par techno, localisation, profil
- **BESS** modélisé avec revenue stacking (arbitrage + FCR + aFRR + capacité)
- **Flexibilité demande**, hydro, interco
- **Policy** très détaillé (CfD, PPA, capacity market)

Outputs:
- Prix baseload, peakload, capture prices/rates
- Revenus BESS, valorisation RES
- Negative hours, curtailment
- Scénarios policy

## Hypothèses Clés 2024 Central (FR)

| Paramètre | 2030 | 2040 | Commentaire |
|-----------|------|------|-------------|
| Gas TTF | 32€ | 30€ | Légèrement sous AFRY |
| CO2 | 100€ | 130€ | Sous AFRY |
| Baseload FR | 65-75€ | 70-85€ | Sous AFRY 10-15% |
| Solaire FR | 50 GW | 80 GW | Au-dessus AFRY |
| Éolien onshore FR | 40 GW | 55 GW | Proche AFRY |
| Éolien offshore FR | 10 GW | 25 GW | Au-dessus AFRY |
| BESS FR | 8 GW | 20 GW | Au-dessus AFRY |
| Capture rate solaire 2030 | 0.70 | 0.60 | Plus bas que AFRY |
| Capture rate éolien 2030 | 0.85 | 0.75 | Plus bas que AFRY |
| Negative hours 2030 FR | 400h | 800h | Au-dessus AFRY |

Aurora plus **optimiste sur déploiement RES/BESS**, plus **pessimiste sur capture rates** (plus de cannibalisation).

## Forces / Faiblesses

**Forces**:
- Capture rates très détaillés (par région, profil)
- BESS modeling avancé (stacking, business case)
- Interface user-friendly, dashboards
- Scénarios policy nombreux

**Faiblesses**:
- Réseau moins détaillé que AFRY (interco simplifiées)
- Nucléaire FR moins détaillé
- Prix parfois bas vs AFRY (flexibilité surestimée?)
- Coût licence élevé aussi

## Comparaison AFRY

Voir afry_bid3.md pour tableau comparatif.

Écart typique:
- Baseload FR 2030: AFRY 80€, Aurora 70€ (12% écart)
- Capture rate solaire 2030: AFRY 0.78, Aurora 0.70
- BESS 2030 FR: AFRY 5GW, Aurora 8GW

**Pourquoi écart?**
- Aurora assume plus de flexibilité (BESS, demande, interco) -> prix plus bas
- AFRY plus conservateur sur flex, plus de CCGT marginal -> prix plus haut
- Les deux valides, mais hypothèses différentes

## Utilisation Business

- **PPA**: Aurora souvent utilisé pour valorisation RES (capture rates)
- **BESS**: Business case BESS, revenue stacking
- **Investissement**: Comparer AFRY vs Aurora pour range valorisation

## Questions pour Challenger Aurora

1. BESS 8GW FR 2030: vs 1GW 2024, rythme 1.4GW/an, pipeline réel?
2. Capture rate solaire 0.70 2030: cohérent avec 50GW solaire + 8GW BESS? Ou pessimiste?
3. Negative hours 400h 2030: vs AFRY 250h, pourquoi plus? Curtailment modélisé?
4. Baseload 70€ 2030: vs forward 2027 65€, vs AFRY 80€, justifier flexibilité
5. Interco FR-DE 8GW 2030: même question que AFRY, projets?
6. Demande 600 TWh FR 2030: source?
7. Gas 32€ 2030: vs AFRY 35€, pourquoi plus bas? Offre LNG?
8. Revenue BESS: stacking assumé? Si FCR saturé, revenu baisse

## Tips Analyste

- Utiliser Aurora pour **capture rates** et **BESS**, AFRY pour **réseau** et **prix baseload**
- Faire moyenne pondérée ou range P10-P90 avec deux modèles
- Toujours challenger BESS deployment: plus BESS = plus de cannibalisation BESS aussi
- Préparer slide comparaison AFRY vs Aurora: hypothèses, prix, capture rates, BESS, risques
