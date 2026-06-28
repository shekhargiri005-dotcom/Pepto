import os

FRONTEND_SRC = r"c:\PROJECT\PEPto\frontend\src"

files = {
    "components/providers/ProviderCard.jsx": """import React from 'react';
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
""",
    "components/providers/ServiceCard.jsx": """import React from 'react';

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
""",
    "components/booking/BookingStatusBadge.jsx": """import React from 'react';
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
""",
    "components/booking/BookingCalendar.jsx": """import React from 'react';

const BookingCalendar = ({ availability, selectedDate, onSelectDate }) => {
    return (
        <div className="glass p-4 rounded-xl">
            <h3 className="text-lg font-bold mb-4">Select a Date & Time</h3>
            <p className="text-sm text-slate-400">Calendar component placeholder. Use react-calendar here.</p>
        </div>
    );
};
export default BookingCalendar;
""",
    "components/reviews/StarRating.jsx": """import React from 'react';

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
""",
    "components/reviews/ReviewCard.jsx": """import React from 'react';
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
""",
    "components/pets/PetCard.jsx": """import React from 'react';

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
""",
    "components/chat/ChatWidget.jsx": """import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const ChatWidget = () => {
    const [isOpen, setIsOpen] = useState(false);
    
    return (
        <div className="fixed bottom-6 right-6 z-50">
            <AnimatePresence>
                {isOpen && (
                    <motion.div 
                        initial={{ opacity: 0, y: 20, scale: 0.9 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 20, scale: 0.9 }}
                        className="glass w-[350px] h-[500px] mb-4 rounded-2xl border border-slate-700 flex flex-col overflow-hidden shadow-2xl"
                    >
                        <div className="bg-gradient-to-r from-[#6C63FF] to-[#FF6584] p-4 flex justify-between items-center text-white">
                            <div className="flex items-center gap-2">
                                <span className="text-2xl">🤖</span>
                                <div>
                                    <h3 className="font-bold">Pepto Assistant</h3>
                                    <p className="text-xs opacity-80">Online 24/7</p>
                                </div>
                            </div>
                            <button onClick={() => setIsOpen(false)} className="hover:bg-white/20 p-1 rounded">✕</button>
                        </div>
                        <div className="flex-1 p-4 overflow-y-auto flex flex-col gap-3 bg-[#0F0F1A]/80">
                            <div className="bg-[#1A1A2E] p-3 rounded-lg rounded-tl-none self-start max-w-[85%] text-sm text-slate-200">
                                Hi there! 🐾 I'm your Pepto AI assistant. How can I help you and your pet today?
                            </div>
                        </div>
                        <div className="p-3 border-t border-slate-800 bg-[#1A1A2E]">
                            <input 
                                type="text" 
                                placeholder="Type a message..." 
                                className="w-full bg-[#0F0F1A] border border-slate-700 rounded-full px-4 py-2 text-sm text-white outline-none focus:border-[#6C63FF] transition-colors"
                            />
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
            
            <button 
                onClick={() => setIsOpen(!isOpen)}
                className="w-14 h-14 rounded-full gradient-btn flex items-center justify-center text-white text-2xl shadow-lg hover:scale-110 transition-transform ml-auto relative"
            >
                {!isOpen && (
                    <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full animate-ping" />
                )}
                💬
            </button>
        </div>
    );
};
export default ChatWidget;
""",
    "components/ui/LoadingSkeleton.jsx": """import React from 'react';

export const CardSkeleton = () => (
    <div className="glass rounded-xl h-64 animate-pulse border border-slate-800">
        <div className="h-32 bg-slate-800/50 w-full" />
        <div className="p-4 space-y-3">
            <div className="h-4 bg-slate-800/50 rounded w-3/4" />
            <div className="h-4 bg-slate-800/50 rounded w-1/2" />
        </div>
    </div>
);
""",
    "components/ui/Modal.jsx": """import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const Modal = ({ isOpen, onClose, title, children }) => {
    return (
        <AnimatePresence>
            {isOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                    <motion.div 
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                    />
                    <motion.div 
                        initial={{ opacity: 0, y: 50, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 20, scale: 0.95 }}
                        className="glass relative w-full max-w-lg rounded-2xl border border-slate-700 p-6 shadow-2xl"
                    >
                        <div className="flex justify-between items-center mb-6">
                            <h2 className="text-xl font-bold text-white">{title}</h2>
                            <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">✕</button>
                        </div>
                        {children}
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    );
};
export default Modal;
""",
    "components/ui/ErrorBoundary.jsx": """import React from 'react';

class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen flex items-center justify-center bg-[#0F0F1A] text-white p-6 text-center">
                    <div className="glass p-10 rounded-2xl max-w-md">
                        <span className="text-5xl block mb-4">😵</span>
                        <h1 className="text-2xl font-bold mb-2">Oops! Something went wrong.</h1>
                        <p className="text-slate-400 mb-6 text-sm">{this.state.error?.message || "An unexpected error occurred."}</p>
                        <button onClick={() => window.location.reload()} className="gradient-btn px-6 py-2 rounded-full font-medium">Refresh Page</button>
                    </div>
                </div>
            );
        }
        return this.props.children;
    }
}
export default ErrorBoundary;
"""
}

for filepath, content in files.items():
    full_path = os.path.join(FRONTEND_SRC, filepath)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Frontend React components generated successfully.")
