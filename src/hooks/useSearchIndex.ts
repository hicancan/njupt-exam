import { useEffect, useState } from 'react';
import { APP_CONFIG } from '@/constants';
import { SitegraphIndexBundle, SitegraphSearchManifest } from '@/types';
import {
    parseSitegraphAttachmentIndex,
    parseSitegraphDocMeta,
    parseSitegraphExternalIndex,
    parseSitegraphInvertedIndex,
    parseSitegraphManifest
} from '@/utils/searchIndex';
import { fetchJson } from '@/utils/fetch';

interface UseSearchIndexResult {
    bundle: SitegraphIndexBundle | null;
    manifest: SitegraphSearchManifest | null;
    optionalUnavailable: string[];
    loading: boolean;
    error: string | null;
}

export function useSearchIndex(): UseSearchIndexResult {
    const [bundle, setBundle] = useState<SitegraphIndexBundle | null>(null);
    const [manifest, setManifest] = useState<SitegraphSearchManifest | null>(null);
    const [optionalUnavailable, setOptionalUnavailable] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const controller = new AbortController();

        const load = async () => {
            const [
                manifestPayload,
                docMetaPayload,
                invertedPayload,
                attachmentPayload,
                externalPayload,
                aliasesPayload
            ] = await Promise.all([
                fetchJson(APP_CONFIG.DATA_URLS.SEARCH_MANIFEST, controller.signal),
                fetchJson(APP_CONFIG.DATA_URLS.SITEGRAPH_DOC_META, controller.signal),
                fetchJson(APP_CONFIG.DATA_URLS.SITEGRAPH_INVERTED_INDEX, controller.signal),
                fetchJson(APP_CONFIG.DATA_URLS.SITEGRAPH_ATTACHMENT_INDEX, controller.signal),
                fetchJson(APP_CONFIG.DATA_URLS.SITEGRAPH_EXTERNAL_INDEX, controller.signal),
                fetchJson(APP_CONFIG.DATA_URLS.QUERY_ALIASES, controller.signal),
            ]);

            const parsedManifest = parseSitegraphManifest(manifestPayload, APP_CONFIG.DATA_URLS.SEARCH_MANIFEST);
            const parsedBundle: SitegraphIndexBundle = {
                manifest: parsedManifest,
                docMeta: parseSitegraphDocMeta(docMetaPayload, APP_CONFIG.DATA_URLS.SITEGRAPH_DOC_META),
                invertedIndex: parseSitegraphInvertedIndex(invertedPayload, APP_CONFIG.DATA_URLS.SITEGRAPH_INVERTED_INDEX),
                attachmentIndex: parseSitegraphAttachmentIndex(attachmentPayload, APP_CONFIG.DATA_URLS.SITEGRAPH_ATTACHMENT_INDEX),
                externalIndex: parseSitegraphExternalIndex(externalPayload, APP_CONFIG.DATA_URLS.SITEGRAPH_EXTERNAL_INDEX),
                queryAliases: aliasesPayload as Record<string, unknown>
            };

            setManifest(parsedManifest);
            setBundle(parsedBundle);
            setOptionalUnavailable([]);
            setError(null);
        };

        load()
            .catch(err => {
                if (err instanceof DOMException && err.name === 'AbortError') {
                    return;
                }
                console.error(err);
                setBundle(null);
                setManifest(null);
                setOptionalUnavailable([]);
                setError(err instanceof Error ? err.message : '无法加载 JWC sitegraph 搜索索引');
            })
            .finally(() => {
                if (!controller.signal.aborted) {
                    setLoading(false);
                }
            });

        return () => controller.abort();
    }, []);

    return { bundle, manifest, optionalUnavailable, loading, error };
}
