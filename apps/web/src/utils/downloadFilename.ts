import { APP_CONFIG } from '@/constants';

export const buildExamCalendarFilename = (className: string): string => {
    return `${APP_CONFIG.APP_NAME}-${className.trim()}.ics`;
};
