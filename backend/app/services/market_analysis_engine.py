"""
Module 2: Market Analysis Engine
Calculs: Capture Price, Capture Rate, Baseload, Peakload, Negative Hours, Cannibalisation, MVF
"""
import numpy as np
import pandas as pd
from typing import List, Optional, Dict, Any, Tuple
import logging
from datetime import datetime

from ..models.schemas import MarketMetrics, MarketAnalysisResponse

logger = logging.getLogger(__name__)

class MarketAnalysisEngine:
    """
    Moteur d'analyse marché électrique européen
    Implémente les KPI standards utilisés par traders, AFRY, Aurora
    """

    def calculate_metrics(
        self,
        prices: List[float],
        generation: Optional[List[float]] = None,
        timestamps: Optional[List[datetime]] = None,
        country: str = "FR",
        technology: str = "solar"
    ) -> MarketMetrics:
        """
        Calcule tous les KPI marché à partir de prix horaires + profil génération optionnel
        """
        prices_arr = np.array(prices, dtype=float)
        n = len(prices_arr)

        if n == 0:
            raise ValueError("Empty price series")

        # Basic stats
        baseload = float(np.mean(prices_arr))
        min_price = float(np.min(prices_arr))
        max_price = float(np.max(prices_arr))
        avg_price = baseload
        std_price = float(np.std(prices_arr))
        p10 = float(np.percentile(prices_arr, 10))
        p50 = float(np.percentile(prices_arr, 50))
        p90 = float(np.percentile(prices_arr, 90))
        volatility = float(std_price / avg_price) if avg_price != 0 else 0

        # Peakload / Offpeak - European definition: Peak = Mon-Fri 8-20h
        peakload, offpeak = self._calculate_peak_offpeak(prices_arr, timestamps)

        # Negative hours
        negative_hours = int(np.sum(prices_arr < 0))
        negative_pct = round(negative_hours / n * 100, 2)
        zero_hours = int(np.sum(prices_arr == 0))

        # Capture price & rate if generation provided
        capture_price = None
        capture_rate = None
        mvf = None
        cannibalisation = None

        if generation is not None and len(generation) == n:
            gen_arr = np.array(generation, dtype=float)
            # Avoid division by zero
            total_gen = np.sum(gen_arr)
            if total_gen > 0:
                # Capture Price = sum(price * gen) / sum(gen)
                capture_price = float(np.sum(prices_arr * gen_arr) / total_gen)
                # Capture Rate = Capture Price / Baseload
                capture_rate = float(capture_price / baseload) if baseload != 0 else None
                # Market Value Factor = same as capture rate (Aurora terminology)
                mvf = capture_rate
                # Cannibalisation factor = 1 - capture_rate (how much value lost vs baseload)
                # Or defined as correlation effect
                if capture_rate is not None:
                    cannibalisation = float(1 - capture_rate)

        return MarketMetrics(
            baseload=round(baseload, 2),
            peakload=round(peakload, 2),
            offpeak=round(offpeak, 2),
            min_price=round(min_price, 2),
            max_price=round(max_price, 2),
            avg_price=round(avg_price, 2),
            std_price=round(std_price, 2),
            negative_hours=negative_hours,
            negative_hours_pct=negative_pct,
            zero_hours=zero_hours,
            capture_price=round(capture_price, 2) if capture_price is not None else None,
            capture_rate=round(capture_rate, 4) if capture_rate is not None else None,
            market_value_factor=round(mvf, 4) if mvf is not None else None,
            cannibalisation_factor=round(cannibalisation, 4) if cannibalisation is not None else None,
            p10=round(p10, 2),
            p50=round(p50, 2),
            p90=round(p90, 2),
            volatility=round(volatility, 4),
            total_hours=n
        )

    def _calculate_peak_offpeak(self, prices: np.ndarray, timestamps: Optional[List[datetime]]) -> Tuple[float, float]:
        """
        Peak: Mon-Fri 8-20h CET (European standard)
        Offpeak: rest
        If no timestamps, approximate: 8-20 = 50% of hours as peak
        """
        if timestamps and len(timestamps) == len(prices):
            peak_prices = []
            offpeak_prices = []
            for price, ts in zip(prices, timestamps):
                if isinstance(ts, str):
                    try:
                        ts = datetime.fromisoformat(ts)
                    except:
                        peak_prices.append(price)
                        continue
                # Weekday Mon=0 ... Fri=4, hour 8-19 inclusive
                is_weekday = ts.weekday() < 5
                is_peak_hour = 8 <= ts.hour < 20
                if is_weekday and is_peak_hour:
                    peak_prices.append(price)
                else:
                    offpeak_prices.append(price)
            peak_avg = float(np.mean(peak_prices)) if peak_prices else float(np.mean(prices))
            offpeak_avg = float(np.mean(offpeak_prices)) if offpeak_prices else float(np.mean(prices))
            return peak_avg, offpeak_avg
        else:
            # Fallback: assume 12h peak / 12h offpeak pattern
            # Simulate: prices higher during day (we can't know, so use mean +/- std)
            # Better: split array into day/night proxy: first 8h offpeak, next 12h peak, last 4h offpeak repeating
            peak_vals = []
            offpeak_vals = []
            for i, p in enumerate(prices):
                hour = i % 24
                if 8 <= hour < 20:
                    peak_vals.append(p)
                else:
                    offpeak_vals.append(p)
            peak_avg = float(np.mean(peak_vals)) if peak_vals else float(np.mean(prices))
            offpeak_avg = float(np.mean(offpeak_vals)) if offpeak_vals else float(np.mean(prices))
            return peak_avg, offpeak_avg

    def analyze(self, prices: List[float], generation: Optional[List[float]] = None,
                timestamps: Optional[List[datetime]] = None, country: str = "FR", technology: str = "solar") -> MarketAnalysisResponse:
        """
        Full analysis with insights
        """
        metrics = self.calculate_metrics(prices, generation, timestamps, country, technology)

        insights = []
        warnings = []

        # Insights generation (proactive agent)
        # Baseload analysis
        if metrics.baseload > 100:
            insights.append(f"🔥 Baseload élevé ({metrics.baseload} €/MWh) - contexte prix hauts, vérifier crise gaz/CO2")
        elif metrics.baseload < 20:
            insights.append(f"📉 Baseload très bas ({metrics.baseload} €/MWh) - forte pénétration renouvelable ou demande faible")

        # Negative hours
        if metrics.negative_hours > 0:
            if metrics.negative_hours_pct > 5:
                warnings.append(f"⚠️ {metrics.negative_hours} heures négatives ({metrics.negative_hours_pct}%) - cannibalisation sévère")
                insights.append(f"💡 Cannibalisation {technology}: {metrics.negative_hours_pct}% heures négatives indique saturation réseau. Opportunité BESS / flexibilité")
            else:
                insights.append(f"Heures négatives: {metrics.negative_hours} ({metrics.negative_hours_pct}%) - dans norme EU 2024")

        # Capture rate
        if metrics.capture_rate is not None:
            if metrics.capture_rate < 0.7:
                warnings.append(f"⚠️ Capture rate faible {metrics.capture_rate} pour {technology} - forte cannibalisation")
                insights.append(f"🔋 BESS opportunity: capture rate {metrics.capture_rate} suggère arbitrage solaire/wind + stockage très rentable")
            elif metrics.capture_rate > 1.1:
                insights.append(f"✅ Capture rate premium {metrics.capture_rate} - {technology} produit aux heures chères (diversification géo/technologique)")
            else:
                insights.append(f"Capture rate {technology}: {metrics.capture_rate} - dans range attendu")

            # Market Value Factor interpretation
            if metrics.market_value_factor and metrics.market_value_factor < 0.8:
                insights.append(f"📊 Market Value Factor {metrics.market_value_factor}: valeur marché dégradée, prévoir floor PPA plus bas")

        # Volatility
        if metrics.volatility > 0.8:
            warnings.append(f"Volatilité extrême {metrics.volatility} - marché instable, risque trading élevé")
            insights.append("💼 Stratégie: considérer hedging accru, BESS 2h+ pour capturer spreads")
        elif metrics.volatility < 0.2:
            insights.append("Volatilité faible - marché calme, spreads BESS limités")

        # Peak/offpeak spread
        spread = metrics.peakload - metrics.offpeak
        spread_pct = (spread / metrics.baseload * 100) if metrics.baseload else 0
        insights.append(f"Peak/Offpeak spread: {spread:.1f} €/MWh ({spread_pct:.0f}% baseload) - indicateur valeur flexibilité")
        if spread > 30:
            insights.append(f"🔋 Spread élevé opportunité BESS: {spread:.0f} €/MWh peak/offpeak")

        # P10/P90
        insights.append(f"Distribution: P10 {metrics.p10} / P50 {metrics.p50} / P90 {metrics.p90} - range {metrics.p90 - metrics.p10:.0f} €/MWh")

        # Country specific
        if country == "FR":
            insights.append("🇫🇷 FR spécifique: surveiller dispo nucléaire (65-85% normal), impact fort sur baseload")
        elif country == "DE":
            insights.append("🇩🇪 DE spécifique: marché le plus volatile EU, forte corrélation wind + interco")

        # Chart data for frontend
        prices_arr = np.array(prices)
        chart_data = {
            "price_histogram": {
                "bins": np.histogram(prices_arr, bins=50)[0].tolist(),
                "edges": np.histogram(prices_arr, bins=50)[1].tolist()
            },
            "price_series": prices[:168] if len(prices) > 168 else prices,  # Last week for chart
            "metrics": metrics.model_dump()
        }

        if generation:
            gen_arr = np.array(generation)
            # Correlation price vs generation
            corr = float(np.corrcoef(prices_arr, gen_arr)[0,1]) if len(prices_arr) > 1 else 0
            chart_data["correlation_price_gen"] = round(corr, 3)
            if corr < -0.3:
                insights.append(f"Corrélation prix/{technology} négative {corr:.2f} - cannibalisation avérée")
            chart_data["generation_series"] = generation[:168]

        return MarketAnalysisResponse(
            metrics=metrics,
            insights=insights,
            warnings=warnings,
            chart_data=chart_data
        )

    def calculate_bess_revenue(self, prices: List[float], capacity_mw: float = 10, duration_h: float = 2, efficiency: float = 0.85) -> Dict[str, Any]:
        """
        Simplified BESS arbitrage revenue estimation
        Assumes perfect foresight 1 cycle/day
        """
        prices_arr = np.array(prices)
        daily_revenues = []
        # Group by day (24h)
        for day_start in range(0, len(prices_arr), 24):
            day_prices = prices_arr[day_start:day_start+24]
            if len(day_prices) < 24:
                continue
            # Find best spread: buy low, sell high
            min_price = np.min(day_prices)
            max_price = np.max(day_prices)
            spread = max_price - min_price
            # Revenue per day = capacity * duration * spread * efficiency - degradation proxy
            revenue = capacity_mw * duration_h * spread * efficiency * 0.9  # 0.9 utilization factor
            daily_revenues.append(revenue)

        if not daily_revenues:
            return {"error": "Insufficient data"}

        avg_daily = float(np.mean(daily_revenues))
        annual = avg_daily * 365
        return {
            "capacity_mw": capacity_mw,
            "duration_h": duration_h,
            "avg_daily_revenue": round(avg_daily, 2),
            "annual_revenue": round(annual, 2),
            "annual_per_mw": round(annual / capacity_mw, 2),
            "daily_revenues_sample": [round(x, 2) for x in daily_revenues[:7]]
        }
