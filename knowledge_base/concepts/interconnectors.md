# Interconnexions (Interconnectors) - Réseau Européen

## Définition

Liaisons électriques entre pays, permettant import/export.

## Capacités FR

| Frontière | Capacité 2024 | 2030 Prévu | Type |
|-----------|---------------|------------|------|
| FR-DE | 4 GW | 6-8 GW | AC + HVDC |
| FR-BE | 3 GW | 4 GW | AC |
| FR-ES | 2.8 GW | 5 GW (projet) | HVDC |
| FR-IT | 3 GW | 4 GW | AC + HVDC |
| FR-GB (IFA) | 2 GW | 2 GW + 1 GW (IFA2) | HVDC |
| FR-CH | 3 GW | 3.5 GW | AC |

Total FR: ~18 GW import/export, ~25-30 GW en 2030.

## Impact Prix

- **Convergence prix**: Plus d'interco = prix plus corrélés EU
- **Volatilité**: Interco réduit volatilité (mutualisation)
- **Capture Rate**: Améliore capture rate RES (export surplus)
- **Negative hours**: Réduit heures négatives (export surplus RES)

Modélisation:
- AFRY: Modélise flows optimisés, NTC (Net Transfer Capacity)
- Si interco saturée, prix divergent (ex: FR 50€, DE -10€ même heure)

## Enjeux 2030

- **Objectif EU**: 15% interconnexion (capacité interco / capacité installée)
- FR: ~15% actuellement, objectif atteint, mais besoin plus pour RES
- **Projets**: 
  - FR-ES: +2.2 GW HVDC Golfe de Gascogne (2027)
  - FR-DE: +2 GW (projet)
  - FR-GB: +1.4 GW (GridLink, FAB)

- **Risque**: Retards autorisations, oppositions locales, coûts

## Questions Challenge

- Scénario AFRY prévoit 8GW FR-DE 2030: réaliste vs 4GW 2024? Projets concrets?
- Si interco 8GW, quel impact sur baseload FR? Convergence avec DE?
- Interco saturée combien d'heures? Si >30%, besoin plus
- Modèle prend en compte loop flows (Allemagne -> Pologne -> FR)?

## Business Impact

- **PPA**: Si interco forte, prix FR corrélé DE, plus volatile
- **BESS**: Interco et BESS substituables partiellement (flexibilité)
- **Trading**: Opportunité arbitrage si spread FR-DE > coût interco

## Calcul

Dans AFRY BID3, interco modélisée comme contrainte:
```
Flow_FR_DE <= NTC_FR_DE
Prix_FR - Prix_DE <= coût congestion si saturée
```

Si non saturée: prix égaux (ou différence = pertes)
Si saturée: prix divergent, rente congestion pour TSO.

## Exemple

- 2024-04-15 12h: Fort solaire DE, prix DE -20€, FR 10€, interco DE->FR saturée 4GW, spread 30€
- Sans interco: DE -50€, FR 30€, spread 80€ -> interco réduit écart
