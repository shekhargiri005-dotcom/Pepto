import React from 'react';

const PetCard = ({ pet, onEdit, onDelete }) => {
    return (
        <div className="glass p-4 rounded-xl flex items-center gap-4 border border-slate-700/50 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-16 h-16 bg-gradient-to-br from-transparent to-[#43D9AD]/10 -z-10 rounded-bl-full" />
            <div className="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center overflow-hidden shrink-0">
                {pet.photo_url ? (
                    <img src={pet.photo_url} alt={pet.name} className="w-full h-full object-cover" />
                ) : (
                    <span className="text-3xl">🐾</span>
                )}
            </div>
            <div className="flex-1">
                <h4 className="font-bold text-white text-lg">{pet.name}</h4>
                <p className="text-sm text-slate-400 capitalize">{pet.breed || pet.species} • {pet.age_years} yrs</p>
                
                <div className="mt-2 flex gap-2">
                    <button onClick={() => onEdit(pet)} className="text-xs text-[#6C63FF] hover:underline">Edit</button>
                    <button onClick={() => onDelete(pet.id)} className="text-xs text-red-400 hover:underline">Delete</button>
                </div>
            </div>
        </div>
    );
};
export default PetCard;
