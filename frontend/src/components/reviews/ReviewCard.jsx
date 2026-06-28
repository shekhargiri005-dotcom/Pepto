import React from 'react';
import StarRating from './StarRating';

const ReviewCard = ({ review }) => {
    return (
        <div className="glass p-5 rounded-xl border border-slate-700/50">
            <div className="flex justify-between items-start mb-3">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-slate-700 flex items-center justify-center text-white font-bold">
                        {review.reviewer_name?.[0] || '?'}
                    </div>
                    <div>
                        <h4 className="font-medium text-white">{review.reviewer_name}</h4>
                        <span className="text-xs text-slate-400">{new Date(review.created_at).toLocaleDateString()}</span>
                    </div>
                </div>
                <StarRating value={review.rating} />
            </div>
            <p className="text-sm text-slate-300 mt-2">{review.comment}</p>
            {review.provider_response && (
                <div className="mt-4 p-3 bg-[#1A1A2E] rounded border-l-2 border-[#6C63FF]">
                    <span className="text-xs font-bold text-[#6C63FF] uppercase">Provider Response</span>
                    <p className="text-sm text-slate-400 mt-1">{review.provider_response}</p>
                </div>
            )}
        </div>
    );
};
export default ReviewCard;
