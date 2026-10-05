import { useState } from 'react';
import { Icon } from './Icon';

export function RawOutputViewer({ output, title = 'Raw model output' }: { output: unknown; title?: string }) {
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);
  const text = typeof output === 'string' ? output : JSON.stringify(output, null, 2);
  async function copy() {
    try { await navigator.clipboard.writeText(text); setCopied(true); setCopyError(false); setTimeout(() => setCopied(false), 1800); }
    catch { setCopyError(true); }
  }
  return <details className="raw-viewer">
    <summary><span><Icon name="code" size={16} />{title}</span><Icon name="chevron" size={14} /></summary>
    <div className="raw-tools"><span>JSON · exact returned payload</span><button type="button" onClick={copy}><Icon name={copied ? 'check' : 'copy'} size={14} />{copied ? 'Copied' : 'Copy'}</button></div>
    {copyError && <p className="copy-error" role="status">Copy is unavailable. You can select the JSON below.</p>}
    <pre tabIndex={0}>{text ?? 'No model payload was returned.'}</pre>
  </details>;
}
