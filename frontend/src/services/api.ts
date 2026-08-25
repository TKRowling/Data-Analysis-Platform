const BASE = '/api';

async function unwrapError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body?.detail === 'string') return body.detail;
    // FastAPI validation errors arrive as a list of {loc, msg}.
    if (Array.isArray(body?.detail)) return body.detail.map((d: { msg: string }) => d.msg).join('; ');
  } catch {
    /* response had no JSON body */
  }
  return `Request failed (${response.status})`;
}

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, options);
  if (!response.ok) throw new Error(await unwrapError(response));
  return response.json() as Promise<T>;
}

export const postJson = <T,>(path: string, body: unknown): Promise<T> =>
  api<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

/** POST that returns a file, used for report downloads. */
export async function postForBlob(path: string, body: unknown): Promise<Blob> {
  const response = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(await unwrapError(response));
  return response.blob();
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
