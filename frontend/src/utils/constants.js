export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

export const SERVICE_CATEGORIES = [
    { value: 'grooming', label: 'Grooming', icon: '✂️', color: '#FF6584' },
    { value: 'vet', label: 'Vet Consultation', icon: '🩺', color: '#6C63FF' },
    { value: 'walking', label: 'Dog Walking', icon: '🦮', color: '#43D9AD' },
    { value: 'boarding', label: 'Pet Boarding', icon: '🏠', color: '#F6C90E' },
    { value: 'training', label: 'Training', icon: '🎾', color: '#3F72AF' },
];

export const BOOKING_STATUS_COLORS = {
    pending: 'bg-yellow-500/20 text-yellow-500',
    confirmed: 'bg-blue-500/20 text-blue-500',
    in_progress: 'bg-indigo-500/20 text-indigo-500',
    completed: 'bg-green-500/20 text-green-500',
    cancelled: 'bg-red-500/20 text-red-500',
    refunded: 'bg-slate-500/20 text-slate-500'
};

export const PET_SPECIES = ['dog', 'cat', 'bird', 'rabbit', 'fish', 'hamster', 'other'];
