# Baseload, Peakload, Offpeak - Définitions Marché Électrique

## Définitions Standard Européennes

**Baseload**: Moyenne prix toutes heures de l'année (8760h)
- Référence pour contrats long-terme, PPA baseload
- FR 2024: ~65 €/MWh, DE 2024: ~78 €/MWh

**Peakload**: Moyenne Mon-Fri 8h-20h (définition EPEX Spot)
- 12h * 5 jours * 52 semaines = 3120h / an
- Reflète demande industrielle/commerciale
- Généralement +10-20% vs baseload

**Offpeak**: Reste (nuits + weekends)
- 5640h / an
- Moins cher, -10-15% vs baseload

**Peak/Offpeak Spread**: Indicateur valeur flexibilité
- Spread = Peak - Offpeak
- 2024 FR: ~20-30 €/MWh, DE: ~30-40 €/MWh
- >30€ = opportunité BESS / effacement

## Autres Produits

- **P10/P50/P90**: Percentiles distribution prix
  - P10: 10% heures en dessous
  - P50: médiane
  - P90: 90% en dessous (pics)
  - Range P90-P10 = mesure risque/volatilité

- **Volatility**: std/mean
  - <0.3: calme
  - 0.3-0.6: normal
  - >0.6: volatile (2022: >1.0)

## Utilisation Business

- **Trading**: Baseload forward Y+1, Q+1 pour hedging
- **PPA**: Pay-as-produced vs baseload, impact capture rate
- **BESS**: Spread peak/offpeak = revenu arbitrage potentiel
- **Modélisation**: AFRY/Aurora forecast baseload 2030 = 60-100 €/MWh FR

## Calcul

```python
# Market Analysis Engine
metrics = engine.calculate_metrics(prices, timestamps=timestamps)
print(metrics.baseload, metrics.peakload, metrics.offpeak)
```

## Benchmarks

| Pays | Baseload 2024 | Peakload 2024 | Spread |
|------|---------------|---------------|--------|
| FR | 65 | 78 | 25 |
| DE | 78 | 92 | 35 |
| BE | 72 | 85 | 28 |
| NL | 75 | 88 | 30 |
| ES | 55 | 65 | 18 |

## Heures Négatives

Voir concept negative_hours.md - impact sur baseload si beaucoup d'heures négatives, baseload baisse.
