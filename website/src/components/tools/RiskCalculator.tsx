import { useState } from 'preact/hooks';
import Turnstile from 'react-turnstile';

export default function RiskCalculator() {
    const [step, setStep] = useState(1);
    const [sector, setSector] = useState(null);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [token, setToken] = useState<string | null>(null);
    const [formData, setFormData] = useState({
        has_fire_noc: false,
        has_guards: false,
        guards_psara_verified: false,
        cctv_retention_days: 0,
        vault_class: 'none',
        has_seismic_sensor: false,
        has_access_control: false,
        server_room_access_log: false
    });

    const updateField = (field, value) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };

    const handleCalculate = async () => {
        if (!token) {
            alert("Please complete the security check.");
            return;
        }
        setLoading(true);
        try {
            const response = await fetch('/api/assess-risk', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    sector, 
                    data: formData,
                    security_token: token
                })
            });
            const data = await response.json();
            setResult(data);
            setStep(4);
        } catch (error) {
            alert('Error');
        } finally {
            setLoading(false);
        }
    };

    if (step === 1) {
        return (
            <div className="p-8 bg-neutral-900 border border-neutral-800 rounded">
                <h3 className="text-xl font-bold mb-4">Select Sector</h3>
                <div className="grid grid-cols-2 gap-4">
                    {['jewellery', 'corporate', 'finance', 'industrial'].map(s => (
                        <button 
                            key={s}
                            onClick={() => { console.log('Selected:', s); setSector(s); }}
                            className={`p-4 border ${sector === s ? 'border-primary-accent bg-primary-accent/10' : 'border-neutral-700'}`}
                        >
                            {s.toUpperCase()}
                        </button>
                    ))}
                </div>
                <button 
                    disabled={!sector}
                    onClick={() => setStep(2)}
                    className="w-full mt-8 p-4 bg-primary-accent text-black font-bold disabled:opacity-50"
                >
                    NEXT
                </button>
            </div>
        )
    }

    if (step === 2) {
        return (
            <div className="p-8 bg-neutral-900 border border-neutral-800 rounded">
                <h3 className="text-xl font-bold mb-4">Universal Compliance</h3>
                <div className="mb-4">
                    <label className="block mb-2">Fire NOC?</label>
                    <button onClick={() => updateField('has_fire_noc', !formData.has_fire_noc)} className="p-2 border border-neutral-700">
                        {formData.has_fire_noc ? 'YES' : 'NO'}
                    </button>
                </div>
                <button onClick={() => setStep(3)} className="w-full mt-8 p-4 bg-primary-accent text-black font-bold">NEXT</button>
            </div>
        )
    }

    if (step === 3) {
        return (
            <div className="p-8 bg-neutral-900 border border-neutral-800 rounded">
                <h3 className="text-xl font-bold mb-4">Final Security Check</h3>
                <div className="mb-6 flex justify-center">
                    <Turnstile
                        sitekey={import.meta.env.PUBLIC_TURNSTILE_SITE_KEY}
                        onVerify={(t) => setToken(t)}
                        theme="dark"
                    />
                </div>
                <button 
                    onClick={handleCalculate} 
                    disabled={!token || loading}
                    className="w-full p-4 bg-primary-accent text-black font-bold disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {loading ? 'CALCULATING...' : 'RUN SIMULATION'}
                </button>
            </div>
        )
    }

    return (
        <div className="p-8 bg-neutral-900 border border-neutral-800 rounded">
            <h3 className="text-xl font-bold mb-4">Result: {result?.score}/100</h3>
            <pre className="text-xs text-neutral-400">{JSON.stringify(result, null, 2)}</pre>
            <button onClick={() => setStep(1)} className="mt-4 text-primary-accent underline">Restart</button>
        </div>
    )
}