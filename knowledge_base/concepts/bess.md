# BESS (Battery Energy Storage System) - Stockage par Batteries

## Définition

Système stockage électrochimique, généralement Li-ion, 1-4h duration.

## Caractéristiques

- **Capacité**: MW (puissance) et MWh (énergie) - ex: 10MW/20MWh = 2h
- **Duration**: 1h, 2h, 4h (standard), 8h+ (long duration émergent)
- **Efficacité**: 85-90% round-trip
- **Cycles**: 1-2 cycles/jour, 300-500 cycles/an
- **Durée vie**: 10-15 ans, dégradation 2-3%/an
- **CAPEX**: 2024 ~ 300-500 €/kWh (2h system), baisse 10%/an

## Revenus (Revenue Stacking)

1. **Arbitrage**: Acheter bas, vendre haut (peak/offpeak spread)
   - FR 2024: 150-250 k€/MW/an pour 2h
   - DE 2024: 200-350 k€/MW/an (plus volatile)

2. **FCR (Frequency Containment Reserve)**: Réglage fréquence primaire
   - FR: ~20-30 €/MW/h, mais marché saturé
   - Besoin: réponse <1s, BESS idéal

3. **aFRR (Automatic Frequency Restoration Reserve)**: Secondaire
   - Plus rémunérateur, mais plus complexe

4. **Capacité (Capacity Market)**: Rémunération disponibilité
   - FR: ~30k€/MW/an, GB: ~60k€/MW/an

5. **NEBEF / Effacement**: Valorisation flexibilité

**Total stacking**: 100-300 k€/MW/an selon pays et duration

## Business Case FR 2024

- CAPEX 10MW/2h: ~6-8 M€
- Revenus: 200 k€/MW/an *10MW = 2 M€/an
- OPEX: 2% CAPEX = 120k€/an
- Payback: 4-6 ans
- IRR: 10-15% (avec stacking)

Si seulement arbitrage: IRR 6-8%, besoin FCR/capacité pour rentabilité.

## Impact sur Marché

- **Negative hours**: BESS charge pendant surplus RES, réduit heures négatives
  - 10GW BESS FR 2030 = -30% heures négatives (estimation AFRY)

- **Capture Rate**: Améliore capture rate RES si co-localisé
  - Solaire + BESS 2h: +0.1-0.15 capture rate

- **Volatilité**: Réduit volatilité et spreads si massif déploiement
  - Risque cannibalisation BESS: si 20GW BESS, spreads compressent

- **Prix**: Baisse prix peak (offre flexibilité), hausse prix offpeak (demande charge)

## Pipeline FR

- 2024: ~1 GW installé
- 2030: 3-8 GW selon RTE/AFRY (scénario central 5GW)
- 2035: 10-20 GW
- Projets: TotalEnergies, Engie, EDF, indépendants

## Modélisation AFRY/Aurora

- AFRY: Modélise BESS comme flexibilité avec optimisation
- Aurora: Détaille revenue stacking
- Vérifier hypothèses: durée, efficacité, CAPEX, cycles

## Questions Challenge

- Scénario prévoit 20GW BESS FR 2030: réaliste vs pipeline 1GW 2024? Rythme 2GW/an?
- Quel revenue stacking assumé? Si seulement arbitrage, business case tient?
- Impact BESS sur capture rate solaire: modélisé?
- Si BESS massif, spreads compressent: boucle rétroaction modélisée?

## Co-localisation

- **Solaire + BESS**: Optimise autoconsommation, lisse profil, améliore PPA
- **Éolien + BESS**: Moins courant, mais opportunité
- **Avantage**: Partage raccordement, réduit coûts

## Réglementation

- EU: Accélération autorisations stockage (RED III)
- FR: PPE prévoit soutien, mais pas de mécanisme dédié encore
- Capacity market: BESS éligible, mais dé-rating factor (ex: 2h = 50% de 4h)

## Calcul Rapide dans Outil

```python
# Market Analysis Engine
bess_revenue = engine.calculate_bess_revenue(prices, capacity_mw=10, duration_h=2)
print(bess_revenue["annual_revenue"])
```
