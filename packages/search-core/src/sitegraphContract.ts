import {
    SitegraphAttachment,
    SitegraphAttachmentSchema,
    SitegraphDocMeta,
    SitegraphDocMetaSchema,
    SitegraphExternalRecord,
    SitegraphExternalRecordSchema,
    SitegraphFullDocument,
    SitegraphFullDocumentSchema,
    SitegraphInvertedIndex,
    SitegraphInvertedIndexSchema,
    SitegraphSearchManifest,
    SitegraphSearchManifestSchema
} from '@njupt-search/contracts';
import { z } from 'zod';

export class SearchContractError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'SearchContractError';
    }
}

const MODEL_FIELD_PREFIX = ['l', 'l', 'm'].join('');
const TASK_FIELD_PREFIX = ['hy', 'task'].join('');
const LEGACY_FIELDS = new Set([
    MODEL_FIELD_PREFIX,
    `${MODEL_FIELD_PREFIX}_provider`,
    `${MODEL_FIELD_PREFIX}_schema_version`,
    'semantic_mode',
    'task_frames',
    `${MODEL_FIELD_PREFIX}_in_core_path`,
    `old_${TASK_FIELD_PREFIX}_removed`,
    'source_channel_production_enabled',
    'github_resource_production_enabled'
]);
const DOC_META_FORBIDDEN_FIELDS = new Set(['content', 'summary', 'attachments', 'provenance']);

const valueAtPath = (payload: unknown, path: PropertyKey[]): unknown => {
    let current = payload;
    for (const part of path) {
        if (current === null || current === undefined) return undefined;
        current = (current as Record<PropertyKey, unknown>)[part];
    }
    return current;
};

const formatZodIssues = (payload: unknown, error: z.ZodError): string => {
    return error.issues.map(issue => {
        const fieldPath = issue.path.join('.') || '<root>';
        const invalidValue = valueAtPath(payload, issue.path);
        return `${fieldPath}: ${issue.message}; value=${JSON.stringify(invalidValue)}`;
    }).join('; ');
};

const parseArray = <T>(schema: z.ZodType<T>, payload: unknown, source: string): T[] => {
    try {
        return z.array(schema).parse(payload);
    } catch (e) {
        if (e instanceof z.ZodError) {
            throw new SearchContractError(`Validation failed for ${source}: ${formatZodIssues(payload, e)}`);
        }
        throw new SearchContractError(`Validation failed for ${source}: ${e instanceof Error ? e.message : String(e)}`);
    }
};

const assertNoLegacyFields = (payload: unknown, source: string, path = '$'): void => {
    if (Array.isArray(payload)) {
        payload.forEach((item, index) => assertNoLegacyFields(item, source, `${path}[${index}]`));
        return;
    }
    if (!payload || typeof payload !== 'object') return;
    for (const [key, value] of Object.entries(payload as Record<string, unknown>)) {
        if (LEGACY_FIELDS.has(key)) {
            throw new SearchContractError(`Validation failed for ${source}: ${path}.${key} is an obsolete search field`);
        }
        assertNoLegacyFields(value, source, `${path}.${key}`);
    }
};

export const parseSitegraphManifest = (payload: unknown, source = 'sitegraph manifest'): SitegraphSearchManifest => {
    try {
        assertNoLegacyFields(payload, source);
        const text = JSON.stringify(payload);
        if (text.includes('D:\\') || text.includes('D:/')) {
            throw new SearchContractError(`Validation failed for ${source}: public manifest must not expose local D: paths`);
        }
        return SitegraphSearchManifestSchema.parse(payload);
    } catch (e) {
        if (e instanceof z.ZodError) {
            throw new SearchContractError(`Validation failed for ${source}: ${formatZodIssues(payload, e)}`);
        }
        throw new SearchContractError(`Validation failed for ${source}: ${e instanceof Error ? e.message : String(e)}`);
    }
};

export const parseSitegraphDocMeta = (payload: unknown, source = 'sitegraph doc_meta'): SitegraphDocMeta[] => {
    assertNoLegacyFields(payload, source);
    const docs = parseArray(SitegraphDocMetaSchema, payload, source);
    const ids = new Set<string>();
    for (const item of docs) {
        if (ids.has(item.id)) throw new SearchContractError(`${source} contains duplicate id: ${item.id}`);
        for (const field of DOC_META_FORBIDDEN_FIELDS) {
            if (field in item) {
                throw new SearchContractError(`Validation failed for ${source}: doc_meta_light must not contain ${field}`);
            }
        }
        ids.add(item.id);
    }
    return docs;
};

export const parseSitegraphFullDocuments = (payload: unknown, source = 'sitegraph full shard'): SitegraphFullDocument[] => {
    assertNoLegacyFields(payload, source);
    return parseArray(SitegraphFullDocumentSchema, payload, source);
};

export const parseSitegraphAttachmentIndex = (payload: unknown, source = 'sitegraph attachment_index'): SitegraphAttachment[] => {
    return parseArray(SitegraphAttachmentSchema, payload, source);
};

export const parseSitegraphExternalIndex = (payload: unknown, source = 'sitegraph external_index'): SitegraphExternalRecord[] => {
    return parseArray(SitegraphExternalRecordSchema, payload, source);
};

export const parseSitegraphInvertedIndex = (payload: unknown, source = 'sitegraph inverted_index'): SitegraphInvertedIndex => {
    try {
        return SitegraphInvertedIndexSchema.parse(payload);
    } catch (e) {
        if (e instanceof z.ZodError) {
            throw new SearchContractError(`Validation failed for ${source}: ${formatZodIssues(payload, e)}`);
        }
        throw new SearchContractError(`Validation failed for ${source}: ${e instanceof Error ? e.message : String(e)}`);
    }
};
