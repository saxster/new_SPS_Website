import { useState } from 'preact/hooks';
import { useSectorPreference, type Sector } from '../../hooks/useSectorPreference';
import './RiskCalculator.css';

interface RiskAssessment {
    score: number;
    risk_level: string;
    critical_failures: string[];
    compliance_gaps: string[];
    recommendations: string[];
}

interface FormData {
    has_fire_noc: boolean;
    has_guards: boolean;
    guards_psara_verified: boolean;
    cctv_retention_days: number;
    vault_class: string;
    has_seismic_sensor: boolean;
    has_access_control: boolean;
    server_room_access_log: boolean;
}

const SECTORS: { id: Sector; label: string; icon: string }[] = [
    { id: 'jewellery', label: 'Jewellery', icon: '💎' },
    { id: 'corporate', label: 'Corporate', icon: '🏢' },
    { id: 'finance', label: 'Finance / NBFC', icon: '🏦' },
    { id: 'it_park', label: 'IT Park', icon: '💻' },
    { id: 'industrial', label: 'Industrial', icon: '🏭' },
    { id: 'residential', label: 'Residential', icon: '🏡' },
];

export default function RiskCalculator() {
    const { setPreference } = useSectorPreference();
    const [step, setStep] = useState(1);
    const [sector, setSector] = useState<Sector | null>(null);

    // ... inside component ...

    const handleSectorSelect = (sId: Sector) => {
        setSector(sId);
        setPreference(sId); // Save preference
    };

    const renderStep1 = () => (
        <div class="step-container fade-in">
            <h3 class="step-title">Select Operational Sector</h3>
            <div class="grid grid-cols-2 gap-4">
                {SECTORS.map(s => (
                    <button
                        key={s.id}
                        class={`sector-btn ${sector === s.id ? 'active' : ''}`}
                        onClick={() => handleSectorSelect(s.id)}
                    >
                        <span class="text-2xl mr-2">{s.icon}</span>
                        {s.label}
                    </button>
                ))}
            </div>
            <button
                class="brutalist-button brutalist-button--primary w-full mt-8"
                disabled={!sector}
                onClick={() => setStep(2)}
            >
                NEXT: COMPLIANCE CHECK →
            </button>
        </div>
    );

    const renderStep2 = () => (
        <div class="step-container fade-in">
            <h3 class="step-title">Universal Compliance (NBC/PSARA)</h3>
            
            <div class="form-group">
                <label>Do you have a valid Fire NOC (NBC 2016)?</label>
                <div class="toggle-group">
                    <button class={formData.has_fire_noc ? 'active' : ''} onClick={() => updateField('has_fire_noc', true)}>YES</button>
                    <button class={!formData.has_fire_noc ? 'active' : ''} onClick={() => updateField('has_fire_noc', false)}>NO</button>
                </div>
            </div>

            <div class="form-group">
                <label>Do you employ Private Security Guards?</label>
                <div class="toggle-group">
                    <button class={formData.has_guards ? 'active' : ''} onClick={() => updateField('has_guards', true)}>YES</button>
                    <button class={!formData.has_guards ? 'active' : ''} onClick={() => updateField('has_guards', false)}>NO</button>
                </div>
            </div>

            {formData.has_guards && (
                <div class="form-group sub-group">
                    <label>Is the Agency PSARA Licensed & Guards Verified?</label>
                    <div class="toggle-group">
                        <button class={formData.guards_psara_verified ? 'active' : ''} onClick={() => updateField('guards_psara_verified', true)}>YES</button>
                        <button class={!formData.guards_psara_verified ? 'active' : ''} onClick={() => updateField('guards_psara_verified', false)}>NO</button>
                    </div>
                </div>
            )}

            <div class="form-group">
                <label>CCTV Retention Period (Days)</label>
                <input 
                    type="number" 
                    value={formData.cctv_retention_days} 
                    onInput={(e) => updateField('cctv_retention_days', parseInt(e.currentTarget.value) || 0)}
                    class="input-number"
                />
            </div>

            <button class="brutalist-button brutalist-button--primary w-full mt-8" onClick={() => setStep(3)}>
                NEXT: SECTOR SPECIFICS →
            </button>
        </div>
    );

    const renderStep3 = () => {
        const isHighRisk = sector === 'jewellery' || sector === 'finance';
        const isCorporate = sector === 'corporate' || sector === 'it_park';

        if (!isHighRisk && !isCorporate) {
            // Skip step 3 for others for now, or add generic
             return (
                 <div class="step-container fade-in">
                     <h3 class="step-title">Finalizing Assessment</h3>
                     <p class="text-neutral-400 mb-8">Ready to run simulation for {SECTORS.find(s => s.id === sector)?.label}.</p>
                     <button class="brutalist-button brutalist-button--primary w-full" onClick={handleCalculate} disabled={loading}>
                        {loading ? 'CALCULATING...' : 'RUN SIMULATION'}
                    </button>
                 </div>
             )
        }

        return (
            <div class="step-container fade-in">
                <h3 class="step-title">Sector Specific Protocols</h3>

                {isHighRisk && (
                    <>
                        <div class="form-group">
                            <label>Strong Room / Vault Class (IS 1550)</label>
                            <select 
                                value={formData.vault_class} 
                                onChange={(e) => updateField('vault_class', e.currentTarget.value)}
                                class="input-select"
                            >
                                <option value="none">None / Non-Standard</option>
                                <option value="class c">Class C (Basic)</option>
                                <option value="class b">Class B (Standard)</option>
                                <option value="class a">Class A (High Security)</option>
                                <option value="class aa">Class AA (Fortified)</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Seismic / Vibration Sensors Installed?</label>
                            <div class="toggle-group">
                                <button class={formData.has_seismic_sensor ? 'active' : ''} onClick={() => updateField('has_seismic_sensor', true)}>YES</button>
                                <button class={!formData.has_seismic_sensor ? 'active' : ''} onClick={() => updateField('has_seismic_sensor', false)}>NO</button>
                            </div>
                        </div>
                    </>
                )}

                {isCorporate && (
                    <>
                         <div class="form-group">
                            <label>Access Control System (Biometric/Card)?</label>
                            <div class="toggle-group">
                                <button class={formData.has_access_control ? 'active' : ''} onClick={() => updateField('has_access_control', true)}>YES</button>
                                <button class={!formData.has_access_control ? 'active' : ''} onClick={() => updateField('has_access_control', false)}>NO</button>
                            </div>
                        </div>
                        <div class="form-group">
                            <label>Server Room Access Logs Maintained?</label>
                            <div class="toggle-group">
                                <button class={formData.server_room_access_log ? 'active' : ''} onClick={() => updateField('server_room_access_log', true)}>YES</button>
                                <button class={!formData.server_room_access_log ? 'active' : ''} onClick={() => updateField('server_room_access_log', false)}>NO</button>
                            </div>
                        </div>
                    </>
                )}

                <button class="brutalist-button brutalist-button--primary w-full mt-8" onClick={handleCalculate} disabled={loading}>
                    {loading ? 'CALCULATING...' : 'RUN SIMULATION'}
                </button>
            </div>
        );
    };

    const renderResult = () => {
        if (!result) return null;
        
        const scoreColor = result.score < 50 ? 'text-critical' : result.score < 80 ? 'text-verified' : 'text-success';
        const borderColor = result.score < 50 ? 'border-critical' : result.score < 80 ? 'border-verified' : 'border-success';

        return (
            <div class="result-container fade-in">
                <div class="score-header">
                    <div class={`score-circle ${borderColor}`}>
                        <span class={`score-value ${scoreColor}`}>{result.score}</span>
                        <span class="score-label">/100</span>
                    </div>
                    <div class="score-meta">
                        <h2 class={`risk-level ${scoreColor}`}>{result.risk_level} RISK</h2>
                        <p class="text-neutral-400 text-sm">Automated Regulatory Assessment</p>
                    </div>
                </div>

                <div class="report-section">
                    {result.critical_failures.length > 0 && (
                        <div class="alert-box critical">
                            <h4>🚨 CRITICAL FAILURES</h4>
                            <ul>
                                {result.critical_failures.map((f, i) => <li key={i}>{f}</li>)}
                            </ul>
                        </div>
                    )}
                    
                    {result.compliance_gaps.length > 0 && (
                        <div class="alert-box warning">
                            <h4>⚠️ COMPLIANCE GAPS</h4>
                            <ul>
                                {result.compliance_gaps.map((f, i) => <li key={i}>{f}</li>)}
                            </ul>
                        </div>
                    )}

                    <div class="recommendations">
                        <h4>🛡️ STRATEGIC RECOMMENDATIONS</h4>
                        <ul>
                            {result.recommendations.map((f, i) => <li key={i}>✓ {f}</li>)}
                        </ul>
                    </div>
                </div>

                <button class="brutalist-button brutalist-button--secondary w-full mt-6" onClick={() => window.location.reload()}>
                    START NEW ASSESSMENT
                </button>
            </div>
        );
    };

    return (
        <div class="risk-calculator-wrapper">
            <div class="progress-bar">
                <div class="fill" style={{ width: `${(step / 4) * 100}%` }}></div>
            </div>
            
            {step === 1 && renderStep1()}
            {step === 2 && renderStep2()}
            {step === 3 && renderStep3()}
            {step === 4 && renderResult()}
        </div>
    );
}
