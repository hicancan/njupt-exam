import { useEffect, useRef, useState } from 'react';
import { SitegraphSearchManifest } from '@/types';

interface UseSearchIndexResult {
    worker: Worker | null;
    manifest: SitegraphSearchManifest | null;
    optionalUnavailable: string[];
    loading: boolean;
    error: string | null;
}

export function useSearchIndex(): UseSearchIndexResult {
    const workerRef = useRef<Worker | null>(null);
    const requestIdRef = useRef(0);
    const [workerState, setWorkerState] = useState<Worker | null>(null);
    const [manifest, setManifest] = useState<SitegraphSearchManifest | null>(null);
    const [optionalUnavailable, setOptionalUnavailable] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const worker = new Worker(new URL('../workers/searchWorker.ts', import.meta.url), { type: 'module' });
        const requestId = ++requestIdRef.current;
        workerRef.current = worker;

        worker.onmessage = (event: MessageEvent) => {
            const message = event.data as { type?: string; requestId?: number; manifest?: SitegraphSearchManifest; message?: string };
            if (message.requestId !== requestId) return;
            if (message.type === 'ready' && message.manifest) {
                setManifest(message.manifest);
                setWorkerState(worker);
                setOptionalUnavailable([]);
                setError(null);
                setLoading(false);
            } else if (message.type === 'error') {
                setManifest(null);
                setWorkerState(null);
                setOptionalUnavailable([]);
                setError(message.message || '无法加载 JWC sitegraph 搜索索引 Worker');
                setLoading(false);
            }
        };
        worker.onerror = event => {
            setManifest(null);
            setWorkerState(null);
            setOptionalUnavailable([]);
            setError(event.message || 'JWC sitegraph 搜索 Worker 启动失败');
            setLoading(false);
        };
        worker.postMessage({ type: 'init', requestId });

        return () => {
            worker.terminate();
            if (workerRef.current === worker) {
                workerRef.current = null;
                setWorkerState(null);
            }
        };
    }, []);

    return { worker: workerState, manifest, optionalUnavailable, loading, error };
}
