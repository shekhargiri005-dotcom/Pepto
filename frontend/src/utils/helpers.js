export const formatCurrency = (amount, currency = 'INR') => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency }).format(amount);
};

export const getInitials = (name) => {
    if (!name) return '?';
    return name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2);
};

export const getStatusColor = (status) => {
    const colors = {
        pending: 'yellow',
        confirmed: 'blue',
        completed: 'green',
        cancelled: 'red'
    };
    return colors[status] || 'slate';
};
