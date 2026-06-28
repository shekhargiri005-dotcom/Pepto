import React from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';

const ProviderCard = ({ provider }) => {
    const navigate = useNavigate();
    return (
        <motion.div 
            whileHover={{ y: -5 }}
            className="glass rounded-xl overflow-hidden cursor-pointer"
            onClick={() => navigate(`/provider/${provider.id}`)}
        >
            <div className="h-32 bg-gradient-to-r from-[#6C63FF] to-[#FF6584] relative">
                {provider.cover_image_url && (
                    <img src={provider.cover_image_url} alt="Cover" className="w-full h-full object-cover opacity-60" />
                )}
                <div className="absolute -bottom-8 left-4 w-16 h-16 rounded-full border-4 border-[#1A1A2E] bg-gray-800 overflow-hidden">
                    {provider.avatar_url ? (
                        <img src={provider.avatar_url} alt="Avatar" className="w-full h-full object-cover" />
                    ) : (
                        <div className="w-full h-full flex items-center justify-center text-xl font-bold">{provider.business_name[0]}</div>
                    )}
                </div>
            </div>
            <div className="p-5 pt-10">
                <div className="flex justify-between items-start">
                    <div>
                        <h3 className="font-bold text-lg text-white flex items-center gap-1">
                            {provider.business_name}
                            {provider.is_verified_business && <span className="text-blue-400 text-sm">✓</span>}
                        </h3>
                        <p className="text-sm text-slate-400">{provider.city}, {provider.state}</p>
                    </div>
                    <div className="flex items-center gap-1 bg-yellow-500/20 text-yellow-500 px-2 py-1 rounded text-sm">
                        <span>★</span> {provider.avg_rating}
                    </div>
                </div>
                
                <div className="mt-4 flex flex-wrap gap-2">
                    {provider.top_services?.map(s => (
                        <span key={s} className="text-xs bg-[#6C63FF]/20 text-[#6C63FF] px-2 py-1 rounded-full">{s}</span>
                    ))}
                </div>
                
                <div className="mt-6 flex justify-between items-center border-t border-slate-700/50 pt-4">
                    <div className="text-sm text-slate-300">
                        {provider.distance && <span>{provider.distance} km away</span>}
                    </div>
                    <button className="gradient-btn px-4 py-2 rounded-full text-sm font-medium text-white">Book Now</button>
                </div>
            </div>
        </motion.div>
    );
};
export default ProviderCard;
