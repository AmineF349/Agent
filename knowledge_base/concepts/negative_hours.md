# Heures Négatives (Negative Hours) - Marché Électrique

## Définition

Heure où prix day-ahead <0 €/MWh. Producteur paie pour produire.

## Causes

1. **Surproduction renouvelable**: Vent + soleil fort, demande faible (weekend, printemps)
2. **Inflexibilité**: Nucléaire, lignite ne peuvent pas s'arrêter rapidement
3. **Subventions**: RES avec CfD ou FIT continuent à produire même prix négatif (tant que prix > -subvention)
4. **Interco saturées**: Impossible d'exporter surplus

## Statistiques Européennes

| Pays | 2023 Heures Négatives | Tendance |
|------|----------------------|----------|
| DE | ~300h | Hausse forte |
| FR | ~150h | Hausse |
| BE | ~100h | Hausse |
| NL | ~250h | Hausse |
| ES | ~50h | Modéré |

2024 YTD: DE déjà >200h mi-année, record attendu.

Forecast 2030:
- FR: 100-800h selon scénario RES + flexibilité
- DE: 200-1500h
- Si BESS massif: réduit de 30-50%

## Impact

- **Capture Rate**: Dégrade capture rate solaire/éolien (produit quand prix négatif)
- **Revenus RES**: Si pas de clause floor, perte directe
- **Curtailment**: Alternative à prix négatif, mais perte énergie
- **BESS**: Opportunité - charge à prix négatif, décharge plus tard

## Modélisation

AFRY/Aurora:
- Certains modèles autorisent prix négatifs illimités
- D'autres modélisent curtailment à partir de -X €/MWh
- Vérifier hypothèse: impact majeur sur capture rate

## Clauses PPA

- **Floor**: Prix minimum 0 €/MWh, protect producteur
- **Cap**: Prix max, protect acheteur
- **Curtailment**: Qui supporte risque écrêtement?
- **Negative hours**: Exclusion ou partage?

## Calcul

```python
negative_hours = sum(1 for p in prices if p < 0)
negative_pct = negative_hours / len(prices) * 100
```

## Opportunité Business

- **BESS**: 
  - Charge pendant heures négatives (revenu négatif = on vous paie pour charger!)
  - Décharge peak
  - Si 300h négatives/an à -10€ moyen, + 3k€/MW/an juste sur négatives

- **Flexibilité demande**:
  - Electrolyseur H2: produit H2 quand prix négatif
  - Chauffage: ballon eau chaude
  - Industriel: déplacement conso

- **Trading**:
  - Stratégie: acheter heures négatives, vendre peak
  - Mais risque: heures négatives imprévisibles

## Questions Challenge

- Scénario prévoit 500h négatives en 2030: cohérent avec capture rate solaire 0.8?
- Si 500h négatives, BESS 20GW suffit ou besoin 40GW?
- Modèle inclut curtailment ou prix négatifs illimités?
- Impact sur business case PPA si floor à 0 vs pas de floor?

## Réglementation

- EU: Discussion sur suppression subventions pendant heures négatives (RED III)
- FR: CRE envisage arrêt soutien si >X heures négatives consécutives
- Impact: RES s'arrêterait plus souvent, moins d'heures négatives mais plus de curtailment
