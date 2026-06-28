import React from 'react';
import { BOOKING_STATUS_COLORS } from '../../utils/constants';

const BookingStatusBadge = ({ status }) => {
    const colorClass = BOOKING_STATUS_COLORS[status.toLowerCase()] || 'bg-slate-500/20 text-slate-500';
    return (
        <span className={`px-2 py-1 rounded-full text-xs font-medium uppercase tracking-wider ${colorClass}`}>
            {status}
        </span>
    );
};
export default BookingStatusBadge;
