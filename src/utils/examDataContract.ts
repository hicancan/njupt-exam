import { Exam, Manifest } from '@/types';

export class DataContractError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'DataContractError';
    }
}

const isRecord = (value: unknown): value is Record<string, unknown> => {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
};

const typeName = (value: unknown): string => {
    if (Array.isArray(value)) return 'array';
    if (value === null) return 'null';
    return typeof value;
};

const readRequiredString = (
    record: Record<string, unknown>,
    key: string,
    label: string
): string => {
    const value = record[key];
    if (typeof value !== 'string' || value.trim() === '') {
        throw new DataContractError(`${label}.${key} must be a non-empty string`);
    }
    return value;
};

const readRequiredNumber = (
    record: Record<string, unknown>,
    key: string,
    label: string
): number => {
    const value = record[key];
    if (typeof value !== 'number' || !Number.isFinite(value)) {
        throw new DataContractError(`${label}.${key} must be a finite number`);
    }
    return value;
};

const assertPositiveNumber = (value: number, key: string, label: string) => {
    if (value <= 0) {
        throw new DataContractError(`${label}.${key} must be greater than 0`);
    }
};

const assertOptionalStringOrNull = (
    record: Record<string, unknown>,
    key: string,
    label: string
) => {
    const value = record[key];
    if (value !== undefined && value !== null && typeof value !== 'string') {
        throw new DataContractError(`${label}.${key} must be a string or null`);
    }
};

const assertOptionalTimestamp = (
    record: Record<string, unknown>,
    key: string,
    label: string
) => {
    assertOptionalStringOrNull(record, key, label);

    const value = record[key];
    if (typeof value === 'string') {
        if (value.trim() === '') {
            throw new DataContractError(`${label}.${key} must not be empty when present`);
        }
        if (Number.isNaN(new Date(value).getTime())) {
            throw new DataContractError(`${label}.${key} must be a parseable date-time string`);
        }
    }
};

export const parseExamData = (payload: unknown, source = 'exam data'): Exam[] => {
    if (!Array.isArray(payload)) {
        throw new DataContractError(`${source} must be an array, got ${typeName(payload)}`);
    }

    const ids = new Set<string>();

    payload.forEach((item, index) => {
        const label = `${source}[${index}]`;
        if (!isRecord(item)) {
            throw new DataContractError(`${label} must be an object, got ${typeName(item)}`);
        }

        const id = readRequiredString(item, 'id', label);
        readRequiredString(item, 'class_name', label);
        readRequiredString(item, 'course_name', label);
        const duration = readRequiredNumber(item, 'duration_minutes', label);
        assertPositiveNumber(duration, 'duration_minutes', label);

        if (ids.has(id)) {
            throw new DataContractError(`${source} contains duplicate id: ${id}`);
        }
        ids.add(id);

        assertOptionalTimestamp(item, 'start_timestamp', label);
        assertOptionalTimestamp(item, 'end_timestamp', label);
        assertOptionalStringOrNull(item, 'parse_error', label);

        const start = item.start_timestamp;
        const end = item.end_timestamp;
        if ((start && !end) || (!start && end)) {
            throw new DataContractError(`${label} has incomplete time range`);
        }
    });

    return payload as Exam[];
};

export const parseManifest = (payload: unknown, source = 'data summary'): Manifest => {
    if (!isRecord(payload)) {
        throw new DataContractError(`${source} must be an object, got ${typeName(payload)}`);
    }

    readRequiredString(payload, 'generated_at', source);
    readRequiredNumber(payload, 'total_records', source);

    if (!Array.isArray(payload.files_processed) || payload.files_processed.some(item => typeof item !== 'string')) {
        throw new DataContractError(`${source}.files_processed must be a string array`);
    }

    assertOptionalStringOrNull(payload, 'source_url', source);
    assertOptionalStringOrNull(payload, 'source_title', source);

    return payload as unknown as Manifest;
};

export const assertManifestMatchesExams = (manifest: Manifest, exams: Exam[]) => {
    if (manifest.total_records !== exams.length) {
        throw new DataContractError(
            `data_summary.total_records=${manifest.total_records} does not match all_exams.length=${exams.length}`
        );
    }
};
