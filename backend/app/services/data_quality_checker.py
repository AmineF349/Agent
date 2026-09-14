"""
Module 1: Data Quality Checker
Vérifie unités, anomalies, valeurs manquantes, incohérences
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
import logging
from ..models.schemas import DataQualityIssue, DataQualityReport

logger = logging.getLogger(__name__)

class DataQualityChecker:
    """
    Service de contrôle qualité pour données marché électrique
    Inspiré des checks utilisés chez AFRY / Aurora
    """

    # Unités attendues par type de données
    EXPECTED_UNITS = {
        "price": ["EUR/MWh", "€/MWh", "EUR/kWh"],
        "capacity": ["MW", "GW", "kW"],
        "energy": ["MWh", "GWh", "TWh"],
        "co2": ["EUR/t", "€/t", "EUR/ton"],
        "gas": ["EUR/MWh", "EUR/therm", "EUR/MMBtu"],
        "cf": ["%", "factor", "p.u."],
    }

    # Ranges réalistes marché EU
    REALISTIC_RANGES = {
        "price": (-500, 3000),  # EUR/MWh (incl. extremes crisis)
        "capacity_factor": (0, 1.2),
        "demand": (1000, 100000),  # MW
        "gas_price": (5, 350),
        "co2_price": (0, 300),
        "capacity": (0, 200000),  # MW
    }

    def check_dataframe(self, df: pd.DataFrame, data_type: str = "price") -> DataQualityReport:
        """
        Analyse complète d'un DataFrame
        """
        issues: List[DataQualityIssue] = []
        total_rows = len(df)
        total_cols = len(df.columns)

        # 1. Check missing values
        missing_pct = {}
        for col in df.columns:
            missing = df[col].isna().sum()
            pct = (missing / total_rows * 100) if total_rows > 0 else 0
            missing_pct[col] = round(pct, 2)

            if pct > 0:
                severity = "critical" if pct > 20 else "high" if pct > 5 else "medium" if pct > 1 else "low"
                issues.append(DataQualityIssue(
                    type="missing",
                    severity=severity,
                    column=col,
                    message=f"{missing} valeurs manquantes ({pct:.1f}%) dans {col}",
                    suggestion="Vérifier source ou imputer avec interpolation / forward-fill"
                ))

        # 2. Check numeric anomalies per column
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            col_data = df[col].dropna()
            if len(col_data) == 0:
                continue

            # Outlier detection via IQR
            q1 = col_data.quantile(0.25)
            q3 = col_data.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr

            outliers = col_data[(col_data < lower) | (col_data > upper)]
            if len(outliers) > 0:
                # Only flag if >1% outliers or extreme values
                outlier_pct = len(outliers) / len(col_data) * 100
                if outlier_pct > 0.5:
                    for idx in outliers.index[:5]:  # Limit to 5 examples
                        issues.append(DataQualityIssue(
                            type="outlier",
                            severity="medium" if outlier_pct < 5 else "high",
                            column=col,
                            row_index=int(idx) if isinstance(idx, (int, np.integer)) else None,
                            value=float(outliers.loc[idx]),
                            expected=f"Range IQR: [{lower:.2f}, {upper:.2f}]",
                            message=f"Outlier détecté dans {col}: {outliers.loc[idx]} (IQR method)",
                            suggestion="Vérifier si spike réel marché ou erreur de saisie"
                        ))

            # Z-score anomalies
            mean = col_data.mean()
            std = col_data.std()
            if std > 0:
                z_scores = (col_data - mean) / std
                extreme = col_data[abs(z_scores) > 4]
                for idx in extreme.index[:3]:
                    issues.append(DataQualityIssue(
                        type="anomaly",
                        severity="high",
                        column=col,
                        row_index=int(idx) if isinstance(idx, (int, np.integer)) else None,
                        value=float(extreme.loc[idx]),
                        expected=f"Mean {mean:.2f} ± 4σ ({std:.2f})",
                        message=f"Anomalie extrême (|z|>4) dans {col}",
                        suggestion="Investiguer événement marché (crise, canicule, etc.)"
                    ))

            # Realistic range check
            if data_type in self.REALISTIC_RANGES:
                r_min, r_max = self.REALISTIC_RANGES[data_type]
                out_of_range = col_data[(col_data < r_min) | (col_data > r_max)]
                for idx in out_of_range.index[:5]:
                    issues.append(DataQualityIssue(
                        type="inconsistency",
                        severity="critical",
                        column=col,
                        row_index=int(idx) if isinstance(idx, (int, np.integer)) else None,
                        value=float(out_of_range.loc[idx]),
                        expected=f"Range réaliste: [{r_min}, {r_max}]",
                        message=f"Valeur hors range réaliste pour {data_type}",
                        suggestion="Corriger unité ou vérifier source"
                    ))

        # 3. Check temporal consistency if timestamp column exists
        time_cols = [c for c in df.columns if 'time' in c.lower() or 'date' in c.lower()]
        for col in time_cols:
            try:
                ts = pd.to_datetime(df[col], errors='coerce')
                # Check duplicates
                dup = ts.duplicated().sum()
                if dup > 0:
                    issues.append(DataQualityIssue(
                        type="inconsistency",
                        severity="high",
                        column=col,
                        message=f"{dup} timestamps dupliqués détectés",
                        suggestion="Dédupliquer et vérifier fuseau horaire"
                    ))
                # Check gaps for hourly data
                if len(ts.dropna()) > 1:
                    ts_sorted = ts.dropna().sort_values()
                    diffs = ts_sorted.diff().dropna()
                    # Expect mostly 1 hour gaps
                    median_diff = diffs.median()
                    gaps = diffs[diffs > median_diff * 1.5]
                    if len(gaps) > 0:
                        issues.append(DataQualityIssue(
                            type="missing",
                            severity="medium",
                            column=col,
                            message=f"{len(gaps)} gaps temporels détectés (médiane {median_diff})",
                            suggestion="Vérifier continuité série horaire"
                        ))
            except Exception as e:
                logger.debug(f"Time check failed for {col}: {e}")

        # 4. Check unit consistency (if unit column or metadata)
        # Heuristic: look for unit in column names or separate column
        for col in df.columns:
            col_lower = col.lower()
            for unit_type, valid_units in self.EXPECTED_UNITS.items():
                if unit_type in col_lower:
                    # If column name contains unit hint, check if values plausible
                    pass  # Could extend with explicit unit validation

        # 5. Cross-column inconsistency
        # Example: if we have price and generation, negative price with low generation is suspicious
        if 'price' in [c.lower() for c in df.columns] and any('solar' in c.lower() or 'wind' in c.lower() for c in df.columns):
            price_col = next((c for c in df.columns if 'price' in c.lower()), None)
            ren_cols = [c for c in df.columns if 'solar' in c.lower() or 'wind' in c.lower()]
            if price_col and ren_cols:
                for ren_col in ren_cols:
                    try:
                        # Negative price but low renewable -> inconsistency
                        mask = (df[price_col] < 0) & (df[ren_col] < df[ren_col].quantile(0.3))
                        suspicious = df[mask]
                        if len(suspicious) > 0:
                            issues.append(DataQualityIssue(
                                type="inconsistency",
                                severity="medium",
                                column=f"{price_col}/{ren_col}",
                                message=f"{len(suspicious)} heures à prix négatif mais {ren_col} faible - vérifier cause (nucléaire, interco?)",
                                suggestion="Investiguer : prix négatifs habituellement corrélés à fort renouvelable"
                            ))
                    except Exception as e:
                        logger.debug(f"Cross-check failed: {e}")

        # Calculate quality score
        # 100 - penalty per issue
        penalty = 0
        for iss in issues:
            if iss.severity == "critical":
                penalty += 15
            elif iss.severity == "high":
                penalty += 8
            elif iss.severity == "medium":
                penalty += 3
            else:
                penalty += 1
        quality_score = max(0, 100 - penalty)
        passed = quality_score >= 70 and not any(i.severity == "critical" for i in issues)

        # Summary
        critical = sum(1 for i in issues if i.severity == "critical")
        high = sum(1 for i in issues if i.severity == "high")
        summary = f"Qualité: {quality_score}/100 | {len(issues)} issues ({critical} critical, {high} high) | Missing avg: {np.mean(list(missing_pct.values())):.1f}%"

        return DataQualityReport(
            total_rows=total_rows,
            total_columns=total_cols,
            issues=issues,
            missing_pct=missing_pct,
            summary=summary,
            quality_score=quality_score,
            passed=passed
        )

    def check_prices(self, prices: List[float]) -> DataQualityReport:
        """Quick check for price list"""
        df = pd.DataFrame({"price": prices})
        return self.check_dataframe(df, data_type="price")

    def suggest_fixes(self, report: DataQualityReport) -> List[str]:
        """Generate actionable fix suggestions"""
        suggestions = []
        if any(i.type == "missing" for i in report.issues):
            suggestions.append("• Imputation: utiliser df.interpolate() + forward-fill pour gaps < 3h, sinon investiguer source")
        if any(i.type == "outlier" for i in report.issues):
            suggestions.append("• Outliers: vérifier si événement réel (ex: 2022 crise) ou erreur. Winsoriser à P1-P99 si besoin")
        if any(i.type == "inconsistency" for i in report.issues):
            suggestions.append("• Incohérences: cross-check avec ENTSO-E / RTE / Energy-Charts")
        if report.quality_score < 70:
            suggestions.append("• Score <70: bloquer utilisation en prod, demander revue manuelle analyste")
        suggestions.append("• Toujours logger source, version, timestamp d'extraction pour traçabilité")
        return suggestions
