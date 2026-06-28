import React from 'react';

export const CardSkeleton = () => (
    <div className="glass rounded-xl h-64 animate-pulse border border-slate-800">
        <div className="h-32 bg-slate-800/50 w-full" />
        <div className="p-4 space-y-3">
            <div className="h-4 bg-slate-800/50 rounded w-3/4" />
            <div className="h-4 bg-slate-800/50 rounded w-1/2" />
        </div>
    </div>
);
