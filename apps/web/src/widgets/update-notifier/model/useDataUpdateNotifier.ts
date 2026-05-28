import { useState, useEffect } from 'react';
import { APP_CONFIG } from '@/app/config/constants';

export function useDataUpdateNotifier() {
    const [newDataAvailable, setNewDataAvailable] = useState(false);

    useEffect(() => {
        if (!('BroadcastChannel' in window)) {
            return;
        }

        const channel = new BroadcastChannel(APP_CONFIG.UPDATE_CHANNEL);
        
        channel.addEventListener('message', (event) => {
            if (event.data && event.data.type === 'CACHE_UPDATED') {
                setNewDataAvailable(true);
            }
        });

        return () => {
            channel.close();
        };
    }, []);

    const reloadToUpdate = () => {
        window.dispatchEvent(new Event(APP_CONFIG.UPDATE_APPLY_EVENT));
    };

    return { newDataAvailable, reloadToUpdate };
}
