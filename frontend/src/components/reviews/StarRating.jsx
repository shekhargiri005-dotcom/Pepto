import React from 'react';

const StarRating = ({ value, onChange, size = 'text-base' }) => {
    return (
        <div className="flex gap-1">
            {[1, 2, 3, 4, 5].map((star) => (
                <span 
                    key={star}
                    onClick={() => onChange && onChange(star)}
                    className={`${size} ${onChange ? 'cursor-pointer' : ''} ${star <= value ? 'text-yellow-500' : 'text-slate-600'}`}
                >
                    ★
                </span>
            ))}
        </div>
    );
};
export default StarRating;
