import React from 'react';

const ServiceCard = ({ service, onBook }) => {
    return (
        <div className="glass p-4 rounded-xl flex justify-between items-center border border-slate-700/50 hover:border-[#6C63FF]/50 transition-colors">
            <div>
                <h4 className="font-bold text-white">{service.name}</h4>
                <p className="text-sm text-slate-400 mt-1">{service.description}</p>
                <div className="flex items-center gap-3 mt-3">
                    <span className="text-lg font-bold text-[#43D9AD]">₹{service.price}</span>
                    <span className="text-xs text-slate-500 bg-slate-800 px-2 py-1 rounded">{service.duration} mins</span>
                </div>
            </div>
            <button 
                onClick={() => onBook(service)}
                className="bg-[#6C63FF]/20 text-[#6C63FF] hover:bg-[#6C63FF] hover:text-white px-4 py-2 rounded-full font-medium transition-colors"
            >
                Select
            </button>
        </div>
    );
};
export default ServiceCard;
