import React from 'react';
import { useParams } from 'react-router-dom';
const BookingFlow = () => {
    const { providerId, serviceId } = useParams();
    return <div className="p-8 mt-20"><h1 className="text-3xl font-bold">Book Service</h1><p>Booking {serviceId} from {providerId}</p></div>;
};
export default BookingFlow;
