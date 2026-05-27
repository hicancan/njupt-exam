const CLASS_LOOKUP_PATTERN = /^[BFPQY]\d{2,}(?:\([A-Z0-9]+\))?$/;
const COMPLETE_CLASS_PATTERN = /^[BFPQY]\d{6}(?:\([A-Z0-9]+\))?$/;

export const normalizeClassQuery = (value: string): string => value.trim().toUpperCase();

export const isClassLookupQuery = (value: string): boolean => {
    return CLASS_LOOKUP_PATTERN.test(normalizeClassQuery(value));
};

export const isCompleteClassQuery = (value: string): boolean => {
    return COMPLETE_CLASS_PATTERN.test(normalizeClassQuery(value));
};

export const isExamHelperQuery = (value: string): boolean => value.trim() === '考试安排';
