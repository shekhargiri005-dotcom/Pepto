import React from 'react';
import { useParams } from 'react-router-dom';
const ProviderProfile = () => {
    const { id } = useParams();
    return <div className="p-8 mt-20"><h1 className="text-3xl font-bold">Provider Profile {id}</h1></div>;
};
export default ProviderProfile;
