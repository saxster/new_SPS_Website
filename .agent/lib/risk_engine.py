from typing import List, Dict, Optional
from pydantic import BaseModel

class RiskAssessment(BaseModel):
    score: int
    risk_level: str  # Critical, High, Moderate, Low
    critical_failures: List[str]
    compliance_gaps: List[str]
    recommendations: List[str]

class RiskEngine:
    """
    SPS 'Deep' Risk Calculation Engine.
    Evaluates physical security posture against Indian Regulations and Best Practices.
    
    Standards Referenced:
    - PSARA 2005 (Private Security Agencies Regulation Act)
    - NBC 2016 (National Building Code - Part 4: Fire)
    - IS 1550 (Indian Standard for Strong Rooms/Vaults)
    - RBI Guidelines for Banks/NBFCs (Applied as best practice for high-value)
    """
    
    def assess(self, sector: str, data: Dict) -> RiskAssessment:
        sector = sector.lower()
        
        # Base Score starts at 100, we deduct for failures
        score = 100
        critical_failures = []
        compliance_gaps = []
        recommendations = []
        
        # --- UNIVERSAL CHECKS (All Sectors) ---
        
        # 1. Fire Safety (NBC 2016)
        if not data.get("has_fire_noc", False):
            score -= 25
            critical_failures.append("Missing Fire NOC (NBC 2016 Violation). Illegal to operate.")
            recommendations.append("Apply for Fire NOC immediately. Premises are currently non-compliant with National Building Code.")
        
        # 2. Guarding (PSARA 2005)
        if data.get("has_guards", False):
            if not data.get("guards_psara_verified", False):
                score -= 15
                critical_failures.append("Security Agency not PSARA Licensed (PSARA Act Section 4 Violation).")
                recommendations.append("Terminate current agency. Hire only PSARA-licensed agencies to avoid legal liability.")
        
        # 3. CCTV Storage (Forensics)
        retention = int(data.get("cctv_retention_days", 0))
        if retention < 30:
            score -= 10
            compliance_gaps.append(f"CCTV Retention ({retention} days) is below standard (30 days).")
            recommendations.append("Upgrade storage to minimum 30 days (90 days recommended for high-risk areas).")

        # --- SECTOR SPECIFIC CHECKS ---
        
        if sector == "jewellery" or sector == "finance":
            # High Risk Logic
            score, crit, gaps, recs = self._assess_high_risk(data, score)
            critical_failures.extend(crit)
            compliance_gaps.extend(gaps)
            recommendations.extend(recs)
            
        elif sector == "corporate" or sector == "it_park":
            # Medium Risk Logic
            score, crit, gaps, recs = self._assess_corporate(data, score)
            critical_failures.extend(crit)
            compliance_gaps.extend(gaps)
            recommendations.extend(recs)
            
        # --- SCORING & OUTPUT ---
        score = max(0, score)
        
        if score < 50:
            risk_level = "CRITICAL"
        elif score < 70:
            risk_level = "HIGH"
        elif score < 90:
            risk_level = "MODERATE"
        else:
            risk_level = "OPTIMIZED"
            
        return RiskAssessment(
            score=score,
            risk_level=risk_level,
            critical_failures=critical_failures,
            compliance_gaps=compliance_gaps,
            recommendations=recommendations
        )

    def _assess_high_risk(self, data, current_score):
        crit = []
        gaps = []
        recs = []
        
        # 1. Strong Room / Vault (IS 1550)
        vault_class = data.get("vault_class", "none").lower()
        if vault_class == "none":
            current_score -= 40
            crit.append("No Classified Strong Room. Assets are uninsurable.")
            recs.append("Construct Strong Room compliant with IS 1550 (Class B or C recommended).")
        elif vault_class not in ["class b", "class c", "class a", "class aa"]:
            current_score -= 20
            gaps.append("Vault is not BIS Rated. Insurance claims may be rejected.")
            
        # 2. Intrusion Alarm
        if not data.get("has_seismic_sensor", False):
            current_score -= 10
            gaps.append("Missing Seismic/Vibration Sensors on Vault.")
            recs.append("Install vibration sensors linked to central CMS.")
            
        return current_score, crit, gaps, recs

    def _assess_corporate(self, data, current_score):
        crit = []
        gaps = []
        recs = []
        
        # 1. Access Control
        if not data.get("has_access_control", False):
            current_score -= 10
            gaps.append("Unrestricted Entry/Exit points.")
            recs.append("Implement Biometric or Card-based Access Control System.")
            
        # 2. Data Security (Physical)
        if not data.get("server_room_access_log", False):
            current_score -= 15
            crit.append("Server Room Access Unlogged (ISO 27001 Physical Security Violation).")
            recs.append("Implement strict logbook/electronic logging for Server Room entry.")
            
        return current_score, crit, gaps, recs

risk_engine = RiskEngine()
