"""
Module 3: Scenario Challenger
Challenge AFRY, Aurora, scénarios internes
Détecte hypothèses inhabituelles, écarts historiques, incohérences économiques
"""
from typing import List, Dict, Any, Optional
import logging
from ..models.schemas import ScenarioInput, ScenarioAssumption, ScenarioIssue, ScenarioChallengerResponse
from ..models.domain import BENCHMARKS, AFRY_RANGES, AURORA_RANGES

logger = logging.getLogger(__name__)

class ScenarioChallenger:
    """
    Service de challenge de scénarios long-terme
    Utilisé pour revue AFRY BID3, Aurora, scénarios internes TotalEnergies
    """

    def __init__(self):
        self.benchmarks = BENCHMARKS
        self.afry_ranges = AFRY_RANGES
        self.aurora_ranges = AURORA_RANGES

    def challenge(self, scenario: ScenarioInput) -> ScenarioChallengerResponse:
        issues: List[ScenarioIssue] = []
        country = scenario.country.upper()
        horizon = scenario.horizon

        # Build dict for easy lookup
        assum_dict = {a.name.lower(): a for a in scenario.assumptions}

        # 1. Check gas price
        gas = assum_dict.get("gas_price") or assum_dict.get("gas") or assum_dict.get("ttf")
        if gas:
            issues.extend(self._check_gas_price(gas, country, horizon, scenario.model_type))

        # 2. Check CO2
        co2 = assum_dict.get("co2_price") or assum_dict.get("co2") or assum_dict.get("eua")
        if co2:
            issues.extend(self._check_co2_price(co2, country, horizon, scenario.model_type))

        # 3. Check demand
        demand = assum_dict.get("demand") or assum_dict.get("load") or assum_dict.get("consumption")
        if demand:
            issues.extend(self._check_demand(demand, country, horizon))

        # 4. Check RES capacities
        for key in ["solar_capacity", "solar", "pv"]:
            if key in assum_dict:
                issues.extend(self._check_res_capacity(assum_dict[key], country, horizon, "solar"))
        for key in ["wind_onshore_capacity", "wind_onshore", "onshore"]:
            if key in assum_dict:
                issues.extend(self._check_res_capacity(assum_dict[key], country, horizon, "wind_onshore"))
        for key in ["wind_offshore_capacity", "wind_offshore", "offshore"]:
            if key in assum_dict:
                issues.extend(self._check_res_capacity(assum_dict[key], country, horizon, "wind_offshore"))

        # 5. Check nuclear
        nuc = assum_dict.get("nuclear_availability") or assum_dict.get("nuclear")
        if nuc:
            issues.extend(self._check_nuclear(nuc, country))

        # 6. Check capture rates (Aurora specific)
        for key in ["solar_capture_rate", "capture_rate_solar", "solar_cr"]:
            if key in assum_dict:
                issues.extend(self._check_capture_rate(assum_dict[key], "solar", horizon))
        for key in ["wind_capture_rate", "capture_rate_wind", "wind_cr"]:
            if key in assum_dict:
                issues.extend(self._check_capture_rate(assum_dict[key], "wind", horizon))

        # 7. Check negative hours
        neg = assum_dict.get("negative_hours") or assum_dict.get("neg_hours")
        if neg:
            issues.extend(self._check_negative_hours(neg, horizon))

        # 8. Economic consistency checks
        issues.extend(self._check_economic_consistency(assum_dict, country, horizon))

        # 9. Model-specific checks
        if scenario.model_type == "AFRY":
            issues.extend(self._check_afry_specific(assum_dict, country, horizon))
        elif scenario.model_type == "Aurora":
            issues.extend(self._check_aurora_specific(assum_dict, country, horizon))

        # Calculate overall score
        score = self._calculate_score(issues)

        # Peer comparison
        peer = self._peer_comparison(assum_dict, country, horizon, scenario.model_type)

        # Risk & opportunities
        risks = self._generate_risks_opportunities(issues, scenario)

        # Summary
        critical = sum(1 for i in issues if i.severity == "critical")
        warning = sum(1 for i in issues if i.severity == "warning")
        summary = f"Scénario {scenario.scenario_name} ({scenario.model_type}) - Score {score}/100 | {len(issues)} points ({critical} critical, {warning} warning) | Horizon {horizon} {country}"
        if critical > 0:
            summary += " 🚨 Revue approfondie recommandée"
        elif warning > 3:
            summary += " ⚠️ Hypothèses à challenger"
        else:
            summary += " ✅ Scénario cohérent"

        return ScenarioChallengerResponse(
            scenario_name=scenario.scenario_name,
            model_type=scenario.model_type,
            overall_score=score,
            issues=issues,
            summary=summary,
            peer_comparison=peer,
            risk_opportunities=risks
        )

    def _check_gas_price(self, assumption: ScenarioAssumption, country: str, horizon: int, model_type: str) -> List[ScenarioIssue]:
        issues = []
        val = assumption.value
        # Ranges widen with horizon
        if horizon <= 2030:
            min_val, max_val, typical = 20, 60, 35
        elif horizon <= 2040:
            min_val, max_val, typical = 18, 55, 32
        else:
            min_val, max_val, typical = 15, 50, 30

        if val < min_val:
            issues.append(ScenarioIssue(
                category="unusual_hypothesis",
                severity="warning" if val > min_val*0.7 else "critical",
                assumption=assumption.name,
                message=f"Gas price {val} {assumption.unit} très bas vs historique ({typical} typique). Implique abondance LNG / faible demande Asie.",
                benchmark=f"Range {horizon}: {min_val}-{max_val} EUR/MWh",
                recommendation="Vérifier hypothèse offre LNG US/Qatar + demande industrielle EU"
            ))
        if val > max_val:
            issues.append(ScenarioIssue(
                category="unusual_hypothesis",
                severity="critical" if val > max_val*1.3 else "warning",
                assumption=assumption.name,
                message=f"Gas price {val} {assumption.unit} élevé - contexte crise persistante. Impact direct sur prix élec.",
                benchmark=f"Range {horizon}: {min_val}-{max_val}",
                recommendation="Challenger: scénario stress ou central? Comparer avec forward TTF"
            ))
        return issues

    def _check_co2_price(self, assumption: ScenarioAssumption, country: str, horizon: int, model_type: str) -> List[ScenarioIssue]:
        issues = []
        val = assumption.value
        if horizon <= 2030:
            min_v, max_v, typical = 60, 150, 90
        elif horizon <= 2040:
            min_v, max_v, typical = 80, 200, 130
        else:
            min_v, max_v, typical = 100, 300, 180

        if val < min_v:
            issues.append(ScenarioIssue(
                category="historical_deviation",
                severity="warning",
                assumption=assumption.name,
                message=f"CO2 {val} {assumption.unit} bas vs trajectoire EU Green Deal. Sous-estime coût marginal.",
                benchmark=f"Attendu {horizon}: {min_v}-{max_v} (typique {typical})",
                recommendation="Aligner avec EU ETS MSR, Fit-for-55"
            ))
        if val > max_v:
            issues.append(ScenarioIssue(
                category="unusual_hypothesis",
                severity="warning",
                assumption=assumption.name,
                message=f"CO2 {val} {assumption.unit} très haut - implique décarbonation agressive / rareté quotas",
                benchmark=f"Range {horizon}: {min_v}-{max_v}",
                recommendation="Vérifier cohérence avec prix élec: +10€ CO2 = +4-5€ élec si CCGT marginal"
            ))
        return issues

    def _check_demand(self, assumption: ScenarioAssumption, country: str, horizon: int) -> List[ScenarioIssue]:
        issues = []
        val = assumption.value
        # Simplified FR demand check (TWh)
        if country == "FR":
            if horizon == 2030:
                min_v, max_v = 500, 650
            elif horizon == 2040:
                min_v, max_v = 550, 750
            else:
                min_v, max_v = 600, 850
            if val < min_v:
                issues.append(ScenarioIssue(
                    category="historical_deviation",
                    severity="warning",
                    assumption=assumption.name,
                    message=f"Demande FR {val} TWh faible pour {horizon}. Implique efficacité énergétique forte / désindustrialisation",
                    benchmark=f"FR {horizon}: {min_v}-{max_v} TWh (2024: ~475 TWh)",
                    recommendation="Challenger électrification (EV, PAC, H2) vs sobriété"
                ))
            if val > max_v:
                issues.append(ScenarioIssue(
                    category="unusual_hypothesis",
                    severity="warning",
                    assumption=assumption.name,
                    message=f"Demande FR {val} TWh très haute - électrification massive",
                    benchmark=f"FR {horizon}: {min_v}-{max_v}",
                    recommendation="Vérifier cohérence réseau RTE, flexibilité"
                ))
        return issues

    def _check_res_capacity(self, assumption: ScenarioAssumption, country: str, horizon: int, tech: str) -> List[ScenarioIssue]:
        issues = []
        val = assumption.value
        # FR ranges
        if country == "FR":
            if tech == "solar":
                if horizon == 2030:
                    min_v, max_v = 30, 60
                elif horizon == 2040:
                    min_v, max_v = 50, 100
                else:
                    min_v, max_v = 70, 150
            elif tech == "wind_onshore":
                if horizon == 2030:
                    min_v, max_v = 30, 55
                else:
                    min_v, max_v = 40, 80
            else:  # offshore
                if horizon == 2030:
                    min_v, max_v = 5, 15
                else:
                    min_v, max_v = 15, 40
        else:
            min_v, max_v = 10, 200  # Generic

        if val < min_v:
            issues.append(ScenarioIssue(
                category="historical_deviation",
                severity="info",
                assumption=assumption.name,
                message=f"{tech} {val} GW sous trajectoire PPE / EU targets",
                benchmark=f"{country} {horizon} {tech}: {min_v}-{max_v} GW",
                recommendation="Vérifier si scénario conservateur ou retard autorisations"
            ))
        if val > max_v:
            issues.append(ScenarioIssue(
                category="unusual_hypothesis",
                severity="warning",
                assumption=assumption.name,
                message=f"{tech} {val} GW ambitieux - implique accélération forte + acceptabilité",
                benchmark=f"{country} {horizon} {tech}: {min_v}-{max_v} GW",
                recommendation="Challenger rythme historique + grid constraints, cannibalisation"
            ))
        return issues

    def _check_nuclear(self, assumption: ScenarioAssumption, country: str) -> List[ScenarioIssue]:
        issues = []
        val = assumption.value
        # Availability factor 0-1
        if val < 0.6:
            issues.append(ScenarioIssue(
                category="unusual_hypothesis",
                severity="critical" if country == "FR" else "warning",
                assumption=assumption.name,
                message=f"Dispo nucléaire {val*100:.0f}% très basse - impact majeur prix FR",
                benchmark="FR historique: 70-80% (65% en 2022 crise)",
                recommendation="Si FR, vérifier plan maintenance EDF, corrosion, EPR"
            ))
        if val > 0.9:
            issues.append(ScenarioIssue(
                category="unusual_hypothesis",
                severity="warning",
                assumption=assumption.name,
                message=f"Dispo nucléaire {val*100:.0f}% optimiste - jamais atteint historiquement",
                benchmark="Max FR: ~85%",
                recommendation="Prendre marge pour aléas"
            ))
        return issues

    def _check_capture_rate(self, assumption: ScenarioAssumption, tech: str, horizon: int) -> List[ScenarioIssue]:
        issues = []
        val = assumption.value
        if tech == "solar":
            min_v, max_v = 0.6, 0.95
            if horizon >= 2040:
                min_v, max_v = 0.4, 0.8
        else:
            min_v, max_v = 0.75, 1.05
            if horizon >= 2040:
                min_v, max_v = 0.6, 0.9

        if val < min_v:
            issues.append(ScenarioIssue(
                category="economic_inconsistency",
                severity="warning",
                assumption=assumption.name,
                message=f"Capture rate {tech} {val} très bas - cannibalisation extrême, modèle prévoit saturation",
                benchmark=f"{tech} {horizon}: {min_v}-{max_v}",
                recommendation="Opportunité BESS, mais vérifier si PPA bancable à ce niveau"
            ))
        if val > max_v:
            issues.append(ScenarioIssue(
                category="unusual_hypothesis",
                severity="warning",
                assumption=assumption.name,
                message=f"Capture rate {tech} {val} élevé - implique peu de cannibalisation / flexibilité forte",
                benchmark=f"{tech} {horizon}: {min_v}-{max_v}",
                recommendation="Vérifier hypothèses flexibilité, interco, BESS dans modèle"
            ))
        return issues

    def _check_negative_hours(self, assumption: ScenarioAssumption, horizon: int) -> List[ScenarioIssue]:
        issues = []
        val = assumption.value
        if horizon <= 2030:
            min_v, max_v = 50, 800
        else:
            min_v, max_v = 200, 2000

        if val > max_v:
            issues.append(ScenarioIssue(
                category="unusual_hypothesis",
                severity="warning",
                assumption=assumption.name,
                message=f"Heures négatives {val} très haut - marché saturé renouvelable, prix captés dégradés",
                benchmark=f"{horizon}: {min_v}-{max_v} heures",
                recommendation="Challenge cohérence avec capture rate + BESS deployment"
            ))
        return issues

    def _check_economic_consistency(self, assum_dict: Dict[str, ScenarioAssumption], country: str, horizon: int) -> List[ScenarioIssue]:
        issues = []
        # Gas + CO2 consistency -> electricity price proxy
        gas = assum_dict.get("gas_price")
        co2 = assum_dict.get("co2_price")
        if gas and co2:
            # Simplified CCGT marginal cost: gas + 0.4*CO2 / efficiency
            # Efficiency ~55%
            elec_proxy = gas.value / 0.55 + co2.value * 0.35 / 0.55
            if elec_proxy > 150 and horizon <= 2030:
                issues.append(ScenarioIssue(
                    category="economic_inconsistency",
                    severity="info",
                    assumption="gas+co2",
                    message=f"Coût marginal CCGT implicite {elec_proxy:.0f} €/MWh élevé (gas {gas.value} + CO2 {co2.value})",
                    benchmark="Baseload 2030 attendu 60-100 €/MWh",
                    recommendation="Vérifier si charbon/nucléaire/RES devient infra-marginal et baisse prix"
                ))

        # RES capacity vs capture rate
        solar_cap = assum_dict.get("solar_capacity")
        solar_cr = assum_dict.get("solar_capture_rate")
        if solar_cap and solar_cr:
            if solar_cap.value > 50 and solar_cr.value > 0.85:
                issues.append(ScenarioIssue(
                    category="economic_inconsistency",
                    severity="warning",
                    assumption="solar capacity vs capture rate",
                    message=f"Incohérence: solar {solar_cap.value} GW élevé mais capture rate {solar_cr.value} haut - devrait cannibaliser",
                    benchmark="Plus de capacité -> plus de cannibalisation",
                    recommendation="Vérifier modèle: flexibilité, export, curtailment inclus?"
                ))

        return issues

    def _check_afry_specific(self, assum_dict: Dict[str, ScenarioAssumption], country: str, horizon: int) -> List[ScenarioIssue]:
        issues = []
        # AFRY BID3 specifics: check interconnector assumptions etc.
        # Placeholder for deeper AFRY knowledge
        return issues

    def _check_aurora_specific(self, assum_dict: Dict[str, ScenarioAssumption], country: str, horizon: int) -> List[ScenarioIssue]:
        issues = []
        return issues

    def _calculate_score(self, issues: List[ScenarioIssue]) -> float:
        penalty = 0
        for iss in issues:
            if iss.severity == "critical":
                penalty += 20
            elif iss.severity == "warning":
                penalty += 8
            else:
                penalty += 2
        return max(0, 100 - penalty)

    def _peer_comparison(self, assum_dict: Dict[str, ScenarioAssumption], country: str, horizon: int, model_type: str) -> Dict[str, Any]:
        # Compare to AFRY/Aurora typical ranges
        comparison = {}
        for name, assump in assum_dict.items():
            if "gas" in name:
                comparison[name] = {
                    "value": assump.value,
                    "AFRY_range": self.afry_ranges.get("gas_price_2030", (25,55)),
                    "Aurora_range": self.aurora_ranges.get("gas_price_2030", (22,50)),
                    "vs_AFRY": "within" if self.afry_ranges["gas_price_2030"][0] <= assump.value <= self.afry_ranges["gas_price_2030"][1] else "outside"
                }
            if "co2" in name:
                comparison[name] = {
                    "value": assump.value,
                    "AFRY_range": self.afry_ranges.get("co2_price_2030", (90,180)),
                    "Aurora_range": self.aurora_ranges.get("co2_price_2030", (80,160)),
                }
        return comparison

    def _generate_risks_opportunities(self, issues: List[ScenarioIssue], scenario: ScenarioInput) -> List[str]:
        ro = []
        # Based on issues, generate business insights
        has_low_capture = any("capture" in i.assumption.lower() and i.severity in ["warning","critical"] for i in issues)
        if has_low_capture:
            ro.append("🔋 Opportunité BESS: capture rate bas indique forte valeur stockage - modéliser BESS 2h/4h")

        has_high_gas = any("gas" in i.assumption.lower() and "élevé" in i.message for i in issues)
        if has_high_gas:
            ro.append("⛽ Risque: gas haut -> avantage compétitif PPA renouvelable, accélérer contracting")

        has_high_co2 = any("co2" in i.assumption.lower() and "haut" in i.message.lower() for i in issues)
        if has_high_co2:
            ro.append("🌿 Opportunité: CO2 haut valorise nucléaire + renouvelable vs thermique")

        has_neg_hours = any("negative" in i.assumption.lower() for i in issues)
        if has_neg_hours:
            ro.append("📉 Risque cannibalisation: prévoir clauses floor + cap dans PPA, valoriser flexibilité")

        ro.append("💼 Action: préparer Q&A pour COMEX avec 3 scénarios sensibilité (gas +/-20%, CO2 +/-30%)")
        ro.append("📊 Next: lancer run sensibilité modèle avec hypothèses challengées")
        return ro
