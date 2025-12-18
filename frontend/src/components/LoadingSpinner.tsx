import React from "react";
import "../styles.css";
import { ParticleLoader } from "./ParticleLoader";

const LoadingSpinner: React.FC = () => {
    return (
        <div className="spinner-container">
            <div className="spinner-modal">
                <div className="logos-container">
                    <img src="/assets/evelta_com_favicon.png" alt="Evelta" className="spinner-logo logo-1" />
                    <img src="/assets/robocraze_com_favicon.png" alt="Robocraze" className="spinner-logo logo-2" />
                    <img src="/assets/robu_in_favicon.png" alt="Robu" className="spinner-logo logo-3" />
                    <img src="/assets/thinkrobotics_com_favicon.png" alt="ThinkRobotics" className="spinner-logo logo-4" />
                </div>
                <div className="spinner-text">Fetching Data</div>
                <div style={{ marginTop: "4px" }}>
                    <ParticleLoader />
                </div>
            </div>
        </div>
    );
};

export default LoadingSpinner;
