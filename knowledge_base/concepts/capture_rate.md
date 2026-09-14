# Capture Rate & Capture Price - Concepts Clés Marché Électrique

## Définition

**Capture Price** = Prix moyen capté par une technologie renouvelable
```
Capture Price = Σ(prix_horaire_h * génération_h) / Σ(génération_h)
```

**Capture Rate** = Ratio vs Baseload
```
Capture Rate = Capture Price / Baseload Price
```

**Market Value Factor (MVF)** = Synonyme Capture Rate (terminologie Aurora)

**Cannibalisation Factor** = 1 - Capture Rate

## Interprétation

| Capture Rate | Signification | Exemple |
|--------------|---------------|---------|
| >1.1 | Premium, produit aux heures chères | Éolien hiver nuit |
| 0.9-1.1 | Dans norme | Éolien diversifié |
| 0.7-0.9 | Cannibalisation modérée | Solaire été |
| <0.7 | Forte cannibalisation | Solaire massif midi |

## Facteurs d'influence

1. **Corrélation production/prix**: Solaire produit midi quand prix bas si beaucoup de solaire
2. **Flexibilité système**: BESS, interco, effacement, hydro
3. **Curtailment**: Si écrêtement, capture rate baisse
4. **Localisation**: Nord vs Sud, offshore vs onshore
5. **Profil**: Solaire plus cannibalisé que éolien (facteur 0.2-0.3)

## Benchmarks Européens 2024

- FR Solaire: 0.75-0.85
- FR Éolien onshore: 0.85-0.95
- DE Solaire: 0.6-0.75 (plus de solaire)
- DE Éolien onshore: 0.8-0.9
- 2030 forecast FR solaire: 0.6-0.8 (baisse avec +RES)
- 2030 forecast FR éolien: 0.75-0.9

## Impact Business

- **PPA**: Prix PPA = Baseload * Capture Rate * (1 - discount)
- Si capture rate 0.7 vs 0.9, perte 20% revenus sur 20 ans = multi-M€
- **BESS**: Améliore capture rate de 0.1-0.2 si co-localisé
- **Hedging**: Capture rate volatil, besoin proxy hedging

## Calcul dans l'outil

Utilisez Market Analysis Engine:
```python
engine.calculate_metrics(prices, generation, technology="solar")
```

## Questions pour Challenger

- Pourquoi capture rate solaire 2030 = 0.78 vs 0.65 Aurora?
- Quelle hypothèse flexibilité (BESS, interco) explique différence?
- Curtailment inclus? Si non, capture rate surestimé
- Sensibilité: +10GW solaire = -0.05 capture rate?

## Opportunité BESS

Si capture rate <0.7:
- BESS 2h améliore valorisation de 10-15 €/MWh
- BESS 4h: 15-25 €/MWh
- Co-localisation solaire+BESS: optimisation self-consumption + arbitrage
