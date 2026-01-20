import { useState } from 'preact/hooks';

interface CheckResult {
  label: string;
  status: 'pass' | 'warn' | 'fail';
  detail: string;
}

const resolveDns = async (name: string, type: string) => {
  const url = `https://dns.google/resolve?name=${encodeURIComponent(name)}&type=${encodeURIComponent(type)}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('DNS lookup failed');
  return res.json();
};

const normalizeDomain = (value: string) => {
  const trimmed = value.trim().toLowerCase();
  if (!trimmed) return '';
  const withoutProtocol = trimmed.replace(/^https?:\/\//, '');
  const withoutPath = withoutProtocol.split('/')[0];
  return withoutPath.split(':')[0];
};

export default function DomainRiskAssessment() {
  const [domainInput, setDomainInput] = useState('');
  const [status, setStatus] = useState<'idle' | 'loading' | 'done' | 'error'>('idle');
  const [results, setResults] = useState<CheckResult[]>([]);
  const [score, setScore] = useState<number | null>(null);
  const [message, setMessage] = useState<string>('');
  const [normalizedDomain, setNormalizedDomain] = useState<string>('');
  const [emailInput, setEmailInput] = useState<string>('');

  const runAssessment = async (event: Event) => {
    event.preventDefault();
    const domain = normalizeDomain(domainInput);
    if (!domain || !domain.includes('.')) {
      setStatus('error');
      setMessage('Enter a valid domain (example.com).');
      return;
    }

    setNormalizedDomain(domain);
    setStatus('loading');
    setMessage('Running DNS and email posture checks...');
    setResults([]);
    setScore(null);

    try {
      const [aRecord, mxRecord, txtRecord, dmarcRecord] = await Promise.all([
        resolveDns(domain, 'A'),
        resolveDns(domain, 'MX'),
        resolveDns(domain, 'TXT'),
        resolveDns(`_dmarc.${domain}`, 'TXT'),
      ]);

      const answersA = Array.isArray(aRecord.Answer) ? aRecord.Answer : [];
      const answersMx = Array.isArray(mxRecord.Answer) ? mxRecord.Answer : [];
      const answersTxt = Array.isArray(txtRecord.Answer) ? txtRecord.Answer : [];
      const answersDmarc = Array.isArray(dmarcRecord.Answer) ? dmarcRecord.Answer : [];

      const hasA = answersA.length > 0;
      const hasMx = answersMx.length > 0;
      const spfTxt = answersTxt.map((entry: any) => String(entry.data || '')).join(' ');
      const hasSpf = spfTxt.toLowerCase().includes('v=spf1');
      const dmarcTxt = answersDmarc.map((entry: any) => String(entry.data || '')).join(' ');
      const hasDmarc = dmarcTxt.toLowerCase().includes('v=dmarc1');

      const checks: CheckResult[] = [
        {
          label: 'DNS Resolution',
          status: hasA ? 'pass' : 'fail',
          detail: hasA ? 'A record found' : 'No A record detected',
        },
        {
          label: 'Mail Exchange',
          status: hasMx ? 'pass' : 'warn',
          detail: hasMx ? 'MX record present' : 'No MX record',
        },
        {
          label: 'SPF Policy',
          status: hasSpf ? 'pass' : 'warn',
          detail: hasSpf ? 'SPF record configured' : 'SPF missing',
        },
        {
          label: 'DMARC Policy',
          status: hasDmarc ? 'pass' : 'fail',
          detail: hasDmarc ? 'DMARC policy active' : 'DMARC missing',
        },
      ];

      let computed = 100;
      if (!hasA) computed -= 20;
      if (!hasMx) computed -= 20;
      if (!hasSpf) computed -= 30;
      if (!hasDmarc) computed -= 30;
      computed = Math.max(0, computed);

      setResults(checks);
      setScore(computed);
      setStatus('done');
      setMessage('Assessment complete.');
    } catch (error) {
      setStatus('error');
      setMessage('Assessment failed. Try again or use a different domain.');
    }
  };

  const riskLabel = score === null ? '—' : score >= 85 ? 'LOW' : score >= 60 ? 'MODERATE' : 'HIGH';
  const riskColor = score === null ? 'text-gray-400' : score >= 85 ? 'text-emerald-400' : score >= 60 ? 'text-yellow-300' : 'text-red-400';
  const reportBody = encodeURIComponent(
    [
      `Domain: ${normalizedDomain || domainInput || '—'}`,
      `Score: ${score ?? '—'}/100`,
      `Exposure tier: ${riskLabel}`,
      '',
      'Checks:',
      ...results.map(result => `- ${result.label}: ${result.status.toUpperCase()} (${result.detail})`),
      '',
      `Reply-to: ${emailInput || 'Not provided'}`,
    ].join('\\n')
  );

  return (
    <div class="space-y-5">
      <div>
        <h3 class="text-white font-bold text-sm">Am I Exposed?</h3>
        <p class="text-xs text-gray-500">Instant domain risk check. No data stored. DNS queries only.</p>
      </div>

      <form class="space-y-3" onSubmit={runAssessment}>
        <input
          type="text"
          value={domainInput}
          onInput={(event) => setDomainInput((event.target as HTMLInputElement).value)}
          placeholder="yourcompany.com"
          class="w-full bg-black border border-neutral-700 text-white p-3 rounded focus:border-blue-500 focus:outline-none transition-colors"
        />
        <input
          type="email"
          value={emailInput}
          onInput={(event) => setEmailInput((event.target as HTMLInputElement).value)}
          placeholder="email@company.com (for report delivery)"
          class="w-full bg-black border border-neutral-700 text-white p-3 text-sm rounded focus:border-blue-500 focus:outline-none transition-colors"
        />
        <button
          type="submit"
          class="w-full bg-blue-500 text-black font-bold py-3 px-4 rounded hover:bg-blue-400 transition-colors"
        >
          RUN DOMAIN RISK CHECK
        </button>
      </form>

      <div class="bg-neutral-900/50 border border-neutral-800 p-4 rounded space-y-4">
        <div class="flex items-center justify-between">
          <span class="text-xs uppercase tracking-widest text-gray-500">Risk Score</span>
          <span class={`text-lg font-bold ${riskColor}`}>{score ?? '--'} / 100</span>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-xs uppercase tracking-widest text-gray-500">Exposure Tier</span>
          <span class={`text-sm font-bold ${riskColor}`}>{riskLabel}</span>
        </div>
        <div class="text-xs text-gray-500">{status === 'loading' ? 'Scanning DNS records…' : message || 'Awaiting domain input.'}</div>
      </div>

      <div class="space-y-2">
        {results.map((item) => (
          <div key={item.label} class="flex items-center justify-between text-sm bg-neutral-900/50 border border-neutral-800 px-3 py-2 rounded">
            <span class="text-gray-300">{item.label}</span>
            <span class={`text-xs uppercase tracking-widest ${item.status === 'pass' ? 'text-emerald-300' : item.status === 'warn' ? 'text-yellow-300' : 'text-red-300'}`}>
              {item.status}
            </span>
          </div>
        ))}
      </div>

      <div class="bg-blue-900/20 border border-blue-800/40 p-4 rounded text-center">
        <h4 class="text-white font-bold mb-2">Need a Dark Web Scan?</h4>
        <p class="text-xs text-gray-400 mb-4">We’ll run a full exposure sweep and send results by email.</p>
        <a
          href={`mailto:consult@sps.com?subject=Domain%20Risk%20Assessment%20Report&body=${reportBody}`}
          class="inline-flex w-full justify-center bg-white text-black font-bold py-2 px-4 rounded hover:bg-gray-200 transition-colors"
        >
          EMAIL ME THE REPORT
        </a>
        <a
          href={`mailto:consult@sps.com?subject=Dark%20Web%20Scan%20Request&body=Domain:%20${encodeURIComponent(normalizedDomain || domainInput)}`}
          class="inline-flex w-full justify-center mt-3 border border-blue-300 text-blue-100 font-bold py-2 px-4 rounded hover:bg-blue-900/30 transition-colors"
        >
          REQUEST DARK WEB SCAN
        </a>
      </div>
    </div>
  );
}
